from datetime import datetime, timezone

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_log import TaskLog


class TaskLogService:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def create(
        self,
        task_name: str,
        task_id: str,
        status: str = "pending",
    ) -> TaskLog:
        log_entry = TaskLog(
            user_id=self.user_id,
            task_name=task_name,
            task_id=task_id,
            status=status,
            logs=[],
        )
        self.db.add(log_entry)
        await self.db.flush()
        await self.db.refresh(log_entry)
        return log_entry

    async def update_status(
        self,
        task_id: str,
        status: str,
        progress: int | None = None,
        current_step: str | None = None,
        result: dict | None = None,
        error_message: str | None = None,
    ) -> TaskLog | None:
        result_obj = await self.db.execute(
            select(TaskLog).where(
                TaskLog.task_id == task_id,
                TaskLog.user_id == self.user_id,
            )
        )
        log_entry = result_obj.scalar_one_or_none()
        if not log_entry:
            return None

        log_entry.status = status
        if progress is not None:
            log_entry.progress = progress
        if current_step is not None:
            log_entry.current_step = current_step
        if result is not None:
            log_entry.result = result
        if error_message is not None:
            log_entry.error_message = error_message

        now = datetime.now(timezone.utc)
        if status in ("running", "started") and log_entry.started_at is None:
            log_entry.started_at = now
        if status in ("success", "failure", "error", "cancelled") and log_entry.completed_at is None:
            log_entry.completed_at = now

        log_entry.updated_at = now
        await self.db.flush()
        await self.db.refresh(log_entry)
        return log_entry

    async def add_log(
        self,
        task_id: str,
        level: str,
        message: str,
    ) -> TaskLog | None:
        result_obj = await self.db.execute(
            select(TaskLog).where(
                TaskLog.task_id == task_id,
                TaskLog.user_id == self.user_id,
            )
        )
        log_entry = result_obj.scalar_one_or_none()
        if not log_entry:
            return None

        log_entry.logs = log_entry.logs or []
        log_entry.logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        })
        log_entry.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_by_task_id(self, task_id: str) -> TaskLog | None:
        result_obj = await self.db.execute(
            select(TaskLog).where(
                TaskLog.task_id == task_id,
                TaskLog.user_id == self.user_id,
            )
        )
        return result_obj.scalar_one_or_none()

    async def get_running_tasks(self) -> list[TaskLog]:
        result_obj = await self.db.execute(
            select(TaskLog)
            .where(
                TaskLog.user_id == self.user_id,
                TaskLog.status.in_(["pending", "running", "started"]),
            )
            .order_by(desc(TaskLog.created_at))
        )
        return list(result_obj.scalars().all())

    async def get_history(
        self,
        page: int = 1,
        page_size: int = 20,
        task_name: str | None = None,
        status: str | None = None,
    ) -> tuple[list[TaskLog], int]:
        query = select(TaskLog).where(TaskLog.user_id == self.user_id)

        if task_name:
            query = query.where(TaskLog.task_name == task_name)
        if status:
            query = query.where(TaskLog.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(desc(TaskLog.created_at)).offset((page - 1) * page_size).limit(page_size)
        result_obj = await self.db.execute(query)
        logs = list(result_obj.scalars().all())

        return logs, total

    async def delete(self, task_id: str) -> bool:
        """Delete a task log entry. Only allows deleting pending/failed tasks."""
        result_obj = await self.db.execute(
            select(TaskLog).where(
                TaskLog.task_id == task_id,
                TaskLog.user_id == self.user_id,
            )
        )
        log_entry = result_obj.scalar_one_or_none()
        if not log_entry:
            return False

        # Only allow deleting pending, failure, or error tasks
        if log_entry.status not in ("pending", "failure", "error"):
            return False

        await self.db.delete(log_entry)
        await self.db.flush()
        return True
