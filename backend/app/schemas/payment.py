from datetime import datetime
from pydantic import BaseModel, Field

from app.models.order import OrderStatus, ProductType, PaymentMethod


class CreateOrderRequest(BaseModel):
    product_type: ProductType
    payment_method: PaymentMethod


class OrderResponse(BaseModel):
    id: int
    order_no: str
    product_type: ProductType
    amount: float
    payment_method: PaymentMethod
    status: OrderStatus
    paid_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderCreateResponse(BaseModel):
    order_id: int
    order_no: str
    payment_url: str


class OrderListResponse(BaseModel):
    total: int
    items: list[OrderResponse]


class OrderStatusResponse(BaseModel):
    order_id: int
    status: OrderStatus
    payment_url: str | None = None
