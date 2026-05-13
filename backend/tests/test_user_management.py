"""
User Management Module - Unit Tests
Tests: CRUD operations, password reset, access control, validation
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.user import User, UserTier, UserStatus
from app.core.security import get_password_hash
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
        from app.models.user import Base
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
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def admin_user(test_db):
    """Create admin user for testing"""
    admin = User(
        email="admin@test.com",
        password_hash=get_password_hash("adminpass123"),
        nickname="Test Admin",
        is_superuser=True,
        tier=UserTier.ENTERPRISE,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    test_db.add(admin)
    await test_db.flush()
    await test_db.refresh(admin)
    return admin


@pytest_asyncio.fixture(scope="function")
async def regular_user(test_db):
    """Create regular user for testing"""
    user = User(
        email="regular@test.com",
        password_hash=get_password_hash("userpass123"),
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
def admin_token(admin_user):
    """Generate admin JWT token"""
    from app.core.security import create_access_token
    return create_access_token(subject=str(admin_user.id))


@pytest.fixture
def regular_token(regular_user):
    """Generate regular user JWT token"""
    from app.core.security import create_access_token
    return create_access_token(subject=str(regular_user.id))


@pytest.mark.asyncio
class TestUserAuthentication:
    """Test authentication and access control"""
    
    async def test_login_success(self, client, admin_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "adminpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_login_wrong_password(self, client, admin_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
    
    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "password123"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestUserList:
    """Test user listing endpoint"""
    
    async def test_list_users_as_admin(self, client, admin_user, regular_user, admin_token):
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
    
    async def test_list_users_as_regular_forbidden(self, client, regular_user, regular_token):
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        assert response.status_code == 403
    
    async def test_list_users_unauthorized(self, client):
        response = await client.get("/api/v1/users/")
        assert response.status_code == 403
    
    async def test_list_users_with_search(self, client, admin_user, regular_user, admin_token):
        response = await client.get(
            "/api/v1/users/?search=admin",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "admin@test.com"
    
    async def test_list_users_pagination(self, client, admin_user, admin_token, test_db):
        # Create more users
        for i in range(5):
            user = User(
                email=f"user{i}@test.com",
                password_hash=get_password_hash("password123"),
                nickname=f"User {i}",
            )
            test_db.add(user)
        await test_db.flush()
        
        response = await client.get(
            "/api/v1/users/?skip=0&limit=3",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 3


@pytest.mark.asyncio
class TestUserCreate:
    """Test user creation endpoint"""
    
    async def test_create_user_success(self, client, admin_user, admin_token):
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "newuser@test.com",
                "nickname": "New User",
                "password": "newpass123",
                "tier": "free",
                "status": "active"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["nickname"] == "New User"
        assert data["tier"] == "free"
        assert data["status"] == "active"
        assert "id" in data
    
    async def test_create_user_duplicate_email(self, client, admin_user, regular_user, admin_token):
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "regular@test.com",
                "nickname": "Duplicate",
                "password": "password123"
            }
        )
        assert response.status_code == 400
    
    async def test_create_user_invalid_email(self, client, admin_user, admin_token):
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "not-an-email",
                "nickname": "Invalid",
                "password": "password123"
            }
        )
        assert response.status_code == 422
    
    async def test_create_user_short_password(self, client, admin_user, admin_token):
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "test@test.com",
                "nickname": "Test",
                "password": "short"
            }
        )
        assert response.status_code == 422
    
    async def test_create_user_as_regular_forbidden(self, client, regular_user, regular_token):
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={
                "email": "new@test.com",
                "password": "password123"
            }
        )
        assert response.status_code == 403
    
    async def test_create_user_with_tier(self, client, admin_user, admin_token):
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "pro@test.com",
                "password": "password123",
                "tier": "pro",
                "status": "active"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tier"] == "pro"
    
    async def test_create_user_as_superuser(self, client, admin_user, admin_token):
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "super@test.com",
                "password": "password123",
                "is_superuser": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_superuser"] is True


@pytest.mark.asyncio
class TestUserGet:
    """Test get single user endpoint"""
    
    async def test_get_user_success(self, client, admin_user, regular_user, admin_token):
        response = await client.get(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == regular_user.id
        assert data["email"] == "regular@test.com"
    
    async def test_get_user_not_found(self, client, admin_user, admin_token):
        response = await client.get(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    async def test_get_user_as_regular_forbidden(self, client, regular_user, regular_token):
        response = await client.get(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestUserUpdate:
    """Test user update endpoint"""
    
    async def test_update_user_nickname(self, client, admin_user, regular_user, admin_token):
        response = await client.put(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"nickname": "Updated Nickname"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "Updated Nickname"
    
    async def test_update_user_tier(self, client, admin_user, regular_user, admin_token):
        response = await client.put(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"tier": "enterprise"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "enterprise"
    
    async def test_update_user_status(self, client, admin_user, regular_user, admin_token):
        response = await client.put(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "suspended"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"
    
    async def test_update_user_not_found(self, client, admin_user, admin_token):
        response = await client.put(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"nickname": "Test"}
        )
        assert response.status_code == 404
    
    async def test_update_user_cannot_unverify_superuser(self, client, admin_user, admin_token):
        response = await client.put(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email_verified": False}
        )
        assert response.status_code == 400
    
    async def test_update_user_as_regular_forbidden(self, client, regular_user, regular_token):
        response = await client.put(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={"nickname": "Hacked"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestUserDelete:
    """Test user deletion endpoint"""
    
    async def test_delete_user_success(self, client, admin_user, admin_token, test_db):
        # Create a user to delete
        user = User(
            email="delete@test.com",
            password_hash=get_password_hash("password123"),
            nickname="Delete Me",
        )
        test_db.add(user)
        await test_db.flush()
        await test_db.refresh(user)
        
        response = await client.delete(
            f"/api/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 204
    
    async def test_delete_user_not_found(self, client, admin_user, admin_token):
        response = await client.delete(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    async def test_delete_self_forbidden(self, client, admin_user, admin_token):
        response = await client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
    
    async def test_delete_user_as_regular_forbidden(self, client, admin_user, regular_user, regular_token):
        response = await client.delete(
            f"/api/v1/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestPasswordReset:
    """Test password reset endpoint"""
    
    async def test_reset_password_success(self, client, admin_user, regular_user, admin_token):
        response = await client.post(
            f"/api/v1/users/{regular_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Password reset successfully" in data["message"]
        assert "New password:" in data["message"]
    
    async def test_reset_password_not_found(self, client, admin_user, admin_token):
        response = await client.post(
            "/api/v1/users/99999/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    async def test_reset_self_password_forbidden(self, client, admin_user, admin_token):
        response = await client.post(
            f"/api/v1/users/{admin_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
    
    async def test_reset_password_as_regular_forbidden(self, client, admin_user, regular_user, regular_token):
        response = await client.post(
            f"/api/v1/users/{regular_user.id}/reset-password",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        assert response.status_code == 403
    
    async def test_reset_password_generates_valid_password(self, client, admin_user, regular_user, admin_token):
        response = await client.post(
            f"/api/v1/users/{regular_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        new_password = data["message"].split("New password: ")[1]
        assert len(new_password) >= 12
        
        # Verify new password works
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "regular@test.com", "password": new_password}
        )
        assert login_resp.status_code == 200


@pytest.mark.asyncio
class TestUserMyProfile:
    """Test user profile endpoints"""
    
    async def test_get_my_profile(self, client, regular_user, regular_token):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "regular@test.com"
    
    async def test_update_my_profile(self, client, regular_user, regular_token):
        response = await client.put(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={"nickname": "My New Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "My New Name"
    
    async def test_update_my_password(self, client, regular_user, regular_token):
        response = await client.put(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={"password": "newpassword123"}
        )
        assert response.status_code == 200
        
        # Verify new password works
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "regular@test.com", "password": "newpassword123"}
        )
        assert login_resp.status_code == 200
