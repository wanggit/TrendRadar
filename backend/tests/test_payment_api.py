"""
Payment API Module - Unit Tests
Tests: create order, list orders, get order, get order status, payment callback
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models.user import User, UserTier, UserStatus
from app.models.order import Order, OrderStatus, ProductType, PaymentMethod
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
async def test_order(test_db, test_user):
    order = Order(
        user_id=test_user.id,
        order_no="TR2026050900000012345678",
        product_type=ProductType.MONTHLY,
        amount=29.9,
        payment_method=PaymentMethod.ALIPAY,
        status=OrderStatus.PENDING,
    )
    test_db.add(order)
    await test_db.flush()
    await test_db.refresh(order)
    return order


@pytest.mark.asyncio
class TestCreateOrder:
    async def test_create_order_payment_not_configured(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/payment/create",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"product_type": "monthly", "payment_method": "alipay"}
        )
        assert response.status_code == 500
        assert "Payment service not configured" in response.json()["detail"]

    async def test_create_order_invalid_product(self, client, test_user, test_token):
        response = await client.post(
            "/api/v1/payment/create",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"product_type": "invalid", "payment_method": "alipay"}
        )
        assert response.status_code == 422

    async def test_create_order_unauthorized(self, client):
        response = await client.post(
            "/api/v1/payment/create",
            json={"product_type": "monthly", "payment_method": "alipay"}
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestListOrders:
    async def test_list_orders_empty(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/payment/orders",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_orders(self, client, test_user, test_token, test_order):
        response = await client.get(
            "/api/v1/payment/orders",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["order_no"] == "TR2026050900000012345678"

    async def test_list_orders_unauthorized(self, client):
        response = await client.get("/api/v1/payment/orders")
        assert response.status_code == 403

    async def test_list_orders_user_isolation(self, client, test_user, test_token, test_db):
        other_user = User(
            email="other@test.com",
            password_hash=get_password_hash("otherpass123"),
        )
        test_db.add(other_user)
        await test_db.flush()

        other_order = Order(
            user_id=other_user.id,
            order_no="TR2026050900000099999999",
            product_type=ProductType.MONTHLY,
            amount=29.9,
            payment_method=PaymentMethod.ALIPAY,
            status=OrderStatus.PENDING,
        )
        test_db.add(other_order)
        await test_db.flush()

        response = await client.get(
            "/api/v1/payment/orders",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


@pytest.mark.asyncio
class TestGetOrder:
    async def test_get_order(self, client, test_user, test_token, test_order):
        response = await client.get(
            f"/api/v1/payment/orders/{test_order.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_order.id
        assert data["order_no"] == test_order.order_no

    async def test_get_order_not_found(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/payment/orders/99999",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404

    async def test_get_order_user_isolation(self, client, test_user, test_token, test_db):
        other_user = User(
            email="other2@test.com",
            password_hash=get_password_hash("otherpass123"),
        )
        test_db.add(other_user)
        await test_db.flush()

        other_order = Order(
            user_id=other_user.id,
            order_no="TR2026050900000088888888",
            product_type=ProductType.MONTHLY,
            amount=29.9,
            payment_method=PaymentMethod.ALIPAY,
            status=OrderStatus.PENDING,
        )
        test_db.add(other_order)
        await test_db.flush()
        await test_db.refresh(other_order)

        response = await client.get(
            f"/api/v1/payment/orders/{other_order.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404

    async def test_get_order_unauthorized(self, client):
        response = await client.get("/api/v1/payment/orders/1")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestGetOrderStatus:
    async def test_get_order_status(self, client, test_user, test_token, test_order):
        response = await client.get(
            f"/api/v1/payment/orders/{test_order.id}/status",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == test_order.id
        assert data["status"] == "pending"

    async def test_get_order_status_not_found(self, client, test_user, test_token):
        response = await client.get(
            "/api/v1/payment/orders/99999/status",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404

    async def test_get_order_status_unauthorized(self, client):
        response = await client.get("/api/v1/payment/orders/1/status")
        assert response.status_code == 403


@pytest.mark.asyncio
class TestPaymentCallback:
    async def test_zpay_callback_missing_signature(self, client):
        response = await client.post(
            "/api/v1/payment/callback/zpay",
            data={"out_trade_no": "TR2026050900000012345678"}
        )
        assert response.status_code == 200
        assert response.text == "fail"

    async def test_zpay_callback_order_not_found(self, client):
        response = await client.post(
            "/api/v1/payment/callback/zpay",
            data={
                "out_trade_no": "TR_NONEXISTENT",
                "sign": "fakesign",
                "trade_status": "TRADE_SUCCESS",
                "money": "29.9",
            }
        )
        assert response.status_code == 200
        assert response.text == "fail"
