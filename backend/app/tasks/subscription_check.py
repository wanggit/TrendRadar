import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import get_sync_engine
from app.models.user import User, UserTier
from app.services.email_service import EmailService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.subscription_check.check_and_expire_subscriptions")
def check_and_expire_subscriptions():
    engine = get_sync_engine()
    with Session(engine) as db:
        now = datetime.now(timezone.utc)
        result = db.execute(
            select(User).where(
                User.tier == UserTier.PRO,
                User.expire_at.isnot(None),
                User.expire_at <= now,
                User.trial_end_at.is_(None),
            )
        )
        users = result.scalars().all()
        count = 0
        for user in users:
            user.tier = UserTier.FREE
            count += 1
            logger.info(f"Subscription expired for user {user.id} ({user.email}), downgraded to FREE")
        if count > 0:
            db.commit()
            # EmailService needs async session, but _send is sync
            # For now, just log - email sending can be added later with sync refactor
            for user in users:
                logger.info(f"Would send subscription expiry email to user {user.id} ({user.email})")
    logger.info(f"Expired {count} subscription(s)")
    return {"expired": count}
