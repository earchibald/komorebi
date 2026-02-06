"""LLM usage and budget API endpoints.

Provides cost visibility and budget management for the
Settings → Billing dashboard.
"""

from fastapi import APIRouter

from ..models.cost import BudgetConfig, UsageSummary
from ..services.cost_service import get_cost_service

router = APIRouter(prefix="/llm", tags=["llm-cost"])


@router.get("/usage", response_model=UsageSummary)
async def get_usage() -> UsageSummary:
    """Get current LLM usage summary for the billing period."""
    return get_cost_service().get_summary()


@router.get("/budget", response_model=BudgetConfig)
async def get_budget() -> BudgetConfig:
    """Get current budget configuration."""
    return get_cost_service().budget


@router.put("/budget", response_model=BudgetConfig)
async def update_budget(config: BudgetConfig) -> BudgetConfig:
    """Update budget configuration (cap, auto-downgrade, model)."""
    svc = get_cost_service()
    svc.budget = config
    return svc.budget
