from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserTier, UserStatus
from app.core.security import get_password_hash
from app.schemas.user import UserCreate, UserUpdate, UserAdminCreate, UserAdminUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user_in: UserCreate) -> User:
        user = User(
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            nickname=user_in.nickname,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, user_update: UserUpdate) -> User:
        if user_update.nickname is not None:
            user.nickname = user_update.nickname
        if user_update.password is not None:
            user.password_hash = get_password_hash(user_update.password)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def create_superuser(self, email: str, password: str, nickname: str = "Admin") -> User:
        existing = await self.get_by_email(email)
        if existing:
            return existing
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            nickname=nickname,
            is_superuser=True,
            tier=UserTier.ENTERPRISE,
            status=UserStatus.ACTIVE,
            email_verified=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def admin_create(self, user_in: UserAdminCreate) -> User:
        user = User(
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            nickname=user_in.nickname,
            tier=user_in.tier,
            status=user_in.status,
            is_superuser=user_in.is_superuser,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def admin_update(self, user: User, user_update: UserAdminUpdate) -> User:
        if user_update.nickname is not None:
            user.nickname = user_update.nickname
        if user_update.tier is not None:
            user.tier = user_update.tier
        if user_update.status is not None:
            user.status = user_update.status
        if user_update.is_superuser is not None:
            user.is_superuser = user_update.is_superuser
        if user_update.email_verified is not None:
            user.email_verified = user_update.email_verified
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()

    async def reset_password(self, user: User, new_password: str) -> User:
        user.password_hash = get_password_hash(new_password)
        await self.db.flush()
        await self.db.refresh(user)
        return user
