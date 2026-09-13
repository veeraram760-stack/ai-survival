import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.database import ShortTermMemory, ProjectMemory, LongTermMemory, MemoryType

logger = logging.getLogger("ai_survival.memory")


class MemoryManager:
    def __init__(self, db_factory):
        self._db_factory = db_factory

    async def set_short_term(self, db: AsyncSession, key: str, value: Any, task_id: Optional[str] = None, project_id: Optional[str] = None, ttl_minutes: Optional[int] = None):
        expires_at = None
        if ttl_minutes:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        memory = ShortTermMemory(
            id=str(uuid.uuid4()),
            task_id=task_id,
            project_id=project_id,
            key=key,
            value=value if isinstance(value, (dict, list)) else {"value": value},
            expires_at=expires_at,
        )
        db.add(memory)
        await db.flush()

    async def get_short_term(self, db: AsyncSession, key: str, task_id: Optional[str] = None, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        query = select(ShortTermMemory).where(
            ShortTermMemory.key == key,
            (ShortTermMemory.expires_at == None) | (ShortTermMemory.expires_at > now),
        )
        if task_id:
            query = query.where(ShortTermMemory.task_id == task_id)
        if project_id:
            query = query.where(ShortTermMemory.project_id == project_id)
        result = await db.execute(query.order_by(ShortTermMemory.created_at.desc()))
        memory = result.scalar_one_or_none()
        return memory.value if memory else None

    async def set_project(self, db: AsyncSession, project_id: str, key: str, value: Any, confidence: float = 0.5):
        existing = await db.execute(
            select(ProjectMemory).where(ProjectMemory.project_id == project_id, ProjectMemory.key == key)
        )
        memory = existing.scalar_one_or_none()
        if memory:
            memory.value = value if isinstance(value, (dict, list)) else {"value": value}
            memory.confidence = confidence
            memory.updated_at = datetime.now(timezone.utc)
        else:
            memory = ProjectMemory(
                id=str(uuid.uuid4()),
                project_id=project_id,
                key=key,
                value=value if isinstance(value, (dict, list)) else {"value": value},
                confidence=confidence,
            )
            db.add(memory)
        await db.flush()

    async def get_project(self, db: AsyncSession, project_id: str, key: str) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(ProjectMemory).where(ProjectMemory.project_id == project_id, ProjectMemory.key == key)
        )
        memory = result.scalar_one_or_none()
        return memory.value if memory else None

    async def set_long_term(self, db: AsyncSession, category: str, key: str, value: Any, confidence: float = 0.5):
        existing = await db.execute(
            select(LongTermMemory).where(LongTermMemory.category == category, LongTermMemory.key == key)
        )
        memory = existing.scalar_one_or_none()
        if memory:
            memory.value = value if isinstance(value, (dict, list)) else {"value": value}
            memory.confidence = confidence
            memory.usage_count += 1
            memory.last_used = datetime.now(timezone.utc)
            memory.updated_at = datetime.now(timezone.utc)
        else:
            memory = LongTermMemory(
                id=str(uuid.uuid4()),
                category=category,
                key=key,
                value=value if isinstance(value, (dict, list)) else {"value": value},
                confidence=confidence,
                last_used=datetime.now(timezone.utc),
            )
            db.add(memory)
        await db.flush()

    async def get_long_term(self, db: AsyncSession, category: str, key: str) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(LongTermMemory).where(LongTermMemory.category == category, LongTermMemory.key == key)
        )
        memory = result.scalar_one_or_none()
        if memory:
            memory.usage_count += 1
            memory.last_used = datetime.now(timezone.utc)
            await db.flush()
        return memory.value if memory else None

    async def search_long_term(self, db: AsyncSession, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(LongTermMemory)
            .where(LongTermMemory.category == category)
            .order_by(LongTermMemory.confidence.desc(), LongTermMemory.usage_count.desc())
            .limit(limit)
        )
        memories = result.scalars().all()
        return [{"key": m.key, "value": m.value, "confidence": m.confidence, "usage_count": m.usage_count} for m in memories]

    async def cleanup_expired(self, db: AsyncSession):
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ShortTermMemory).where(ShortTermMemory.expires_at != None, ShortTermMemory.expires_at <= now)
        )
        expired = result.scalars().all()
        for memory in expired:
            await db.delete(memory)
        if expired:
            await db.commit()
            logger.info(f"Cleaned up {len(expired)} expired short-term memories")
