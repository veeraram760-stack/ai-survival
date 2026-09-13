"""
Background scheduler for automatic affiliate marketing tasks and revenue cycles
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from config.settings import settings

logger = logging.getLogger("ai_survival.scheduler")


class AutoPromotionScheduler:
    """Schedule automatic affiliate marketing tasks"""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.running = False
        self.task_interval = getattr(settings, "auto_promotion_interval_minutes", 60)
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0

    async def start(self):
        """Start the scheduler loop"""
        self.running = True
        logger.info(f"Auto-promotion scheduler started, interval: {self.task_interval} minutes")
        await asyncio.sleep(10)
        while self.running:
            try:
                await self._run_promotion_cycle()
                self.last_run = datetime.now(timezone.utc)
                self.run_count += 1
            except Exception as e:
                self.error_count += 1
                logger.error(f"Scheduler cycle failed: {e}")
            await asyncio.sleep(self.task_interval * 60)

    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Auto-promotion scheduler stopped")

    async def _run_promotion_cycle(self):
        """Run one promotion cycle across all eligible agents"""
        if not self.orchestrator:
            logger.warning("Orchestrator not set, skipping promotion cycle")
            return

        agents = self.orchestrator.get_all_agents()
        eligible_agents = [
            a for a in agents
            if getattr(a, "status", None) and a.status.value in ("ALIVE", "TESTING", "GROWING")
        ]

        if not eligible_agents:
            logger.info("No eligible agents for promotion cycle")
            return

        results: List[Dict[str, Any]] = []
        execution_engine = getattr(self.orchestrator, "execution_engine", None)
        if not execution_engine:
            logger.warning("Execution engine not available on orchestrator")
            return

        db_factory = getattr(self.orchestrator, "_db_factory", None)
        if not db_factory:
            logger.warning("DB factory not available on orchestrator")
            return

        for agent in eligible_agents:
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    async with db_factory() as db:
                        result = await execution_engine.execute_agent_task(
                            db=db,
                            agent_id=agent.id,
                            task_type="auto_promotion",
                            task_data={"agent_id": agent.id, "agent_type": agent.agent_type},
                        )
                    results.append({"agent_id": agent.id, "result": result})
                    break
                except Exception as e:
                    error_text = str(e)
                    if "database is locked" in error_text or "OperationalError" in error_text:
                        if attempt < max_retries:
                            wait = 2 * attempt
                            logger.warning(f"Database locked for agent {agent.id}, retry {attempt}/{max_retries} in {wait}s")
                            await asyncio.sleep(wait)
                            continue
                    logger.error(f"Auto promotion failed for agent {agent.id}: {e}")
                    results.append({"agent_id": agent.id, "error": str(e)})
                    break

        success_count = sum(1 for r in results if r.get("result", {}).get("status") != "failed")
        logger.info(f"Promotion cycle complete: {success_count}/{len(results)} succeeded")


class RevenueCycleScheduler:
    """Schedule revenue agent strategy cycles"""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.running = False
        self.cycle_interval = getattr(settings, "revenue_cycle_interval_minutes", 15)
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0

    async def start(self):
        """Start the scheduler loop"""
        self.running = True
        logger.info(f"Revenue cycle scheduler started, interval: {self.cycle_interval} minutes")
        await asyncio.sleep(30)  # Stagger start
        while self.running:
            try:
                await self._run_revenue_cycle()
                self.last_run = datetime.now(timezone.utc)
                self.run_count += 1
            except Exception as e:
                self.error_count += 1
                logger.error(f"Revenue cycle failed: {e}")
            await asyncio.sleep(self.cycle_interval * 60)

    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Revenue cycle scheduler stopped")

    async def _run_revenue_cycle(self):
        """Run revenue strategy cycles for all revenue agents"""
        if not self.orchestrator:
            logger.warning("Orchestrator not set, skipping revenue cycle")
            return

        revenue_agents = [a for a in self.orchestrator.get_all_agents() if a.agent_type == "revenue"]
        if not revenue_agents:
            logger.info("No revenue agents for revenue cycle")
            return

        db_factory = getattr(self.orchestrator, "_db_factory", None)
        if not db_factory:
            logger.warning("DB factory not available on orchestrator")
            return

        ledger = getattr(self.orchestrator, "ledger", None)
        if not ledger:
            logger.warning("Ledger not available on orchestrator")
            return

        results = []
        for agent in revenue_agents:
            if agent.status.value not in ("ALIVE", "TESTING", "GROWING", "REPRODUCTION_READY"):
                continue
            try:
                async with db_factory() as db:
                    if hasattr(agent, 'execute_cycle'):
                        context = {"niche": getattr(agent, "niche", "tech")}
                        result = await agent.execute_cycle(db, ledger, context)
                        results.append({"agent_id": agent.id, "strategy": agent.strategy_name, "result": result})
                        logger.info(f"Revenue agent {agent.id} ({agent.strategy_name}): {result.get('status')} - Rev: ${result.get('revenue', 0):.2f}")
            except Exception as e:
                logger.error(f"Revenue cycle failed for agent {agent.id}: {e}")
                results.append({"agent_id": agent.id, "error": str(e)})

        success_count = sum(1 for r in results if r.get("result", {}).get("status") == "success")
        logger.info(f"Revenue cycle complete: {success_count}/{len(results)} succeeded")


class AnalyticsScheduler:
    """Schedule periodic analytics and reporting"""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.running = False
        self.interval = 60  # Hourly
        self.last_run: Optional[datetime] = None

    async def start(self):
        self.running = True
        logger.info("Analytics scheduler started")
        await asyncio.sleep(60)
        while self.running:
            try:
                await self._run_analytics()
                self.last_run = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(f"Analytics cycle failed: {e}")
            await asyncio.sleep(self.interval * 60)

    async def stop(self):
        self.running = False
        logger.info("Analytics scheduler stopped")

    async def _run_analytics(self):
        if not self.orchestrator:
            return
        
        db_factory = getattr(self.orchestrator, "_db_factory", None)
        if not db_factory:
            return

        async with db_factory() as db:
            from sqlalchemy import select, func
            from ..models.database import Agent, Transaction, AgentMetric
            
            # Agent performance snapshot
            agents = self.orchestrator.get_all_agents()
            revenue_agents = [a for a in agents if a.agent_type == "revenue"]
            
            # Store metrics
            for agent in agents:
                metric = AgentMetric(
                    id=str(__import__('uuid').uuid4()),
                    agent_id=agent.id,
                    date=datetime.now(timezone.utc),
                    revenue=float(agent.revenue),
                    expenses=float(agent.expenses),
                    profit=float(agent.profit),
                    roi=agent.roi,
                    success_rate=agent.success_rate,
                    experiments_run=agent.experiments_count,
                    experiments_success=agent.successful_experiments,
                )
                db.add(metric)
            
            await db.commit()
            logger.info(f"Analytics snapshot stored for {len(agents)} agents")


_scheduler: Optional[AutoPromotionScheduler] = None
_revenue_scheduler: Optional[RevenueCycleScheduler] = None
_analytics_scheduler: Optional[AnalyticsScheduler] = None


def get_scheduler(orchestrator=None) -> AutoPromotionScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AutoPromotionScheduler(orchestrator=orchestrator)
    elif orchestrator and not _scheduler.orchestrator:
        _scheduler.orchestrator = orchestrator
    return _scheduler


def get_revenue_scheduler(orchestrator=None) -> RevenueCycleScheduler:
    global _revenue_scheduler
    if _revenue_scheduler is None:
        _revenue_scheduler = RevenueCycleScheduler(orchestrator=orchestrator)
    elif orchestrator and not _revenue_scheduler.orchestrator:
        _revenue_scheduler.orchestrator = orchestrator
    return _revenue_scheduler


def get_analytics_scheduler(orchestrator=None) -> AnalyticsScheduler:
    global _analytics_scheduler
    if _analytics_scheduler is None:
        _analytics_scheduler = AnalyticsScheduler(orchestrator=orchestrator)
    elif orchestrator and not _analytics_scheduler.orchestrator:
        _analytics_scheduler.orchestrator = orchestrator
    return _analytics_scheduler
