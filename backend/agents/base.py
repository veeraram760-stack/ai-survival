import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.database import Agent as DB_Agent, AgentStatus, AgentMetric, AgentLineage, AgentBudget, Transaction
from config.settings import settings


class Agent:
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        strategy: str = "default",
        parent_id: Optional[str] = None,
        generation: int = 0,
        capabilities: Optional[List[str]] = None,
    ):
        self.id = agent_id
        self.parent_id = parent_id
        self.generation = generation
        self.agent_type = agent_type
        self.strategy = strategy
        self.capabilities = capabilities or []
        self.budget = Decimal("0")
        self.revenue = Decimal("0")
        self.expenses = Decimal("0")
        self.profit = Decimal("0")
        self.roi = 0.0
        self.success_rate = 0.0
        self.status = AgentStatus.TESTING
        self.risk_score = 0.0
        self.reproduction_permissions = 0
        self.lifetime_revenue = Decimal("0")
        self.lifetime_expenses = Decimal("0")
        self.lifetime_profit = Decimal("0")
        self.days_alive = 0
        self.experiments_count = 0
        self.successful_experiments = 0
        self.failed_experiments = 0
        self.creation_timestamp = datetime.now(timezone.utc)
        self.terminated_at = None
        self.level = "SPECIALIST"
        self.supervisor_id = None
        self.autonomy_level = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "agent_type": self.agent_type,
            "strategy": self.strategy,
            "capabilities": self.capabilities,
            "budget": float(self.budget),
            "revenue": float(self.revenue),
            "expenses": float(self.expenses),
            "profit": float(self.profit),
            "roi": self.roi,
            "success_rate": self.success_rate,
            "status": self.status.value,
            "risk_score": self.risk_score,
            "reproduction_permissions": self.reproduction_permissions,
            "lifetime_revenue": float(self.lifetime_revenue),
            "lifetime_expenses": float(self.lifetime_expenses),
            "lifetime_profit": float(self.lifetime_profit),
            "days_alive": self.days_alive,
            "experiments_count": self.experiments_count,
            "successful_experiments": self.successful_experiments,
            "failed_experiments": self.failed_experiments,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "level": getattr(self, "level", "SPECIALIST"),
            "supervisor_id": getattr(self, "supervisor_id", None),
            "autonomy_level": getattr(self, "autonomy_level", 3),
        }

    async def persist(self, db: AsyncSession):
        db_agent = DB_Agent(
            id=self.id,
            parent_id=self.parent_id,
            generation=self.generation,
            agent_type=self.agent_type,
            strategy=self.strategy,
            capabilities=self.capabilities,
            budget=float(self.budget),
            revenue=float(self.revenue),
            expenses=float(self.expenses),
            profit=float(self.profit),
            roi=self.roi,
            success_rate=self.success_rate,
            status=self.status,
            risk_score=self.risk_score,
            reproduction_permissions=self.reproduction_permissions,
            lifetime_revenue=float(self.lifetime_revenue),
            lifetime_expenses=float(self.lifetime_expenses),
            lifetime_profit=float(self.lifetime_profit),
            days_alive=self.days_alive,
            experiments_count=self.experiments_count,
            successful_experiments=self.successful_experiments,
            failed_experiments=self.failed_experiments,
            creation_timestamp=self.creation_timestamp,
            terminated_at=self.terminated_at,
            level=getattr(self, "level", "SPECIALIST"),
            supervisor_id=getattr(self, "supervisor_id", None),
            autonomy_level=getattr(self, "autonomy_level", 3),
        )
        db.add(db_agent)
        await db.flush()

    async def load(self, db: AsyncSession, agent_id: str):
        result = await db.execute(select(DB_Agent).where(DB_Agent.id == agent_id))
        db_agent = result.scalar_one_or_none()
        if not db_agent:
            raise ValueError(f"Agent {agent_id} not found")
        self.id = db_agent.id
        self.parent_id = db_agent.parent_id
        self.generation = db_agent.generation
        self.agent_type = db_agent.agent_type
        self.strategy = db_agent.strategy
        self.capabilities = db_agent.capabilities or []
        self.budget = Decimal(str(db_agent.budget))
        self.revenue = Decimal(str(db_agent.revenue))
        self.expenses = Decimal(str(db_agent.expenses))
        self.profit = Decimal(str(db_agent.profit))
        self.roi = db_agent.roi
        self.success_rate = db_agent.success_rate
        self.status = db_agent.status
        self.risk_score = db_agent.risk_score
        self.reproduction_permissions = db_agent.reproduction_permissions
        self.lifetime_revenue = Decimal(str(db_agent.lifetime_revenue))
        self.lifetime_expenses = Decimal(str(db_agent.lifetime_expenses))
        self.lifetime_profit = Decimal(str(db_agent.lifetime_profit))
        self.days_alive = db_agent.days_alive
        self.experiments_count = db_agent.experiments_count
        self.successful_experiments = db_agent.successful_experiments
        self.failed_experiments = db_agent.failed_experiments
        self.creation_timestamp = db_agent.creation_timestamp
        self.terminated_at = db_agent.terminated_at
        self.level = getattr(db_agent, "level", "SPECIALIST") or "SPECIALIST"
        self.supervisor_id = getattr(db_agent, "supervisor_id", None)
        self.autonomy_level = getattr(db_agent, "autonomy_level", 3) or 3

    async def record_transaction(
        self, db: AsyncSession, category: str, action: str, amount: Decimal, risk_level: str = "LOW", approval_reason: Optional[str] = None
    ) -> Transaction:
        txn = Transaction(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            agent_id=self.id,
            category=category,
            action=action,
            amount=amount,
            balance_before=Decimal("0"),
            balance_after=Decimal("0"),
            status="PENDING",
            risk_level=risk_level,
            approval_reason=approval_reason,
        )
        db.add(txn)
        await db.flush()
        return txn

    async def update_metrics(self, db: AsyncSession):
        metric = AgentMetric(
            id=str(uuid.uuid4()),
            agent_id=self.id,
            date=datetime.now(timezone.utc),
            revenue=float(self.revenue),
            expenses=float(self.expenses),
            profit=float(self.profit),
            roi=self.roi,
            success_rate=self.success_rate,
            experiments_run=self.experiments_count,
            experiments_success=self.successful_experiments,
        )
        db.add(metric)
