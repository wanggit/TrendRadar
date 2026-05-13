from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.news import Platform
from app.models.rss import RSSFeed
from app.models.ai_report import AIReport
from app.services.config_service import ConfigService
from app.services.scheduler_service import UserScheduler
from app.services.task_log_service import TaskLogService
from app.tasks.crawl import crawl_platforms, crawl_rss
from app.tasks.analyze import analyze_news
from app.tasks.push import push_notification
from app.schemas.task import (
    TaskStatusResponse,
    TaskTriggerRequest,
    TaskTriggerResponse,
    ScheduleResponse,
    ScheduleDetailResponse,
    TaskLogResponse,
    TaskLogListResponse,
    TaskLogEntry,
    RunningTaskResponse,
    AIReportResponse,
    AIReportListResponse,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _ensure_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _compute_duration_seconds(log_entry) -> float | None:
    started = _ensure_aware(log_entry.started_at)
    completed = _ensure_aware(log_entry.completed_at)
    if started and completed:
        return (completed - started).total_seconds()
    if started:
        return (datetime.now(timezone.utc) - started).total_seconds()
    return None


def _compute_elapsed_seconds(log_entry) -> float | None:
    started = _ensure_aware(log_entry.started_at)
    if started:
        completed = _ensure_aware(log_entry.completed_at) or datetime.now(timezone.utc)
        return (completed - started).total_seconds()
    return None


def _to_task_log_response(log_entry) -> TaskLogResponse:
    logs = []
    for entry in (log_entry.logs or []):
        logs.append(TaskLogEntry(**entry))
    return TaskLogResponse(
        id=log_entry.id,
        task_name=log_entry.task_name,
        task_id=log_entry.task_id,
        status=log_entry.status,
        progress=log_entry.progress,
        current_step=log_entry.current_step,
        logs=logs,
        result=log_entry.result,
        error_message=log_entry.error_message,
        started_at=log_entry.started_at,
        completed_at=log_entry.completed_at,
        created_at=log_entry.created_at,
        duration_seconds=_compute_duration_seconds(log_entry),
    )


@router.post("/trigger/crawl", response_model=TaskTriggerResponse)
async def trigger_crawl(
    data: TaskTriggerRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a crawl task for the current user."""
    config_service = ConfigService(db)
    config = await config_service.get_or_create_user_config(current_user.id)

    result = await db.execute(
        select(Platform).where(
            Platform.user_id == current_user.id,
            Platform.enabled == True,
        ).order_by(Platform.id)
    )
    enabled_platforms = result.scalars().all()
    platform_configs = [{"source_id": p.source_id, "name": p.name} for p in enabled_platforms]

    rss_result = await db.execute(
        select(RSSFeed).where(
            RSSFeed.user_id == current_user.id,
            RSSFeed.enabled == True,
        ).order_by(RSSFeed.id)
    )
    enabled_rss_feeds = rss_result.scalars().all()
    rss_configs = [{"feed_url": f.feed_url, "name": f.name, "max_age_days": f.max_age_days, "feed_key": f.feed_key} for f in enabled_rss_feeds]

    task_ids = []
    log_service = TaskLogService(db, current_user.id)

    if platform_configs:
        task = crawl_platforms.delay(current_user.id, platform_configs)
        task_ids.append({"task": "crawl_platforms", "task_id": task.id})
        await log_service.create(
            task_name="crawl_platforms",
            task_id=task.id,
            status="pending",
        )

    if rss_configs:
        task = crawl_rss.delay(current_user.id, rss_configs)
        task_ids.append({"task": "crawl_rss", "task_id": task.id})
        await log_service.create(
            task_name="crawl_rss",
            task_id=task.id,
            status="pending",
        )

    await db.commit()

    return TaskTriggerResponse(
        status="triggered",
        tasks=task_ids,
    )


@router.post("/trigger/analyze", response_model=TaskTriggerResponse)
async def trigger_analyze(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger an AI analysis task for the current user."""
    task = analyze_news.delay(current_user.id)

    log_service = TaskLogService(db, current_user.id)
    await log_service.create(
        task_name="analyze_news",
        task_id=task.id,
        status="pending",
    )
    await db.commit()

    return TaskTriggerResponse(
        status="triggered",
        tasks=[{"task": "analyze_news", "task_id": task.id}],
    )


@router.post("/trigger/push", response_model=TaskTriggerResponse)
async def trigger_push(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a push notification task for the current user."""
    config_service = ConfigService(db)
    config = await config_service.get_or_create_user_config(current_user.id)
    report_mode = config.report.get("mode", "current")

    task = push_notification.delay(current_user.id, report_mode)

    log_service = TaskLogService(db, current_user.id)
    await log_service.create(
        task_name="push_notification",
        task_id=task.id,
        status="pending",
    )
    await db.commit()

    return TaskTriggerResponse(
        status="triggered",
        tasks=[{"task": "push_notification", "task_id": task.id}],
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get the status of a specific task."""
    from app.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    return TaskStatusResponse(
        task_id=task_id,
        status=result.status,
        result=result.result if result.ready() else None,
    )


@router.get("/logs", response_model=TaskLogListResponse)
async def get_task_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_name: str | None = Query(None),
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task execution history for the current user."""
    log_service = TaskLogService(db, current_user.id)
    logs, total = await log_service.get_history(
        page=page,
        page_size=page_size,
        task_name=task_name,
        status=status,
    )

    return TaskLogListResponse(
        total=total,
        logs=[_to_task_log_response(log) for log in logs],
    )


@router.get("/logs/{task_id}", response_model=TaskLogResponse)
async def get_task_log(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed log for a specific task."""
    log_service = TaskLogService(db, current_user.id)
    log_entry = await log_service.get_by_task_id(task_id)

    if not log_entry:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task log not found")

    return _to_task_log_response(log_entry)


@router.delete("/logs/{task_id}")
async def delete_task_log(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task log entry. Only pending/failed tasks can be deleted."""
    from fastapi import HTTPException

    log_service = TaskLogService(db, current_user.id)
    deleted = await log_service.delete(task_id)

    if not deleted:
        raise HTTPException(
            status_code=400,
            detail="无法删除该任务。只能删除等待中、失败或错误的任务。",
        )

    await db.commit()
    return {"status": "deleted", "task_id": task_id}


@router.get("/running", response_model=list[RunningTaskResponse])
async def get_running_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all currently running tasks for the current user."""
    log_service = TaskLogService(db, current_user.id)
    running = await log_service.get_running_tasks()

    return [
        RunningTaskResponse(
            task_id=log.task_id,
            task_name=log.task_name,
            status=log.status,
            progress=log.progress,
            current_step=log.current_step,
            started_at=log.started_at,
            elapsed_seconds=_compute_elapsed_seconds(log),
        )
        for log in running
    ]


@router.get("/schedule", response_model=ScheduleResponse)
async def get_user_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current schedule configuration for the user."""
    config_service = ConfigService(db)
    config = await config_service.get_or_create_user_config(current_user.id)

    schedule = UserScheduler.get_schedule_for_user(
        current_user.id,
        config.schedule,
        config.timeline,
    )

    return ScheduleResponse(
        enabled=config.schedule.get("enabled", True),
        preset=config.schedule.get("preset", "morning_evening"),
        entries=list(schedule.keys()),
    )


@router.get("/schedule/detail", response_model=ScheduleDetailResponse)
async def get_user_schedule_detail(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed human-readable schedule information for the user."""
    config_service = ConfigService(db)
    config = await config_service.get_or_create_user_config(current_user.id)

    info = UserScheduler.get_schedule_info(
        current_user.id,
        config.schedule,
        config.timeline,
    )

    return ScheduleDetailResponse(**info)


def _to_ai_report_response(report) -> AIReportResponse:
    return AIReportResponse(
        id=report.id,
        task_id=report.task_id,
        core_trends=report.core_trends or "",
        sentiment_controversy=report.sentiment_controversy or "",
        signals=report.signals or "",
        rss_insights=report.rss_insights or "",
        outlook_strategy=report.outlook_strategy or "",
        standalone_summaries=report.standalone_summaries,
        success=report.success,
        error=report.error,
        method=report.method,
        total_news=report.total_news,
        analyzed_news=report.analyzed_news,
        hotlist_count=report.hotlist_count,
        rss_count=report.rss_count,
        created_at=report.created_at,
    )


@router.get("/reports/latest", response_model=AIReportResponse | None)
async def get_latest_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest AI analysis report for the current user."""
    result = await db.execute(
        select(AIReport)
        .where(AIReport.user_id == current_user.id)
        .order_by(AIReport.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        return None
    return _to_ai_report_response(report)


@router.get("/reports/{report_id}", response_model=AIReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific AI analysis report by ID."""
    result = await db.execute(
        select(AIReport)
        .where(AIReport.id == report_id, AIReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_ai_report_response(report)


@router.get("/reports", response_model=AIReportListResponse)
async def get_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI analysis report history for the current user."""
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(AIReport).where(AIReport.user_id == current_user.id)
    )
    total = len(count_result.scalars().all())

    result = await db.execute(
        select(AIReport)
        .where(AIReport.user_id == current_user.id)
        .order_by(AIReport.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    reports = result.scalars().all()

    return AIReportListResponse(
        total=total,
        reports=[_to_ai_report_response(r) for r in reports],
    )
