"""
AI Reports Module - Unit Tests
Tests: AIReport model, DeepAnalysisService, API endpoints
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.user import User, UserTier, UserStatus
from app.models.ai_report import AIReport
from app.core.security import get_password_hash, create_access_token
from app.db.session import get_db

# Test database URL (in-memory SQLite)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database session"""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create tables
    async with engine.begin() as conn:
        from app.db.base import Base
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """Create test client with overridden DB dependency"""
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
    """Create test user"""
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
    """Generate test user JWT token"""
    return create_access_token(subject=str(test_user.id))


@pytest.mark.asyncio
class TestAIReportModel:
    """Test AIReport model"""
    
    async def test_create_ai_report(self, test_db, test_user):
        report = AIReport(
            user_id=test_user.id,
            task_id="test-task-123",
            core_trends="Test core trends",
            sentiment_controversy="Test sentiment",
            signals="Test signals",
            rss_insights="Test RSS insights",
            outlook_strategy="Test outlook",
            standalone_summaries={"source1": "summary1"},
            success=True,
            method="ai",
            total_news=50,
            analyzed_news=45,
            hotlist_count=40,
            rss_count=10,
        )
        test_db.add(report)
        await test_db.flush()
        await test_db.refresh(report)
        
        assert report.id is not None
        assert report.user_id == test_user.id
        assert report.task_id == "test-task-123"
        assert report.core_trends == "Test core trends"
        assert report.success is True
        assert report.method == "ai"
        assert report.total_news == 50
    
    async def test_ai_report_default_values(self, test_db, test_user):
        report = AIReport(
            user_id=test_user.id,
            task_id="test-task-456",
        )
        test_db.add(report)
        await test_db.flush()
        await test_db.refresh(report)
        
        assert report.core_trends == ""
        assert report.sentiment_controversy == ""
        assert report.signals == ""
        assert report.rss_insights == ""
        assert report.outlook_strategy == ""
        assert report.standalone_summaries == {}
        assert report.success is False
        assert report.method == "ai"
        assert report.total_news == 0
    
    async def test_ai_report_with_error(self, test_db, test_user):
        report = AIReport(
            user_id=test_user.id,
            success=False,
            error="AI API timeout",
            method="ai",
        )
        test_db.add(report)
        await test_db.flush()
        await test_db.refresh(report)
        
        assert report.success is False
        assert report.error == "AI API timeout"
    
    async def test_ai_report_keyword_method(self, test_db, test_user):
        report = AIReport(
            user_id=test_user.id,
            method="keyword",
            success=True,
            tags={"科技": 10, "财经": 5},
            filtered_count=15,
        )
        test_db.add(report)
        await test_db.flush()
        await test_db.refresh(report)
        
        assert report.method == "keyword"
        assert report.tags == {"科技": 10, "财经": 5}
        assert report.filtered_count == 15


@pytest.mark.asyncio
class TestAIReportsAPI:
    """Test AI reports API endpoints"""
    
    async def test_get_latest_report_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/reports/latest",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        assert response.json() is None
    
    async def test_get_latest_report(self, client, test_user, test_token, test_db):
        report = AIReport(
            user_id=test_user.id,
            task_id="task-1",
            core_trends="Latest trends",
            sentiment_controversy="Latest sentiment",
            signals="Latest signals",
            rss_insights="Latest RSS",
            outlook_strategy="Latest outlook",
            success=True,
            total_news=30,
            analyzed_news=25,
        )
        test_db.add(report)
        await test_db.flush()
        
        response = await client.get(
            "/api/v1/tasks/reports/latest",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["core_trends"] == "Latest trends"
        assert data["sentiment_controversy"] == "Latest sentiment"
        assert data["signals"] == "Latest signals"
        assert data["rss_insights"] == "Latest RSS"
        assert data["outlook_strategy"] == "Latest outlook"
        assert data["success"] is True
        assert data["total_news"] == 30
    
    async def test_get_report_by_id(self, client, test_user, test_token, test_db):
        report = AIReport(
            user_id=test_user.id,
            task_id="task-2",
            core_trends="Specific report",
            success=True,
            hotlist_count=20,
            rss_count=5,
        )
        test_db.add(report)
        await test_db.flush()
        await test_db.refresh(report)
        
        response = await client.get(
            f"/api/v1/tasks/reports/{report.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == report.id
        assert data["core_trends"] == "Specific report"
        assert data["hotlist_count"] == 20
        assert data["rss_count"] == 5
    
    async def test_get_report_not_found(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/tasks/reports/99999",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 404
    
    async def test_get_report_isolation(self, client, test_user, test_token, test_db):
        """Ensure users can only access their own reports"""
        other_user = User(
            email="other@test.com",
            password_hash=get_password_hash("otherpass123"),
        )
        test_db.add(other_user)
        await test_db.flush()
        
        report = AIReport(
            user_id=other_user.id,
            core_trends="Other user report",
            success=True,
        )
        test_db.add(report)
        await test_db.flush()
        await test_db.refresh(report)
        
        response = await client.get(
            f"/api/v1/tasks/reports/{report.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 404
    
    async def test_get_reports_list(self, client, test_user, test_token, test_db):
        for i in range(5):
            report = AIReport(
                user_id=test_user.id,
                task_id=f"task-{i}",
                core_trends=f"Report {i}",
                success=True,
            )
            test_db.add(report)
        await test_db.flush()
        
        response = await client.get(
            "/api/v1/tasks/reports",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["reports"]) == 5
    
    async def test_get_reports_pagination(self, client, test_user, test_token, test_db):
        for i in range(10):
            report = AIReport(
                user_id=test_user.id,
                task_id=f"task-{i}",
                core_trends=f"Report {i}",
                success=True,
            )
            test_db.add(report)
        await test_db.flush()
        
        response = await client.get(
            "/api/v1/tasks/reports?page=1&page_size=3",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["reports"]) == 3
    
    async def test_get_reports_unauthorized(self, client):
        response = await client.get("/api/v1/tasks/reports/latest")
        assert response.status_code == 403
        
        response = await client.get("/api/v1/tasks/reports/1")
        assert response.status_code == 403
        
        response = await client.get("/api/v1/tasks/reports")
        assert response.status_code == 403
    
    async def test_get_reports_returns_newest_first(self, client, test_user, test_token, test_db):
        import asyncio
        for i in range(3):
            report = AIReport(
                user_id=test_user.id,
                task_id=f"task-{i}",
                core_trends=f"Report {i}",
                success=True,
            )
            test_db.add(report)
            await test_db.flush()
            await asyncio.sleep(0.01)
        
        response = await client.get(
            "/api/v1/tasks/reports",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["reports"]) == 3
        assert data["reports"][0]["core_trends"] == "Report 2"
    
    async def test_report_response_schema(self, client, test_user, test_token, test_db):
        report = AIReport(
            user_id=test_user.id,
            task_id="task-schema",
            core_trends="Core",
            sentiment_controversy="Sentiment",
            signals="Signals",
            rss_insights="RSS",
            outlook_strategy="Outlook",
            standalone_summaries={"知乎": "知乎总结", "微博": "微博总结"},
            success=True,
            method="ai",
            total_news=100,
            analyzed_news=90,
            hotlist_count=80,
            rss_count=20,
        )
        test_db.add(report)
        await test_db.flush()
        await test_db.refresh(report)
        
        response = await client.get(
            f"/api/v1/tasks/reports/{report.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "id", "task_id", "core_trends", "sentiment_controversy",
            "signals", "rss_insights", "outlook_strategy",
            "standalone_summaries", "success", "error", "method",
            "total_news", "analyzed_news", "hotlist_count", "rss_count",
            "created_at"
        ]
        for field in required_fields:
            assert field in data
        
        assert data["standalone_summaries"] == {"知乎": "知乎总结", "微博": "微博总结"}
        assert data["method"] == "ai"
