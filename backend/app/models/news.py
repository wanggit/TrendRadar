from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'weibo', 'zhihu'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="platforms")
    news_items = relationship("NewsItem", back_populates="platform")

    __table_args__ = (Index("idx_platform_user_source", "user_id", "source_id"),)


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    platform_id: Mapped[int] = mapped_column(Integer, ForeignKey("platforms.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    translated_title: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True, default="")
    rank: Mapped[int] = mapped_column(Integer, nullable=True)
    hot_value: Mapped[float] = mapped_column(Float, nullable=True)
    crawl_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="news_items")
    platform = relationship("Platform", back_populates="news_items")

    __table_args__ = (
        Index("idx_news_user_crawl", "user_id", "crawl_time"),
        Index("idx_news_user_platform", "user_id", "platform_id"),
        Index("idx_news_url", "url"),
    )
