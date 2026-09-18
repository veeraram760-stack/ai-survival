import asyncio
import uuid
import logging
import traceback
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base import Agent
from .factory import AgentFactory
from ..revenue.simulation import RevenueEngine
from ..models.database import (
    Agent as DB_Agent, AgentStatus, Decision, DecisionType, ApprovalStatus,
    AgentMetric, SystemState, SystemMode
)
from config.settings import settings

logger = logging.getLogger("ai_survival.orchestrator")


class AgentOrchestrator:
    def __init__(self, capital_ledger, risk_manager, ceo: Optional[Any] = None, revenue_engine: Optional[RevenueEngine] = None, execution_engine: Optional[Any] = None, experiment_engine: Optional[Any] = None):
        self.ledger = capital_ledger
        self.risk_manager = risk_manager
        self.factory = AgentFactory(risk_manager)
        self.agents: Dict[str, Agent] = {}
        self.running = False
        self._loop_task = None
        self._db_factory = None
        self.ceo = ceo
        self.revenue_engine = revenue_engine or RevenueEngine()
        self.execution_engine = execution_engine

        # Lazy import: engine.py imports AgentOrchestrator at module top,
        # so a top-level import here would create a circular import cycle.
        from ..evolution.engine import EvolutionSystem
        self.evolution = EvolutionSystem(self, self.risk_manager, experiment_engine)

    def set_db_factory(self, db_factory):
        self._db_factory = db_factory

    async def start(self):
        self.running = True
        self._loop_task = asyncio.create_task(self._main_loop())
        logger.info("Agent orchestrator started")

    async def stop(self):
        self.running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Agent orchestrator stopped")

    async def _main_loop(self):
        await self._bootstrap_initial_agents()
        while self.running:
            try:
                async with self._db_factory() as db:
                    await self._run_cycle(db)
                    await db.commit()
            except Exception as e:
                error_text = str(e)
                if "database is locked" in error_text or "OperationalError" in error_text:
                    logger.warning(f"Database locked in main loop, retrying in 2s: {e}")
                    await asyncio.sleep(2)
                    continue
                logger.error(f"Error in main loop: {e}")
                logger.error(traceback.format_exc())
            await asyncio.sleep(60)

    async def _bootstrap_initial_agents(self):
        if self._db_factory is None:
            logger.warning("DB factory not set, skipping bootstrap")
            return
        async with self._db_factory() as db:
            result = await db.execute(select(func.count(DB_Agent.id)))
            count = result.scalar_one()
            logger.info(f"Bootstrap check: current agent count = {count}")
            if count == 0:
                logger.info("Creating initial agents...")
                await self._create_initial_agents(db)
                await db.commit()
                logger.info("Bootstrapped initial agents")
            else:
                logger.info(f"Database already has {count} agents, skipping bootstrap")
                existing = await db.execute(select(DB_Agent))
                for a in existing.scalars().all():
                    level = getattr(a, "level", "SPECIALIST") or "SPECIALIST"
                    if level == "SELF_IMPROVER":
                        from .self_improver import SelfImproverAgent
                        agent = SelfImproverAgent(
                            agent_id=a.id,
                            agent_type=a.agent_type,
                            strategy=a.strategy,
                        )
                    elif level == "AGENT_DEVELOPER":
                        from .developer import AgentDeveloper
                        agent = AgentDeveloper(
                            agent_id=a.id,
                            agent_type=a.agent_type,
                            strategy=a.strategy,
                        )
                    else:
                        agent = Agent(
                            agent_id=a.id,
                            agent_type=a.agent_type,
                            strategy=a.strategy,
                            parent_id=a.parent_id,
                            generation=a.generation,
                            capabilities=a.capabilities or [],
                        )
                    agent.budget = Decimal(str(a.budget))
                    agent.revenue = Decimal(str(a.revenue))
                    agent.expenses = Decimal(str(a.expenses))
                    agent.profit = Decimal(str(a.profit))
                    agent.roi = a.roi
                    agent.success_rate = a.success_rate
                    agent.status = a.status
                    agent.risk_score = a.risk_score
                    agent.reproduction_permissions = a.reproduction_permissions
                    agent.lifetime_revenue = Decimal(str(a.lifetime_revenue))
                    agent.lifetime_expenses = Decimal(str(a.lifetime_expenses))
                    agent.lifetime_profit = Decimal(str(a.lifetime_profit))
                    agent.days_alive = a.days_alive
                    agent.experiments_count = a.experiments_count
                    agent.successful_experiments = a.successful_experiments
                    agent.failed_experiments = a.failed_experiments
                    agent.creation_timestamp = a.creation_timestamp
                    agent.terminated_at = a.terminated_at
                    agent.level = level
                    agent.supervisor_id = getattr(a, "supervisor_id", None)
                    agent.autonomy_level = getattr(a, "autonomy_level", 3) or 3
                    self.agents[agent.id] = agent
                logger.info(f"Loaded {len(self.agents)} agents from database")

    async def _create_initial_agents(self, db: AsyncSession):
        supervisors = [
            ("RESEARCH", "research_management"),
            ("CONTENT", "content_management"),
            ("BUSINESS", "business_management"),
            ("OPERATIONS", "operations_management"),
            ("QUALITY", "quality_management"),
            ("RISK", "risk_management"),
        ]
        supervisor_ids = {}
        for dept, strategy in supervisors:
            try:
                agent = await self.factory.create_agent(
                    db=db,
                    agent_type=dept.lower(),
                    strategy=strategy,
                    level="SUPERVISOR",
                )
                self.agents[agent.id] = agent
                supervisor_ids[dept] = agent.id
                logger.info(f"Created supervisor: {dept} ({agent.id})")
            except Exception as e:
                logger.error(f"Failed to create supervisor {dept}: {e}")

        self_improver = None
        try:
            self_improver = await self.factory.create_agent(
                db=db,
                agent_type="self_improver",
                strategy="self_optimization",
                level="SELF_IMPROVER",
            )
            self.agents[self_improver.id] = self_improver
            logger.info(f"Created self-improver agent: {self_improver.id}")
        except Exception as e:
            logger.error(f"Failed to create self_improver: {e}")

        agent_developer = None
        try:
            agent_developer = await self.factory.create_agent(
                db=db,
                agent_type="agent_developer",
                strategy="agent_evolution",
                level="AGENT_DEVELOPER",
            )
            self.agents[agent_developer.id] = agent_developer
            logger.info(f"Created agent developer: {agent_developer.id}")
        except Exception as e:
            logger.error(f"Failed to create agent_developer: {e}")

        # Create revenue agents (one per strategy)
        revenue_strategies = [
            ("affiliate_content", "BUSINESS"),
            ("digital_products", "BUSINESS"),
            ("print_on_demand", "BUSINESS"),
            ("shopify_store", "BUSINESS"),
        ]
        for strategy, dept in revenue_strategies:
            try:
                supervisor_id = supervisor_ids.get(dept)
                agent = await self.factory.create_agent(
                    db=db,
                    agent_type="revenue",
                    strategy=strategy,
                    level="SPECIALIST",
                    supervisor_id=supervisor_id,
                )
                agent.supervisor_id = supervisor_id
                self.agents[agent.id] = agent
                logger.info(f"Created revenue agent: {strategy} under {dept} ({agent.id})")
            except Exception as e:
                logger.error(f"Failed to create revenue agent {strategy}: {e}")
                logger.error(traceback.format_exc())

        initial_types = [
            ("research", "market_research", "RESEARCH"),
            ("content", "short_form_video", "CONTENT"),
            ("affiliate", "niche_affiliate", "BUSINESS"),
            ("sales", "cold_outreach", "BUSINESS"),
            ("finance", "budget_tracking", "BUSINESS"),
            ("risk", "risk_monitoring", "RISK"),
            ("digital_product", "simple_products", "BUSINESS"),
            ("market", "paper_trading", "BUSINESS"),
            ("experiment", "hypothesis_testing", "OPERATIONS"),
            ("learning", "knowledge_management", "OPERATIONS"),
            ("factory", "agent_creation", "OPERATIONS"),
        ]
        for agent_type, strategy, dept in initial_types:
            try:
                supervisor_id = supervisor_ids.get(dept)
                agent = await self.factory.create_agent(
                    db=db,
                    agent_type=agent_type,
                    strategy=strategy,
                    level="SPECIALIST",
                    supervisor_id=supervisor_id,
                )
                agent.supervisor_id = supervisor_id
                self.agents[agent.id] = agent
                logger.info(f"Created specialist: {agent_type} under {dept} ({agent.id})")
            except Exception as e:
                logger.error(f"Failed to create {agent_type}: {e}")
                logger.error(traceback.format_exc())

    async def _run_cycle(self, db: AsyncSession):
        await self._update_agent_metrics(db)
        await self._run_revenue_simulations(db)
        await self._fetch_real_conversions(db)
        await self._run_revenue_agents(db)  # Execute revenue strategies
        if hasattr(self, 'ceo') and self.ceo is not None:
            await self._generate_ceo_decisions(db)
        await self._process_decisions(db)
        await self.run_self_improvement_cycle(db)
        await self._run_evolution_step(db)
        await self._evaluate_system_mode(db)
        await self._update_dashboard_state(db)

    async def _run_evolution_step(self, db: AsyncSession) -> Dict[str, Any]:
        """Population-level evolution: reproduce winners, prune failures."""
        result = {"reproductions": [], "pruned": [], "clones": 0}

        capacity = await self.evolution.check_population_capacity(db)
        result["population"] = {k: capacity[k] for k in ("current", "soft_cap", "hard_cap")}

        # 1. Reproduce winners — only when population allows
        if capacity["can_create"]:
            live = [a for a in self.agents.values()
                    if a.status in (AgentStatus.ALIVE, AgentStatus.GROWING, AgentStatus.REPRODUCTION_READY)]
            candidates = sorted(live, key=lambda a: a.lifetime_profit, reverse=True)[:3]

            for parent in candidates:
                verdict = await self.evolution.evaluate_reproduction(db, parent.id)
                if not verdict.get("eligible"):
                    continue
                child = await self.evolution.clone_winner(
                    db, parent.id,
                    mutations={"strategy": f"{parent.strategy}_v{parent.generation + 1}"},
                )
                result["reproductions"].append(child)
                result["clones"] += 1
                break  # rate limit: at most 1 clone per cycle (hard cap is the backstop)

        # 2. Prune failed agents (defensive cleanup)
        result["pruned"] = await self.evolution.prune_agents(db)

        logger.info(f"Evolution step: {result}")
        return result

    async def _fetch_real_conversions(self, db: AsyncSession):
        """Periodically fetch real conversions from affiliate networks"""
        from ..tools import tool_registry

        # Only run every 10 cycles to avoid API rate limits
        if not hasattr(self, '_conversion_fetch_counter'):
            self._conversion_fetch_counter = 0
        self._conversion_fetch_counter += 1

        if self._conversion_fetch_counter % 10 != 0:
            return

        try:
            conversion_tool = tool_registry.get("track_conversions")
            if not conversion_tool:
                return

            result = await conversion_tool.execute(network="all")

            if result.get("status") == "success":
                networks = result.get("networks", {})
                for network_name, network_data in networks.items():
                    if network_data.get("status") == "success":
                        commissions = network_data.get("commissions", [])
                        for commission_data in commissions:
                            commission_amount = float(commission_data.get("commission", 0))
                            if commission_amount > 0:
                                transaction_id = commission_data.get("transaction_id") or commission_data.get("id")
                                if transaction_id:
                                    # Check if already recorded
                                    from sqlalchemy import select
                                    from ..models.database import Transaction, TransactionStatus
                                    existing = await db.execute(
                                        select(Transaction).where(
                                            Transaction.action == f"affiliate_commission_{network_name}",
                                            Transaction.approval_reason.like(f"%{transaction_id}%")
                                        )
                                    )
                                    if not existing.scalar_one_or_none():
                                        txn = await self.ledger.record_transaction(
                                            db=db,
                                            agent_id=None,  # Would need to map to agent
                                            category="real_revenue",
                                            action=f"affiliate_commission_{network_name}",
                                            amount=commission_amount,
                                            risk_level="LOW",
                                            approval_reason=f"Real {network_name} commission fetched: transaction {transaction_id}",
                                        )
                                        # The network confirmed this commission, so it counts as
                                        # received money — mark it COMPLETED immediately.
                                        await self.ledger.commit_transaction(db, txn.id)
                                        logger.info(f"Recorded {network_name} commission: ${commission_amount:.2f}")
            await db.commit()
        except Exception as e:
            logger.error(f"Error fetching real conversions: {e}")

    async def _run_revenue_simulations(self, db: AsyncSession):
        for agent in self.agents.values():
            if agent.status.value not in ["ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY"]:
                continue
            try:
                result = await self._execute_agent_work(db, agent)
                if not result:
                    continue
                
                await db.commit()
                
                from sqlalchemy import select
                from ..models.database import Agent as DB_Agent
                db_agent_result = await db.execute(select(DB_Agent).where(DB_Agent.id == agent.id))
                db_agent = db_agent_result.scalar_one_or_none()
                if db_agent:
                    agent.experiments_count = db_agent.experiments_count
                    agent.successful_experiments = db_agent.successful_experiments
                    agent.failed_experiments = db_agent.failed_experiments
                    agent.status = db_agent.status
                
                revenue = Decimal(str(result.get("revenue", 0)))
                expenses = Decimal(str(result.get("expenses", 0)))
                is_real = result.get("real", False)

                if settings.real_money_only and not is_real:
                    revenue = Decimal("0")

                agent.revenue += revenue
                agent.expenses += expenses
                agent.profit = agent.revenue - agent.expenses
                agent.lifetime_revenue += revenue
                agent.lifetime_expenses += expenses
                agent.lifetime_profit = agent.lifetime_revenue - agent.lifetime_expenses
                if agent.expenses > 0:
                    agent.roi = float(agent.profit / agent.expenses)

                category_prefix = "real" if is_real else "simulated"
                if revenue > 0:
                    await self.ledger.record_transaction(
                        db=db,
                        agent_id=agent.id,
                        category=f"{category_prefix}_revenue",
                        action=f"{category_prefix}_{agent.agent_type}_earnings",
                        amount=revenue,
                        risk_level="LOW",
                        approval_reason="Automated revenue" + (" from real tools" if is_real else " simulation"),
                    )
                if expenses > 0:
                    await self.ledger.record_transaction(
                        db=db,
                        agent_id=agent.id,
                        category=f"{category_prefix}_expenses",
                        action=f"{category_prefix}_{agent.agent_type}_costs",
                        amount=-expenses,
                        risk_level="LOW",
                        approval_reason="Automated expense" + (" from real tools" if is_real else " simulation"),
                    )
            except Exception as e:
                logger.error(f"Revenue simulation error for agent {agent.id}: {e}")

    async def _execute_agent_work(self, db: AsyncSession, agent, task_type: Optional[str] = None) -> Dict[str, Any]:
        if self.execution_engine:
            if not task_type:
                task_type = self._map_agent_to_task(agent.agent_type)
            task_data = {
                "agent_type": agent.agent_type,
                "strategy": agent.strategy,
                "days_alive": agent.days_alive,
                "capabilities": agent.capabilities,
            }
            try:
                result = await self.execution_engine.execute_agent_task(
                    db, agent.id, task_type, task_data
                )
                if result.get("status") in ("success", "partial"):
                    revenue = result.get("revenue", 0)
                    if revenue == 0 and not result.get("real"):
                        return self.revenue_engine.run_daily_simulation(agent)
                    return {
                        "revenue": revenue,
                        "expenses": result.get("expenses", 0),
                        "real": result.get("real", False),
                        "tool_results": result.get("tool_results"),
                    }
            except Exception as e:
                logger.error(f"Real task execution failed for agent {agent.id}: {e}")
                if settings.real_money_only:
                    return {"revenue": 0, "expenses": 0, "real": False, "error": str(e)}

        # Only fall back to simulation if NOT in real_money_only mode
        if settings.real_money_only:
            return {"revenue": 0, "expenses": 0, "real": False, "error": "Real execution failed and real_money_only mode enabled"}
        if self.revenue_engine:
            return self.revenue_engine.run_daily_simulation(agent)
        return {"revenue": 0, "expenses": 0, "real": False}

    def _map_agent_to_task(self, agent_type: str) -> str:
        mapping = {
            "web_research": "market_research",
            "script": "content_generation",
            "marketing": "affiliate_marketing",
            "sales": "sales_outreach",
            "finance": "budget_optimization",
            "risk_monitoring": "risk_assessment",
            "product_creation": "product_creation",
            "market_analysis": "market_analysis",
            "experiment": "experiment_execution",
            "learning": "knowledge_update",
            "agent_evolution": "agent_evolution",
            "supervisor": "generic_task",
        }
        return mapping.get(agent_type, "generic_task")

    async def _generate_ceo_decisions(self, db: AsyncSession):
        if not hasattr(self, 'ceo') or self.ceo is None:
            logger.warning("CEO not attached to orchestrator")
            return
        try:
            decisions = await self.ceo.analyze_and_decide(db)
            logger.info(f"CEO generated {len(decisions)} decisions")
            for decision_data in decisions:
                await self.ceo.record_decision(
                    db,
                    decision_data["type"],
                    decision_data["payload"],
                    decision_data.get("priority", "MEDIUM"),
                    decision_data.get("agent_id"),
                )
            if decisions:
                await db.commit()
        except Exception as e:
            logger.error(f"Error in CEO decision cycle: {e}")

    async def _update_agent_metrics(self, db: AsyncSession):
        for agent in self.agents.values():
            if agent.status in [AgentStatus.ALIVE, AgentStatus.TESTING, AgentStatus.GROWING, AgentStatus.REPRODUCTION_READY]:
                agent.days_alive += 1
                if agent.experiments_count > 0:
                    agent.success_rate = agent.successful_experiments / agent.experiments_count
                if agent.expenses > 0:
                    agent.roi = float(agent.profit / agent.expenses)
                await agent.update_metrics(db)

    async def _process_decisions(self, db: AsyncSession):
        pending_result = await db.execute(
            select(Decision).where(Decision.approval_status == ApprovalStatus.PENDING)
        )
        pending_decisions = pending_result.scalars().all()
        for decision in pending_decisions:
            await self._execute_decision(db, decision)

    async def _execute_decision(self, db: AsyncSession, decision: Decision):
        decision_type = decision.decision_type
        payload = decision.payload or {}

        if decision_type == DecisionType.CREATE_AGENT:
            try:
                agent = await self.factory.create_agent(
                    db=db,
                    agent_type=payload.get("agent_type", "generic"),
                    strategy=payload.get("strategy", "default"),
                    parent_id=payload.get("parent_id"),
                    capabilities=payload.get("capabilities"),
                )
                self.agents[agent.id] = agent
                decision.approval_status = ApprovalStatus.EXECUTED
                decision.executed_at = datetime.now(timezone.utc)
                decision.result = {"agent_id": agent.id}
            except Exception as e:
                decision.approval_status = ApprovalStatus.DENIED
                decision.risk_assessment = str(e)

        elif decision_type == DecisionType.CLONE_AGENT:
            promote_agent_id = payload.get("promote_agent_id")
            if promote_agent_id and promote_agent_id in self.agents:
                agent = self.agents[promote_agent_id]
                if agent.status.value == "TESTING":
                    from ..models.database import AgentStatus
                    agent.status = AgentStatus.ALIVE
                    db_agent_result = await db.execute(select(DB_Agent).where(DB_Agent.id == promote_agent_id))
                    db_agent = db_agent_result.scalar_one_or_none()
                    if db_agent:
                        db_agent.status = AgentStatus.ALIVE
                    decision.approval_status = ApprovalStatus.EXECUTED
                    decision.executed_at = datetime.now(timezone.utc)
                    decision.result = {"agent_id": promote_agent_id, "new_status": "ALIVE"}
                    return
            parent_id = payload.get("parent_id")
            if parent_id and parent_id in self.agents:
                parent = self.agents[parent_id]
                mutations = payload.get("mutations")
                try:
                    child = await self.factory.clone_agent(db, parent, mutations)
                    self.agents[child.id] = child
                    decision.approval_status = ApprovalStatus.EXECUTED
                    decision.executed_at = datetime.now(timezone.utc)
                    decision.result = {"child_id": child.id}
                except Exception as e:
                    decision.approval_status = ApprovalStatus.DENIED
                    decision.risk_assessment = str(e)

        elif decision_type == DecisionType.TERMINATE_AGENT:
            agent_id = payload.get("agent_id")
            if agent_id and agent_id in self.agents:
                agent = self.agents[agent_id]
                await self.factory.terminate_agent(
                    db, agent, payload.get("reason", "Performance criteria not met"),
                    payload.get("useful_discoveries")
                )
                del self.agents[agent_id]
                decision.approval_status = ApprovalStatus.EXECUTED
                decision.executed_at = datetime.now(timezone.utc)

    async def _evaluate_system_mode(self, db: AsyncSession):
        mode = await self.risk_manager.evaluate_system_mode(db)
        snapshot = await db.execute(select(SystemState).where(SystemState.id == "current"))
        state = snapshot.scalar_one_or_none()
        if not state:
            state = SystemState(id="current", current_mode=mode, capital=float(self.ledger.current_balance))
            db.add(state)
        else:
            state.current_mode = mode
            state.capital = float(self.ledger.current_balance)
            state.reserve = float(self.ledger.survival_reserve)
            state.operating = float(self.ledger.operating_capital)
            state.growth = float(self.ledger.growth_capital)
            state.total_agents = len(self.agents)
            active_count = sum(1 for a in self.agents.values() if a.status in [
                AgentStatus.ALIVE, AgentStatus.TESTING, AgentStatus.GROWING, AgentStatus.REPRODUCTION_READY
            ])
            state.active_agents = active_count
            state.last_updated = datetime.now(timezone.utc)

    async def _update_dashboard_state(self, db: AsyncSession):
        pass

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)

    def get_all_agents(self) -> List[Agent]:
        return list(self.agents.values())

    def get_agents_by_type(self, agent_type: str) -> List[Agent]:
        return [a for a in self.agents.values() if a.agent_type == agent_type]

    def get_supervisors(self) -> List[Agent]:
        return [a for a in self.agents.values() if getattr(a, "level", "SPECIALIST") == "SUPERVISOR"]

    def get_specialists(self, supervisor_id: Optional[str] = None) -> List[Agent]:
        specialists = [a for a in self.agents.values() if getattr(a, "level", "SPECIALIST") == "SPECIALIST"]
        if supervisor_id:
            specialists = [a for a in specialists if getattr(a, "supervisor_id", None) == supervisor_id]
        return specialists

    def get_supervisor_for_agent(self, agent_id: str) -> Optional[Agent]:
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        supervisor_id = getattr(agent, "supervisor_id", None)
        if supervisor_id:
            return self.agents.get(supervisor_id)
        return None

    def get_lineage(self, agent_id: str) -> Dict[str, Any]:
        agent = self.agents.get(agent_id)
        if not agent:
            return {}
        lineage = {"id": agent_id, "type": agent.agent_type, "level": getattr(agent, "level", "SPECIALIST"), "children": []}
        for child in self.agents.values():
            if child.parent_id == agent_id:
                lineage["children"].append(self.get_lineage(child.id))
        return lineage

    def get_hierarchy_tree(self) -> Dict[str, Any]:
        supervisors = self.get_supervisors()
        tree = {"supervisors": [], "specialists": []}
        for sup in supervisors:
            sup_data = sup.to_dict()
            sup_data["specialists"] = [a.to_dict() for a in self.get_specialists(sup.id)]
            tree["supervisors"].append(sup_data)
        unassigned = [a.to_dict() for a in self.get_specialists() if not getattr(a, "supervisor_id", None)]
        tree["specialists"] = unassigned
        return tree

    def get_self_improver(self) -> Optional[Agent]:
        for a in self.agents.values():
            if getattr(a, "level", None) == "SELF_IMPROVER":
                return a
        return None

    def get_agent_developer(self) -> Optional[Agent]:
        for a in self.agents.values():
            if getattr(a, "level", None) == "AGENT_DEVELOPER":
                return a
        return None

    def get_self_improving_agents(self) -> List[Agent]:
        return [a for a in self.agents.values() if getattr(a, "level", None) in ("SELF_IMPROVER", "AGENT_DEVELOPER")]

    async def run_self_improvement_cycle(self, db: AsyncSession) -> Dict[str, Any]:
        self_improver = self.get_self_improver()
        developer = self.get_agent_developer()
        result = {"cycle": getattr(self_improver, "improvement_cycle", 0) + 1 if self_improver else 1}

        if self_improver:
            try:
                developer_id = developer.id if developer else None
                cycle_result = await self_improver.run_self_improvement_cycle(
                    db, self, developer_agent_id=developer_id
                )
                result["self_improvement"] = cycle_result

                from backend.models.improvement import AgentImprovement
                improvement = AgentImprovement(
                    id=str(__import__('uuid').uuid4()),
                    agent_id=self_improver.id,
                    cycle=cycle_result.get("cycle", result["cycle"]),
                    status=cycle_result.get("status", "UNKNOWN"),
                    self_analysis=cycle_result.get("self_analysis"),
                    weaknesses_found=cycle_result.get("weaknesses", []),
                    improvement_plan=cycle_result.get("improvement_plan"),
                    execution_results=cycle_result.get("execution"),
                    learning=cycle_result.get("learning"),
                    improvements_applied=0,
                    improvements_failed=0,
                )
                if cycle_result.get("execution"):
                    improvement.improvements_applied = cycle_result["execution"].get("successful_improvements", 0)
                    improvement.improvements_failed = cycle_result["execution"].get("failed_improvements", 0)
                if cycle_result.get("learning"):
                    improvement.learning = cycle_result["learning"]
                db.add(improvement)
                await db.flush()

                if self_improver.auto_improve_enabled and cycle_result.get("status") != "FAILED":
                    try:
                        evolve_result = await developer.evolve_strategy(db, self_improver.id)
                        result["strategy_evolution"] = evolve_result
                    except Exception as e:
                        logger.error(f"Strategy evolution failed: {e}")
            except Exception as e:
                logger.error(f"Self-improvement cycle recording failed: {e}")

        if developer:
            try:
                dev_result = await developer.run_development_cycle(db, self)
                result["development"] = dev_result
            except Exception as e:
                logger.error(f"Agent development cycle failed: {e}")
                result["development"] = {"status": "error", "error": str(e)}

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return result

    async def _run_revenue_agents(self, db: AsyncSession):
        """Execute revenue generation cycles for all revenue agents"""
        revenue_agents = [a for a in self.agents.values() if a.agent_type == "revenue"]
        
        for agent in revenue_agents:
            if agent.status.value not in ["ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY"]:
                continue
            
            try:
                # Run the agent's revenue strategy
                context = {
                    "niche": getattr(agent, "niche", "tech"),
                    "budget": float(agent.budget) if agent.budget else 0.5,
                }
                result = await agent.execute_cycle(db, self.ledger, context)
                
                logger.info(f"Revenue agent {agent.id} ({agent.strategy_name}): {result.get('status')} - "
                          f"Revenue: ${result.get('revenue', 0):.2f}, Expenses: ${result.get('expenses', 0):.2f}")
                
            except Exception as e:
                logger.error(f"Revenue agent {agent.id} cycle failed: {e}")

    def get_revenue_agents(self) -> List[Agent]:
        """Get all revenue agents"""
        return [a for a in self.agents.values() if a.agent_type == "revenue"]

    def get_revenue_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all revenue agents"""
        revenue_agents = self.get_revenue_agents()
        total_revenue = sum(float(a.revenue) for a in revenue_agents)
        total_expenses = sum(float(a.expenses) for a in revenue_agents)
        total_profit = sum(float(a.profit) for a in revenue_agents)
        
        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "total_profit": total_profit,
            "roi": (total_profit / total_expenses) if total_expenses > 0 else 0,
            "agent_count": len(revenue_agents),
            "by_strategy": {
                a.strategy_name: a.get_performance_summary() for a in revenue_agents
            }
        }
