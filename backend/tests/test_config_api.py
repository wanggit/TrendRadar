"""
Config API Module - Unit Tests
Tests: runtime, ai-system, platforms, rss, schedule, notification, frequency-words, export, import, diff
"""
import pytest
import pytest_asyncio
import json
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
class TestRuntimeConfig:
    async def test_get_runtime_config(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/runtime",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_config" in data
        assert "ai_config" in data
        assert "timezone" in data["user_config"]

    async def test_get_runtime_config_unauthorized(self, client):
        response = await client.get("/api/v1/config/runtime")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestSystemAIConfig:
    async def test_get_system_ai_config(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/ai-system",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "model" in data

    async def test_get_system_ai_config_unauthorized(self, client):
        response = await client.get("/api/v1/config/ai-system")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestPlatformsConfig:
    async def test_get_platforms_config(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/platforms",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "enabled" in data
        assert "sources" in data

    async def test_update_platforms_config(self, client, test_user, test_token):
        new_config = {"enabled": True, "sources": [{"id": "weibo", "name": "微博热搜"}]}
        response = await client.put(
            "/api/v1/config/platforms",
            headers={"Authorization": f"Bearer {test_token}"},
            json=new_config
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True

    async def test_platforms_config_unauthorized(self, client):
        response = await client.get("/api/v1/config/platforms")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestRSSConfig:
    async def test_get_rss_config(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/rss",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "enabled" in data

    async def test_update_rss_config(self, client, test_user, test_token):
        new_config = {"enabled": True, "feeds": [], "freshness_filter": {"enabled": True, "max_age_days": 3}}
        response = await client.put(
            "/api/v1/config/rss",
            headers={"Authorization": f"Bearer {test_token}"},
            json=new_config
        )
        assert response.status_code == 200
        data = response.json()
        assert data["freshness_filter"]["max_age_days"] == 3

    async def test_rss_config_unauthorized(self, client):
        response = await client.get("/api/v1/config/rss")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestScheduleConfig:
    async def test_get_schedule_config(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/schedule",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "enabled" in data

    async def test_update_schedule_config(self, client, test_user, test_token):
        new_config = {"enabled": False, "preset": "all_day"}
        response = await client.put(
            "/api/v1/config/schedule",
            headers={"Authorization": f"Bearer {test_token}"},
            json=new_config
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    async def test_schedule_config_unauthorized(self, client):
        response = await client.get("/api/v1/config/schedule")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestNotificationConfig:
    async def test_get_notification_config(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/notification",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "enabled" in data

    async def test_update_notification_config(self, client, test_user, test_token):
        new_config = {"enabled": True, "channels": {"telegram": {"enabled": True, "bot_token": "test", "chat_id": "123"}}}
        response = await client.put(
            "/api/v1/config/notification",
            headers={"Authorization": f"Bearer {test_token}"},
            json=new_config
        )
        assert response.status_code == 200
        data = response.json()
        assert data["channels"]["telegram"]["enabled"] is True

    async def test_notification_config_unauthorized(self, client):
        response = await client.get("/api/v1/config/notification")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestFrequencyWords:
    async def test_get_frequency_words(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/frequency-words",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "frequency_words" in data

    async def test_update_frequency_words(self, client, test_user, test_token):
        response = await client.put(
            "/api/v1/config/frequency-words",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"frequency_words": "test words"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["frequency_words"] == "test words"

    async def test_frequency_words_unauthorized(self, client):
        response = await client.get("/api/v1/config/frequency-words")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestConfigExport:
    async def test_export_config(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/export",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "timezone" in data

    async def test_export_config_unauthorized(self, client):
        response = await client.get("/api/v1/config/export")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestConfigImport:
    async def test_import_config(self, client, test_user, test_token):
        config_data = {
            "timezone": "UTC",
            "schedule": {"enabled": True, "preset": "morning_evening"},
        }
        response = await client.post(
            "/api/v1/config/import",
            headers={"Authorization": f"Bearer {test_token}"},
            files={"file": ("config.json", json.dumps(config_data), "application/json")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "UTC"

    async def test_import_config_invalid_json(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/config/import",
            headers={"Authorization": f"Bearer {test_token}"},
            files={"file": ("config.json", "not valid json", "application/json")}
        )
        assert response.status_code == 400

    async def test_import_config_empty(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/config/import",
            headers={"Authorization": f"Bearer {test_token}"},
            files={"file": ("config.json", json.dumps({"unknown_field": "value"}), "application/json")}
        )
        assert response.status_code == 400

    async def test_import_config_unauthorized(self, client):
        response = await client.post(
            "/api/v1/config/import",
            files={"file": ("config.json", "{}", "application/json")}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestConfigDiff:
    async def test_get_config_diff(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/config/diff",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "modified" in data
        assert "unchanged" in data

    async def test_get_config_diff_unauthorized(self, client):
        response = await client.get("/api/v1/config/diff")
        assert response.status_code == 403

    async def test_get_config_diff_after_modification(self, client, test_user, test_token):
        # Modify schedule first
        await client.put(
            "/api/v1/config/schedule",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"enabled": False, "preset": "all_day"}
        )

        response = await client.get(
            "/api/v1/config/diff",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "schedule" in data["modified"]
