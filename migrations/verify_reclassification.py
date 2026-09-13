import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, func
from backend.database.connection import async_session_maker
from backend.models.database import Transaction


async def check():
    async with async_session_maker() as s:
        real_rev = await s.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.amount > 0,
                Transaction.category.ilike("real%"),
            )
        )
        sim_rev = await s.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.amount > 0,
                Transaction.category.ilike("simulated%"),
            )
        )
        real_exp = await s.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.amount < 0,
                Transaction.category.ilike("real%"),
            )
        )
        sim_exp = await s.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.amount < 0,
                Transaction.category.ilike("simulated%"),
            )
        )
        print("real_revenue:", real_rev.scalar_one())
        print("simulated_revenue:", sim_rev.scalar_one())
        print("real_expenses:", real_exp.scalar_one())
        print("simulated_expenses:", sim_exp.scalar_one())


if __name__ == "__main__":
    asyncio.run(check())
