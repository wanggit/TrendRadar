"""
Trial Service - Unit Tests
Tests: trial creation, expiry, reminders
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import User, UserTier
from app.core.security import get_password_hash
from app.services.trial_service import TrialService

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        from app.models.user import Base as UserBase
        await conn.run_sync(UserBase.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def new_user(test_db):
    user = User(
        email="trial@test.com",
        password_hash=get_password_hash("password123"),
        nickname="Trial User",
        tier=UserTier.FREE,
        trial_used=False,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def trial_user(test_db):
    now = datetime.now(timezone.utc)
    user = User(
        email="active-trial@test.com",
        password_hash=get_password_hash("password123"),
        nickname="Active Trial",
        tier=UserTier.PRO,
        trial_used=True,
        trial_start_at=now,
        trial_end_at=now + timedelta(days=5),
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def expired_trial_user(test_db):
    now = datetime.now(timezone.utc)
    user = User(
        email="expired-trial@test.com",
        password_hash=get_password_hash("password123"),
        nickname="Expired Trial",
        tier=UserTier.PRO,
        trial_used=True,
        trial_start_at=now - timedelta(days=10),
        trial_end_at=now - timedelta(days=3),
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


class TestCreateTrial:
    @pytest.mark.asyncio
    async def test_create_trial_sets_pro_tier(self, test_db, new_user):
        service = TrialService(test_db)
        await service.create_trial(new_user)
        assert new_user.tier == UserTier.PRO
        assert new_user.trial_used is True
        assert new_user.trial_start_at is not None
        assert new_user.trial_end_at is not None

    @pytest.mark.asyncio
    async def test_create_trial_sets_7_days(self, test_db, new_user):
        service = TrialService(test_db)
        before = datetime.now(timezone.utc)
        await service.create_trial(new_user)
        after = datetime.now(timezone.utc)
        expected_end_min = before + timedelta(days=7)
        expected_end_max = after + timedelta(days=7)
        assert expected_end_min <= new_user.trial_end_at <= expected_end_max

    @pytest.mark.asyncio
    async def test_create_trial_skips_if_already_used(self, test_db, trial_user):
        service = TrialService(test_db)
        old_end = trial_user.trial_end_at
        await service.create_trial(trial_user)
        assert trial_user.trial_end_at == old_end


class TestIsTrialActive:
    def test_active_trial_returns_true(self, trial_user):
        service = TrialService(None)
        assert service.is_trial_active(trial_user) is True

    def test_expired_trial_returns_false(self, expired_trial_user):
        service = TrialService(None)
        assert service.is_trial_active(expired_trial_user) is False

    def test_free_user_returns_false(self, test_db, new_user):
        service = TrialService(None)
        assert service.is_trial_active(new_user) is False


class TestGetTrialDaysLeft:
    def test_returns_days_for_active_trial(self, trial_user):
        service = TrialService(None)
        days = service.get_trial_days_left(trial_user)
        assert days is not None
        assert 0 <= days <= 5

    def test_returns_none_for_expired(self, expired_trial_user):
        service = TrialService(None)
        assert service.get_trial_days_left(expired_trial_user) is None


class TestCheckAndExpireTrials:
    @pytest.mark.asyncio
    async def test_expires_trials(self, test_db, expired_trial_user):
        service = TrialService(test_db)
        count = await service.check_and_expire_trials()
        assert count == 1
        assert expired_trial_user.tier == UserTier.FREE

    @pytest.mark.asyncio
    async def test_does_not_expire_active_trials(self, test_db, trial_user):
        service = TrialService(test_db)
        count = await service.check_and_expire_trials()
        assert count == 0
        assert trial_user.tier == UserTier.PRO
