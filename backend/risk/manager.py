import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, func
from ..finance.ledger import CapitalLedger
from config.settings import settings
from ..models.database import RiskEvent, RiskEventType


class RiskManager:
    def __init__(self, capital_ledger: CapitalLedger):
        self.ledger = capital_ledger
        self.emergency_mode = False

    async def evaluate_spend(
        self,
        db,
        agent_id: Optional[str],
        amount: Decimal,
        category: str,
        reason: str,
        expected_return: Optional[Decimal] = None,
    ) -> tuple[bool, str]:
        if amount > Decimal(str(settings.max_single_spend)):
            await self._log_risk_event(db, agent_id, RiskEventType.SPEND_DENIED, {
                "reason": f"Exceeds max single spend limit of ${settings.max_single_spend}",
                "requested_amount": float(amount),
                "category": category,
            })
            return False, f"Exceeds max single spend limit of ${settings.max_single_spend}"

        can_spend, reason = self.ledger.can_spend(amount)
        if not can_spend:
            await self._log_risk_event(db, agent_id, RiskEventType.SPEND_DENIED, {
                "reason": reason,
                "requested_amount": float(amount),
                "category": category,
                "current_balance": float(self.ledger.current_balance),
                "survival_reserve": float(self.ledger.survival_reserve),
            })
            return False, reason

        if self.ledger.current_balance < self.ledger.survival_reserve * Decimal("2"):
            await self._log_risk_event(db, agent_id, RiskEventType.CAPITAL_THRESHOLD, {
                "reason": "Capital approaching survival reserve",
                "current_balance": float(self.ledger.current_balance),
                "survival_reserve": float(self.ledger.survival_reserve),
            })

        return True, "Approved"

    async def evaluate_agent_creation(self, db, agent_type: str) -> tuple[bool, str]:
        current_agents = await self._count_active_agents(db)
        if current_agents >= settings.population_hard_cap:
            await self._log_risk_event(db, None, RiskEventType.POPULATION_LIMIT_HIT, {
                "current_agents": current_agents,
                "hard_cap": settings.population_hard_cap,
            })
            return False, f"Population hard cap reached ({settings.population_hard_cap})"
        if current_agents >= settings.population_soft_cap:
            creation_cost = Decimal(str(settings.max_agent_creation_cost))
            can_spend, reason = self.ledger.can_spend(creation_cost)
            if not can_spend:
                return False, f"Population soft cap reached and cannot afford creation: {reason}"
        return True, "Approved"

    async def evaluate_reproduction(self, db, parent_id: str, child_roi: float, child_profit: Decimal) -> tuple[bool, str]:
        if child_profit < Decimal(str(settings.reproduction_min_profit)):
            return False, f"Insufficient profit: ${child_profit} < ${settings.reproduction_min_profit}"
        if child_roi < settings.reproduction_min_roi:
            return False, f"Insufficient ROI: {child_roi} < {settings.reproduction_min_roi}"
        return True, "Approved"

    async def evaluate_system_mode(self, db) -> str:
        reserve_ratio = float(self.ledger.survival_reserve) / float(self.ledger.current_balance) if self.ledger.current_balance > 0 else 1.0
        if reserve_ratio >= 0.9:
            return "DEAD"
        elif reserve_ratio >= 0.6:
            return "SURVIVAL"
        elif reserve_ratio >= 0.35:
            return "DEFENSIVE"
        else:
            return "GROWTH"

    async def _count_active_agents(self, db) -> int:
        from ..models.database import Agent, AgentStatus
        result = await db.execute(
            select(func.count(Agent.id)).where(
                Agent.status.in_([
                    AgentStatus.ALIVE,
                    AgentStatus.TESTING,
                    AgentStatus.GROWING,
                    AgentStatus.REPRODUCTION_READY,
                ])
            )
        )
        return result.scalar_one()

    async def _log_risk_event(
        self, db, agent_id: Optional[str], event_type: RiskEventType, details: dict
    ):
        event = RiskEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            agent_id=agent_id,
            details=details,
            severity="HIGH" if event_type in [RiskEventType.RESERVE_VIOLATION_ATTEMPT, RiskEventType.CAPITAL_THRESHOLD] else "MEDIUM",
        )
        db.add(event)
