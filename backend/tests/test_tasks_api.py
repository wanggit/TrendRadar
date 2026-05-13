"""
Tasks API Module - Unit Tests
Tests: trigger crawl/analyze/push, schedule, running tasks, task logs
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.user import User, UserTier, UserStatus
from app.core.security import get_password_hash, create_access_token
from app.db.session import get_db

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
        from app.db.base import Base
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    app = create_app()

    async def override_get_db():
        try:
            yield test_db
            await test_db.commit()
        except Exception:
            await test_db.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_user(test_db):
    user = User(
        email="test@test.com",
        password_hash=get_password_hash("testpass123"),
        nickname="Test User",
        is_superuser=False,
        tier=UserTier.FREE,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest.fixture
def test_token(test_user):
    return create_access_token(subject=str(test_user.id))


@pytest.mark.asyncio
class TestTriggerCrawl:
    async def test_trigger_crawl_no_platforms(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/tasks/trigger/crawl",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"

    async def test_trigger_crawl_unauthorized(self, client):
        response = await client.post("/api/v1/tasks/trigger/crawl")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestTriggerAnalyze:
    async def test_trigger_analyze(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/tasks/trigger/analyze",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task"] == "analyze_news"

    async def test_trigger_analyze_unauthorized(self, client):
        response = await client.post("/api/v1/tasks/trigger/analyze")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestTriggerPush:
    async def test_trigger_push(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/tasks/trigger/push",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task"] == "push_notification"

    async def test_trigger_push_unauthorized(self, client):
        response = await client.post("/api/v1/tasks/trigger/push")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestScheduleEndpoints:
    async def test_get_schedule(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/schedule",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "preset" in data
        assert "entries" in data

    async def test_get_schedule_detail(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/schedule/detail",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_get_schedule_unauthorized(self, client):
        response = await client.get("/api/v1/tasks/schedule")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestRunningTasks:
    async def test_get_running_tasks_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/running",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_running_tasks_unauthorized(self, client):
        response = await client.get("/api/v1/tasks/running")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestTaskLogs:
    async def test_get_task_logs_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/logs",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["logs"] == []

    async def test_get_task_logs_pagination(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/logs?page=1&page_size=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "logs" in data

    async def test_get_task_logs_filter_by_task_name(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/logs?task_name=crawl_platforms",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_get_task_logs_filter_by_status(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/logs?status=success",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_get_task_logs_unauthorized(self, client):
        response = await client.get("/api/v1/tasks/logs")
        assert response.status_code == 403

    async def test_get_task_log_not_found(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/logs/nonexistent-task-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404

    async def test_get_task_log_unauthorized(self, client):
        response = await client.get("/api/v1/tasks/logs/some-task-id")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestTaskStatus:
    async def test_get_task_status_unauthorized(self, client):
        response = await client.get("/api/v1/tasks/status/some-task-id")
        assert response.status_code == 403
