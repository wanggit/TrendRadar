import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserTier
from app.models.order import Order, OrderStatus, ProductType, PaymentMethod
from app.schemas.payment import (
    CreateOrderRequest,
    OrderResponse,
    OrderCreateResponse,
    OrderListResponse,
    OrderStatusResponse,
)
from app.core.constants import PRODUCT_PRICES

router = APIRouter(prefix="/payment", tags=["payment"])


def _generate_order_no() -> str:
    now = datetime.now(timezone.utc)
    return f"TR{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"


def _calculate_expire_date(product_type: ProductType) -> datetime:
    days = PRODUCT_PRICES[product_type.value]["days"]
    return datetime.now(timezone.utc) + timedelta(days=days)


@router.post("/create", response_model=OrderCreateResponse)
async def create_order(
    req: CreateOrderRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product_info = PRODUCT_PRICES.get(req.product_type.value)
    if not product_info:
        raise HTTPException(status_code=400, detail="Invalid product type")

    order_no = _generate_order_no()
    order_expire_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    order = Order(
        user_id=current_user.id,
        order_no=order_no,
        product_type=req.product_type,
        amount=product_info["price"],
        payment_method=req.payment_method,
        status=OrderStatus.PENDING,
        expire_at=order_expire_at,
    )
    db.add(order)
    await db.flush()

    from app.services.payment import ZPayService

    zpay = ZPayService()
    if not zpay.uid or not zpay.key:
        raise HTTPException(status_code=500, detail="Payment service not configured")

    payment_type = "alipay" if req.payment_method == PaymentMethod.ALIPAY else "wxpay"
    subject = f"TrendRadar 专业版 {product_info['label']}"
    notify_url = f"{request.base_url}api/v1/payment/callback/zpay"
    frontend_url = "http://localhost:5173"
    return_url = f"{frontend_url}/orders"

    client_ip = request.client.host if request.client else "127.0.0.1"
    result = zpay.create_order(
        order_no=order_no,
        amount=product_info["price"],
        subject=subject,
        notify_url=notify_url,
        return_url=return_url,
        payment_type=payment_type,
        clientip=client_ip,
    )

    if result["code"] != 0:
        raise HTTPException(status_code=502, detail=result.get("msg", "Failed to create payment order"))

    await db.commit()
    await db.refresh(order)

    return OrderCreateResponse(
        order_id=order.id,
        order_no=order.order_no,
        payment_url=result["data"]["pay_url"],
    )


@router.post("/callback/zpay", response_class=PlainTextResponse)
async def zpay_callback(request: Request, db: AsyncSession = Depends(get_db)):
    form_data = await request.form()
    data = dict(form_data)

    from app.services.payment import ZPayService

    zpay = ZPayService()
    if not zpay.verify_callback(data):
        return PlainTextResponse("fail")

    order_no = data.get("out_trade_no")
    if not order_no:
        return PlainTextResponse("fail")

    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if not order:
        return PlainTextResponse("fail")

    if order.status == OrderStatus.PAID:
        return PlainTextResponse("success")

    money = float(data.get("money", 0))
    if abs(money - order.amount) > 0.01:
        return PlainTextResponse("fail")

    trade_status = data.get("trade_status", "")
    if trade_status != "TRADE_SUCCESS":
        order.status = OrderStatus.FAILED
        await db.commit()
        return PlainTextResponse("success")

    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc)
    order.trade_no = data.get("trade_no")

    user_result = await db.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.tier = UserTier.PRO
        user.expire_at = _calculate_expire_date(order.product_type)

    await db.commit()
    return PlainTextResponse("success")


@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    count_result = await db.execute(
        select(func.count(Order.id)).where(Order.user_id == current_user.id)
    )
    total = count_result.scalar()

    return OrderListResponse(
        total=total,
        items=[OrderResponse.model_validate(o) for o in orders],
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/orders/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == OrderStatus.PENDING:
        from app.services.payment import ZPayService

        zpay = ZPayService()
        query_result = zpay.query_order(order.order_no)
        if query_result.get("status") == 1:
            order.status = OrderStatus.PAID
            order.paid_at = datetime.now(timezone.utc)
            order.trade_no = query_result.get("trade_no")
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            if user:
                user.tier = UserTier.PRO
                user.expire_at = _calculate_expire_date(order.product_type)
            await db.commit()

    return OrderStatusResponse(
        order_id=order.id,
        status=order.status,
    )
