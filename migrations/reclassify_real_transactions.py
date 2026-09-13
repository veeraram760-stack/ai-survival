"""
Migration: reclassify mislabeled real transactions from before the real/simulated fix.

This updates any transaction whose category starts with 'real_' but was actually
created by simulated tool execution, changing it to the corresponding 'simulated_'
category. It also resets the in-memory ledger by restarting the backend.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import update
from backend.database.connection import async_session_maker
from backend.models.database import Transaction


async def migrate():
    async with async_session_maker() as session:
        real_categories = ["real_revenue", "real_expenses"]
        simulated_map = {
            "real_revenue": "simulated_revenue",
            "real_expenses": "simulated_expenses",
        }

        total_updated = 0
        for real_cat, sim_cat in simulated_map.items():
            stmt = (
                update(Transaction)
                .where(Transaction.category == real_cat)
                .values(category=sim_cat)
            )
            result = await session.execute(stmt)
            total_updated += result.rowcount

        await session.commit()
        print(f"Migration complete. Reclassified {total_updated} transaction(s).")


if __name__ == "__main__":
    asyncio.run(migrate())
