import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserTier
from app.core.constants import TRIAL_DAYS

logger = logging.getLogger(__name__)


class TrialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_trial(self, user: User) -> User:
        if user.trial_used:
            return user
        now = datetime.now(timezone.utc)
        user.tier = UserTier.PRO
        user.trial_start_at = now
        user.trial_end_at = now + timedelta(days=TRIAL_DAYS)
        user.trial_used = True
        return user

    async def check_and_expire_trials(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
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
            await self.db.flush()
        return count

    async def send_trial_reminders(self, email_service) -> int:
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
            result = await self.db.execute(
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
                try:
                    await email_service.send_trial_reminder(user, int(day_label))
                    count += 1
                    logger.info(f"Trial reminder sent to user {user.id} ({user.email}), {day_label} days left")
                except Exception as e:
                    logger.error(f"Failed to send trial reminder to user {user.id}: {e}")
        return count

    def is_trial_active(self, user: User) -> bool:
        if user.tier != UserTier.PRO:
            return False
        if not user.trial_end_at:
            return False
        now = datetime.now(timezone.utc)
        end_at = user.trial_end_at
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=timezone.utc)
        return end_at > now

    def get_trial_days_left(self, user: User) -> int | None:
        if not self.is_trial_active(user):
            return None
        end_at = user.trial_end_at
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=timezone.utc)
        delta = end_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    def is_trial_expiring_soon(self, user: User, days: int = 3) -> bool:
        days_left = self.get_trial_days_left(user)
        if days_left is None:
            return False
        return days_left <= days
