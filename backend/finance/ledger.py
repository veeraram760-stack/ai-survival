import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.database import Transaction, TransactionStatus, Agent
from config.settings import settings


class CapitalLedger:
    def __init__(self, starting_capital: float):
        self.starting_capital = Decimal(str(starting_capital))
        self.current_balance = self.starting_capital
        self.survival_reserve = self.starting_capital * Decimal(str(settings.survival_reserve_ratio))
        self.operating_capital = self.current_balance - self.survival_reserve
        self.growth_capital = Decimal("0")
        self.total_revenue = Decimal("0")
        self.total_expenses = Decimal("0")
        self.realized_profit = Decimal("0")
        self.unrealized_pnl = Decimal("0")

    async def record_transaction(
        self,
        db: AsyncSession,
        agent_id: Optional[str],
        category: str,
        action: str,
        amount: Decimal,
        expected_return: Optional[Decimal] = None,
        actual_return: Optional[Decimal] = None,
        risk_level: str = "LOW",
        approval_reason: Optional[str] = None,
    ) -> Transaction:
        balance_before = self.current_balance
        balance_after = balance_before + amount
        transaction_id = str(uuid.uuid4())

        transaction = Transaction(
            id=transaction_id,
            timestamp=datetime.now(timezone.utc),
            agent_id=agent_id,
            category=category,
            action=action,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            expected_return=expected_return,
            actual_return=actual_return,
            status=TransactionStatus.PENDING,
            risk_level=risk_level,
            approval_reason=approval_reason,
        )

        self.current_balance = balance_after
        if amount < 0:
            self.total_expenses += abs(amount)
            if self.operating_capital > 0:
                reduction = min(abs(amount), self.operating_capital)
                self.operating_capital -= reduction
                if self.operating_capital < 0:
                    self.growth_capital += self.operating_capital
                    self.operating_capital = Decimal("0")
        else:
            self.total_revenue += amount
            self.realized_profit += amount
            self.growth_capital += amount

        db.add(transaction)
        return transaction

    async def commit_transaction(self, db: AsyncSession, transaction_id: str):
        result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
        transaction = result.scalar_one_or_none()
        if transaction:
            transaction.status = TransactionStatus.COMPLETED

    async def reverse_transaction(self, db: AsyncSession, transaction_id: str, reason: str):
        result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
        transaction = result.scalar_one_or_none()
        if not transaction:
            raise ValueError("Transaction not found")

        reverse_txn = Transaction(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            agent_id=transaction.agent_id,
            category=transaction.category,
            action=f"REVERSE:{transaction.action}",
            amount=-transaction.amount,
            balance_before=self.current_balance,
            balance_after=self.current_balance - transaction.amount,
            expected_return=transaction.expected_return,
            actual_return=transaction.actual_return,
            status=TransactionStatus.REVERSED,
            risk_level=transaction.risk_level,
            approval_reason=reason,
        )
        self.current_balance -= transaction.amount
        db.add(reverse_txn)

    def get_capital_snapshot(self) -> dict:
        return {
            "total_capital": float(self.current_balance),
            "survival_reserve": float(self.survival_reserve),
            "operating_capital": float(self.operating_capital),
            "growth_capital": float(self.growth_capital),
            "total_revenue": float(self.total_revenue),
            "total_expenses": float(self.total_expenses),
            "realized_profit": float(self.realized_profit),
            "unrealized_pnl": float(self.unrealized_pnl),
            "net_profit": float(self.realized_profit - self.total_expenses),
            "roi": float((self.realized_profit - self.total_expenses) / self.starting_capital) if self.starting_capital > 0 else 0.0,
        }

    def can_spend(self, amount: Decimal) -> tuple[bool, str]:
        if self.current_balance - amount < 0:
            return False, "Insufficient total capital"
        if self.current_balance - amount < self.survival_reserve:
            return False, "Would breach survival reserve"
        if self.operating_capital - amount < Decimal(str(settings.min_operating_capital_ratio)) * self.starting_capital:
            return False, "Would breach minimum operating capital"
        return True, "Approved"
