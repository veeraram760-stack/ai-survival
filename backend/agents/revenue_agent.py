"""
Revenue Agent - Executes revenue-generating strategies autonomously
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base import Agent, AgentStatus
from .strategies import get_strategy, list_strategies
from ..models.database import Agent as DB_Agent, Transaction
from ..finance.ledger import CapitalLedger
from config.settings import settings

logger = logging.getLogger("ai_survival.agents.revenue")


class RevenueAgent(Agent):
    """Agent specialized in executing revenue strategies"""

    def __init__(
        self,
        agent_id: str,
        strategy_name: str = "multi_channel",
        parent_id: Optional[str] = None,
        generation: int = 0,
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="revenue",
            strategy=strategy_name,
            parent_id=parent_id,
            generation=generation,
            capabilities=["revenue_generation", "strategy_execution", "multi_channel"],
        )
        self.level = "SPECIALIST"
        self.strategy_name = strategy_name
        # strategy stays as the string name (persisted to DB String column);
        # the executable object lives in strategy_handler
        self.strategy_handler = get_strategy(strategy_name)
        self.cycle_count = 0
        self.last_execution = None
        self.consecutive_failures = 0

    async def execute_cycle(self, db: AsyncSession, ledger: CapitalLedger, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute one revenue generation cycle"""
        # Lazy-resolve handler for agents loaded from DB (Agent.load doesn't set strategy_handler)
        handler = getattr(self, "strategy_handler", None)
        if handler is None:
            name = getattr(self, "strategy_name", None) or self.strategy or "multi_channel"
            self.strategy_name = name
            handler = get_strategy(name)
            self.strategy_handler = handler
        if not handler:
            return {"status": "failed", "error": f"Strategy {self.strategy_name} not found"}

        self.cycle_count += 1
        self.last_execution = datetime.now(timezone.utc)
        context = context or {}

        # Check if we can afford to run
        can_spend, reason = ledger.can_spend(Decimal(str(settings.max_single_spend)))
        if not can_spend:
            logger.warning(f"Revenue agent {self.id}: Cannot spend - {reason}")
            return {"status": "skipped", "reason": reason}

        logger.info(f"Revenue agent {self.id} executing {self.strategy_name} strategy (cycle {self.cycle_count})")

        try:
            # Execute strategy
            result = await self.strategy_handler.execute(self, context)

            # Update agent metrics
            if result.get("status") == "success":
                self.consecutive_failures = 0
                revenue = Decimal(str(result.get("revenue", 0)))
                expenses = Decimal(str(result.get("expenses", 0)))

                self.revenue += revenue
                self.expenses += expenses
                self.profit = self.revenue - self.expenses
                self.lifetime_revenue += revenue
                self.lifetime_expenses += expenses
                self.lifetime_profit = self.lifetime_revenue - self.lifetime_expenses

                if self.expenses > 0:
                    self.roi = float(self.profit / self.expenses)

                # Record transactions
                if revenue > 0:
                    await ledger.record_transaction(
                        db=db,
                        agent_id=self.id,
                        category="real_revenue",
                        action=f"{self.strategy_name}_revenue",
                        amount=revenue,
                        risk_level="LOW",
                        approval_reason=f"Revenue from {self.strategy_name} strategy",
                    )
                if expenses > 0:
                    await ledger.record_transaction(
                        db=db,
                        agent_id=self.id,
                        category="simulated_expenses" if not settings.real_money_only else "real_expenses",
                        action=f"{self.strategy_name}_costs",
                        amount=-expenses,
                        risk_level="LOW",
                        approval_reason=f"Costs for {self.strategy_name} strategy",
                    )

                # Update status based on performance
                if self.profit > 100:
                    self.status = AgentStatus.GROWING
                elif self.profit > 10:
                    self.status = AgentStatus.ALIVE
                elif self.cycle_count > 10 and self.profit <= 0:
                    self.status = AgentStatus.TESTING

            else:
                self.consecutive_failures += 1
                if self.consecutive_failures >= 5:
                    self.status = AgentStatus.FAILED

            await self.update_metrics(db)
            await self.persist(db)

            return result

        except Exception as e:
            logger.error(f"Revenue agent {self.id} cycle failed: {e}")
            self.consecutive_failures += 1
            return {"status": "failed", "error": str(e)}

    async def switch_strategy(self, new_strategy_name: str) -> bool:
        """Switch to a different revenue strategy"""
        handler = get_strategy(new_strategy_name)
        if not handler:
            return False

        self.strategy_name = new_strategy_name
        self.strategy = new_strategy_name  # string for DB persistence
        self.strategy_handler = handler
        self.consecutive_failures = 0
        logger.info(f"Revenue agent {self.id} switched to {new_strategy_name}")
        return True

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for CEO decisions"""
        return {
            "agent_id": self.id,
            "strategy": getattr(self, "strategy_name", None) or self.strategy,
            "cycles": self.cycle_count,
            "revenue": float(self.revenue),
            "expenses": float(self.expenses),
            "profit": float(self.profit),
            "roi": self.roi,
            "status": self.status.value,
            "consecutive_failures": self.consecutive_failures,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
        }


class RevenueAgentFactory:
    """Factory for creating revenue agents with different strategies"""

    STRATEGY_CONFIGS = {
        "affiliate_content": {"budget": 0.50, "risk": "LOW", "expected_roi": 2.0},
        "digital_products": {"budget": 1.00, "risk": "MEDIUM", "expected_roi": 5.0},
        "print_on_demand": {"budget": 0.75, "risk": "LOW", "expected_roi": 3.0},
        "shopify_store": {"budget": 2.00, "risk": "HIGH", "expected_roi": 10.0},
        "multi_channel": {"budget": 3.00, "risk": "MEDIUM", "expected_roi": 8.0},
    }

    @classmethod
    def create_agent(cls, agent_id: str, strategy_name: str, parent_id: str = None) -> RevenueAgent:
        """Create a revenue agent with specified strategy"""
        agent = RevenueAgent(
            agent_id=agent_id,
            strategy_name=strategy_name,
            parent_id=parent_id,
        )
        config = cls.STRATEGY_CONFIGS.get(strategy_name, {})
        agent.budget = Decimal(str(config.get("budget", 1.0)))
        agent.risk_score = 0.2 if config.get("risk") == "LOW" else 0.5 if config.get("risk") == "MEDIUM" else 0.8
        return agent

    @classmethod
    def create_diversified_team(cls, count: int = 4) -> List[RevenueAgent]:
        """Create a diversified team of revenue agents"""
        strategies = list(cls.STRATEGY_CONFIGS.keys())[:-1]  # Exclude multi_channel
        agents = []
        for i, strategy in enumerate(strategies[:count]):
            agent_id = str(uuid.uuid4())
            agent = cls.create_agent(agent_id, strategy)
            agents.append(agent)
        return agents

    @classmethod
    def get_recommended_strategy(cls, capital: float, risk_tolerance: str = "MEDIUM") -> str:
        """Recommend strategy based on available capital and risk tolerance"""
        if capital < 5:
            return "affiliate_content"
        elif capital < 20:
            return "digital_products" if risk_tolerance != "HIGH" else "print_on_demand"
        elif capital < 100:
            return "print_on_demand" if risk_tolerance == "LOW" else "multi_channel"
        else:
            return "shopify_store" if risk_tolerance == "HIGH" else "multi_channel"