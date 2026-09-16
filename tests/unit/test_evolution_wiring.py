"""
Wiring tests for EvolutionSystem integration into AgentOrchestrator.
Verifies the evolution step runs each cycle: reproduce winners, prune failures.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.finance.ledger import CapitalLedger
from backend.risk.manager import RiskManager
from backend.agents.orchestrator import AgentOrchestrator
from backend.evolution.engine import EvolutionSystem
from backend.models.database import AgentStatus


def _make_orchestrator():
    ledger = CapitalLedger(starting_capital=100.0)
    risk = RiskManager(ledger)
    return AgentOrchestrator(ledger, risk)


def _make_agent(agent_id, profit, roi, success_rate, strategy="default", generation=0):
    agent = MagicMock()
    agent.id = agent_id
    agent.status = AgentStatus.ALIVE
    agent.lifetime_profit = Decimal(str(profit))
    agent.roi = roi
    agent.success_rate = success_rate
    agent.strategy = strategy
    agent.generation = generation
    return agent


class TestEvolutionIntegration:

    @pytest.mark.asyncio
    async def test_init_creates_evolution_system(self):
        orchestrator = _make_orchestrator()

        assert isinstance(orchestrator.evolution, EvolutionSystem)
        assert orchestrator.evolution.orchestrator is orchestrator

    @pytest.mark.asyncio
    async def test_evolution_step_clones_top_winner(self):
        orchestrator = _make_orchestrator()

        winner = _make_agent("winner-1", 100.00, 2.5, 0.9, strategy="viral_content", generation=2)
        loser = _make_agent("loser-1", 20.00, 1.0, 0.4)
        orchestrator.agents = {"winner-1": winner, "loser-1": loser}

        mock_db = AsyncMock(spec=AsyncSession)
        capacity = {"can_create": True, "current": 5, "soft_cap": 100, "hard_cap": 1000}

        with patch.object(
            orchestrator.evolution, "check_population_capacity",
            new=AsyncMock(return_value=capacity),
        ), patch.object(
            orchestrator.evolution, "evaluate_reproduction",
            new=AsyncMock(side_effect=[{"eligible": True}, {"eligible": False}]),
        ), patch.object(
            orchestrator.evolution, "clone_winner",
            new=AsyncMock(return_value={"status": "success", "child_id": "child-1", "mutations": None}),
        ) as mock_clone:
            result = await orchestrator._run_evolution_step(mock_db)

        mock_clone.assert_awaited_once()
        parent_arg = mock_clone.await_args.args[1]
        assert parent_arg == "winner-1"
        assert result["clones"] == 1
        assert result["reproductions"] == [{"status": "success", "child_id": "child-1", "mutations": None}]

    @pytest.mark.asyncio
    async def test_evolution_step_no_clone_when_off_capacity(self):
        orchestrator = _make_orchestrator()

        winner = _make_agent("winner-1", 100.00, 2.5, 0.9)
        orchestrator.agents = {"winner-1": winner}

        mock_db = AsyncMock(spec=AsyncSession)
        capacity = {"can_create": False, "current": 100, "soft_cap": 100, "hard_cap": 1000}

        with patch.object(
            orchestrator.evolution, "check_population_capacity",
            new=AsyncMock(return_value=capacity),
        ), patch.object(
            orchestrator.evolution, "clone_winner", new=AsyncMock(),
        ) as mock_clone:
            result = await orchestrator._run_evolution_step(mock_db)

        mock_clone.assert_not_awaited()
        assert result["clones"] == 0
        assert result["pruned"] == []  # no FAILED agents seeded

    @pytest.mark.asyncio
    async def test_evolution_step_prunes_failed_agents(self):
        orchestrator = _make_orchestrator()

        failed = _make_agent("dead-1", -50.00, -1.0, 0.1)
        failed.status = AgentStatus.FAILED
        orchestrator.agents = {"dead-1": failed}

        mock_db = AsyncMock(spec=AsyncSession)
        capacity = {"can_create": False, "current": 100, "soft_cap": 100, "hard_cap": 1000}

        with patch.object(
            orchestrator.evolution, "check_population_capacity",
            new=AsyncMock(return_value=capacity),
        ), patch.object(
            orchestrator.evolution.factory, "terminate_agent", new=AsyncMock(),
        ) as mock_terminate:
            result = await orchestrator._run_evolution_step(mock_db)

        assert "dead-1" not in orchestrator.agents
        assert "dead-1" in result["pruned"]
        mock_terminate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_cycle_invokes_evolution_step(self):
        orchestrator = _make_orchestrator()

        mock_db = AsyncMock(spec=AsyncSession)

        steps = [
            "_update_agent_metrics",
            "_run_revenue_simulations",
            "_fetch_real_conversions",
            "_run_revenue_agents",
            "_process_decisions",
            "run_self_improvement_cycle",
            "_evaluate_system_mode",
            "_update_dashboard_state",
        ]
        active = {name: AsyncMock(return_value=None) for name in set(steps + ["_run_evolution_step"])}

        with patch.object(orchestrator, "_run_evolution_step", active["_run_evolution_step"]), \
             patch.object(orchestrator, "_update_agent_metrics", active["_update_agent_metrics"]), \
             patch.object(orchestrator, "_run_revenue_simulations", active["_run_revenue_simulations"]), \
             patch.object(orchestrator, "_fetch_real_conversions", active["_fetch_real_conversions"]), \
             patch.object(orchestrator, "_run_revenue_agents", active["_run_revenue_agents"]), \
             patch.object(orchestrator, "_process_decisions", active["_process_decisions"]), \
             patch.object(orchestrator, "run_self_improvement_cycle", active["run_self_improvement_cycle"]), \
             patch.object(orchestrator, "_evaluate_system_mode", active["_evaluate_system_mode"]), \
             patch.object(orchestrator, "_update_dashboard_state", active["_update_dashboard_state"]):
            await orchestrator._run_cycle(mock_db)

        active["_run_evolution_step"].assert_awaited_once_with(mock_db)