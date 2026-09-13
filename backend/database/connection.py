from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.pool import NullPool, StaticPool
import logging
from config.settings import settings

logger = logging.getLogger("ai_survival.database")

if settings.database_url.startswith("sqlite"):
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=StaticPool,
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    from ..models.database import (
        Agent, AgentLineage, AgentMetric, AgentBudget, Experiment, Strategy,
        Decision, ReproductionEvent, AgentDeath, RiskEvent, SystemState,
        LearningMemory, Opportunity, ContentAsset, Campaign, Trade, AuditLog,
        Transaction, Company, Withdrawal, Task, ShortTermMemory, ProjectMemory,
        LongTermMemory, AgentPerformance
    )
    from ..models.improvement import AgentImprovement
    async with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=30000"))
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_short_term_memory_task ON short_term_memory(task_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_short_term_memory_project ON short_term_memory(project_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_project_memory_project ON project_memory(project_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_long_term_memory_category ON long_term_memory(category)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_performance_agent ON agent_performance(agent_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_improvements_agent ON agent_improvements(agent_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_improvements_cycle ON agent_improvements(cycle)"))
        except Exception:
            pass
    logger.info("Database initialized")


async def close_db():
    await engine.dispose()
    logger.info("Database connection closed")


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


class DBSessionFactory:
    def __init__(self, session_maker=async_session_maker):
        self.session_maker = session_maker

    @asynccontextmanager
    async def session(self):
        async with self.session_maker() as session:
            try:
                yield session
            finally:
                await session.close()
