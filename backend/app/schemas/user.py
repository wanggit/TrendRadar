from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserTier, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    nickname: str | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    nickname: str | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class UserResponse(UserBase):
    id: int
    tier: UserTier
    status: UserStatus
    is_superuser: bool
    email_verified: bool
    trial_start_at: datetime | None = None
    trial_end_at: datetime | None = None
    trial_used: bool = False
    expire_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    items: list[UserResponse]


class UserAdminCreate(BaseModel):
    email: EmailStr
    nickname: str | None = None
    password: str = Field(..., min_length=8, max_length=128)
    tier: UserTier = UserTier.FREE
    status: UserStatus = UserStatus.ACTIVE
    is_superuser: bool = False


class UserAdminUpdate(BaseModel):
    nickname: str | None = None
    tier: UserTier | None = None
    status: UserStatus | None = None
    is_superuser: bool | None = None
    email_verified: bool | None = None


class PasswordResetResponse(BaseModel):
    message: str
