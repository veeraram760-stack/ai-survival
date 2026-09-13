import uuid
import logging
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base import Agent
from .specialist import Specialist
from config.settings import settings

logger = logging.getLogger("ai_survival.self_improver")


class SelfImproverAgent(Specialist):
    def __init__(self, agent_id: str, agent_type: str = "self_improver", strategy: str = "self_optimization"):
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            strategy=strategy,
            capabilities=[
                "self_analysis",
                "improvement_planning",
                "experiment_design",
                "learning_integration",
                "performance_monitoring",
                "meta_learning",
            ],
        )
        self.level = "SELF_IMPROVER"
        self.improvement_cycle = 0
        self.improvements_applied = 0
        self.improvements_failed = 0
        self.last_improvement_cycle = None
        self.known_weaknesses: List[str] = []
        self.known_strengths: List[str] = []
        self.auto_improve_enabled = True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "level": "SELF_IMPROVER",
            "improvement_cycle": self.improvement_cycle,
            "improvements_applied": self.improvements_applied,
            "improvements_failed": self.improvements_failed,
            "last_improvement_cycle": self.last_improvement_cycle.isoformat() if self.last_improvement_cycle else None,
            "known_weaknesses": self.known_weaknesses,
            "known_strengths": self.known_strengths,
            "auto_improve_enabled": self.auto_improve_enabled,
        })
        return data

    async def analyze_self(self, db: AsyncSession, orchestrator) -> Dict[str, Any]:
        analysis = {
            "agent_id": self.id,
            "type": self.agent_type,
            "generation": self.generation,
            "performance": {
                "roi": self.roi,
                "success_rate": self.success_rate,
                "profit": float(self.lifetime_profit),
                "revenue": float(self.lifetime_revenue),
                "expenses": float(self.lifetime_expenses),
                "days_alive": self.days_alive,
                "experiments": self.experiments_count,
                "successful_experiments": self.successful_experiments,
                "failed_experiments": self.failed_experiments,
            },
            "capabilities": self.capabilities,
            "strategy": self.strategy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        all_agents = orchestrator.get_all_agents()
        if all_agents:
            total_profit = sum(a.lifetime_profit for a in all_agents)
            avg_roi = sum(a.roi for a in all_agents) / len(all_agents) if all_agents else 0
            analysis["system_context"] = {
                "total_agents": len(all_agents),
                "total_profit": float(total_profit),
                "avg_roi": avg_roi,
                "self_rank": self._rank_among_agents(all_agents),
            }

        if self.experiments_count > 0:
            analysis["success_ratio"] = self.successful_experiments / self.experiments_count
        else:
            analysis["success_ratio"] = 0.0

        if self.lifetime_expenses > 0 and self.lifetime_profit < 0:
            analysis["efficiency_score"] = float(self.lifetime_profit / self.lifetime_expenses)
        else:
            analysis["efficiency_score"] = float(self.lifetime_profit) if self.lifetime_profit > 0 else 0.0

        return analysis

    def _rank_among_agents(self, all_agents: List[Agent]) -> int:
        ranked = sorted(all_agents, key=lambda a: a.lifetime_profit, reverse=True)
        for i, a in enumerate(ranked):
            if a.id == self.id:
                return i + 1
        return len(ranked) + 1

    async def identify_weaknesses(self, db: AsyncSession, orchestrator) -> List[Dict[str, Any]]:
        weaknesses = []

        if self.success_rate < 0.5 and self.experiments_count >= 5:
            weaknesses.append({
                "type": "low_success_rate",
                "severity": "HIGH",
                "description": f"Success rate {self.success_rate:.2f} below 0.5 threshold",
                "suggested_improvement": "Review and optimize experimental strategies",
            })

        if self.roi < 0 and self.lifetime_expenses > 1:
            weaknesses.append({
                "type": "negative_roi",
                "severity": "CRITICAL",
                "description": f"ROI {self.roi:.2f} is negative",
                "suggested_improvement": "Reduce expenses or pivot strategy",
            })

        if self.days_alive > 10 and self.experiments_count < 5:
            weaknesses.append({
                "type": "low_activity",
                "severity": "MEDIUM",
                "description": f"Only {self.experiments_count} experiments in {self.days_alive} days",
                "suggested_improvement": "Increase experiment frequency",
            })

        if self.capabilities == ["generic"]:
            weaknesses.append({
                "type": "no_capabilities",
                "severity": "HIGH",
                "description": "Agent has no specialized capabilities",
                "suggested_improvement": "Develop domain-specific capabilities",
            })

        all_agents = orchestrator.get_all_agents()
        for other in all_agents:
            if other.id == self.id:
                continue
            if other.lifetime_profit > self.lifetime_profit * 2 and other.lifetime_profit > 10:
                weaknesses.append({
                    "type": "underperformance",
                    "severity": "MEDIUM",
                    "description": f"Agent {other.id} significantly outperforms self",
                    "suggested_improvement": f"Analyze {other.id}'s strategy: {other.strategy}",
                    "reference_agent": other.id,
                })

        weak_types = [w["type"] for w in weaknesses]
        if "low_success_rate" not in weak_types and self.success_rate >= 0.7:
            strengths = ["high_success_rate", "stable_performance"]
            self.known_strengths = strengths
        if "negative_roi" not in weak_types and self.roi > 1.0:
            self.known_strengths.append("positive_roi")

        self.known_weaknesses = weak_types
        return weaknesses

    async def create_improvement_plan(
        self,
        db: AsyncSession,
        orchestrator,
        weaknesses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        improvements = []

        for w in weaknesses:
            if w["severity"] in ("CRITICAL", "HIGH"):
                improvements.append({
                    "priority": "HIGH",
                    "weakness": w["type"],
                    "action": w.get("suggested_improvement", "Improve performance"),
                    "estimated_impact": "significant",
                })
            elif w["severity"] == "MEDIUM":
                improvements.append({
                    "priority": "MEDIUM",
                    "weakness": w["type"],
                    "action": w.get("suggested_improvement", "Improve performance"),
                    "estimated_impact": "moderate",
                })

        all_agents = orchestrator.get_all_agents()
        high_performers = [a for a in all_agents if a.lifetime_profit > 10 and a.id != self.id]
        if high_performers:
            best = max(high_performers, key=lambda a: a.lifetime_profit)
            improvements.append({
                "priority": "HIGH",
                "weakness": "strategy_gap",
                "action": f"Adopt and adapt strategies from {best.id} ({best.agent_type}:{best.strategy})",
                "estimated_impact": "significant",
                "reference_agent": best.id,
            })

        improvement = {
            "plan_id": str(uuid.uuid4())[:8],
            "cycle": self.improvement_cycle + 1,
            "improvements": improvements,
            "total_high_priority": sum(1 for i in improvements if i["priority"] == "HIGH"),
            "total_medium_priority": sum(1 for i in improvements if i["priority"] == "MEDIUM"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self.improvement_cycle += 1
        self.last_improvement_cycle = datetime.now(timezone.utc)
        return improvement

    async def execute_improvements(
        self,
        db: AsyncSession,
        orchestrator,
        developer_agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = []
        actions_taken = []

        developer = None
        if developer_agent_id and developer_agent_id in orchestrator.agents:
            developer = orchestrator.agents[developer_agent_id]
            logger.info(f"SelfImprover {self.id} delegating to AgentDeveloper {developer.id}")

        all_agents = orchestrator.get_all_agents()
        targets = [
            a for a in all_agents
            if a.id != self.id
            and a.status.value in ("ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY")
            and getattr(a, "level", "SPECIALIST") == "SPECIALIST"
        ]

        for target in targets[:5]:
            action = {
                "target_agent_id": target.id,
                "agent_type": target.agent_type,
                "action": "development",
            }

            if developer:
                try:
                    dev_result = await developer.develop_agent(db, target.id, orchestrator)
                    action["result"] = dev_result.get("status", "unknown")
                    action["stages_completed"] = dev_result.get("completed_stages", 0)
                    action["total_stages"] = dev_result.get("total_stages", 0)
                    action["success"] = dev_result.get("status") == "COMPLETED"
                    results.append(action)
                    actions_taken.append(f"Developed {target.id}: {action['result']}")
                except Exception as e:
                    action["result"] = "error"
                    action["error"] = str(e)
                    action["success"] = False
                    results.append(action)
                    logger.error(f"Development failed for {target.id}: {e}")
            else:
                action["result"] = "skipped_no_developer"
                action["success"] = False
                results.append(action)
                actions_taken.append(f"No developer available for {target.id}")

        if not targets:
            actions_taken.append("No agents needing development")

        improvement_record = {
            "cycle": self.improvement_cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actions_taken": actions_taken,
            "results": results,
            "targets_processed": len(results),
            "successful_improvements": sum(1 for r in results if r.get("success")),
            "failed_improvements": sum(1 for r in results if not r.get("success")),
        }

        self.improvements_applied += improvement_record["successful_improvements"]
        self.improvements_failed += improvement_record["failed_improvements"]

        return improvement_record

    async def learn_from_results(
        self,
        db: AsyncSession,
        improvement_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        success_count = sum(1 for r in improvement_results.get("results", []) if r.get("success"))
        fail_count = sum(1 for r in improvement_results.get("results", []) if not r.get("success"))

        if success_count > fail_count:
            self.success_rate = min(1.0, self.success_rate + 0.05)
        elif fail_count > 0:
            self.success_rate = max(0.0, self.success_rate - 0.02)

        if fail_count > 2:
            self.auto_improve_enabled = False

        learning = {
            "cycle": self.improvement_cycle,
            "successes": success_count,
            "failures": fail_count,
            "auto_improve_enabled": self.auto_improve_enabled,
            "learned_insights": improvement_results.get("insights", []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return learning

    async def run_self_improvement_cycle(
        self,
        db: AsyncSession,
        orchestrator,
        developer_agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cycle_result = {
            "agent_id": self.id,
            "cycle": self.improvement_cycle + 1,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            analysis = await self.analyze_self(db, orchestrator)
            cycle_result["self_analysis"] = analysis

            weaknesses = await self.identify_weaknesses(db, orchestrator)
            cycle_result["weaknesses"] = weaknesses

            if not weaknesses:
                cycle_result["status"] = "NO_IMPROVEMENTS_NEEDED"
                cycle_result["completed_at"] = datetime.now(timezone.utc).isoformat()
                return cycle_result

            plan = await self.create_improvement_plan(db, orchestrator, weaknesses)
            cycle_result["improvement_plan"] = plan

            improvement_record = await self.execute_improvements(db, orchestrator, developer_agent_id)
            cycle_result["execution"] = improvement_record

            learning = await self.learn_from_results(db, improvement_record)
            cycle_result["learning"] = learning

            cycle_result["status"] = "IMPROVEMENTS_SCHEDULED"
        except Exception as e:
            logger.error(f"Self-improvement cycle failed for {self.id}: {e}")
            cycle_result["status"] = "FAILED"
            cycle_result["error"] = str(e)

        cycle_result["completed_at"] = datetime.now(timezone.utc).isoformat()
        return cycle_result
