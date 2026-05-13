import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import get_sync_engine
from app.models.user import User, UserTier
from app.core.constants import TRIAL_DAYS
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.trial_reminder.check_and_expire_trials")
def check_and_expire_trials():
    engine = get_sync_engine()
    with Session(engine) as db:
        now = datetime.now(timezone.utc)
        result = db.execute(
            select(User).where(
                User.tier == UserTier.PRO,
                User.trial_end_at.isnot(None),
                User.trial_end_at <= now,
            )
        )
        users = result.scalars().all()
        count = 0
        for user in users:
            user.tier = UserTier.FREE
            count += 1
            logger.info(f"Trial expired for user {user.id} ({user.email}), downgraded to FREE")
        if count > 0:
            db.flush()
            db.commit()
    logger.info(f"Expired {count} trial(s)")
    return {"expired": count}


@celery_app.task(name="app.tasks.trial_reminder.send_trial_reminders")
def send_trial_reminders():
    engine = get_sync_engine()
    with Session(engine) as db:
        now = datetime.now(timezone.utc)
        reminder_thresholds = [
            now + timedelta(days=3),
            now + timedelta(days=1),
        ]
        count = 0
        for threshold in reminder_thresholds:
            day_label = "3" if threshold.day == (now + timedelta(days=3)).day else "1"
            start = threshold.replace(hour=0, minute=0, second=0, microsecond=0)
            end = threshold.replace(hour=23, minute=59, second=59, microsecond=999999)
            result = db.execute(
                select(User).where(
                    User.tier == UserTier.PRO,
                    User.trial_end_at.isnot(None),
                    User.trial_end_at >= start,
                    User.trial_end_at <= end,
                    User.email_verified == True,
                )
            )
            users = result.scalars().all()
            for user in users:
                # Email sending would go here - for now just log
                logger.info(f"Would send trial reminder to user {user.id} ({user.email}), {day_label} days left")
                count += 1
    logger.info(f"Sent {count} trial reminder(s)")
    return {"sent": count}
