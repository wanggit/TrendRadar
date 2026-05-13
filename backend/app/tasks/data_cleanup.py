import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import get_sync_engine
from app.models.user import User, UserTier
from app.models.news import NewsItem
from app.core.constants import TIER_LIMITS

logger = logging.getLogger(__name__)


def cleanup_user_data_sync(db: Session, user_id: int, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = db.execute(
        select(func.count(NewsItem.id)).where(
            NewsItem.user_id == user_id,
            NewsItem.created_at < cutoff,
        )
    )
    count = result.scalar() or 0
    if count > 0:
        db.execute(
            NewsItem.__table__.delete().where(
                NewsItem.user_id == user_id,
                NewsItem.created_at < cutoff,
            )
        )
    return count


@celery_app.task(name="app.tasks.data_cleanup.cleanup_expired_data")
def cleanup_expired_data():
    engine = get_sync_engine()
    with Session(engine) as db:
        result = db.execute(select(User.id, User.tier).where(User.tier.in_([UserTier.FREE, UserTier.PRO])))
        users = result.all()
        total_cleaned = 0
        for user_id, tier in users:
            retention_days = TIER_LIMITS[tier]["data_retention_days"]
            cleaned = cleanup_user_data_sync(db, user_id, retention_days)
            total_cleaned += cleaned
        db.commit()
    logger.info(f"Cleaned up {total_cleaned} expired news item(s)")
    return {"cleaned": total_cleaned}
