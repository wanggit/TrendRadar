"""
AI Prompts Module - Unit Tests
Tests: AIPrompt model, ConfigService AI prompt methods, API endpoints
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.user import User, UserTier, UserStatus
from app.models.ai_prompt import AIPrompt
from app.core.security import get_password_hash, create_access_token
from app.db.session import get_db
from app.services.config_service import ConfigService

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
class TestAIPromptModel:
    """Test AIPrompt model"""
    
    async def test_create_ai_prompt(self, test_db, test_user):
        prompt = AIPrompt(
            user_id=test_user.id,
            prompt_type="interests",
            content="Test interest content"
        )
        test_db.add(prompt)
        await test_db.flush()
        await test_db.refresh(prompt)
        
        assert prompt.id is not None
        assert prompt.user_id == test_user.id
        assert prompt.prompt_type == "interests"
        assert prompt.content == "Test interest content"
    
    async def test_ai_prompt_default_content(self, test_db, test_user):
        prompt = AIPrompt(
            user_id=test_user.id,
            prompt_type="classify"
        )
        test_db.add(prompt)
        await test_db.flush()
        await test_db.refresh(prompt)
        
        assert prompt.content == ""
    
    async def test_ai_prompt_repr(self, test_db, test_user):
        prompt = AIPrompt(
            user_id=test_user.id,
            prompt_type="extract",
            content="Test"
        )
        test_db.add(prompt)
        await test_db.flush()
        await test_db.refresh(prompt)
        
        assert repr(prompt) == f"<AIPrompt(user_id={test_user.id}, type=extract)>"


@pytest.mark.asyncio
class TestConfigServiceAIPrompts:
    """Test ConfigService AI prompt methods"""
    
    async def test_get_ai_prompt_empty(self, test_db, test_user):
        service = ConfigService(test_db)
        content = await service.get_ai_prompt(test_user.id, "interests")
        assert content == ""
    
    async def test_set_ai_prompt_new(self, test_db, test_user):
        service = ConfigService(test_db)
        prompt = await service.set_ai_prompt(test_user.id, "interests", "New content")
        
        assert prompt.content == "New content"
        assert prompt.prompt_type == "interests"
        assert prompt.user_id == test_user.id
    
    async def test_set_ai_prompt_update(self, test_db, test_user):
        service = ConfigService(test_db)
        
        # Create initial prompt
        await service.set_ai_prompt(test_user.id, "classify", "Initial content")
        
        # Update prompt
        prompt = await service.set_ai_prompt(test_user.id, "classify", "Updated content")
        
        assert prompt.content == "Updated content"
    
    async def test_get_ai_prompts_all_types(self, test_db, test_user):
        service = ConfigService(test_db)

        # Set all prompt types
        await service.set_ai_prompt(test_user.id, "interests", "Interest content")
        await service.set_ai_prompt(test_user.id, "classify", "Classify content")
        await service.set_ai_prompt(test_user.id, "extract", "Extract content")
        await service.set_ai_prompt(test_user.id, "update_tags", "Update content")
        await service.set_ai_prompt(test_user.id, "analysis", "Analysis content")

        prompts = await service.get_ai_prompts(test_user.id)

        assert prompts["interests_content"] == "Interest content"
        assert prompts["classify_prompt"] == "Classify content"
        assert prompts["extract_prompt"] == "Extract content"
        assert prompts["update_tags_prompt"] == "Update content"
        assert prompts["analysis_prompt"] == "Analysis content"

    async def test_set_ai_prompts_batch(self, test_db, test_user):
        service = ConfigService(test_db)

        prompts = {
            "interests_content": "Batch interest",
            "classify_prompt": "Batch classify",
            "extract_prompt": "Batch extract",
            "update_tags_prompt": "Batch update",
            "prompt_content": "Batch analysis",
        }
        await service.set_ai_prompts(test_user.id, prompts)

        retrieved = await service.get_ai_prompts(test_user.id)
        assert retrieved["interests_content"] == "Batch interest"
        assert retrieved["classify_prompt"] == "Batch classify"
        assert retrieved["extract_prompt"] == "Batch extract"
        assert retrieved["update_tags_prompt"] == "Batch update"
        assert retrieved["analysis_prompt"] == "Batch analysis"


@pytest.mark.asyncio
class TestAIPromptsAPI:
    """Test AI prompts API endpoints"""
    
    async def test_get_full_config_includes_prompts(self, client, test_user, test_token, test_db):
        service = ConfigService(test_db)
        await service.set_ai_prompt(test_user.id, "interests", "Test interests")
        await service.set_ai_prompt(test_user.id, "classify", "Test classify")
        
        response = await client.get(
            "/api/v1/config/",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ai_filter" in data
        assert data["ai_filter"]["interests_content"] == "Test interests"
        assert data["ai_filter"]["classify_prompt"] == "Test classify"
    
    async def test_update_full_config_saves_prompts(self, client, test_user, test_token, test_db):
        config_data = {
            "ai_filter": {
                "batch_size": 100,
                "batch_interval": 3,
                "min_score": 0.8,
                "reclassify_threshold": 0.5,
                "interests_content": "Updated interests",
                "classify_prompt": "Updated classify",
                "extract_prompt": "Updated extract",
                "update_tags_prompt": "Updated update",
            }
        }
        
        response = await client.put(
            "/api/v1/config/",
            headers={"Authorization": f"Bearer {test_token}"},
            json=config_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ai_filter"]["interests_content"] == "Updated interests"
        assert data["ai_filter"]["classify_prompt"] == "Updated classify"
        
        # Verify in database
        service = ConfigService(test_db)
        prompts = await service.get_ai_prompts(test_user.id)
        assert prompts["interests_content"] == "Updated interests"
        assert prompts["classify_prompt"] == "Updated classify"
    
    async def test_update_partial_prompts(self, client, test_user, test_token, test_db):
        # First set all prompts via API
        config_data = {
            "ai_filter": {
                "interests_content": "Original interests",
                "classify_prompt": "Original classify",
                "extract_prompt": "Original extract",
                "update_tags_prompt": "Original update",
            }
        }
        
        response = await client.put(
            "/api/v1/config/",
            headers={"Authorization": f"Bearer {test_token}"},
            json=config_data
        )
        assert response.status_code == 200
        
        # Verify all prompts were saved
        service = ConfigService(test_db)
        prompts = await service.get_ai_prompts(test_user.id)
        assert prompts["interests_content"] == "Original interests"
        assert prompts["classify_prompt"] == "Original classify"
        
        # Update only interests_content
        config_data = {
            "ai_filter": {
                "interests_content": "New interests only",
            }
        }
        
        response = await client.put(
            "/api/v1/config/",
            headers={"Authorization": f"Bearer {test_token}"},
            json=config_data
        )
        
        assert response.status_code == 200
        
        # Verify only interests was updated, others remain
        prompts = await service.get_ai_prompts(test_user.id)
        assert prompts["interests_content"] == "New interests only"
        assert prompts["classify_prompt"] == "Original classify"
        assert prompts["extract_prompt"] == "Original extract"
        assert prompts["update_tags_prompt"] == "Original update"


@pytest.mark.asyncio
class TestAIFilterConfigSchema:
    """Test AIFilterConfig schema with prompt content"""
    
    def test_ai_filter_config_default_values(self):
        from app.schemas.config import AIFilterConfig
        
        config = AIFilterConfig()
        
        assert config.batch_size == 200
        assert config.batch_interval == 2
        assert config.min_score == 0.7
        assert config.reclassify_threshold == 0.6
        assert config.interests_content != ""  # Should have default content
        assert config.classify_prompt != ""  # Should have default content
        assert config.extract_prompt != ""  # Should have default content
        assert config.update_tags_prompt != ""  # Should have default content
    
    def test_ai_filter_config_custom_values(self):
        from app.schemas.config import AIFilterConfig
        
        config = AIFilterConfig(
            batch_size=100,
            interests_content="Custom interests",
            classify_prompt="Custom classify",
        )
        
        assert config.batch_size == 100
        assert config.interests_content == "Custom interests"
        assert config.classify_prompt == "Custom classify"
        assert config.extract_prompt != ""  # Should have default
        assert config.update_tags_prompt != ""  # Should have default
    
    def test_ai_filter_config_contains_system_user_markers(self):
        from app.schemas.config import AIFilterConfig
        
        config = AIFilterConfig()
        
        assert "[system]" in config.classify_prompt
        assert "[user]" in config.classify_prompt
        assert "[system]" in config.extract_prompt
        assert "[user]" in config.extract_prompt
        assert "[system]" in config.update_tags_prompt
        assert "[user]" in config.update_tags_prompt


@pytest.mark.asyncio
class TestPromptContentParsing:
    """Test prompt content parsing logic"""
    
    def test_parse_prompt_content_with_system_user(self):
        content = """[system]
You are a classifier

[user]
Classify these items: {items}"""
        
        # Replicate the parsing logic from AIFilter
        if not content:
            system, user = "", ""
        elif "[system]" in content and "[user]" in content:
            parts = content.split("[user]")
            system_part = parts[0]
            user_part = parts[1] if len(parts) > 1 else ""
            system = system_part.split("[system]")[1].strip() if "[system]" in system_part else ""
            user = user_part.strip()
        else:
            system, user = "", content.strip()
        
        assert system == "You are a classifier"
        assert "{items}" in user
    
    def test_parse_prompt_content_empty(self):
        content = ""
        
        if not content:
            system, user = "", ""
        elif "[system]" in content and "[user]" in content:
            parts = content.split("[user]")
            system_part = parts[0]
            user_part = parts[1] if len(parts) > 1 else ""
            system = system_part.split("[system]")[1].strip() if "[system]" in system_part else ""
            user = user_part.strip()
        else:
            system, user = "", content.strip()
        
        assert system == ""
        assert user == ""
    
    def test_parse_prompt_content_no_markers(self):
        content = "Just plain text"
        
        if not content:
            system, user = "", ""
        elif "[system]" in content and "[user]" in content:
            parts = content.split("[user]")
            system_part = parts[0]
            user_part = parts[1] if len(parts) > 1 else ""
            system = system_part.split("[system]")[1].strip() if "[system]" in system_part else ""
            user = user_part.strip()
        else:
            system, user = "", content.strip()
        
        assert system == ""
        assert user == "Just plain text"


@pytest.mark.asyncio
class TestAIAnalysisPromptSchema:
    """Test AIAnalysisConfig schema with prompt_content"""

    def test_ai_analysis_config_default_values(self):
        from app.schemas.config import AIAnalysisConfig

        config = AIAnalysisConfig()

        assert config.enabled is True
        assert config.language == "Chinese"
        assert config.mode == "follow_report"
        assert config.max_news_for_analysis == 150
        assert config.prompt_content != ""  # Should have default content
        assert config.include_rss is False
        assert config.include_standalone is True
        assert config.include_rank_timeline is True

    def test_ai_analysis_config_contains_system_user_markers(self):
        from app.schemas.config import AIAnalysisConfig

        config = AIAnalysisConfig()

        assert "[system]" in config.prompt_content
        assert "[user]" in config.prompt_content

    def test_ai_analysis_config_custom_prompt_content(self):
        from app.schemas.config import AIAnalysisConfig

        custom_prompt = """[system]
You are a custom analyzer

[user]
Analyze: {news_content}"""

        config = AIAnalysisConfig(prompt_content=custom_prompt)

        assert config.prompt_content == custom_prompt
        assert "[system]" in config.prompt_content
        assert "[user]" in config.prompt_content


@pytest.mark.asyncio
class TestAIAnalysisPromptAPI:
    """Test AI analysis prompt API endpoints"""

    async def test_get_full_config_includes_analysis_prompt(self, client, test_user, test_token, test_db):
        service = ConfigService(test_db)
        await service.set_ai_prompt(test_user.id, "analysis", "Test analysis prompt")

        response = await client.get(
            "/api/v1/config/",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "ai_analysis" in data
        assert data["ai_analysis"]["prompt_content"] == "Test analysis prompt"

    async def test_update_full_config_saves_analysis_prompt(self, client, test_user, test_token, test_db):
        config_data = {
            "ai_analysis": {
                "enabled": True,
                "language": "中文",
                "mode": "daily",
                "max_news_for_analysis": 100,
                "prompt_content": "Updated analysis prompt",
                "include_rss": True,
                "include_standalone": False,
                "include_rank_timeline": True,
            }
        }

        response = await client.put(
            "/api/v1/config/",
            headers={"Authorization": f"Bearer {test_token}"},
            json=config_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ai_analysis"]["prompt_content"] == "Updated analysis prompt"

        # Verify in database
        service = ConfigService(test_db)
        content = await service.get_ai_prompt(test_user.id, "analysis")
        assert content == "Updated analysis prompt"

    async def test_update_partial_analysis_config_preserves_prompt(self, client, test_user, test_token, test_db):
        # First set the analysis prompt
        service = ConfigService(test_db)
        await service.set_ai_prompt(test_user.id, "analysis", "Original analysis prompt")

        # Update only other fields
        config_data = {
            "ai_analysis": {
                "enabled": True,
                "language": "English",
            }
        }

        response = await client.put(
            "/api/v1/config/",
            headers={"Authorization": f"Bearer {test_token}"},
            json=config_data
        )

        assert response.status_code == 200
        data = response.json()
        # The prompt should still be the original one since we didn't update it
        assert data["ai_analysis"]["prompt_content"] == "Original analysis prompt"
