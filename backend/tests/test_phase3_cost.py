"""Phase 3 tests: CostService, Billing API, Watcher utilities.

Covers:
- Token counting heuristic
- Cost estimation per model
- Budget enforcement and auto-downgrade
- CostService usage recording
- Billing API endpoints (usage, budget GET/PUT)
- Watcher utility functions (hash_prefix, should_ignore)
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.models.cost import BudgetConfig, ModelUsage, UsageSummary
from backend.app.services.cost_service import (
    CostService,
    BudgetExceeded,
    count_tokens,
    estimate_cost,
)
from backend.app.core.watcher import _hash_prefix, _should_ignore


# ══════════════════════════════════════════════════════════════
# Token Counting & Cost Estimation
# ══════════════════════════════════════════════════════════════

class TestTokenCounting:

    def test_count_tokens_basic(self):
        assert count_tokens("hello world!!") == 3  # 13 chars / 4

    def test_count_tokens_empty(self):
        assert count_tokens("") == 1  # min 1

    def test_count_tokens_short(self):
        assert count_tokens("hi") == 1  # min 1

    def test_count_tokens_long(self):
        text = "a" * 4000
        assert count_tokens(text) == 1000

    def test_estimate_cost_gpt4(self):
        cost = estimate_cost("gpt-4", 1000, 500)
        # gpt-4: 0.03/1K input + 0.06/1K output = 0.03 + 0.03 = 0.06
        assert cost == pytest.approx(0.06, abs=0.001)

    def test_estimate_cost_local_model_free(self):
        cost = estimate_cost("llama3", 10000, 5000)
        assert cost == 0.0

    def test_estimate_cost_unknown_model(self):
        cost = estimate_cost("unknown-model", 1000, 1000)
        assert cost > 0  # conservative defaults


# ══════════════════════════════════════════════════════════════
# CostService
# ══════════════════════════════════════════════════════════════

class TestCostService:

    def test_check_budget_no_cap(self):
        svc = CostService(BudgetConfig(daily_cap_usd=None))
        result = svc.check_budget()
        assert result is None

    def test_check_budget_under_cap(self):
        svc = CostService(BudgetConfig(daily_cap_usd=10.0))
        result = svc.check_budget()
        assert result is None

    def test_check_budget_exceeded_auto_downgrade(self):
        svc = CostService(BudgetConfig(
            daily_cap_usd=0.01,
            auto_downgrade=True,
            downgrade_model="llama3",
        ))
        svc._daily_spent = 0.02  # Over the cap
        result = svc.check_budget()
        assert result == "llama3"

    def test_check_budget_exceeded_no_downgrade(self):
        svc = CostService(BudgetConfig(
            daily_cap_usd=0.01,
            auto_downgrade=False,
        ))
        svc._daily_spent = 0.02
        with pytest.raises(BudgetExceeded):
            svc.check_budget()

    @pytest.mark.asyncio
    async def test_record_usage(self):
        svc = CostService(BudgetConfig(daily_cap_usd=None))
        usage = await svc.record_usage(
            model="llama3",
            input_text="hello world",
            output_text="response text here",
            request_type="compact",
        )
        assert usage.model_name == "llama3"
        assert usage.input_tokens > 0
        assert usage.output_tokens > 0

    @pytest.mark.asyncio
    async def test_record_usage_accumulates(self):
        svc = CostService(BudgetConfig(daily_cap_usd=None))
        await svc.record_usage("llama3", "input1", "output1")
        await svc.record_usage("llama3", "input2", "output2")
        summary = svc.get_summary()
        assert len(summary.models) == 1
        assert summary.models[0].request_count == 2

    @pytest.mark.asyncio
    async def test_record_usage_multiple_models(self):
        svc = CostService(BudgetConfig(daily_cap_usd=None))
        await svc.record_usage("llama3", "a", "b")
        await svc.record_usage("gpt-4", "c", "d")
        summary = svc.get_summary()
        assert len(summary.models) == 2

    def test_get_summary(self):
        svc = CostService(BudgetConfig(daily_cap_usd=5.0))
        summary = svc.get_summary()
        assert summary.total_cost_usd == 0.0
        assert summary.budget_cap_usd == 5.0
        assert summary.budget_remaining_usd == 5.0
        assert summary.throttled is False

    def test_budget_config_setter(self):
        svc = CostService()
        svc.budget = BudgetConfig(daily_cap_usd=1.0)
        assert svc.budget.daily_cap_usd == 1.0


# ══════════════════════════════════════════════════════════════
# Watcher Utility Functions
# ══════════════════════════════════════════════════════════════

class TestWatcherUtils:

    def test_should_ignore_git(self):
        assert _should_ignore("/repo/.git/objects/abc123") is True

    def test_should_ignore_pycache(self):
        assert _should_ignore("/repo/src/__pycache__/module.cpython-311.pyc") is True

    def test_should_ignore_node_modules(self):
        assert _should_ignore("/repo/frontend/node_modules/react/index.js") is True

    def test_should_not_ignore_normal(self):
        assert _should_ignore("/repo/src/main.py") is False

    def test_should_not_ignore_root(self):
        assert _should_ignore("/repo/README.md") is False

    def test_hash_prefix_nonexistent_file(self):
        result = _hash_prefix("/nonexistent/path/to/file.txt")
        assert result is None


# ══════════════════════════════════════════════════════════════
# Billing API Tests
# ══════════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def billing_client():
    """Create an async HTTP client for billing endpoints."""
    from backend.app.main import app
    from backend.app.db.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Reset the CostService singleton for clean test state
    import backend.app.services.cost_service as cs
    cs._cost_service = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    cs._cost_service = None


class TestBillingAPI:

    @pytest.mark.asyncio
    async def test_get_usage(self, billing_client):
        resp = await billing_client.get("/api/v1/llm/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "total_cost_usd" in data

    @pytest.mark.asyncio
    async def test_get_budget(self, billing_client):
        resp = await billing_client.get("/api/v1/llm/budget")
        assert resp.status_code == 200
        data = resp.json()
        assert "auto_downgrade" in data

    @pytest.mark.asyncio
    async def test_update_budget(self, billing_client):
        resp = await billing_client.put("/api/v1/llm/budget", json={
            "daily_cap_usd": 2.50,
            "auto_downgrade": True,
            "downgrade_model": "mistral",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["daily_cap_usd"] == 2.50
        assert data["downgrade_model"] == "mistral"

    @pytest.mark.asyncio
    async def test_get_budget_after_update(self, billing_client):
        await billing_client.put("/api/v1/llm/budget", json={
            "daily_cap_usd": 1.00,
            "auto_downgrade": False,
            "downgrade_model": "llama3",
        })
        resp = await billing_client.get("/api/v1/llm/budget")
        data = resp.json()
        assert data["daily_cap_usd"] == 1.00
        assert data["auto_downgrade"] is False


# ══════════════════════════════════════════════════════════════
# Pydantic Model Tests
# ══════════════════════════════════════════════════════════════

class TestCostModels:

    def test_model_usage_defaults(self):
        usage = ModelUsage(model_name="gpt-4")
        assert usage.input_tokens == 0
        assert usage.estimated_cost_usd == 0.0

    def test_usage_summary_defaults(self):
        summary = UsageSummary()
        assert summary.models == []
        assert summary.throttled is False
        assert summary.period == "daily"

    def test_budget_config_defaults(self):
        config = BudgetConfig()
        assert config.daily_cap_usd is None
        assert config.auto_downgrade is True
        assert config.downgrade_model == "llama3"
