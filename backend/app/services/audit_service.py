from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        action: str,
        user_id: int | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def query_logs(
        self,
        user_id: int | None = None,
        action: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if start_time:
            query = query.where(AuditLog.created_at >= start_time)
            count_query = count_query.where(AuditLog.created_at >= start_time)
        if end_time:
            query = query.where(AuditLog.created_at <= end_time)
            count_query = count_query.where(AuditLog.created_at <= end_time)

        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return logs, total
