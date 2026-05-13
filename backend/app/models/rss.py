from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RSSFeed(Base):
    __tablename__ = "rss_feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    feed_url: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    feed_key: Mapped[str] = mapped_column(String(50), nullable=True)  # stable string ID for config references (e.g. "my-blog")
    enabled: Mapped[bool] = mapped_column(default=True)
    max_age_days: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="rss_feeds")
    items = relationship("RSSItem", back_populates="feed")

    __table_args__ = (Index("idx_rss_feed_user_url", "user_id", "feed_url"),)


class RSSItem(Base):
    __tablename__ = "rss_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    feed_id: Mapped[int] = mapped_column(Integer, ForeignKey("rss_feeds.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    translated_title: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    translated_summary: Mapped[str] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    crawl_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="rss_items")
    feed = relationship("RSSFeed", back_populates="items")

    __table_args__ = (
        Index("idx_rss_item_user_feed", "user_id", "feed_id"),
        Index("idx_rss_item_url", "url"),
    )
