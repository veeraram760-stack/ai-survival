import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.database import (
    LearningMemory, Experiment, Agent, AgentMetric, AgentDeath, Strategy
)
from config.settings import settings


class LearningSystem:
    def __init__(self):
        self.memory_cache: Dict[str, Dict[str, Any]] = {}

    async def store_knowledge(
        self,
        db: AsyncSession,
        category: str,
        key: str,
        value: Any,
        confidence: float = 0.5,
        source_agent_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> LearningMemory:
        existing = await db.execute(
            select(LearningMemory).where(LearningMemory.category == category, LearningMemory.key == key)
        )
        memory = existing.scalar_one_or_none()
        if memory:
            memory.value = value
            memory.confidence = max(memory.confidence, confidence)
            memory.updated_at = datetime.now(timezone.utc)
            if source_agent_id:
                memory.source_agent_id = source_agent_id
            if experiment_id:
                memory.experiment_id = experiment_id
        else:
            memory = LearningMemory(
                id=str(uuid.uuid4()),
                category=category,
                key=key,
                value=value,
                confidence=confidence,
                source_agent_id=source_agent_id,
                experiment_id=experiment_id,
            )
            db.add(memory)
        await db.flush()
        return memory

    async def get_knowledge(self, db: AsyncSession, category: str, key: str) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(LearningMemory).where(LearningMemory.category == category, LearningMemory.key == key)
        )
        memory = result.scalar_one_or_none()
        return memory.value if memory else None

    async def summarize_learning(self, db: AsyncSession) -> Dict[str, Any]:
        strategies_result = await db.execute(select(Strategy))
        strategies = strategies_result.scalars().all()

        successful_strategies = [s for s in strategies if s.avg_roi > 0]
        failed_strategies = [s for s in strategies if s.avg_roi <= 0]

        top_performer = max(strategies, key=lambda s: s.avg_roi) if strategies else None
        worst_performer = min(strategies, key=lambda s: s.avg_roi) if strategies else None

        agent_metrics_result = await db.execute(select(AgentMetric))
        all_metrics = agent_metrics_result.scalars().all()

        return {
            "what_worked": [
                {"strategy": s.name, "avg_roi": s.avg_roi, "success_rate": s.successes / s.total_experiments if s.total_experiments > 0 else 0}
                for s in successful_strategies[:5]
            ],
            "what_failed": [
                {"strategy": s.name, "avg_roi": s.avg_roi, "success_rate": s.successes / s.total_experiments if s.total_experiments > 0 else 0}
                for s in failed_strategies[:5]
            ],
            "top_performer": {
                "strategy": top_performer.name,
                "avg_roi": top_performer.avg_roi,
            } if top_performer else None,
            "worst_performer": {
                "strategy": worst_performer.name,
                "avg_roi": worst_performer.avg_roi,
            } if worst_performer else None,
            "total_metrics_analyzed": len(all_metrics),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_recommendations(self, db: AsyncSession) -> List[Dict[str, Any]]:
        recommendations = []
        strategies_result = await db.execute(select(Strategy).where(Strategy.status == "ACTIVE"))
        strategies = strategies_result.scalars().all()

        for strategy in strategies:
            if strategy.avg_roi > settings.reproduction_min_roi and strategy.successes >= 3:
                recommendations.append({
                    "type": "SCALE",
                    "strategy": strategy.name,
                    "reason": f"Strong performance: ROI={strategy.avg_roi:.2f}, success_rate={strategy.successes}/{strategy.total_experiments}",
                    "confidence": 0.8,
                })
            elif strategy.avg_roi < 0 and strategy.failures >= 3:
                recommendations.append({
                    "type": "TERMINATE",
                    "strategy": strategy.name,
                    "reason": f"Persistent losses: ROI={strategy.avg_roi:.2f}",
                    "confidence": 0.9,
                })
        return recommendations
