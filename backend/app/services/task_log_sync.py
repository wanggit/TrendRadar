import time
import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.task_log import TaskLog
from app.db.session import get_sync_engine

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_RETRY_DELAY = 0.5


def _with_retry(func):
    for attempt in range(_MAX_RETRIES):
        try:
            return func()
        except Exception as e:
            if "database is locked" in str(e).lower() and attempt < _MAX_RETRIES - 1:
                wait = _RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Database locked, retry {attempt + 1}/{_MAX_RETRIES} in {wait}s")
                time.sleep(wait)
            else:
                raise


def create_task_log(user_id: int, task_name: str, task_id: str, status: str = "pending") -> int:
    engine = get_sync_engine()

    def _create():
        with Session(engine) as session:
            log_entry = TaskLog(
                user_id=user_id,
                task_name=task_name,
                task_id=task_id,
                status=status,
                logs=[],
            )
            session.add(log_entry)
            session.commit()
            return log_entry.id

    return _with_retry(_create)


def update_task_status(
    task_id: str,
    status: str,
    progress: int | None = None,
    current_step: str | None = None,
    result: dict | None = None,
    error_message: str | None = None,
):
    engine = get_sync_engine()

    def _update():
        with Session(engine) as session:
            log_entry = session.query(TaskLog).filter(TaskLog.task_id == task_id).first()
            if not log_entry:
                return

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
            session.commit()

    _with_retry(_update)


def add_task_log_entry(task_id: str, level: str, message: str):
    engine = get_sync_engine()

    def _add():
        with Session(engine) as session:
            log_entry = session.query(TaskLog).filter(TaskLog.task_id == task_id).first()
            if not log_entry:
                return

            # Refresh to get latest data from DB (in case of concurrent updates)
            session.refresh(log_entry)
            
            current_logs = log_entry.logs or []
            new_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
            }
            # Create new list to ensure SQLAlchemy detects the change
            log_entry.logs = current_logs + [new_entry]
            flag_modified(log_entry, 'logs')
            log_entry.updated_at = datetime.now(timezone.utc)
            session.commit()

    _with_retry(_add)
