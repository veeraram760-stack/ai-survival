import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..agents.orchestrator import AgentOrchestrator
from ..agents.factory import AgentFactory
from ..risk.manager import RiskManager
from ..experiments.engine import ExperimentEngine
from config.settings import settings
from ..models.database import Agent as DB_Agent, AgentStatus, AgentDeath


class EvolutionSystem:
    def __init__(self, orchestrator: AgentOrchestrator, risk_manager: RiskManager, experiment_engine: ExperimentEngine):
        self.orchestrator = orchestrator
        self.factory = AgentFactory(risk_manager)
        self.risk_manager = risk_manager
        self.experiment_engine = experiment_engine

    async def evaluate_reproduction(self, db: AsyncSession, agent_id: str) -> Dict[str, Any]:
        result = await db.execute(select(DB_Agent).where(DB_Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            return {"eligible": False, "reason": "Agent not found"}

        if agent.status not in [AgentStatus.ALIVE, AgentStatus.GROWING, AgentStatus.REPRODUCTION_READY]:
            return {"eligible": False, "reason": f"Agent status is {agent.status.value}"}

        current_agents = await self._count_active_agents(db)
        if current_agents >= settings.population_hard_cap:
            return {"eligible": False, "reason": "Population hard cap reached"}

        if agent.lifetime_profit < Decimal(str(settings.reproduction_min_profit)):
            return {
                "eligible": False,
                "reason": f"Insufficient lifetime profit: ${agent.lifetime_profit} < ${settings.reproduction_min_profit}",
            }

        if agent.roi < settings.reproduction_min_roi:
            return {"eligible": False, "reason": f"Insufficient ROI: {agent.roi} < {settings.reproduction_min_roi}"}

        if agent.success_rate < settings.reproduction_min_success_rate:
            return {"eligible": False, "reason": f"Success rate too low: {agent.success_rate} < {settings.reproduction_min_success_rate}"}

        return {
            "eligible": True,
            "agent_id": agent_id,
            "profit": float(agent.lifetime_profit),
            "roi": agent.roi,
            "success_rate": agent.success_rate,
        }

    async def clone_winner(self, db: AsyncSession, parent_id: str, mutations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        parent = self.orchestrator.get_agent(parent_id)
        if not parent:
            return {"status": "failed", "error": "Parent agent not found"}

        approved, reason = await self.risk_manager.evaluate_reproduction(
            db, parent_id, parent.roi, parent.lifetime_profit
        )
        if not approved:
            return {"status": "denied", "reason": reason}

        try:
            child = await self.factory.clone_agent(db, parent, mutations)
            self.orchestrator.agents[child.id] = child
            return {"status": "success", "child_id": child.id, "mutations": mutations}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def mutate_strategy(self, db: AsyncSession, agent_id: str, mutations: Dict[str, Any]) -> Dict[str, Any]:
        agent = self.orchestrator.get_agent(agent_id)
        if not agent:
            return {"status": "failed", "error": "Agent not found"}

        for key, value in mutations.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

        agent.strategy = mutations.get("strategy", agent.strategy)
        return {"status": "success", "agent_id": agent_id, "mutations": mutations}

    async def prune_agents(self, db: AsyncSession) -> List[str]:
        terminated = []
        for agent_id, agent in list(self.orchestrator.agents.items()):
            if agent.status == AgentStatus.FAILED:
                await self.factory.terminate_agent(db, agent, "Marked as failed by evolution system")
                del self.orchestrator.agents[agent_id]
                terminated.append(agent_id)
        return terminated

    async def _count_active_agents(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(DB_Agent.id)).where(
                DB_Agent.status.in_([
                    AgentStatus.ALIVE,
                    AgentStatus.TESTING,
                    AgentStatus.GROWING,
                    AgentStatus.REPRODUCTION_READY,
                ])
            )
        )
        return result.scalar_one()

    async def check_population_capacity(self, db: AsyncSession) -> Dict[str, Any]:
        """Check if population is at soft/hard caps"""
        current_agents = await self._count_active_agents(db)

        if current_agents >= settings.population_hard_cap:
            return {
                "can_create": False,
                "at_soft_cap": True,
                "at_hard_cap": True,
                "current": current_agents,
                "soft_cap": settings.population_soft_cap,
                "hard_cap": settings.population_hard_cap,
                "reason": "Population hard cap reached"
            }
        elif current_agents >= settings.population_soft_cap:
            return {
                "can_create": True,
                "at_soft_cap": True,
                "at_hard_cap": False,
                "current": current_agents,
                "soft_cap": settings.population_soft_cap,
                "hard_cap": settings.population_hard_cap,
                "reason": "At soft cap - creation requires available capital"
            }
        else:
            return {
                "can_create": True,
                "at_soft_cap": False,
                "at_hard_cap": False,
                "current": current_agents,
                "soft_cap": settings.population_soft_cap,
                "hard_cap": settings.population_hard_cap,
                "reason": "Below caps"
            }

    async def record_agent_death(
        self,
        db: AsyncSession,
        agent_id: str,
        failure_reasons: list = None,
        useful_discoveries: list = None,
    ) -> str:
        """Record an agent's death and preserve useful discoveries"""
        from ..models.database import AgentDeath, Agent, AgentStatus

        agent = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent.scalar_one_or_none()

        if agent:
            death = AgentDeath(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                agent_type=agent.agent_type,
                strategy=agent.strategy,
                lifetime_revenue=agent.lifetime_revenue,
                lifetime_expenses=agent.lifetime_expenses,
                lifetime_profit=agent.lifetime_profit,
                days_alive=agent.days_alive,
                experiments_count=agent.experiments_count,
                successful_experiments=agent.successful_experiments,
                failed_experiments=agent.failed_experiments,
                failure_reasons=failure_reasons or [],
                useful_discoveries=useful_discoveries or [],
            )
            db.add(death)

            # Also mark agent as failed
            agent.status = AgentStatus.FAILED
            agent.terminated_at = datetime.now(timezone.utc)

            await db.flush()
            return death.id
        return ""
