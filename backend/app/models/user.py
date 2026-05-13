import enum
from datetime import datetime, timezone, timedelta

from sqlalchemy import String, Boolean, DateTime, Enum, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(100), nullable=True)
    tier: Mapped[UserTier] = mapped_column(Enum(UserTier), default=UserTier.FREE, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    config = relationship("UserConfig", back_populates="user", uselist=False)
    ai_prompts = relationship("AIPrompt", back_populates="user")
    platforms = relationship("Platform", back_populates="user")
    news_items = relationship("NewsItem", back_populates="user")
    rss_feeds = relationship("RSSFeed", back_populates="user")
    rss_items = relationship("RSSItem", back_populates="user")
    task_logs = relationship("TaskLog", back_populates="user")
    ai_reports = relationship("AIReport", back_populates="user")
    orders = relationship("Order", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tier={self.tier.value})>"
