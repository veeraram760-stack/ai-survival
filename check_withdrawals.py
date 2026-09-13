import asyncio
import sys
sys.path.insert(0, ".")

from backend.database.connection import async_session_maker
from backend.models.database import Withdrawal
from sqlalchemy import select

async def check():
    async with async_session_maker() as s:
        result = await s.execute(
            select(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(3)
        )
        withdrawals = result.scalars().all()
        for w in withdrawals:
            print(f"ID: {w.id}, Amount: {w.amount}, Status: {w.status}, Created: {w.created_at}")

if __name__ == "__main__":
    asyncio.run(check())
