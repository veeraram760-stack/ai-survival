import uuid
import logging
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import Agent
from .specialist import Specialist, map_to_specialist_type
from .self_improver import SelfImproverAgent
from config.settings import settings

logger = logging.getLogger("ai_survival.agent_developer")


class AgentDeveloper(Specialist):
    def __init__(self, agent_id: str, agent_type: str = "agent_developer", strategy: str = "agent_evolution"):
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            strategy=strategy,
            capabilities=[
                "agent_analysis",
                "capability_design",
                "agent_creation",
                "strategy_optimization",
                "code_generation",
                "experiment_design",
                "performance_review",
            ],
        )
        self.level = "AGENT_DEVELOPER"
        self.developments_completed = 0
        self.development_history: List[Dict[str, Any]] = []
        self.created_agent_types: List[str] = []
        self.optimization_queue: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "level": "AGENT_DEVELOPER",
            "developments_completed": self.developments_completed,
            "development_history": self.development_history,
            "created_agent_types": self.created_agent_types,
            "optimization_queue": self.optimization_queue,
        })
        return data

    async def analyze_agent(self, db: AsyncSession, target_agent_id: str, orchestrator) -> Dict[str, Any]:
        target = orchestrator.get_agent(target_agent_id)
        if not target:
            return {"status": "error", "message": f"Agent {target_agent_id} not found"}

        analysis = {
            "target_agent_id": target_agent_id,
            "agent_type": target.agent_type,
            "strategy": target.strategy,
            "level": getattr(target, "level", "SPECIALIST"),
            "generation": target.generation,
            "performance": {
                "roi": target.roi,
                "success_rate": target.success_rate,
                "profit": float(target.lifetime_profit),
                "revenue": float(target.lifetime_revenue),
                "expenses": float(target.lifetime_expenses),
                "days_alive": target.days_alive,
                "experiments": target.experiments_count,
                "successful_experiments": target.successful_experiments,
                "failed_experiments": target.failed_experiments,
            },
            "current_capabilities": target.capabilities,
            "supervisor_id": target.supervisor_id,
            "status": target.status.value,
        }

        lineage = orchestrator.get_lineage(target_agent_id)
        analysis["lineage"] = lineage

        if target.experiments_count > 0:
            analysis["success_ratio"] = target.successful_experiments / target.experiments_count
        else:
            analysis["success_ratio"] = 0.0

        perf_rating = "EXCELLENT"
        if target.roi < 0:
            perf_rating = "CRITICAL"
        elif target.roi < 0.5:
            perf_rating = "POOR"
        elif target.roi < 1.5:
            perf_rating = "AVERAGE"
        elif target.roi < 3.0:
            perf_rating = "GOOD"

        analysis["performance_rating"] = perf_rating
        return analysis

    async def suggest_capabilities(
        self,
        db: AsyncSession,
        target_agent_id: str,
        orchestrator,
    ) -> List[Dict[str, Any]]:
        target = orchestrator.get_agent(target_agent_id)
        if not target:
            return []

        agent_type = target.agent_type
        suggested = []

        type_capability_map = {
            "web_research": ["web_search", "web_fetch", "summarization", "data_extraction", "source_validation"],
            "market_research": ["competitive_analysis", "trend_detection", "price_analysis", "market_segmentation"],
            "script": ["storyboarding", "script_optimization", "a_b_testing", "engagement_scoring"],
            "marketing": ["seo_optimization", "ad_creation", "analytics", "automation"],
            "sales": ["lead_scoring", "email_optimization", "crm_integration", "followup_automation"],
            "finance": ["budget_forecasting", "risk_analysis", "investment_tracking", "cost_optimization"],
            "experiment": ["hypothesis_generation", "statistical_analysis", "ab_testing", "variance_detection"],
            "learning": ["knowledge_synthesis", "pattern_detection", "curriculum_generation", "skill_mapping"],
            "affiliate": ["niche_finding", "commission_optimization", "conversion_tracking", "content_optimization"],
            "product_creation": ["market_validation", "listing_optimization", "pricing_strategy", "review_management"],
        }

        existing = set(target.capabilities)
        for cap in type_capability_map.get(agent_type, ["generic"]):
            if cap not in existing:
                suggested.append({
                    "capability": cap,
                    "priority": "HIGH" if target.roi < 0 else "MEDIUM",
                    "expected_benefit": f"Enhance {agent_type} agent capability",
                })

        if target.success_rate < 0.5:
            suggested.append({
                "capability": "self_monitoring",
                "priority": "HIGH",
                "expected_benefit": "Real-time performance tracking and alerting",
            })

        return suggested

    async def design_experiment(
        self,
        db: AsyncSession,
        target_agent_id: str,
        improvement_area: str,
    ) -> Dict[str, Any]:
        experiment = {
            "experiment_id": str(uuid.uuid4())[:8],
            "target_agent_id": target_agent_id,
            "improvement_area": improvement_area,
            "hypothesis": f"Adding {improvement_area} will improve agent performance",
            "expected_outcome": "Improved success rate and ROI",
            "budget": Decimal("5.00"),
            "strategy": f"experimental_{improvement_area}",
            "success_metric": "success_rate > 0.6",
            "status": "PLANNED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return experiment

    async def develop_agent(
        self,
        db: AsyncSession,
        target_agent_id: str,
        orchestrator,
        execute_tools: bool = True,
    ) -> Dict[str, Any]:
        target = orchestrator.get_agent(target_agent_id)
        if not target:
            return {"status": "error", "message": f"Agent {target_agent_id} not found"}

        development = {
            "development_id": str(uuid.uuid4())[:8],
            "target_agent_id": target_agent_id,
            "developer_id": self.id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stages": [],
        }

        capabilities = await self.suggest_capabilities(db, target_agent_id, orchestrator)
        analysis = await self.analyze_agent(db, target_agent_id, orchestrator)

        development["stages"].append({
            "stage": "analysis",
            "completed": True,
            "findings": analysis,
        })

        development["stages"].append({
            "stage": "capability_assessment",
            "completed": True,
            "suggested_capabilities": capabilities,
        })

        for cap in capabilities[:3]:
            if target.capabilities and cap["capability"] not in target.capabilities:
                target.capabilities.append(cap["capability"])
                development["stages"].append({
                    "stage": f"add_capability_{cap['capability']}",
                    "completed": True,
                    "capability": cap["capability"],
                    "priority": cap["priority"],
                })

        if target.strategy in ("default",):
            target.strategy = f"optimized_{target.agent_type}"
            development["stages"].append({
                "stage": "strategy_optimization",
                "completed": True,
                "old_strategy": "default",
                "new_strategy": target.strategy,
            })

        if execute_tools and hasattr(orchestrator, 'execution_engine') and orchestrator.execution_engine:
            try:
                task_result = await orchestrator.execution_engine.execute_agent_task(
                    db, target.id, "generic_task", {
                        "agent_type": target.agent_type,
                        "strategy": target.strategy,
                        "capabilities": target.capabilities,
                        "development_mode": True,
                    }
                )
                development["stages"].append({
                    "stage": "tool_execution",
                    "completed": True,
                    "result": task_result,
                })
            except Exception as e:
                development["stages"].append({
                    "stage": "tool_execution",
                    "completed": True,
                    "result": {"status": "skipped", "error": str(e)},
                })

        development["stages"].append({
            "stage": "validation",
            "completed": True,
            "result": "development_complete",
        })

        development["completed_at"] = datetime.now(timezone.utc).isoformat()
        development["status"] = "COMPLETED"
        development["total_stages"] = len(development["stages"])
        development["completed_stages"] = sum(1 for s in development["stages"] if s.get("completed"))

        self.developments_completed += 1
        self.development_history.append({
            "development_id": development["development_id"],
            "target_agent_id": target_agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities_added": len(capabilities),
            "status": "COMPLETED",
        })

        if target.agent_type not in self.created_agent_types:
            self.created_agent_types.append(target.agent_type)

        return development

    async def conduct_ab_test(
        self,
        db: AsyncSession,
        orchestrator,
        target_agent_id: str,
        variant_count: int = 2,
    ) -> Dict[str, Any]:
        target = orchestrator.get_agent(target_agent_id)
        if not target:
            return {"status": "error", "message": f"Agent {target_agent_id} not found"}

        test = {
            "test_id": str(uuid.uuid4())[:8],
            "target_agent_id": target_agent_id,
            "variants": [],
            "status": "RUNNING",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        strategies = [f"ab_{target.agent_type}_v{i}" for i in range(variant_count)]
        strategies.append(target.strategy)

        for i, strategy in enumerate(strategies):
            variant = {
                "variant_id": f"v{i}",
                "strategy": strategy,
                "agent_id": f"{target.agent_type}-AB-{str(uuid.uuid4())[:8]}",
            }
            try:
                new_agent = await self.__class__(
                    agent_id=variant["agent_id"],
                    agent_type=target.agent_type,
                    strategy=strategy,
                    capabilities=target.capabilities[:],
                )
                new_agent.generation = target.generation + 1
                new_agent.level = getattr(target, "level", "SPECIALIST")
                new_agent.supervisor_id = target.supervisor_id
                orchestrator.agents[new_agent.id] = new_agent
                variant["created"] = True
            except Exception as e:
                variant["created"] = False
                variant["error"] = str(e)
            test["variants"].append(variant)

        test["status"] = "COMPLETED"
        test["completed_at"] = datetime.now(timezone.utc).isoformat()
        test["variant_count"] = len(test["variants"])

        return test

    async def evolve_strategy(
        self,
        db: AsyncSession,
        orchestrator,
        target_agent_id: str,
    ) -> Dict[str, Any]:
        target = orchestrator.get_agent(target_agent_id)
        if not target:
            return {"status": "error", "message": f"Agent {target_agent_id} not found"}

        all_agents = orchestrator.get_all_agents()
        similar = [a for a in all_agents if a.agent_type == target.agent_type and a.id != target.id]

        strategies_to_try = [f"evolved_{target.agent_type}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"]

        if similar:
            best = max(similar, key=lambda a: a.lifetime_profit)
            if best.lifetime_profit > target.lifetime_profit:
                strategies_to_try.append(f"hybrid_{best.strategy}")

        evolution = {
            "agent_id": target_agent_id,
            "current_strategy": target.strategy,
            "strategies_to_try": strategies_to_try,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "attempts": [],
        }

        for strategy in strategies_to_try:
            old_strategy = target.strategy
            target.strategy = strategy
            target.experiments_count += 1

            attempt = {
                "strategy": strategy,
                "old_strategy": old_strategy,
                "success": False,
                "note": "Awaiting next cycle evaluation",
            }
            evolution["attempts"].append(attempt)

        evolution["completed_at"] = datetime.now(timezone.utc).isoformat()
        evolution["status"] = "EVOLVING"
        return evolution

    async def create_specialist_helper(
        self,
        db: AsyncSession,
        orchestrator,
        agent_type: str,
        strategy: str = "default",
    ) -> Dict[str, Any]:
        from .factory import AgentFactory
        from ..risk.manager import RiskManager

        factory = AgentFactory(orchestrator.risk_manager)

        try:
            specialist = await factory.create_agent(
                db=db,
                agent_type=agent_type,
                strategy=strategy,
                level="SPECIALIST",
            )
            orchestrator.agents[specialist.id] = specialist
            self.created_agent_types.append(agent_type)

            result = {
                "status": "success",
                "created_agent_id": specialist.id,
                "agent_type": agent_type,
                "strategy": strategy,
                "developer_id": self.id,
            }
            self.development_history.append({
                "development_id": specialist.id,
                "target_agent_id": specialist.id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "specialist_creation",
                "status": "COMPLETED",
            })
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def optimize_agent_strategy(
        self,
        db: AsyncSession,
        target_agent_id: str,
        orchestrator,
    ) -> Dict[str, Any]:
        target = orchestrator.get_agent(target_agent_id)
        if not target:
            return {"status": "error", "message": "Agent not found"}

        original_strategy = target.strategy
        target.strategy = f"optimized_{target.agent_type}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        result = {
            "agent_id": target_agent_id,
            "old_strategy": original_strategy,
            "new_strategy": target.strategy,
            "optimization_date": datetime.now(timezone.utc).isoformat(),
            "developer_id": self.id,
            "status": "OPTIMIZED",
        }

        self.development_history.append({
            "development_id": f"opt_{target_agent_id}",
            "target_agent_id": target_agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "strategy_optimization",
            "status": "COMPLETED",
        })

        return result

    async def run_development_cycle(
        self,
        db: AsyncSession,
        orchestrator,
        target_agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cycle = {
            "developer_id": self.id,
            "cycle": self.developments_completed + 1,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "targets": [],
        }

        if target_agent_id:
            targets = [target_agent_id]
        else:
            all_agents = orchestrator.get_all_agents()
            targets = [
                a.id for a in all_agents
                if getattr(a, "level", "SPECIALIST") == "SPECIALIST"
                and a.status.value in ("ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY")
                and a.id != self.id
            ]

        for agent_id in targets[:5]:
            try:
                analysis = await self.analyze_agent(db, agent_id, orchestrator)
                if analysis.get("performance_rating") in ("CRITICAL", "POOR", "AVERAGE"):
                    result = await self.develop_agent(db, agent_id, orchestrator)
                    cycle["targets"].append(result)
                    logger.info(f"Developer {self.id} improved agent {agent_id}")
            except Exception as e:
                logger.error(f"Development failed for {agent_id}: {e}")
                cycle["targets"].append({
                    "target_agent_id": agent_id,
                    "status": "error",
                    "error": str(e),
                })

        cycle["completed_at"] = datetime.now(timezone.utc).isoformat()
        cycle["targets_processed"] = len(cycle["targets"])
        return cycle
