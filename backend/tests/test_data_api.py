"""
Data API Module - Unit Tests
Tests: platforms, news, RSS feeds, RSS items CRUD and filtering
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.user import User, UserTier, UserStatus
from app.models.news import Platform, NewsItem
from app.models.rss import RSSFeed, RSSItem
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


@pytest_asyncio.fixture(scope="function")
async def test_platform(test_db, test_user):
    platform = Platform(
        user_id=test_user.id,
        source_id="weibo",
        name="微博热搜",
        enabled=True,
    )
    test_db.add(platform)
    await test_db.flush()
    await test_db.refresh(platform)
    return platform


@pytest_asyncio.fixture(scope="function")
async def test_news_items(test_db, test_user, test_platform):
    now = datetime.now(timezone.utc)
    items = []
    for i in range(5):
        item = NewsItem(
            user_id=test_user.id,
            platform_id=test_platform.id,
            title=f"Test News {i}",
            url=f"https://example.com/news/{i}",
            rank=i + 1,
            hot_value=100.0 - i * 10,
            crawl_time=now,
        )
        test_db.add(item)
        items.append(item)
    await test_db.flush()
    return items


@pytest_asyncio.fixture(scope="function")
async def test_rss_feed(test_db, test_user):
    feed = RSSFeed(
        user_id=test_user.id,
        feed_url="https://example.com/feed.xml",
        name="Test Feed",
        enabled=True,
        max_age_days=1,
    )
    test_db.add(feed)
    await test_db.flush()
    await test_db.refresh(feed)
    return feed


@pytest_asyncio.fixture(scope="function")
async def test_rss_items(test_db, test_user, test_rss_feed):
    now = datetime.now(timezone.utc)
    items = []
    for i in range(3):
        item = RSSItem(
            user_id=test_user.id,
            feed_id=test_rss_feed.id,
            title=f"RSS Item {i}",
            url=f"https://example.com/rss/{i}",
            summary=f"Summary {i}",
            crawl_time=now,
        )
        test_db.add(item)
        items.append(item)
    await test_db.flush()
    return items


@pytest.mark.asyncio
class TestPlatformsAPI:
    async def test_list_platforms_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/data/platforms",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_platforms(self, client, test_user, test_token, test_platform):
        response = await client.get(
            "/api/v1/data/platforms",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source_id"] == "weibo"
        assert data[0]["name"] == "微博热搜"

    async def test_create_platform(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/data/platforms",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"source_id": "zhihu", "name": "知乎热榜", "enabled": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "zhihu"
        assert data["name"] == "知乎热榜"

    async def test_delete_platform(self, client, test_user, test_token, test_platform):
        response = await client.delete(
            f"/api/v1/data/platforms/{test_platform.source_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 204

    async def test_delete_platform_not_found(self, client, test_user, test_token):
        response = await client.delete(
            "/api/v1/data/platforms/nonexistent",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404

    async def test_list_platforms_unauthorized(self, client):
        response = await client.get("/api/v1/data/platforms")
        assert response.status_code == 403

    async def test_platform_user_isolation(self, client, test_user, test_token, test_db):
        other_user = User(
            email="other@test.com",
            password_hash=get_password_hash("otherpass123"),
        )
        test_db.add(other_user)
        await test_db.flush()

        other_platform = Platform(
            user_id=other_user.id,
            source_id="baidu",
            name="百度热搜",
        )
        test_db.add(other_platform)
        await test_db.flush()

        response = await client.get(
            "/api/v1/data/platforms",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


@pytest.mark.asyncio
class TestNewsAPI:
    async def test_list_news_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/data/news",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_news(self, client, test_user, test_token, test_news_items):
        response = await client.get(
            "/api/v1/data/news",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    async def test_list_news_pagination(self, client, test_user, test_token, test_news_items):
        response = await client.get(
            "/api/v1/data/news?limit=2&offset=0",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    async def test_list_news_filter_by_platform(self, client, test_user, test_token, test_platform, test_news_items):
        response = await client.get(
            f"/api/v1/data/news?platform_id={test_platform.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5

    async def test_list_news_filter_by_keyword(self, client, test_user, test_token, test_platform, test_db):
        now = datetime.now(timezone.utc)
        item = NewsItem(
            user_id=test_user.id,
            platform_id=test_platform.id,
            title="AI breakthrough in China",
            url="https://example.com/ai-news",
            rank=1,
            crawl_time=now,
        )
        test_db.add(item)
        await test_db.flush()

        response = await client.get(
            "/api/v1/data/news?keyword=AI",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "AI" in data["items"][0]["title"]

    async def test_list_news_unauthorized(self, client):
        response = await client.get("/api/v1/data/news")
        assert response.status_code == 403

    async def test_news_user_isolation(self, client, test_user, test_token, test_db, test_platform):
        now = datetime.now(timezone.utc)
        other_user = User(
            email="other2@test.com",
            password_hash=get_password_hash("otherpass123"),
        )
        test_db.add(other_user)
        await test_db.flush()

        other_item = NewsItem(
            user_id=other_user.id,
            platform_id=test_platform.id,
            title="Other user news",
            url="https://example.com/other",
            rank=1,
            crawl_time=now,
        )
        test_db.add(other_item)
        await test_db.flush()

        response = await client.get(
            "/api/v1/data/news",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


@pytest.mark.asyncio
class TestRSSFeedsAPI:
    async def test_list_rss_feeds_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/data/rss/feeds",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_rss_feeds(self, client, test_user, test_token, test_rss_feed):
        response = await client.get(
            "/api/v1/data/rss/feeds",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["feed_url"] == "https://example.com/feed.xml"

    async def test_create_rss_feed(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/data/rss/feeds",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"feed_url": "https://blog.example.com/rss", "name": "My Blog", "max_age_days": 7}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feed_url"] == "https://blog.example.com/rss"
        assert data["name"] == "My Blog"

    async def test_update_rss_feed(self, client, test_user, test_token, test_rss_feed):
        response = await client.put(
            f"/api/v1/data/rss/feeds/{test_rss_feed.id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"feed_url": "https://new.example.com/feed", "name": "Updated Feed", "max_age_days": 3, "enabled": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feed_url"] == "https://new.example.com/feed"
        assert data["name"] == "Updated Feed"
        assert data["enabled"] is False

    async def test_delete_rss_feed(self, client, test_user, test_token, test_rss_feed):
        response = await client.delete(
            f"/api/v1/data/rss/feeds/{test_rss_feed.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 204

    async def test_delete_rss_feed_not_found(self, client, test_user, test_token):
        response = await client.delete(
            "/api/v1/data/rss/feeds/99999",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404

    async def test_rss_feed_user_isolation(self, client, test_user, test_token, test_db):
        other_user = User(
            email="other3@test.com",
            password_hash=get_password_hash("otherpass123"),
        )
        test_db.add(other_user)
        await test_db.flush()

        other_feed = RSSFeed(
            user_id=other_user.id,
            feed_url="https://other.example.com/feed",
            name="Other Feed",
        )
        test_db.add(other_feed)
        await test_db.flush()

        response = await client.get(
            "/api/v1/data/rss/feeds",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
class TestRSSItemsAPI:
    async def test_list_rss_items_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/data/rss/items",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_list_rss_items(self, client, test_user, test_token, test_rss_items):
        response = await client.get(
            "/api/v1/data/rss/items",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_rss_items_pagination(self, client, test_user, test_token, test_rss_items):
        response = await client.get(
            "/api/v1/data/rss/items?limit=2&offset=0",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    async def test_list_rss_items_filter_by_feed(self, client, test_user, test_token, test_rss_feed, test_rss_items):
        response = await client.get(
            f"/api/v1/data/rss/items?feed_id={test_rss_feed.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    async def test_list_rss_items_filter_by_keyword(self, client, test_user, test_token, test_rss_feed, test_db):
        now = datetime.now(timezone.utc)
        item = RSSItem(
            user_id=test_user.id,
            feed_id=test_rss_feed.id,
            title="Machine Learning advances",
            url="https://example.com/ml",
            summary="ML summary",
            crawl_time=now,
        )
        test_db.add(item)
        await test_db.flush()

        response = await client.get(
            "/api/v1/data/rss/items?keyword=Machine",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Machine" in data["items"][0]["title"]

    async def test_list_rss_items_unauthorized(self, client):
        response = await client.get("/api/v1/data/rss/items")
        assert response.status_code == 403

    async def test_rss_items_user_isolation(self, client, test_user, test_token, test_db, test_rss_feed):
        now = datetime.now(timezone.utc)
        other_user = User(
            email="other4@test.com",
            password_hash=get_password_hash("otherpass123"),
        )
        test_db.add(other_user)
        await test_db.flush()

        other_item = RSSItem(
            user_id=other_user.id,
            feed_id=test_rss_feed.id,
            title="Other user RSS item",
            url="https://example.com/other-rss",
            crawl_time=now,
        )
        test_db.add(other_item)
        await test_db.flush()

        response = await client.get(
            "/api/v1/data/rss/items",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
