"""LLM cost governance models.

Token usage tracking, budget caps, and auto-downgrade
configuration for controlling LLM spend.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelUsage(BaseModel):
    """Token usage for a specific model."""

    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    request_count: int = 0


class UsageSummary(BaseModel):
    """Aggregated usage across all models for a period."""

    models: list[ModelUsage] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    budget_cap_usd: Optional[float] = None
    budget_remaining_usd: Optional[float] = None
    throttled: bool = False
    period: str = "daily"


class BudgetConfig(BaseModel):
    """Budget cap configuration."""

    daily_cap_usd: Optional[float] = Field(None, ge=0, description="Daily cost cap in USD")
    auto_downgrade: bool = Field(default=True, description="Auto-downgrade to local model when cap hit")
    downgrade_model: str = Field(default="llama3", description="Model to downgrade to")
