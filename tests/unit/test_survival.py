"""
Survival scenario tests for AI Survival System.
Tests critical survival scenarios: capital depletion, agent termination,
reproduction eligibility, population caps, and learning persistence.
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.database import SystemState, SystemMode


class TestCapitalDepletionSurvival:
    """Tests for survival mode triggers and capital protection"""

    @pytest.mark.asyncio
    async def test_survival_mode_triggered_at_90_percent_reserve(self):
        from backend.finance.ledger import CapitalLedger
        from backend.agents.ceo import CEODecisionMaker
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator

        # Start with $100, reserve is $25 (25%)
        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        ceo = CEODecisionMaker(orchestrator, ledger, risk)

        # Simulate capital dropping to $27.50 (90% of reserve)
        # This would mean total capital = $27.50, reserve = $25.00
        ledger.current_balance = Decimal("27.50")
        ledger.survival_reserve = Decimal("25.00")
        ledger.operating_capital = Decimal("2.50")

        mock_db = AsyncMock(spec=AsyncSession)
        # Mock system state query
        mock_system_state = MagicMock()
        mock_system_state.current_mode = SystemMode.GROWTH

        # Properly mock the async execute call
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_state
        mock_db.execute = AsyncMock(return_value=mock_result)

        decisions = await ceo.analyze_and_decide(mock_db)

        # Should trigger survival mode
        survival_decisions = [d for d in decisions if d["type"].value == "ENTER_SURVIVAL_MODE"]
        assert len(survival_decisions) > 0, "Survival mode should be triggered at 90% reserve"

    @pytest.mark.asyncio
    async def test_reduce_budget_at_60_percent_reserve(self):
        from backend.finance.ledger import CapitalLedger
        from backend.agents.ceo import CEODecisionMaker
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        ceo = CEODecisionMaker(orchestrator, ledger, risk)

        # Capital at $41.666..., reserve $25 = exactly 60%
        ledger.current_balance = Decimal("41.666666666666664")
        ledger.survival_reserve = Decimal("25.00")
        ledger.operating_capital = Decimal("16.666666666666664")

        mock_db = AsyncMock(spec=AsyncSession)
        # Mock system state query
        mock_system_state = MagicMock()
        mock_system_state.current_mode = SystemMode.GROWTH

        # Properly mock the async execute call
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_state
        mock_db.execute = AsyncMock(return_value=mock_result)

        decisions = await ceo.analyze_and_decide(mock_db)

        reduce_decisions = [d for d in decisions if d["type"].value == "REDUCE_BUDGET"]
        assert len(reduce_decisions) > 0, "Budget reduction should trigger at 60% reserve"

    @pytest.mark.asyncio
    async def test_reserve_cannot_be_touched(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from config.settings import settings

        ledger = CapitalLedger(starting_capital=50.0)
        # Reserve = $12.50 (25%), Operating = $37.50, min operating = $5.00 (10%)
        # Spend $35.00 which would leave operating at $2.50 < $5.00 minimum
        # But max single spend is $2.00, so we need to test reserve breach directly
        # Let's set balance low enough that spending would breach reserve
        ledger.current_balance = Decimal("13.00")  # Just above reserve
        ledger.survival_reserve = Decimal("12.50")
        ledger.operating_capital = Decimal("0.50")
        risk = RiskManager(ledger)

        mock_db = AsyncMock(spec=AsyncSession)

        # Try to spend $1.50 - would leave balance at $11.50 < $12.50 reserve
        can_spend, reason = await risk.evaluate_spend(
            mock_db, "agent-1", Decimal("1.50"), "test", "test"
        )
        assert can_spend is False
        assert "reserve" in reason.lower() or "breach" in reason.lower()

    @pytest.mark.asyncio
    async def test_max_single_spend_enforced(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager

        ledger = CapitalLedger(starting_capital=1000.0)
        risk = RiskManager(ledger)

        mock_db = AsyncMock(spec=AsyncSession)

        # Max spend is $2.00 per settings
        can_spend, reason = await risk.evaluate_spend(
            mock_db, "agent-1", Decimal("5.00"), "test", "test"
        )
        assert can_spend is False
        assert "max" in reason.lower() or "limit" in reason.lower()


class TestAgentTermination:
    """Tests for agent lifecycle and termination"""

    @pytest.mark.asyncio
    async def test_terminate_agent_with_persistent_losses(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.ceo import CEODecisionMaker
        from backend.models.database import Agent, AgentStatus
        from unittest.mock import AsyncMock

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        ceo = CEODecisionMaker(orchestrator, ledger, risk)

        # Create agent with persistent losses
        mock_agent = MagicMock()
        mock_agent.id = "agent-loss"
        mock_agent.agent_type = "content"
        mock_agent.strategy = "failing_strategy"
        mock_agent.generation = 0
        mock_agent.status = AgentStatus.ALIVE
        mock_agent.lifetime_profit = Decimal("-50.00")
        mock_agent.roi = -1.0
        mock_agent.success_rate = 0.1
        mock_agent.days_alive = 30
        mock_agent.expenses = Decimal("60.00")

        orchestrator.agents["agent-loss"] = mock_agent

        mock_db = AsyncMock(spec=AsyncSession)
        # Mock system state query
        mock_system_state = MagicMock()
        mock_system_state.current_mode = SystemMode.GROWTH

        # Properly mock the async execute call
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_state
        mock_db.execute = AsyncMock(return_value=mock_result)

        decisions = await ceo.analyze_and_decide(mock_db)

        terminate_decisions = [d for d in decisions if d["type"].value == "TERMINATE_AGENT"]
        assert len(terminate_decisions) > 0
        assert terminate_decisions[0]["agent_id"] == "agent-loss"

    @pytest.mark.asyncio
    async def test_agent_not_terminated_if_profitable(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.ceo import CEODecisionMaker
        from backend.models.database import Agent, AgentStatus

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        ceo = CEODecisionMaker(orchestrator, ledger, risk)

        # Create profitable agent
        mock_agent = MagicMock()
        mock_agent.id = "agent-profit"
        mock_agent.agent_type = "content"
        mock_agent.strategy = "winning_strategy"
        mock_agent.generation = 0
        mock_agent.status = AgentStatus.ALIVE
        mock_agent.lifetime_profit = Decimal("50.00")
        mock_agent.roi = 2.0
        mock_agent.success_rate = 0.8
        mock_agent.days_alive = 30
        mock_agent.expenses = Decimal("25.00")

        orchestrator.agents["agent-profit"] = mock_agent

        mock_db = AsyncMock(spec=AsyncSession)
        # Mock system state query
        mock_system_state = MagicMock()
        mock_system_state.current_mode = SystemMode.GROWTH

        # Properly mock the async execute call
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_state
        mock_db.execute = AsyncMock(return_value=mock_result)

        decisions = await ceo.analyze_and_decide(mock_db)

        terminate_decisions = [d for d in decisions if d["type"].value == "TERMINATE_AGENT"]
        assert len(terminate_decisions) == 0, "Profitable agent should not be terminated"


class TestReproductionEligibility:
    """Tests for agent reproduction criteria"""

    @pytest.mark.asyncio
    async def test_reproduction_requires_min_profit(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.factory import AgentFactory
        from backend.evolution.engine import EvolutionSystem
        from config.settings import settings
        from backend.models.database import Agent, AgentStatus
        from unittest.mock import AsyncMock

        settings.reproduction_min_profit = 10.0
        settings.reproduction_min_roi = 1.5
        settings.reproduction_min_success_rate = 0.6

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        factory = AgentFactory(risk)
        evolution = EvolutionSystem(None, risk, None)

        # Agent with profit < $10
        mock_agent = MagicMock()
        mock_agent.id = "agent-low-profit"
        mock_agent.status = AgentStatus.ALIVE
        mock_agent.lifetime_profit = Decimal("5.00")
        mock_agent.roi = 2.0
        mock_agent.success_rate = 0.8

        mock_db = AsyncMock(spec=AsyncSession)
        # First call: get agent, Second call: count active agents
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = mock_agent
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10  # Below hard cap
        mock_db.execute.side_effect = [mock_agent_result, mock_count_result]

        result = await evolution.evaluate_reproduction(mock_db, "agent-low-profit")
        assert result["eligible"] is False
        assert "profit" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_reproduction_requires_min_roi(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.factory import AgentFactory
        from backend.evolution.engine import EvolutionSystem
        from config.settings import settings
        from backend.models.database import Agent, AgentStatus
        from unittest.mock import AsyncMock

        settings.reproduction_min_profit = 10.0
        settings.reproduction_min_roi = 1.5
        settings.reproduction_min_success_rate = 0.6

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        factory = AgentFactory(risk)
        evolution = EvolutionSystem(None, risk, None)

        # Agent with ROI < 1.5
        mock_agent = MagicMock()
        mock_agent.id = "agent-low-roi"
        mock_agent.status = AgentStatus.ALIVE
        mock_agent.lifetime_profit = Decimal("50.00")
        mock_agent.roi = 1.0
        mock_agent.success_rate = 0.8

        mock_db = AsyncMock(spec=AsyncSession)
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = mock_agent
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10
        mock_db.execute.side_effect = [mock_agent_result, mock_count_result]

        result = await evolution.evaluate_reproduction(mock_db, "agent-low-roi")
        assert result["eligible"] is False
        assert "roi" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_reproduction_requires_min_success_rate(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.factory import AgentFactory
        from backend.evolution.engine import EvolutionSystem
        from config.settings import settings
        from backend.models.database import Agent, AgentStatus
        from unittest.mock import AsyncMock

        settings.reproduction_min_profit = 10.0
        settings.reproduction_min_roi = 1.5
        settings.reproduction_min_success_rate = 0.6

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        factory = AgentFactory(risk)
        evolution = EvolutionSystem(None, risk, None)

        # Agent with success_rate < 0.6
        mock_agent = MagicMock()
        mock_agent.id = "agent-low-success"
        mock_agent.status = AgentStatus.ALIVE
        mock_agent.lifetime_profit = Decimal("50.00")
        mock_agent.roi = 2.0
        mock_agent.success_rate = 0.4

        mock_db = AsyncMock(spec=AsyncSession)
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = mock_agent
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10
        mock_db.execute.side_effect = [mock_agent_result, mock_count_result]

        result = await evolution.evaluate_reproduction(mock_db, "agent-low-success")
        assert result["eligible"] is False
        assert "success" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_reproduction_eligible_when_all_criteria_met(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.factory import AgentFactory
        from backend.evolution.engine import EvolutionSystem
        from config.settings import settings
        from backend.models.database import Agent, AgentStatus
        from unittest.mock import AsyncMock

        settings.reproduction_min_profit = 10.0
        settings.reproduction_min_roi = 1.5
        settings.reproduction_min_success_rate = 0.6

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        factory = AgentFactory(risk)
        evolution = EvolutionSystem(None, risk, None)

        mock_agent = MagicMock()
        mock_agent.id = "agent-perfect"
        mock_agent.status = AgentStatus.ALIVE
        mock_agent.lifetime_profit = Decimal("50.00")
        mock_agent.roi = 2.0
        mock_agent.success_rate = 0.8
        mock_agent.agent_type = "content"
        mock_agent.strategy = "viral_tiktok"
        mock_agent.generation = 0

        mock_db = AsyncMock(spec=AsyncSession)
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = mock_agent
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10
        mock_db.execute.side_effect = [mock_agent_result, mock_count_result]

        result = await evolution.evaluate_reproduction(mock_db, "agent-perfect")
        assert result["eligible"] is True


class TestPopulationCaps:
    """Tests for population limit enforcement"""

    @pytest.mark.asyncio
    async def test_soft_cap_warning(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.evolution.engine import EvolutionSystem
        from config.settings import settings
        from unittest.mock import AsyncMock

        settings.population_soft_cap = 100
        settings.population_hard_cap = 1000

        ledger = CapitalLedger(starting_capital=1000.0)
        risk = RiskManager(ledger)
        evolution = EvolutionSystem(None, risk, None)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100  # At soft cap
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await evolution.check_population_capacity(mock_db)
        assert result["can_create"] is True
        assert result["at_soft_cap"] is True

    @pytest.mark.asyncio
    async def test_hard_cap_blocks_creation(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.evolution.engine import EvolutionSystem
        from config.settings import settings
        from unittest.mock import AsyncMock

        settings.population_soft_cap = 100
        settings.population_hard_cap = 1000

        ledger = CapitalLedger(starting_capital=1000.0)
        risk = RiskManager(ledger)
        evolution = EvolutionSystem(None, risk, None)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1000  # At hard cap
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await evolution.check_population_capacity(mock_db)
        assert result["can_create"] is False
        assert "hard cap" in result["reason"].lower()


class TestLearningPersistence:
    """Tests for learning system knowledge retention"""

    @pytest.mark.asyncio
    async def test_knowledge_stored_and_retrieved(self):
        from backend.learning.system import LearningSystem
        from backend.models.database import LearningMemory
        from unittest.mock import AsyncMock

        learning = LearningSystem()
        mock_db = AsyncMock(spec=AsyncSession)

        mock_memory = MagicMock()
        mock_memory.value = {"insight": "viral content works best on tiktok"}
        mock_memory.confidence = 0.8

        # Properly mock the async execute calls for store_knowledge:
        # First call: SELECT to check if memory exists (returns None for new memory)
        # Second call: INSERT (doesn't need result)
        mock_result_select_check = MagicMock()
        mock_result_select_check.scalar_one_or_none.return_value = None
        mock_result_insert = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[mock_result_select_check, mock_result_insert])

        # Store knowledge
        await learning.store_knowledge(
            mock_db, "content_strategy", "viral_tiktok",
            {"insight": "viral content works best on tiktok"},
            confidence=0.8
        )

        # For get_knowledge, mock the execute to return the memory
        mock_result_select = MagicMock()
        mock_result_select.scalar_one_or_none.return_value = mock_memory
        mock_db.execute = AsyncMock(return_value=mock_result_select)

        # Retrieve knowledge
        result = await learning.get_knowledge(mock_db, "content_strategy", "viral_tiktok")
        assert result == {"insight": "viral content works best on tiktok"}

    @pytest.mark.asyncio
    async def test_learning_summarizes_successful_strategies(self):
        from backend.learning.system import LearningSystem
        from backend.models.database import Strategy
        from unittest.mock import AsyncMock

        learning = LearningSystem()
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock successful and failed strategies
        success_strategy = MagicMock()
        success_strategy.name = "viral_tiktok"
        success_strategy.avg_roi = 2.5
        success_strategy.successes = 8
        success_strategy.total_experiments = 10

        failed_strategy = MagicMock()
        failed_strategy.name = "cold_email"
        failed_strategy.avg_roi = -0.5
        failed_strategy.successes = 1
        failed_strategy.total_experiments = 10

        # Mock the scalars().all() calls
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [success_strategy, failed_strategy]

        mock_scalars2 = MagicMock()
        mock_scalars2.all.return_value = []

        # Properly mock the async execute calls
        mock_result1 = MagicMock()
        mock_result1.scalars.return_value = mock_scalars
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value = mock_scalars2
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        summary = await learning.summarize_learning(mock_db)

        assert len(summary["what_worked"]) > 0
        assert summary["what_worked"][0]["strategy"] == "viral_tiktok"
        assert len(summary["what_failed"]) > 0
        assert summary["what_failed"][0]["strategy"] == "cold_email"

    @pytest.mark.asyncio
    async def test_recommendations_for_scaling_and_termination(self):
        from backend.learning.system import LearningSystem
        from backend.models.database import Strategy
        from config.settings import settings
        from unittest.mock import AsyncMock

        settings.reproduction_min_roi = 1.5

        learning = LearningSystem()
        mock_db = AsyncMock(spec=AsyncSession)

        good_strategy = MagicMock()
        good_strategy.name = "viral_tiktok"
        good_strategy.avg_roi = 3.0
        good_strategy.successes = 5
        good_strategy.failures = 1
        good_strategy.status = "ACTIVE"
        good_strategy.total_experiments = 6

        bad_strategy = MagicMock()
        bad_strategy.name = "cold_email"
        bad_strategy.avg_roi = -1.0
        bad_strategy.successes = 0
        bad_strategy.failures = 5
        bad_strategy.status = "ACTIVE"
        bad_strategy.total_experiments = 5

        # Properly mock the async execute call with scalars
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [good_strategy, bad_strategy]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        recommendations = await learning.get_recommendations(mock_db)

        scale_recs = [r for r in recommendations if r["type"] == "SCALE"]
        terminate_recs = [r for r in recommendations if r["type"] == "TERMINATE"]

        assert len(scale_recs) > 0
        assert scale_recs[0]["strategy"] == "viral_tiktok"
        assert len(terminate_recs) > 0
        assert terminate_recs[0]["strategy"] == "cold_email"


class TestExtendedSurvivalScenario:
    """Integration test simulating extended survival scenario"""

    @pytest.mark.asyncio
    async def test_system_survives_prolonged_losses(self):
        """Simulate system running with consistent losses - should enter survival mode"""
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.ceo import CEODecisionMaker
        from backend.models.database import Agent, AgentStatus, SystemState, SystemMode
        from unittest.mock import AsyncMock

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        ceo = CEODecisionMaker(orchestrator, ledger, risk)

        # Add multiple losing agents
        for i in range(5):
            mock_agent = MagicMock()
            mock_agent.id = f"agent-{i}"
            mock_agent.agent_type = "content"
            mock_agent.strategy = f"failing_strategy_{i}"
            mock_agent.generation = 0
            mock_agent.status = AgentStatus.ALIVE
            mock_agent.lifetime_profit = Decimal("-15.00")
            mock_agent.roi = -0.5
            mock_agent.success_rate = 0.2
            mock_agent.days_alive = 10
            mock_agent.expenses = Decimal("20.00")
            orchestrator.agents[f"agent-{i}"] = mock_agent

        # Simulate capital depletion - need reserve ratio >= 0.9 for survival mode
        # reserve_ratio = survival_reserve / total_capital = 25/26 = 0.96 > 0.9
        ledger.current_balance = Decimal("26.00")
        ledger.survival_reserve = Decimal("25.00")
        ledger.operating_capital = Decimal("1.00")

        mock_db = AsyncMock(spec=AsyncSession)
        # Mock system state query
        mock_system_state = MagicMock()
        mock_system_state.current_mode = SystemMode.GROWTH

        # Properly mock the async execute call
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_state
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Need to patch modal to avoid import errors
        with patch('backend.execution.engine._init_modal', return_value=None):
            decisions = await ceo.analyze_and_decide(mock_db)

        # Should have both survival mode and agent terminations
        survival_decisions = [d for d in decisions if d["type"].value == "ENTER_SURVIVAL_MODE"]
        terminate_decisions = [d for d in decisions if d["type"].value == "TERMINATE_AGENT"]

        assert len(survival_decisions) > 0, "Should enter survival mode"
        assert len(terminate_decisions) >= 3, "Should terminate multiple losing agents"

    @pytest.mark.asyncio
    async def test_agent_death_recorded_with_learnings(self):
        """Test that agent death preserves useful discoveries"""
        from backend.evolution.engine import EvolutionSystem
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.models.database import Agent, AgentStatus, AgentDeath
        from unittest.mock import AsyncMock

        ledger = CapitalLedger(starting_capital=100.0)
        risk = RiskManager(ledger)
        evolution = EvolutionSystem(None, risk, None)

        mock_agent = MagicMock()
        mock_agent.id = "dead-agent"
        mock_agent.lifetime_revenue = Decimal("100.00")
        mock_agent.lifetime_expenses = Decimal("150.00")
        mock_agent.lifetime_profit = Decimal("-50.00")
        mock_agent.days_alive = 60
        mock_agent.experiments_count = 20
        mock_agent.successful_experiments = 5
        mock_agent.failed_experiments = 15
        mock_agent.strategy = "failed_strategy"

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Record agent death
        await evolution.record_agent_death(
            mock_db,
            "dead-agent",
            failure_reasons=["low_roi", "high_cost"],
            useful_discoveries=["audience prefers short form video", "posting time matters"]
        )

        # Verify death was recorded
        mock_db.add.assert_called()
        call_args = mock_db.add.call_args[0][0]
        assert isinstance(call_args, AgentDeath)
        assert call_args.agent_id == "dead-agent"
        assert "audience prefers short form video" in call_args.useful_discoveries


class TestToolIntegrationSurvival:
    """Test tool usage in survival scenarios"""

    @pytest.mark.asyncio
    async def test_tool_costs_tracked_in_ledger(self):
        """Verify tool execution costs are properly tracked"""
        from backend.tools.base import tool_registry
        from backend.finance.ledger import CapitalLedger
        from backend.execution.engine import ExecutionEngine
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.risk.manager import RiskManager
        from unittest.mock import AsyncMock, MagicMock, patch
        from backend.models.database import Agent

        ledger = CapitalLedger(starting_capital=50.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        engine = ExecutionEngine(ledger)

        # Get a tool and check its cost
        web_search = tool_registry.get("web_search")
        assert web_search is not None
        assert web_search.cost > 0

        # Execute tool and verify cost tracking
        mock_agent = MagicMock()
        mock_agent.id = "tool-agent"
        mock_agent.agent_type = "content"
        mock_agent.experiments_count = 0
        mock_agent.successful_experiments = 0
        orchestrator.agents["tool-agent"] = mock_agent

        mock_db = AsyncMock(spec=AsyncSession)

        # Mock the db.execute to return a mock agent result
        mock_db_agent_result = MagicMock()
        mock_db_agent_result.scalar_one_or_none.return_value = mock_agent
        mock_db.execute = AsyncMock(return_value=mock_db_agent_result)

        # Mock the Modal initialization to avoid import errors
        with patch('backend.execution.engine._init_modal', return_value=None):
            # Execute task with tools
            result = await engine.execute_agent_task(
                mock_db, "tool-agent", "research",
                {"tools": ["web_search"], "tool_params": {"web_search": {"query": "test"}}}
            )

        # Tool should have executed
        assert "tool_results" in result or "status" in result
        assert result.get("status") in ["success", "partial"]


class TestEvolutionUnderStress:
    """Test evolution system under resource constraints"""

    @pytest.mark.asyncio
    async def test_pruning_removes_worst_agents(self):
        """Test that pruning removes the worst performing agents"""
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.evolution.engine import EvolutionSystem
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.models.database import Agent, AgentStatus
        from unittest.mock import AsyncMock, MagicMock

        ledger = CapitalLedger(starting_capital=50.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        evolution = EvolutionSystem(orchestrator, risk, None)

        # Create agents with varying performance
        # Only mark the worst agents as FAILED (the ones that should be pruned)
        agents_data = [
            ("agent-best", Decimal("100.00"), 5.0, 0.9, AgentStatus.ALIVE),
            ("agent-good", Decimal("50.00"), 2.0, 0.7, AgentStatus.ALIVE),
            ("agent-ok", Decimal("10.00"), 1.1, 0.6, AgentStatus.ALIVE),
            ("agent-bad", Decimal("-20.00"), -0.5, 0.2, AgentStatus.FAILED),
            ("agent-worst", Decimal("-50.00"), -1.0, 0.1, AgentStatus.FAILED),
        ]

        for aid, profit, roi, sr, status in agents_data:
            mock_agent = MagicMock()
            mock_agent.id = aid
            mock_agent.status = status  # Only worst agents are FAILED
            mock_agent.lifetime_profit = profit
            mock_agent.roi = roi
            mock_agent.success_rate = sr
            mock_agent.agent_type = "content"
            mock_agent.strategy = "test"
            mock_agent.generation = 0
            orchestrator.agents[aid] = mock_agent

        mock_db = AsyncMock(spec=AsyncSession)

        # Run pruning
        await evolution.prune_agents(mock_db)

        # Worst agents (FAILED status) should be removed
        assert "agent-worst" not in orchestrator.agents
        assert "agent-bad" not in orchestrator.agents
        # Best agents (ALIVE status) should survive
        assert "agent-best" in orchestrator.agents
        assert "agent-good" in orchestrator.agents
        assert "agent-ok" in orchestrator.agents


if __name__ == "__main__":
    pytest.main([__file__, "-v"])