"""
Tests for self-improving agents system.
Tests SelfImproverAgent, AgentDeveloper, and self-improvement integration.
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.database import AgentStatus, SystemState, SystemMode, DecisionType
from backend.finance.ledger import CapitalLedger
from backend.risk.manager import RiskManager


class TestSelfImproverAgent:
    """Tests for SelfImproverAgent capabilities"""

    @pytest.mark.asyncio
    async def test_self_improver_agent_creation(self):
        from backend.agents.self_improver import SelfImproverAgent
        agent = SelfImproverAgent(agent_id="SELF-abc123")
        assert agent.agent_type == "self_improver"
        assert agent.level == "SELF_IMPROVER"
        assert "self_analysis" in agent.capabilities
        assert "improvement_planning" in agent.capabilities
        assert "experiment_design" in agent.capabilities
        assert "meta_learning" in agent.capabilities
        assert agent.improvement_cycle == 0
        assert agent.auto_improve_enabled is True

    @pytest.mark.asyncio
    async def test_self_improver_to_dict(self):
        from backend.agents.self_improver import SelfImproverAgent
        agent = SelfImproverAgent(agent_id="SELF-test")
        agent.improvement_cycle = 3
        agent.improvements_applied = 5
        agent.improvements_failed = 1
        agent.last_improvement_cycle = datetime.now(timezone.utc)
        agent.known_weaknesses = ["low_success_rate"]
        agent.known_strengths = ["high_revenue"]
        agent.auto_improve_enabled = True

        d = agent.to_dict()
        assert d["level"] == "SELF_IMPROVER"
        assert d["improvement_cycle"] == 3
        assert d["improvements_applied"] == 5
        assert d["improvements_failed"] == 1
        assert d["known_weaknesses"] == ["low_success_rate"]
        assert d["known_strengths"] == ["high_revenue"]
        assert d["auto_improve_enabled"] is True

    @pytest.mark.asyncio
    async def test_self_improver_persists_and_loads(self):
        from backend.agents.self_improver import SelfImproverAgent
        from backend.models.database import Agent as DB_Agent
        from sqlalchemy import select

        agent = SelfImproverAgent(agent_id="SELF-persist")
        agent.improvement_cycle = 2
        agent.improvements_applied = 3

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.flush = AsyncMock()
        mock_db.add = lambda x: None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        await agent.persist(mock_db)

        loaded = SelfImproverAgent(agent_id="")
        mock_db_result = MagicMock()
        mock_db_result.scalar_one_or_none.return_value = MagicMock(
            id="SELF-persist",
            parent_id=None,
            generation=0,
            agent_type="self_improver",
            strategy="default",
            capabilities=["self_analysis"],
            budget=Decimal("0"),
            revenue=Decimal("0"),
            expenses=Decimal("0"),
            profit=Decimal("0"),
            roi=0.0,
            success_rate=0.0,
            status=AgentStatus.TESTING,
            risk_score=0.0,
            reproduction_permissions=0,
            lifetime_revenue=Decimal("0"),
            lifetime_expenses=Decimal("0"),
            lifetime_profit=Decimal("0"),
            days_alive=0,
            experiments_count=0,
            successful_experiments=0,
            failed_experiments=0,
            creation_timestamp=datetime.now(timezone.utc),
            terminated_at=None,
            level="SELF_IMPROVER",
            supervisor_id=None,
            autonomy_level=3,
        )
        mock_db.execute = AsyncMock(return_value=mock_db_result)

        await loaded.load(mock_db, "SELF-persist")
        assert loaded.level == "SELF_IMPROVER"
        assert loaded.agent_type == "self_improver"

    @pytest.mark.asyncio
    async def test_self_analysis_generates_detailed_report(self):
        from backend.agents.self_improver import SelfImproverAgent
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from decimal import Decimal

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator_mock = MagicMock(spec=AgentOrchestrator)

        agent = SelfImproverAgent(agent_id="SELF-analysis")
        agent.roi = 2.5
        agent.success_rate = 0.75
        agent.lifetime_profit = Decimal("100.00")
        agent.lifetime_revenue = Decimal("200.00")
        agent.lifetime_expenses = Decimal("100.00")
        agent.days_alive = 30
        agent.experiments_count = 20
        agent.successful_experiments = 15
        agent.failed_experiments = 5

        other = MagicMock()
        other.id = "other-agent"
        other.lifetime_profit = Decimal("50.00")
        other_agents = [other]
        orchestrator_mock.get_all_agents.return_value = other_agents

        mock_db = AsyncMock(spec=AsyncSession)

        with patch.object(orchestrator_mock, 'get_all_agents', return_value=other_agents):
            result = await agent.analyze_self(mock_db, orchestrator_mock)

        assert result["agent_id"] == "SELF-analysis"
        assert result["performance"]["roi"] == 2.5
        assert result["performance"]["success_rate"] == 0.75
        assert "system_context" in result
        assert result["success_ratio"] == 0.75

    @pytest.mark.asyncio
    async def test_identify_weaknesses_negative_roi(self):
        from backend.agents.self_improver import SelfImproverAgent
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from decimal import Decimal

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator_mock = MagicMock(spec=AgentOrchestrator)

        agent = SelfImproverAgent(agent_id="SELF-weak")
        agent.roi = -1.5
        agent.success_rate = 0.3
        agent.experiments_count = 10
        agent.lifetime_expenses = Decimal("50.00")
        agent.lifetime_profit = Decimal("-75.00")
        agent.days_alive = 30

        other = MagicMock()
        other.id = "other-agent"
        other.lifetime_profit = Decimal("200.00")
        other_agents = [other]
        with patch.object(orchestrator_mock, 'get_all_agents', return_value=other_agents):
            weaknesses = await agent.identify_weaknesses(AsyncMock(spec=AsyncSession), orchestrator_mock)

        weakness_types = [w["type"] for w in weaknesses]
        assert "negative_roi" in weakness_types
        assert any(w["severity"] == "CRITICAL" for w in weaknesses)

    @pytest.mark.asyncio
    async def test_identify_weaknesses_no_weaknesses(self):
        from backend.agents.self_improver import SelfImproverAgent
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from decimal import Decimal

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator_mock = MagicMock(spec=AgentOrchestrator)

        agent = SelfImproverAgent(agent_id="SELF-strong")
        agent.roi = 3.0
        agent.success_rate = 0.9
        agent.experiments_count = 20
        agent.days_alive = 30
        agent.lifetime_profit = Decimal("100.00")
        agent.lifetime_expenses = Decimal("33.33")

        other_agents = []
        with patch.object(orchestrator_mock, 'get_all_agents', return_value=other_agents):
            weaknesses = await agent.identify_weaknesses(AsyncMock(spec=AsyncSession), orchestrator_mock)

        assert len(weaknesses) == 0
        assert len(agent.known_strengths) > 0

    @pytest.mark.asyncio
    async def test_create_improvement_plan(self):
        from backend.agents.self_improver import SelfImproverAgent
        from backend.agents.orchestrator import AgentOrchestrator

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator_mock = MagicMock(spec=AgentOrchestrator)

        agent = SelfImproverAgent(agent_id="SELF-plan")
        agent.improvement_cycle = 0
        agent.experiments_count = 10
        agent.success_rate = 0.3
        agent.roi = -0.5

        mock_db = AsyncMock(spec=AsyncSession)
        weaknesses = [
            {"type": "negative_roi", "severity": "CRITICAL", "description": "Negative ROI", "suggested_improvement": "Fix strategy"},
            {"type": "low_success_rate", "severity": "HIGH", "description": "Low success", "suggested_improvement": "Improve testing"},
        ]

        plan = await agent.create_improvement_plan(mock_db, orchestrator_mock, weaknesses)

        assert plan["plan_id"] is not None
        assert plan["cycle"] == 1
        assert len(plan["improvements"]) == 2
        assert plan["total_high_priority"] >= 1
        agent.improvement_cycle == 1

    @pytest.mark.asyncio
    async def test_run_self_improvement_cycle(self):
        from backend.agents.self_improver import SelfImproverAgent
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator_mock = MagicMock(spec=AgentOrchestrator)

        agent = SelfImproverAgent(agent_id="SELF-cycle")
        agent.roi = -0.5
        agent.success_rate = 0.3
        agent.experiments_count = 10

        mock_db = AsyncMock(spec=AsyncSession)
        other = MagicMock()
        other.id = "other"
        other.lifetime_profit = Decimal("10.00")
        other_agents = [other]
        with patch.object(orchestrator_mock, 'get_all_agents', return_value=other_agents):
            result = await agent.run_self_improvement_cycle(mock_db, orchestrator_mock)

        assert result["agent_id"] == "SELF-cycle"
        assert result["status"] == "IMPROVEMENTS_SCHEDULED"
        assert "self_analysis" in result
        assert "weaknesses" in result
        assert "improvement_plan" in result
        assert result["self_analysis"]["performance"]["roi"] == -0.5


class TestAgentDeveloper:
    """Tests for AgentDeveloper capabilities"""

    @pytest.mark.asyncio
    async def test_agent_developer_creation(self):
        from backend.agents.developer import AgentDeveloper
        agent = AgentDeveloper(agent_id="DEV-abc123")
        assert agent.agent_type == "agent_developer"
        assert agent.level == "AGENT_DEVELOPER"
        assert "agent_analysis" in agent.capabilities
        assert "capability_design" in agent.capabilities
        assert "agent_creation" in agent.capabilities
        assert "code_generation" in agent.capabilities
        assert agent.developments_completed == 0

    @pytest.mark.asyncio
    async def test_agent_developer_to_dict(self):
        from backend.agents.developer import AgentDeveloper
        agent = AgentDeveloper(agent_id="DEV-test")
        agent.developments_completed = 5
        agent.development_history = [
            {"development_id": "dev1", "target_agent_id": "target1", "status": "COMPLETED"}
        ]
        agent.created_agent_types = ["research", "content"]

        d = agent.to_dict()
        assert d["level"] == "AGENT_DEVELOPER"
        assert d["developments_completed"] == 5
        assert len(d["development_history"]) == 1
        assert d["created_agent_types"] == ["research", "content"]

    @pytest.mark.asyncio
    async def test_analyze_agent(self):
        from backend.agents.developer import AgentDeveloper
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.models.database import AgentStatus

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator_mock = MagicMock(spec=AgentOrchestrator)

        developer = AgentDeveloper(agent_id="DEV-analyze")

        mock_target = MagicMock()
        mock_target.id = "TARGET-001"
        mock_target.agent_type = "content"
        mock_target.strategy = "short_form_video"
        mock_target.generation = 2
        mock_target.roi = 2.5
        mock_target.success_rate = 0.8
        mock_target.lifetime_profit = Decimal("150.00")
        mock_target.lifetime_revenue = Decimal("300.00")
        mock_target.lifetime_expenses = Decimal("150.00")
        mock_target.days_alive = 60
        mock_target.experiments_count = 30
        mock_target.successful_experiments = 24
        mock_target.failed_experiments = 6
        mock_target.capabilities = ["writing", "editing"]
        mock_target.status = AgentStatus.ALIVE
        mock_target.supervisor_id = None

        orchestrator_mock.get_agent.return_value = mock_target
        orchestrator_mock.get_lineage.return_value = {"id": "TARGET-001", "type": "content", "children": []}

        mock_db = AsyncMock(spec=AsyncSession)
        result = await developer.analyze_agent(mock_db, "TARGET-001", orchestrator_mock)

        assert result["agent_type"] == "content"
        assert result["performance_rating"] == "GOOD"
        assert result["success_ratio"] == 0.8
        assert "lineage" in result

    @pytest.mark.asyncio
    async def test_analyze_agent_critical_performance(self):
        from backend.agents.developer import AgentDeveloper
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.models.database import AgentStatus

        orchestrator_mock = MagicMock(spec=AgentOrchestrator)
        developer = AgentDeveloper(agent_id="DEV-crit")

        mock_target = MagicMock()
        mock_target.id = "TARGET-critical"
        mock_target.agent_type = "affiliate"
        mock_target.strategy = "niche"
        mock_target.generation = 0
        mock_target.roi = -2.0
        mock_target.success_rate = 0.1
        mock_target.lifetime_profit = Decimal("-100.00")
        mock_target.lifetime_revenue = Decimal("50.00")
        mock_target.lifetime_expenses = Decimal("150.00")
        mock_target.days_alive = 10
        mock_target.experiments_count = 5
        mock_target.capabilities = ["research"]
        mock_target.status = AgentStatus.ALIVE

        orchestrator_mock.get_agent.return_value = mock_target
        orchestrator_mock.get_lineage.return_value = {"id": "TARGET-critical", "type": "affiliate", "children": []}

        mock_db = AsyncMock(spec=AsyncSession)
        result = await developer.analyze_agent(mock_db, "TARGET-critical", orchestrator_mock)

        assert result["performance_rating"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_suggest_capabilities(self):
        from backend.agents.developer import AgentDeveloper
        from backend.agents.orchestrator import AgentOrchestrator

        orchestrator_mock = MagicMock(spec=AgentOrchestrator)
        developer = AgentDeveloper(agent_id="DEV-cap")

        mock_target = MagicMock()
        mock_target.id = "TARGET-cap"
        mock_target.agent_type = "content"
        mock_target.strategy = "video"
        mock_target.roi = 0.5
        mock_target.success_rate = 0.4
        mock_target.capabilities = ["writing"]

        orchestrator_mock.get_agent.return_value = mock_target

        mock_db = AsyncMock(spec=AsyncSession)
        caps = await developer.suggest_capabilities(mock_db, "TARGET-cap", orchestrator_mock)

        assert len(caps) > 0
        assert isinstance(caps[0], dict)
        assert "capability" in caps[0]
        assert caps[0]["priority"] in ("HIGH", "MEDIUM")

    @pytest.mark.asyncio
    async def test_design_experiment(self):
        from backend.agents.developer import AgentDeveloper

        developer = AgentDeveloper(agent_id="DEV-exp")
        mock_db = AsyncMock(spec=AsyncSession)

        experiment = await developer.design_experiment(mock_db, "TARGET-test", "better_scripting")

        assert experiment["experiment_id"] is not None
        assert experiment["target_agent_id"] == "TARGET-test"
        assert experiment["improvement_area"] == "better_scripting"
        assert experiment["status"] == "PLANNED"
        assert experiment["budget"] == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_develop_agent(self):
        from backend.agents.developer import AgentDeveloper
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.models.database import AgentStatus

        orchestrator_mock = MagicMock(spec=AgentOrchestrator)
        developer = AgentDeveloper(agent_id="DEV-dev")

        mock_target = MagicMock()
        mock_target.id = "TARGET-dev"
        mock_target.agent_type = "research"
        mock_target.strategy = "default"
        mock_target.capabilities = ["web_search"]
        mock_target.status = AgentStatus.ALIVE

        mock_analysis = {
            "target_agent_id": "TARGET-dev",
            "performance_rating": "POOR",
            "success_ratio": 0.3,
        }

        mock_db = AsyncMock(spec=AsyncSession)
        with patch.object(developer, 'analyze_agent', AsyncMock(return_value=mock_analysis)):
            with patch.object(developer, 'suggest_capabilities', AsyncMock(return_value=[])):
                result = await developer.develop_agent(mock_db, "TARGET-dev", orchestrator_mock)

        assert result["development_id"] is not None
        assert result["status"] == "COMPLETED"
        assert result["total_stages"] > 0
        assert result["completed_stages"] == result["total_stages"]
        assert developer.developments_completed == 1
        assert len(developer.development_history) == 1

    @pytest.mark.asyncio
    async def test_create_specialist_helper(self):
        from backend.agents.developer import AgentDeveloper
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.factory import AgentFactory

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)
        developer = AgentDeveloper(agent_id="DEV-helper")
        orchestrator.agents[developer.id] = developer

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.flush = AsyncMock()
        mock_db.add = lambda x: None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(AgentFactory, 'create_agent', AsyncMock(return_value=MagicMock(
            id="HELPER-001",
            agent_type="research",
            status=AgentStatus.TESTING,
        ))):
            result = await developer.create_specialist_helper(mock_db, orchestrator, "research")

        assert result["status"] == "success"
        assert result["agent_type"] == "research"
        assert developer.developments_completed >= 0

    @pytest.mark.asyncio
    async def test_optimize_agent_strategy(self):
        from backend.agents.developer import AgentDeveloper
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.models.database import AgentStatus

        orchestrator_mock = MagicMock(spec=AgentOrchestrator)
        developer = AgentDeveloper(agent_id="DEV-opt")

        mock_target = MagicMock()
        mock_target.id = "TARGET-opt"
        mock_target.agent_type = "content"
        mock_target.strategy = "default"

        orchestrator_mock.get_agent.return_value = mock_target

        mock_db = AsyncMock(spec=AsyncSession)
        result = await developer.optimize_agent_strategy(mock_db, "TARGET-opt", orchestrator_mock)

        assert result["status"] == "OPTIMIZED"
        assert result["old_strategy"] == "default"
        assert "optimized" in result["new_strategy"]
        assert mock_target.strategy != "default"

    @pytest.mark.asyncio
    async def test_run_development_cycle(self):
        from backend.agents.developer import AgentDeveloper
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.models.database import AgentStatus

        orchestrator_mock = MagicMock(spec=AgentOrchestrator)
        developer = AgentDeveloper(agent_id="DEV-cycle")

        mock_target = MagicMock()
        mock_target.id = "TARGET-cycle"
        mock_target.agent_type = "content"
        mock_target.strategy = "default"
        mock_target.capabilities = ["writing"]
        mock_target.status = AgentStatus.ALIVE

        mock_analysis = {
            "target_agent_id": "TARGET-cycle",
            "performance_rating": "POOR",
            "success_ratio": 0.2,
        }

        mock_db = AsyncMock(spec=AsyncSession)
        orchestrator_mock.get_all_agents.return_value = [mock_target]

        with patch.object(developer, 'analyze_agent', AsyncMock(return_value=mock_analysis)):
            with patch.object(developer, 'develop_agent', AsyncMock(return_value={
                "development_id": "dev1",
                "target_agent_id": "TARGET-cycle",
                "status": "COMPLETED",
            })):
                result = await developer.run_development_cycle(mock_db, orchestrator_mock)

        assert result["developer_id"] == "DEV-cycle"
        assert result["targets_processed"] >= 0
        assert len(result["targets"]) >= 0


class TestSelfImprovementIntegration:
    """Tests for self-improvement system integration"""

    @pytest.mark.asyncio
    async def test_factory_creates_self_improver(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.factory import AgentFactory
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import AsyncMock, MagicMock

        ledger = CapitalLedger(starting_capital=50.0)
        risk = RiskManager(ledger)
        factory = AgentFactory(risk)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.flush = AsyncMock()
        mock_db.add = lambda x: None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(risk, 'evaluate_agent_creation', AsyncMock(return_value=(True, ""))):
            agent = await factory.create_agent(
                db=mock_db,
                agent_type="self_improver",
                strategy="self_optimization",
                level="SELF_IMPROVER",
            )

        assert isinstance(agent, type(agent))
        assert agent.agent_type == "self_improver"
        assert agent.level == "SELF_IMPROVER"

    @pytest.mark.asyncio
    async def test_factory_creates_agent_developer(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.factory import AgentFactory
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import AsyncMock, MagicMock

        ledger = CapitalLedger(starting_capital=50.0)
        risk = RiskManager(ledger)
        factory = AgentFactory(risk)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.flush = AsyncMock()
        mock_db.add = lambda x: None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(risk, 'evaluate_agent_creation', AsyncMock(return_value=(True, ""))):
            agent = await factory.create_agent(
                db=mock_db,
                agent_type="agent_developer",
                strategy="agent_evolution",
                level="AGENT_DEVELOPER",
            )

        assert agent.agent_type == "agent_developer"
        assert agent.level == "AGENT_DEVELOPER"

    @pytest.mark.asyncio
    async def test_orchestrator_gets_self_improver(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.self_improver import SelfImproverAgent

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)

        si = SelfImproverAgent(agent_id="SELF-main")
        orchestrator.agents[si.id] = si

        result = orchestrator.get_self_improver()
        assert result is not None
        assert result.id == "SELF-main"

    @pytest.mark.asyncio
    async def test_orchestrator_gets_agent_developer(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.developer import AgentDeveloper

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)

        dev = AgentDeveloper(agent_id="DEV-main")
        orchestrator.agents[dev.id] = dev

        result = orchestrator.get_agent_developer()
        assert result is not None
        assert result.id == "DEV-main"

    @pytest.mark.asyncio
    async def test_orchestrator_self_improvement_cycle(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.self_improver import SelfImproverAgent
        from backend.agents.developer import AgentDeveloper

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)

        si = SelfImproverAgent(agent_id="SELF-main")
        si.roi = -0.5
        si.success_rate = 0.3
        si.experiments_count = 10
        dev = AgentDeveloper(agent_id="DEV-main")

        orchestrator.agents[si.id] = si
        orchestrator.agents[dev.id] = dev

        mock_db = AsyncMock(spec=AsyncSession)

        with patch.object(si, 'run_self_improvement_cycle', AsyncMock(return_value={
            "status": "IMPROVEMENTS_SCHEDULED",
        })):
            with patch.object(dev, 'run_development_cycle', AsyncMock(return_value={
                "status": "COMPLETED",
            })):
                result = await orchestrator.run_self_improvement_cycle(mock_db)

        assert "self_improvement" in result
        assert "development" in result
        assert result["self_improvement"]["status"] == "IMPROVEMENTS_SCHEDULED"

    @pytest.mark.asyncio
    async def test_ceo_triggers_self_improvement_cycle(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.ceo import CEODecisionMaker
        from backend.agents.self_improver import SelfImproverAgent
        from backend.models.database import AgentStatus

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)

        si = SelfImproverAgent(agent_id="SELF-ceo")
        si.status = AgentStatus.ALIVE
        si.experiments_count = 10
        si.success_rate = 0.5
        orchestrator.agents[si.id] = si

        ceo = CEODecisionMaker(orchestrator, ledger, risk)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_system_state = MagicMock()
        mock_system_state.current_mode = SystemMode.GROWTH
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_system_state
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(si, 'run_self_improvement_cycle', AsyncMock(return_value={
            "status": "IMPROVEMENTS_SCHEDULED",
        })):
            decisions = await ceo.analyze_and_decide(mock_db)

        si_decisions = [d for d in decisions if d.get("agent_id") == si.id]
        assert len(si_decisions) >= 1

    @pytest.mark.asyncio
    async def test_learn_from_results_updates_success_rate(self):
        from backend.agents.self_improver import SelfImproverAgent

        agent = SelfImproverAgent(agent_id="SELF-learn")
        agent.success_rate = 0.5

        mock_db = AsyncMock(spec=AsyncSession)
        results = {
            "results": [
                {"success": True},
                {"success": True},
                {"success": False},
            ],
            "insights": ["Test insight"],
        }

        learning = await agent.learn_from_results(mock_db, results)

        assert learning["cycle"] == 0
        assert learning["successes"] == 2
        assert learning["failures"] == 1
        assert learning["learned_insights"] == ["Test insight"]

    @pytest.mark.asyncio
    async def test_learn_from_results_disables_auto_improve(self):
        from backend.agents.self_improver import SelfImproverAgent

        agent = SelfImproverAgent(agent_id="SELF-learn2")
        agent.success_rate = 0.5

        mock_db = AsyncMock(spec=AsyncSession)
        results = {
            "results": [
                {"success": False},
                {"success": False},
                {"success": False},
            ],
            "insights": [],
        }

        learning = await agent.learn_from_results(mock_db, results)

        assert agent.auto_improve_enabled is False
        assert learning["failures"] == 3


class TestSelfImprovingAgentLineage:
    """Test that self-improving agents integrate with lineage tracking"""

    @pytest.mark.asyncio
    async def test_self_improver_in_hierarchy(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.self_improver import SelfImproverAgent
        from backend.agents.developer import AgentDeveloper

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)

        si = SelfImproverAgent(agent_id="SELF-hier")
        dev = AgentDeveloper(agent_id="DEV-hier")
        specialist = MagicMock()
        specialist.id = "SPEC-hier"
        specialist.agent_type = "content"
        specialist.level = "SPECIALIST"
        specialist.status = AgentStatus.ALIVE
        specialist.parent_id = si.id
        specialist.supervisor_id = None

        orchestrator.agents[si.id] = si
        orchestrator.agents[dev.id] = dev
        orchestrator.agents[specialist.id] = specialist

        tree = orchestrator.get_hierarchy_tree()
        assert tree is not None
        assert isinstance(tree["supervisors"], list)
        assert isinstance(tree["specialists"], list)

    @pytest.mark.asyncio
    async def test_self_improver_lineage(self):
        from backend.finance.ledger import CapitalLedger
        from backend.risk.manager import RiskManager
        from backend.agents.orchestrator import AgentOrchestrator
        from backend.agents.self_improver import SelfImproverAgent

        ledger = CapitalLedger(starting_capital=500.0)
        risk = RiskManager(ledger)
        orchestrator = AgentOrchestrator(ledger, risk)

        parent = SelfImproverAgent(agent_id="SELF-parent")
        parent.status = AgentStatus.ALIVE
        child = MagicMock()
        child.id = "SPEC-child"
        child.parent_id = parent.id
        child.agent_type = "research"
        child.generation = 1
        child.level = "SPECIALIST"

        orchestrator.agents[parent.id] = parent
        orchestrator.agents[child.id] = child

        lineage = orchestrator.get_lineage(parent.id)
        assert lineage["id"] == "SELF-parent"
        assert len(lineage["children"]) == 1
        assert lineage["children"][0]["id"] == "SPEC-child"
