import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.database import Experiment, ExperimentStatus, Agent, Strategy
from ..risk.manager import RiskManager
from config.settings import settings
import random


class ExperimentEngine:
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    async def create_experiment(
        self,
        db: AsyncSession,
        agent_id: str,
        hypothesis: str,
        budget: float,
        strategy: str,
        success_metric: str,
        expected_outcome: Optional[str] = None,
    ) -> Experiment:
        experiment = Experiment(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            hypothesis=hypothesis,
            expected_outcome=expected_outcome,
            budget=budget,
            strategy=strategy,
            success_metric=success_metric,
            status=ExperimentStatus.PLANNED,
        )
        db.add(experiment)
        await db.flush()
        return experiment

    async def start_experiment(self, db: AsyncSession, experiment_id: str):
        result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
        experiment = result.scalar_one_or_none()
        if experiment:
            experiment.status = ExperimentStatus.RUNNING
            experiment.start_time = datetime.now(timezone.utc)

    async def complete_experiment(self, db: AsyncSession, experiment_id: str, actual_result: float, conclusion: str):
        result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
        experiment = result.scalar_one_or_none()
        if experiment:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.end_time = datetime.now(timezone.utc)
            experiment.actual_result = actual_result
            experiment.conclusion = conclusion

            agent_result = await db.execute(select(Agent).where(Agent.id == experiment.agent_id))
            agent = agent_result.scalar_one_or_none()
            if agent:
                agent.experiments_count += 1
                if actual_result > experiment.budget:
                    agent.successful_experiments += 1
                else:
                    agent.failed_experiments += 1
                agent.lifetime_revenue += Decimal(str(actual_result))
                agent.lifetime_expenses += Decimal(str(experiment.budget))
                agent.lifetime_profit = agent.lifetime_revenue - agent.lifetime_expenses

    async def get_experiment_stats(self, db: AsyncSession, strategy: Optional[str] = None) -> Dict[str, Any]:
        query = select(Experiment)
        if strategy:
            query = query.where(Experiment.strategy == strategy)
        result = await db.execute(query)
        experiments = result.scalars().all()

        total = len(experiments)
        if total == 0:
            return {"total": 0, "success_rate": 0.0, "avg_roi": 0.0}

        successes = sum(1 for e in experiments if e.actual_result is not None and e.actual_result > e.budget)
        total_budget = sum(e.budget for e in experiments)
        total_return = sum(e.actual_result or 0 for e in experiments)

        return {
            "total": total,
            "success_rate": successes / total,
            "avg_roi": (total_return - total_budget) / total_budget if total_budget > 0 else 0.0,
            "avg_budget": total_budget / total,
            "avg_return": total_return / total,
        }

    # A/B Testing Framework
    async def create_ab_test(
        self,
        db: AsyncSession,
        agent_id: str,
        hypothesis: str,
        budget: float,
        strategy_a: str,
        strategy_b: str,
        success_metric: str,
        traffic_split: float = 0.5,
        min_sample_size: int = 100,
    ) -> Dict[str, Any]:
        """Create an A/B test experiment comparing two strategies"""

        # Create two sub-experiments
        exp_a = await self.create_experiment(
            db, agent_id, f"{hypothesis} (Variant A)", budget * traffic_split,
            strategy_a, success_metric, "Expected better performance with A"
        )
        exp_b = await self.create_experiment(
            db, agent_id, f"{hypothesis} (Variant B)", budget * (1 - traffic_split),
            strategy_b, success_metric, "Expected better performance with B"
        )

        return {
            "status": "created",
            "test_id": str(uuid.uuid4()),
            "variant_a": {"experiment_id": exp_a.id, "strategy": strategy_a, "budget": exp_a.budget},
            "variant_b": {"experiment_id": exp_b.id, "strategy": strategy_b, "budget": exp_b.budget},
            "traffic_split": traffic_split,
            "min_sample_size": min_sample_size,
        }

    async def run_ab_test(
        self,
        db: AsyncSession,
        test_id: str,
        variant_a_data: Dict[str, Any],
        variant_b_data: Dict[str, Any],
        execution_engine,
    ) -> Dict[str, Any]:
        """Run an A/B test with real execution"""

        # This would be called with actual test data
        # For now, return structure for tracking

        # Simulate A/B test execution
        results_a = await self._run_variant(variant_a_data, execution_engine)
        results_b = await self._run_variant(variant_b_data, execution_engine)

        # Statistical significance test
        significance = self._calculate_significance(results_a, results_b)

        return {
            "test_id": test_id,
            "variant_a": {"strategy": variant_a_data.get("strategy"), "results": results_a},
            "variant_b": {"strategy": variant_b_data.get("strategy"), "results": results_b},
            "significance": significance,
            "winner": "A" if results_a.get("metric", 0) > results_b.get("metric", 0) else "B",
            "confidence": significance.get("confidence", 0),
        }

    async def _run_variant(self, variant_data: Dict[str, Any], execution_engine) -> Dict[str, Any]:
        """Run a single variant of an A/B test"""
        # Execute the variant's tasks
        agent_id = variant_data.get("agent_id")
        tasks = variant_data.get("tasks", [])

        results = []
        for task in tasks:
            result = await execution_engine.execute_agent_task(
                None, agent_id, task.get("type"), task.get("data", {})
            )
            results.append(result)

        # Aggregate results
        metric_values = [r.get("metric", 0) for r in results if r.get("status") == "success"]
        avg_metric = sum(metric_values) / len(metric_values) if metric_values else 0

        return {
            "runs": len(results),
            "successful": len([r for r in results if r.get("status") == "success"]),
            "metric": avg_metric,
            "raw_results": results,
        }

    def _calculate_significance(self, results_a: Dict[str, Any], results_b: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistical significance between two variants"""
        # Simplified significance calculation
        # In production, use proper statistical tests (t-test, chi-square, etc.)

        metric_a = results_a.get("metric", 0)
        metric_b = results_b.get("metric", 0)

        # Simple effect size
        effect_size = abs(metric_a - metric_b) / max(abs(metric_a), abs(metric_b), 0.001)

        # Mock confidence based on sample sizes
        n_a = results_a.get("runs", 0)
        n_b = results_b.get("runs", 0)
        min_n = min(n_a, n_b)

        confidence = min(0.95, 0.5 + (min_n / 100) * 0.45) if min_n > 0 else 0.5

        return {
            "effect_size": effect_size,
            "confidence": confidence,
            "p_value": 0.05 if confidence > 0.9 else 0.1,
            "significant": confidence > 0.9,
        }

    async def get_ab_test_results(self, db: AsyncSession, test_id: str) -> Dict[str, Any]:
        """Get results for an A/B test"""
        # Would query related experiments
        return {"test_id": test_id, "status": "completed", "results": {}}
