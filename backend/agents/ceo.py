import json
import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..agents.orchestrator import AgentOrchestrator
from ..finance.ledger import CapitalLedger
from ..risk.manager import RiskManager
from ..execution.llm_providers import get_llm_provider
from ..models.database import Decision, DecisionType, ApprovalStatus, Agent, SystemState
from ..tasks.manager import TaskManager
from ..memory.manager import MemoryManager
from ..performance.tracker import PerformanceTracker
from ..agents.revenue_agent import RevenueAgentFactory
from config.settings import settings
import logging

logger = logging.getLogger("ai_survival.ceo")


class CEODecisionMaker:
    def __init__(self, orchestrator: AgentOrchestrator, ledger: CapitalLedger, risk_manager: RiskManager, task_manager: Optional[TaskManager] = None, memory_manager: Optional[MemoryManager] = None, performance_tracker: Optional[PerformanceTracker] = None):
        self.orchestrator = orchestrator
        self.ledger = ledger
        self.risk_manager = risk_manager
        self.task_manager = task_manager
        self.memory_manager = memory_manager
        self.performance_tracker = performance_tracker
        self.llm = get_llm_provider()

    async def run_cycle(self, db: AsyncSession):
        if self.task_manager:
            self._observe(db)
            context = await self._understand(db)
            plan = await self._plan(db, context)
            await self._delegate(db, plan)
            await self._monitor(db)
            evaluation = await self._evaluate(db)
            await self._decide(db, evaluation)
            await self._learn(db, evaluation)

    def _observe(self, db: AsyncSession):
        snapshot = self.ledger.get_capital_snapshot()
        agents = self.orchestrator.get_all_agents()
        system_state = self.risk_manager.evaluate_system_mode(db)
        logger.info(f"OBSERVE: Capital=${snapshot['total_capital']:.2f}, Agents={len(agents)}, Mode={system_state}")

    async def _understand(self, db: AsyncSession) -> Dict[str, Any]:
        snapshot = self.ledger.get_capital_snapshot()
        agents = self.orchestrator.get_all_agents()
        system_state_result = await db.execute(select(SystemState).where(SystemState.id == "current"))
        system_state = system_state_result.scalar_one_or_none()

        if self.memory_manager:
            long_term = await self.memory_manager.search_long_term(db, "strategy", limit=5)
            project = await self.memory_manager.get_project(db, "main", "current_goals")
        else:
            long_term = []
            project = None

        return {
            "snapshot": snapshot,
            "agents": agents,
            "system_state": system_state,
            "long_term_insights": long_term,
            "project_goals": project,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _plan(self, db: AsyncSession, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        tasks = []
        snapshot = context["snapshot"]
        agents = context["agents"]
        system_state = context.get("system_state")

        if self.risk_manager.ledger.current_balance < self.risk_manager.ledger.survival_reserve * Decimal("2"):
            tasks.append({
                "title": "Enter survival mode",
                "description": "Capital approaching survival reserve. Reduce costs and pause non-critical agents.",
                "priority": "HIGH",
                "supervisor": "RISK",
            })

        active_agents = [a for a in agents if a.status.value in ["ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY"]]
        if len(active_agents) < 5:
            tasks.append({
                "title": "Create new specialist agent",
                "description": "Agent count is low. Create a new specialist to increase coverage.",
                "priority": "MEDIUM",
                "supervisor": "OPERATIONS",
            })

        for agent in active_agents:
            if agent.lifetime_profit < -5 and agent.expenses > 2:
                tasks.append({
                    "title": f"Evaluate underperforming agent {agent.id}",
                    "description": f"Agent {agent.agent_type} has persistent losses.",
                    "priority": "HIGH",
                    "supervisor": "OPERATIONS",
                    "agent_id": agent.id,
                })

        return tasks

    async def _delegate(self, db: AsyncSession, plan: List[Dict[str, Any]]):
        if not self.task_manager:
            return
        for task_plan in plan:
            try:
                task = await self.task_manager.create_task(
                    db=db,
                    title=task_plan["title"],
                    description=task_plan.get("description", ""),
                    priority=task_plan.get("priority", "MEDIUM"),
                    supervisor=task_plan.get("supervisor"),
                    assigned_agent=task_plan.get("agent_id"),
                    autonomy_level=2 if task_plan.get("priority") == "HIGH" else 3,
                )
                logger.info(f"Delegated task {task.id} to supervisor {task_plan.get('supervisor')}")
            except Exception as e:
                logger.error(f"Failed to delegate task: {e}")

    async def _monitor(self, db: AsyncSession):
        if self.task_manager:
            await self.task_manager.check_timeouts(db)
            pending = await self.task_manager.get_pending_tasks(db, limit=50)
            running = await self.task_manager.get_running_tasks(db, limit=50)
            logger.info(f"MONITOR: {len(pending)} pending tasks, {len(running)} running tasks")

    async def _evaluate(self, db: AsyncSession) -> Dict[str, Any]:
        if self.task_manager:
            stats = await self.task_manager.get_task_stats(db)
        else:
            stats = {}
        snapshot = self.ledger.get_capital_snapshot()
        return {
            "task_stats": stats,
            "capital_snapshot": snapshot,
            "agent_count": len(self.orchestrator.get_all_agents()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _decide(self, db: AsyncSession, evaluation: Dict[str, Any]):
        if self.memory_manager:
            await self.memory_manager.set_project(db, "main", "last_evaluation", evaluation, confidence=0.8)

    async def _learn(self, db: AsyncSession, evaluation: Dict[str, Any]):
        if not self.memory_manager:
            return
        snapshot = evaluation.get("capital_snapshot", {})
        mode = snapshot.get("current_mode", "UNKNOWN")
        await self.memory_manager.set_long_term(db, "system", f"mode_{mode}", {
            "snapshot": snapshot,
            "evaluated_at": evaluation.get("timestamp"),
        }, confidence=0.7)

    async def analyze_and_decide(self, db: AsyncSession) -> List[Dict[str, Any]]:
        if self.task_manager:
            await self.run_cycle(db)

        decisions = []
        decisions.extend(await self._evaluate_survival_mode())
        decisions.extend(await self._evaluate_agent_performance())
        decisions.extend(await self._autonomous_revenue_discovery(db))
        decisions.extend(await self._autonomous_self_improvement(db))
        decisions.extend(await self._trigger_self_improvement_cycle(db))
        decisions.extend(await self._allocate_revenue_budgets(db))
        decisions.extend(await self._evaluate_revenue_reproduction(db))
        return decisions

    async def _trigger_self_improvement_cycle(self, db: AsyncSession) -> List[Dict[str, Any]]:
        decisions = []
        try:
            if not hasattr(self, 'orchestrator') or not self.orchestrator:
                return decisions

            self_improver = self.orchestrator.get_self_improver()
            developer = self.orchestrator.get_agent_developer()

            if self_improver:
                decisions.append({
                    "type": DecisionType.START_EXPERIMENT,
                    "payload": {
                        "title": f"Self-improvement cycle {getattr(self_improver, 'improvement_cycle', 0) + 1}",
                        "agent_id": self_improver.id,
                        "description": "Execute self-analysis and improvement planning",
                        "priority": "MEDIUM",
                    },
                    "priority": "MEDIUM",
                    "agent_id": self_improver.id,
                })

            if developer:
                decisions.append({
                    "type": DecisionType.START_EXPERIMENT,
                    "payload": {
                        "title": "Agent development cycle",
                        "agent_id": developer.id,
                        "description": "Develop and optimize underperforming agents",
                        "priority": "LOW",
                    },
                    "priority": "LOW",
                    "agent_id": developer.id,
                })
        except Exception as e:
            logger.error(f"Self-improvement cycle trigger failed: {e}")
        return decisions

    async def _autonomous_revenue_discovery(self, db: AsyncSession) -> List[Dict[str, Any]]:
        decisions = []
        try:
            from ..tools import tool_registry
            tool = tool_registry.get("revenue_discovery")
            if not tool:
                return decisions

            snapshot = self.ledger.get_capital_snapshot()
            result = await tool.execute(
                current_capital=float(snapshot.get("total_capital", 50.0)),
                existing_networks=["amazon", "cj", "shareasale"],
                count=5,
            )
            if result.get("status") == "success":
                opportunities = result.get("opportunities", [])
                for opp in opportunities[:3]:
                    decisions.append({
                        "type": DecisionType.START_EXPERIMENT,
                        "payload": {
                            "title": f"Test opportunity: {opp.get('opportunity_name', 'New Revenue Stream')}",
                            "description": f"Auto-discovered: {opp.get('description', opp.get('opportunity_name', ''))}",
                            "opportunity": opp,
                            "priority": "HIGH" if opp.get("confidence", 0) > 0.7 else "MEDIUM",
                        },
                        "priority": "HIGH" if opp.get("confidence", 0) > 0.7 else "MEDIUM",
                    })
                if opportunities:
                    await self.memory_manager.set_project(db, "revenue", "discovered_opportunities", opportunities, confidence=0.6)
        except Exception as e:
            logger.error(f"Autonomous revenue discovery failed: {e}")
        return decisions

    async def _autonomous_self_improvement(self, db: AsyncSession) -> List[Dict[str, Any]]:
        decisions = []
        try:
            from ..tools import tool_registry
            tool = tool_registry.get("self_improvement")
            if not tool:
                return decisions

            snapshot = self.ledger.get_capital_snapshot()
            agents = self.orchestrator.get_all_agents()
            agent_perf = []
            for a in agents:
                agent_perf.append({
                    "id": a.id,
                    "type": a.agent_type,
                    "profit": float(a.lifetime_profit),
                    "roi": a.roi,
                    "success_rate": a.success_rate,
                })

            current_tools = list(tool_registry.list_tools().keys())
            result = await tool.execute(
                capital=float(snapshot.get("total_capital", 0)),
                real_revenue=float(snapshot.get("real_revenue", 0)),
                agent_performance=agent_perf,
                current_tools=current_tools,
            )
            if result.get("status") == "success":
                improvements = result.get("improvements", [])
                for imp in improvements[:2]:
                    decisions.append({
                        "type": DecisionType.CREATE_AGENT,
                        "payload": {
                            "title": f"Self-improvement: {imp.get('description', 'System optimization')}",
                            "improvement": imp,
                            "priority": imp.get("priority", "MEDIUM"),
                        },
                        "priority": imp.get("priority", "MEDIUM"),
                    })
        except Exception as e:
            logger.error(f"Autonomous self-improvement failed: {e}")
        return decisions

    async def _evaluate_survival_mode(self) -> List[Dict[str, Any]]:
        decisions = []
        reserve_ratio = self.ledger.survival_reserve / self.ledger.current_balance if self.ledger.current_balance > 0 else 1.0

        if reserve_ratio >= 0.9:
            decisions.append({
                "type": DecisionType.ENTER_SURVIVAL_MODE,
                "payload": {"reason": "Capital critically close to survival reserve"},
                "priority": "HIGH",
            })
        elif reserve_ratio >= 0.6:
            decisions.append({
                "type": DecisionType.REDUCE_BUDGET,
                "payload": {"reason": "Capital approaching reserve threshold", "reduction_ratio": 0.5},
                "priority": "MEDIUM",
            })
        return decisions

    async def _evaluate_agent_performance(self) -> List[Dict[str, Any]]:
        decisions = []
        for agent in self.orchestrator.get_all_agents():
            if agent.status.value not in ["ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY"]:
                continue

            if agent.status.value == "TESTING" and self._should_promote_to_alive(agent):
                logger.info(f"Promoting agent {agent.id} to ALIVE")
                decisions.append({
                    "type": DecisionType.CLONE_AGENT,
                    "payload": {"promote_agent_id": agent.id, "new_status": "ALIVE"},
                    "priority": "MEDIUM",
                    "agent_id": agent.id,
                })

            if agent.lifetime_profit > 50 and agent.roi > 2.0 and agent.success_rate > 0.6:
                mutations = await self._generate_strategic_mutations(agent)
                decisions.append({
                    "type": DecisionType.CLONE_AGENT,
                    "payload": {
                        "parent_id": agent.id,
                        "mutations": mutations,
                    },
                    "priority": "MEDIUM",
                    "agent_id": agent.id,
                })

            if agent.lifetime_profit < -10 or (agent.expenses > 20 and agent.lifetime_profit < 0):
                decisions.append({
                    "type": DecisionType.TERMINATE_AGENT,
                    "payload": {
                        "agent_id": agent.id,
                        "reason": "Persistent losses or poor ROI",
                    },
                    "priority": "HIGH",
                    "agent_id": agent.id,
                })
        return decisions

    def _should_promote_to_alive(self, agent) -> bool:
        if agent.status.value != "TESTING":
            return False
        if agent.experiments_count < 5:
            return False
        if agent.successful_experiments > 0:
            return True
        if agent.experiments_count >= 10 and agent.lifetime_expenses > 0:
            return True
        return False

    async def _generate_strategic_mutations(self, agent) -> Dict[str, Any]:
        snapshot = self.ledger.get_capital_snapshot()
        context = f"""
Agent {agent.id} ({agent.agent_type}:{agent.strategy}) is a high performer:
- Lifetime profit: ${float(agent.lifetime_profit):.2f}
- ROI: {agent.roi:.2f}
- Success rate: {agent.success_rate:.2f}
- Generation: {agent.generation}
- Days alive: {agent.days_alive}

Current capital: ${snapshot['total_capital']:.2f}, Reserve ratio: {snapshot['survival_reserve']/snapshot['total_capital']*100:.1f}%

Suggest 1-3 strategic mutations to improve performance. Return JSON:
{{"mutations": {{"strategy": "new_strategy_name", "risk_score": 0.3, "budget_multiplier": 1.2}}}}
"""
        llm_result = await self.llm.generate(prompt=context, max_tokens=500, temperature=0.4)
        if llm_result.get("status") == "success":
            try:
                return json.loads(llm_result["output"]).get("mutations", {"strategy": f"{agent.strategy}_variant"})
            except json.JSONDecodeError:
                pass
        return {"strategy": f"{agent.strategy}_variant_{datetime.now(timezone.utc).strftime('%Y%m%d')}"}

    async def _evaluate_experiments(self, db: AsyncSession) -> List[Dict[str, Any]]:
        return []

    async def _get_system_state(self, db: AsyncSession):
        from ..models.database import SystemState
        result = await db.execute(select(SystemState).where(SystemState.id == "current"))
        return result.scalar_one_or_none()

    async def _allocate_revenue_budgets(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Allocate operating capital to revenue agents based on performance"""
        decisions = []
        snapshot = self.ledger.get_capital_snapshot()
        operating_capital = snapshot.get("operating_capital", 0)
        growth_capital = snapshot.get("growth_capital", 0)
        
        if operating_capital < 5:
            return decisions
        
        revenue_agents = [a for a in self.orchestrator.get_all_agents() if a.agent_type == "revenue"]
        if not revenue_agents:
            return decisions
        
        # Calculate performance scores
        for agent in revenue_agents:
            perf = agent.get_performance_summary()
            score = 0
            if perf["revenue"] > 0:
                score += perf["roi"] * 10
            if perf["profit"] > 0:
                score += perf["profit"] * 2
            if perf["cycles"] > 0:
                score += min(perf["cycles"] * 5, 50)
            score -= perf["consecutive_failures"] * 20
            
            # Allocate budget proportionally
            total_score = sum(max(0, a.get_performance_summary()["roi"] * 10 + a.get_performance_summary()["profit"] * 2 + min(a.get_performance_summary()["cycles"] * 5, 50) - a.get_performance_summary()["consecutive_failures"] * 20, 1) for a in revenue_agents)
            
            if total_score > 0:
                allocation = (max(score, 1) / total_score) * float(operating_capital) * 0.8  # Use 80% of operating capital
                if allocation > float(agent.budget) * 2:  # Significant increase
                    decisions.append({
                        "type": DecisionType.ALLOCATE_BUDGET,
                        "payload": {
                            "agent_id": agent.id,
                            "new_budget": round(allocation, 2),
                            "reason": f"Performance-based allocation: ROI={perf['roi']:.2f}, Profit=${perf['profit']:.2f}",
                        },
                        "priority": "MEDIUM",
                        "agent_id": agent.id,
                    })
        
        return decisions

    async def _evaluate_revenue_reproduction(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Evaluate top revenue agents for cloning/reproduction"""
        decisions = []
        revenue_agents = [a for a in self.orchestrator.get_all_agents() if a.agent_type == "revenue"]
        
        for agent in revenue_agents:
            perf = agent.get_performance_summary()
            
            # Check reproduction criteria
            can_reproduce = (
                perf["profit"] >= 10.0 and
                perf["roi"] >= 1.5 and
                perf["cycles"] >= 5 and
                perf["consecutive_failures"] == 0 and
                agent.reproduction_permissions < 3
            )
            
            if can_reproduce:
                # Create mutated clone with same strategy
                mutations = await self._generate_strategic_mutations(agent)
                mutations["reproduction"] = True
                mutations["parent_strategy"] = agent.strategy_name
                
                decisions.append({
                    "type": DecisionType.CLONE_AGENT,
                    "payload": {
                        "parent_id": agent.id,
                        "mutations": mutations,
                    },
                    "priority": "MEDIUM",
                    "agent_id": agent.id,
                })
                
                # Increment reproduction permissions
                agent.reproduction_permissions += 1
                await agent.persist(db)
        
        return decisions

    async def record_decision(self, db: AsyncSession, decision_type: DecisionType, payload: Dict[str, Any], priority: str = "MEDIUM", agent_id: Optional[str] = None) -> Decision:
        decision = Decision(
            id=str(__import__('uuid').uuid4()),
            agent_id=agent_id,
            decision_type=decision_type,
            payload=payload,
            approval_status=ApprovalStatus.PENDING,
        )
        db.add(decision)
        await db.flush()
        return decision