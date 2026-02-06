"""LLM cost governance service.

Provides token counting (heuristic), cost estimation, budget
enforcement with auto-downgrade, and usage recording.

The CostService wraps every LLM call so that:
1. Tokens are counted (len/4 heuristic for MVP).
2. Usage is recorded in the ``llm_usage`` table.
3. Budget caps are enforced — when exceeded, subsequent calls
   auto-downgrade to a local model or raise ``BudgetExceeded``.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from ..models.cost import BudgetConfig, ModelUsage, UsageSummary

logger = logging.getLogger(__name__)

# Approximate cost per 1K tokens (USD) for common models.
# Only used for estimation — not billing.
_COST_PER_1K: dict[str, tuple[float, float]] = {
    # (input_per_1k, output_per_1k)
    "gpt-4": (0.03, 0.06),
    "gpt-4o": (0.005, 0.015),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3-opus": (0.015, 0.075),
    "claude-3-sonnet": (0.003, 0.015),
    "claude-3-haiku": (0.00025, 0.00125),
    # Local models are free
    "llama3": (0.0, 0.0),
    "llama3.1": (0.0, 0.0),
    "gemma": (0.0, 0.0),
    "mistral": (0.0, 0.0),
}


class BudgetExceeded(Exception):
    """Raised when the daily budget cap is exceeded."""

    def __init__(self, cap_usd: float, spent_usd: float) -> None:
        self.cap_usd = cap_usd
        self.spent_usd = spent_usd
        super().__init__(
            f"Budget exceeded: ${spent_usd:.4f} / ${cap_usd:.4f} daily cap"
        )


def count_tokens(text: str) -> int:
    """Heuristic token count: len(text) / 4.

    Accurate within ~15-20% for English text. Good enough for
    budget alerting; not for exact billing reconciliation.
    """
    return max(1, len(text) // 4)


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate cost in USD for a given model and token counts."""
    rates = _COST_PER_1K.get(model, (0.001, 0.002))  # conservative default
    input_cost = (input_tokens / 1000) * rates[0]
    output_cost = (output_tokens / 1000) * rates[1]
    return round(input_cost + output_cost, 6)


class CostService:
    """Middleware-style service for tracking and enforcing LLM costs.

    Usage::

        cost_svc = CostService()

        # Before calling LLM
        cost_svc.check_budget()  # raises BudgetExceeded if over cap

        # After calling LLM
        await cost_svc.record_usage(
            model="gpt-4",
            input_text="...",
            output_text="...",
            request_type="compact",
        )
    """

    def __init__(self, budget: Optional[BudgetConfig] = None) -> None:
        self._budget = budget or BudgetConfig()
        # In-memory accumulator (reset daily or from DB)
        self._daily_spent: float = 0.0
        self._usage_by_model: dict[str, ModelUsage] = {}
        self._last_reset: datetime = datetime.utcnow()

    @property
    def budget(self) -> BudgetConfig:
        return self._budget

    @budget.setter
    def budget(self, config: BudgetConfig) -> None:
        self._budget = config

    def check_budget(self) -> str | None:
        """Check if budget allows another request.

        Returns:
            The downgrade model name if budget exceeded and auto_downgrade
            is on, or None if budget is fine.

        Raises:
            BudgetExceeded: If cap exceeded and auto_downgrade is off.
        """
        self._maybe_reset()

        if self._budget.daily_cap_usd is None:
            return None  # No cap set

        if self._daily_spent < self._budget.daily_cap_usd:
            return None  # Under budget

        if self._budget.auto_downgrade:
            return self._budget.downgrade_model

        raise BudgetExceeded(self._budget.daily_cap_usd, self._daily_spent)

    async def record_usage(
        self,
        model: str,
        input_text: str,
        output_text: str,
        request_type: str = "unknown",
    ) -> ModelUsage:
        """Record a completed LLM call.

        Updates in-memory totals and writes to database.
        """
        self._maybe_reset()

        input_tokens = count_tokens(input_text)
        output_tokens = count_tokens(output_text)
        total_tokens = input_tokens + output_tokens
        cost = estimate_cost(model, input_tokens, output_tokens)

        # Update in-memory accumulator
        if model not in self._usage_by_model:
            self._usage_by_model[model] = ModelUsage(model_name=model)

        usage = self._usage_by_model[model]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.total_tokens += total_tokens
        usage.estimated_cost_usd += cost
        usage.request_count += 1

        self._daily_spent += cost

        # Persist to DB
        try:
            await self._persist(model, input_tokens, output_tokens, cost, request_type)
        except Exception:
            logger.warning("Failed to persist LLM usage to DB", exc_info=True)

        return ModelUsage(
            model_name=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            request_count=1,
        )

    def get_summary(self) -> UsageSummary:
        """Return current usage summary."""
        self._maybe_reset()
        models = list(self._usage_by_model.values())
        cap = self._budget.daily_cap_usd

        return UsageSummary(
            models=models,
            total_cost_usd=round(self._daily_spent, 6),
            budget_cap_usd=cap,
            budget_remaining_usd=round(cap - self._daily_spent, 6) if cap else None,
            throttled=cap is not None and self._daily_spent >= cap,
            period="daily",
        )

    def _maybe_reset(self) -> None:
        """Reset daily counters if the day has rolled over."""
        now = datetime.utcnow()
        if now.date() != self._last_reset.date():
            self._daily_spent = 0.0
            self._usage_by_model.clear()
            self._last_reset = now

    async def _persist(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        request_type: str,
    ) -> None:
        """Write usage row to llm_usage table."""
        from ..db.database import async_session, LLMUsageTable

        async with async_session() as session:
            row = LLMUsageTable(
                model_name=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=cost,
                request_type=request_type,
                created_at=datetime.utcnow(),
            )
            session.add(row)
            await session.commit()


# Module-level singleton — importable from anywhere
_cost_service: Optional[CostService] = None


def get_cost_service() -> CostService:
    """Get or create the global CostService singleton."""
    global _cost_service
    if _cost_service is None:
        cap = os.getenv("KOMOREBI_DAILY_CAP_USD")
        budget = BudgetConfig(
            daily_cap_usd=float(cap) if cap else None,
            auto_downgrade=os.getenv("KOMOREBI_AUTO_DOWNGRADE", "true").lower() == "true",
            downgrade_model=os.getenv("KOMOREBI_DOWNGRADE_MODEL", "llama3"),
        )
        _cost_service = CostService(budget=budget)
    return _cost_service
