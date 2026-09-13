import pytest
import asyncio
from decimal import Decimal
from datetime import datetime


@pytest.mark.asyncio
async def test_capital_ledger_initialization():
    from backend.finance.ledger import CapitalLedger
    ledger = CapitalLedger(starting_capital=50.0)
    assert ledger.current_balance == Decimal("50.00")
    assert ledger.survival_reserve == Decimal("12.50")
    assert ledger.operating_capital == Decimal("37.50")


@pytest.mark.asyncio
async def test_cannot_spend_reserve():
    from backend.finance.ledger import CapitalLedger
    ledger = CapitalLedger(starting_capital=50.0)
    can_spend, reason = ledger.can_spend(Decimal("40.00"))
    assert can_spend is False
    assert "reserve" in reason.lower() or "breach" in reason.lower()


@pytest.mark.asyncio
async def test_can_spend_within_operating():
    from backend.finance.ledger import CapitalLedger
    ledger = CapitalLedger(starting_capital=50.0)
    can_spend, reason = ledger.can_spend(Decimal("10.00"))
    assert can_spend is True


@pytest.mark.asyncio
async def test_transaction_updates_balance():
    from backend.finance.ledger import CapitalLedger
    from unittest.mock import AsyncMock, MagicMock
    ledger = CapitalLedger(starting_capital=50.0)
    mock_db = MagicMock()
    txn = await ledger.record_transaction(mock_db, "test-agent", "test", "credit", Decimal("5.00"))
    assert ledger.current_balance == Decimal("55.00")
    assert ledger.total_revenue == Decimal("5.00")


@pytest.mark.asyncio
async def test_risk_manager_blocks_reserve_spend():
    from backend.finance.ledger import CapitalLedger
    from backend.risk.manager import RiskManager
    from unittest.mock import AsyncMock, MagicMock
    ledger = CapitalLedger(starting_capital=50.0)
    risk = RiskManager(ledger)
    mock_db = MagicMock()
    approved, reason = await risk.evaluate_spend(mock_db, "agent-1", Decimal("40.00"), "test", "test")
    assert approved is False


@pytest.mark.asyncio
async def test_risk_manager_approves_small_spend():
    from backend.finance.ledger import CapitalLedger
    from backend.risk.manager import RiskManager
    from unittest.mock import AsyncMock, MagicMock
    ledger = CapitalLedger(starting_capital=50.0)
    risk = RiskManager(ledger)
    mock_db = MagicMock()
    approved, reason = await risk.evaluate_spend(mock_db, "agent-1", Decimal("1.00"), "test", "test")
    assert approved is True


@pytest.mark.asyncio
async def test_agent_factory_creates_agent():
    from backend.finance.ledger import CapitalLedger
    from backend.risk.manager import RiskManager
    from backend.agents.factory import AgentFactory
    from unittest.mock import AsyncMock, MagicMock, MagicMock
    from sqlalchemy.ext.asyncio import AsyncSession

    ledger = CapitalLedger(starting_capital=50.0)
    risk = RiskManager(ledger)
    factory = AgentFactory(risk)

    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.flush = AsyncMock()
    mock_db.add = lambda x: None
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    mock_db.execute = AsyncMock(return_value=mock_result)

    agent = await factory.create_agent(mock_db, "content", "test_strategy")
    assert agent.agent_type == "script"
    assert agent.strategy == "test_strategy"
    assert agent.status.value == "TESTING"


@pytest.mark.asyncio
async def test_evolution_reproduction_eligibility():
    from backend.finance.ledger import CapitalLedger
    from backend.risk.manager import RiskManager
    from backend.agents.factory import AgentFactory
    from backend.evolution.engine import EvolutionSystem
    from config.settings import settings
    from unittest.mock import AsyncMock, MagicMock, MagicMock
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, func

    settings.reproduction_min_profit = 10.0
    settings.reproduction_min_roi = 1.5
    settings.reproduction_min_success_rate = 0.6

    ledger = CapitalLedger(starting_capital=50.0)
    risk = RiskManager(ledger)
    factory = AgentFactory(risk)
    evolution = EvolutionSystem(None, risk, None)

    mock_db = AsyncMock(spec=AsyncSession)

    # First call: evaluate_reproduction finds the agent
    mock_result1 = MagicMock()
    from backend.models.database import Agent, AgentStatus
    from decimal import Decimal

    class MockAgent:
        id = "agent-1"
        status = AgentStatus.ALIVE
        lifetime_profit = Decimal("50.00")
        roi = 2.0
        success_rate = 0.8

    mock_agent = MockAgent()
    mock_result1.scalar_one_or_none.return_value = mock_agent

    # Second call: _count_active_agents returns 0
    mock_result2 = MagicMock()
    mock_result2.scalar_one.return_value = 0

    # Mock execute to return different results for different calls
    mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

    result = await evolution.evaluate_reproduction(mock_db, "agent-1")
    assert result["eligible"] is True
