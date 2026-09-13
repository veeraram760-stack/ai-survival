import uuid
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.database import Task as DBTask, TaskStatus, TaskPriority
from config.settings import settings

logger = logging.getLogger("ai_survival.tasks")


class TaskManager:
    def __init__(self, db_factory):
        self._db_factory = db_factory
        self._counter = 0

    def _generate_task_id(self) -> str:
        year = datetime.now(timezone.utc).year
        self._counter += 1
        return f"TASK-{year}-{self._counter:03d}"

    async def create_task(
        self,
        db: AsyncSession,
        title: str,
        description: str = "",
        goal: str = "",
        priority: str = "MEDIUM",
        project_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        expected_output: Optional[Dict[str, Any]] = None,
        assigned_agent: Optional[str] = None,
        supervisor: Optional[str] = None,
        tools_required: Optional[List[str]] = None,
        memory_required: Optional[List[str]] = None,
        max_retries: int = 3,
        autonomy_level: int = 3,
        timeout_minutes: Optional[int] = None,
    ) -> DBTask:
        task_id = self._generate_task_id()
        task = DBTask(
            id=task_id,
            project_id=project_id,
            parent_task_id=parent_task_id,
            title=title,
            description=description,
            goal=goal,
            priority=TaskPriority(priority),
            status=TaskStatus.CREATED,
            input_data=input_data or {},
            expected_output=expected_output,
            assigned_agent=assigned_agent,
            supervisor=supervisor,
            tools_required=tools_required or [],
            memory_required=memory_required or [],
            max_retries=max_retries,
            autonomy_level=autonomy_level,
        )
        if timeout_minutes:
            task.timeout_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
        db.add(task)
        await db.flush()
        logger.info(f"Created task {task_id}: {title}")
        return task

    async def get_task(self, db: AsyncSession, task_id: str) -> Optional[DBTask]:
        result = await db.execute(select(DBTask).where(DBTask.id == task_id))
        return result.scalar_one_or_none()

    async def update_status(self, db: AsyncSession, task_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        task = await self.get_task(db, task_id)
        if not task:
            return None
        task.status = TaskStatus(status)
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        if status == "RUNNING" and not task.started_at:
            task.started_at = datetime.now(timezone.utc)
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            task.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return task

    async def retry_task(self, db: AsyncSession, task_id: str) -> Optional[DBTask]:
        task = await self.get_task(db, task_id)
        if not task:
            return None
        if task.retry_count >= task.max_retries:
            logger.warning(f"Task {task_id} exceeded max retries ({task.max_retries})")
            await self.update_status(db, task_id, "FAILED", error="Max retries exceeded")
            return None
        task.retry_count += 1
        task.status = TaskStatus.RETRYING
        task.error = None
        await db.flush()
        logger.info(f"Retrying task {task_id} (attempt {task.retry_count}/{task.max_retries})")
        return task

    async def get_pending_tasks(self, db: AsyncSession, limit: int = 100) -> List[DBTask]:
        result = await db.execute(
            select(DBTask)
            .where(DBTask.status.in_([TaskStatus.CREATED, TaskStatus.QUEUED, TaskStatus.RETRYING]))
            .order_by(DBTask.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_running_tasks(self, db: AsyncSession, limit: int = 100) -> List[DBTask]:
        result = await db.execute(
            select(DBTask)
            .where(DBTask.status == TaskStatus.RUNNING)
            .order_by(DBTask.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_tasks_by_project(self, db: AsyncSession, project_id: str) -> List[DBTask]:
        result = await db.execute(
            select(DBTask).where(DBTask.project_id == project_id).order_by(DBTask.created_at.desc())
        )
        return result.scalars().all()

    async def check_timeouts(self, db: AsyncSession):
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(DBTask).where(
                DBTask.status == TaskStatus.RUNNING,
                DBTask.timeout_at != None,
                DBTask.timeout_at <= now,
            )
        )
        timed_out = result.scalars().all()
        for task in timed_out:
            logger.warning(f"Task {task.id} timed out")
            await self.update_status(db, task.id, "FAILED", error="Task timed out")
        if timed_out:
            await db.commit()

    async def get_task_stats(self, db: AsyncSession) -> Dict[str, Any]:
        status_counts = {}
        for status in TaskStatus:
            count_result = await db.execute(
                select(func.count(DBTask.id)).where(DBTask.status == status)
            )
            status_counts[status.value] = count_result.scalar_one() or 0
        total_result = await db.execute(select(func.count(DBTask.id)))
        total = total_result.scalar_one() or 0
        return {"total": total, "by_status": status_counts}
