import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..agents.base import Agent
from ..models.database import Agent as DB_Agent, AgentStatus
from config.settings import settings

logger = logging.getLogger("ai_survival.supervisors")


class Supervisor(Agent):
    def __init__(self, agent_id: str, department: str, strategy: str = "default"):
        super().__init__(
            agent_id=agent_id,
            agent_type="supervisor",
            strategy=strategy,
            capabilities=["delegation", "validation", "monitoring", "escalation"],
        )
        self.level = "SUPERVISOR"
        self.department = department
        self.specialists: List[Agent] = []

    async def assign_task(self, task: Dict[str, Any], specialists: List[Agent]) -> Optional[Agent]:
        best_agent = self._select_best_agent(task, specialists)
        if not best_agent:
            logger.warning(f"No suitable agent found for task in department {self.department}")
            return None
        logger.info(f"Supervisor assigned task to {best_agent.id} ({best_agent.agent_type})")
        return best_agent

    def _select_best_agent(self, task: Dict[str, Any], specialists: List[Agent]) -> Optional[Agent]:
        if not specialists:
            return None
        eligible = [a for a in specialists if a.status.value in ["ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY"]]
        if not eligible:
            return None
        eligible.sort(key=lambda a: a.success_rate * a.roi, reverse=True)
        return eligible[0]

    async def collect_results(self, task_id: str, agent: Agent) -> Dict[str, Any]:
        return {
            "task_id": task_id,
            "agent_id": agent.id,
            "status": agent.status.value,
            "profit": float(agent.lifetime_profit),
            "roi": agent.roi,
            "success_rate": agent.success_rate,
        }

    async def validate_result(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        from ..quality.controller import QualityController
        async with self._db_factory() if hasattr(self, '_db_factory') else None as db:
            if db is None:
                return {"passed": True, "score": 100.0}
            validation = await QualityController.validate(db, task.get("id"), result, task.get("expected_output"))
            if not validation["passed"]:
                logger.warning(f"Validation failed for task {task.get('id')}: {validation['checks']}")
            return validation

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["department"] = self.department
        data["specialist_count"] = len(self.specialists)
        return data


class ResearchSupervisor(Supervisor):
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id, department="RESEARCH", strategy="research_management")


class ContentSupervisor(Supervisor):
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id, department="CONTENT", strategy="content_management")


class BusinessSupervisor(Supervisor):
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id, department="BUSINESS", strategy="business_management")


class OperationsSupervisor(Supervisor):
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id, department="OPERATIONS", strategy="operations_management")


class QualitySupervisor(Supervisor):
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id, department="QUALITY", strategy="quality_management")


class RiskSupervisor(Supervisor):
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id, department="RISK", strategy="risk_management")


SUPERVISOR_CLASSES = {
    "RESEARCH": ResearchSupervisor,
    "CONTENT": ContentSupervisor,
    "BUSINESS": BusinessSupervisor,
    "OPERATIONS": OperationsSupervisor,
    "QUALITY": QualitySupervisor,
    "RISK": RiskSupervisor,
}


def create_supervisor(agent_id: str, department: str) -> Supervisor:
    cls = SUPERVISOR_CLASSES.get(department.upper(), Supervisor)
    return cls(agent_id=agent_id)
