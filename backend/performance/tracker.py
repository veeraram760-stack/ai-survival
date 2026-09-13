import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.database import AgentPerformance

logger = logging.getLogger("ai_survival.performance")


class PerformanceTracker:
    def __init__(self, db_factory):
        self._db_factory = db_factory

    async def record_task_execution(
        self,
        db: AsyncSession,
        agent_id: str,
        task_id: str,
        success: bool,
        duration_seconds: float,
        cost: float,
        quality_score: float = 0.0,
    ):
        result = await db.execute(
            select(AgentPerformance).where(AgentPerformance.agent_id == agent_id)
        )
        perf = result.scalar_one_or_none()
        if not perf:
            perf = AgentPerformance(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                last_used=datetime.now(timezone.utc),
            )
            db.add(perf)

        perf.task_count += 1
        if success:
            perf.success_count += 1
        else:
            perf.failure_count += 1

        total_time = perf.average_time * (perf.task_count - 1) + duration_seconds
        perf.average_time = total_time / perf.task_count

        total_cost = perf.average_cost * (perf.task_count - 1) + cost
        perf.average_cost = total_cost / perf.task_count

        total_quality = perf.quality_score * (perf.task_count - 1) + quality_score
        perf.quality_score = total_quality / perf.task_count

        perf.reliability_score = perf.success_count / perf.task_count if perf.task_count > 0 else 0.0
        perf.last_used = datetime.now(timezone.utc)
        await db.flush()

    async def get_performance(self, db: AsyncSession, agent_id: str) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(AgentPerformance).where(AgentPerformance.agent_id == agent_id)
        )
        perf = result.scalar_one_or_none()
        if not perf:
            return None
        return {
            "agent_id": perf.agent_id,
            "task_count": perf.task_count,
            "success_count": perf.success_count,
            "failure_count": perf.failure_count,
            "average_time": perf.average_time,
            "average_cost": perf.average_cost,
            "quality_score": perf.quality_score,
            "reliability_score": perf.reliability_score,
            "last_used": perf.last_used.isoformat() if perf.last_used else None,
        }

    async def get_top_agents(self, db: AsyncSession, limit: int = 10, metric: str = "reliability_score") -> List[Dict[str, Any]]:
        order_col = getattr(AgentPerformance, metric, AgentPerformance.reliability_score)
        result = await db.execute(
            select(AgentPerformance).order_by(order_col.desc()).limit(limit)
        )
        perfs = result.scalars().all()
        return [
            {
                "agent_id": p.agent_id,
                "task_count": p.task_count,
                "success_count": p.success_count,
                "failure_count": p.failure_count,
                "reliability_score": p.reliability_score,
                "quality_score": p.quality_score,
                "average_cost": p.average_cost,
            }
            for p in perfs
        ]
