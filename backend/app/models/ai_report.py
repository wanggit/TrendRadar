from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Text, Index, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # 5 core analysis sections
    core_trends: Mapped[str] = mapped_column(Text, default="")
    sentiment_controversy: Mapped[str] = mapped_column(Text, default="")
    signals: Mapped[str] = mapped_column(Text, default="")
    rss_insights: Mapped[str] = mapped_column(Text, default="")
    outlook_strategy: Mapped[str] = mapped_column(Text, default="")
    standalone_summaries: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    # Metadata
    raw_response: Mapped[str] = mapped_column(Text, default="")
    success: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str] = mapped_column(Text, nullable=True, default="")
    method: Mapped[str] = mapped_column(String(20), default="ai")  # "ai" or "keyword"

    # Stats
    total_news: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_news: Mapped[int] = mapped_column(Integer, default=0)
    hotlist_count: Mapped[int] = mapped_column(Integer, default=0)
    rss_count: Mapped[int] = mapped_column(Integer, default=0)
    filtered_count: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="ai_reports")

    __table_args__ = (
        Index("idx_ai_report_user", "user_id"),
        Index("idx_ai_report_created", "created_at"),
        Index("idx_ai_report_task", "task_id"),
    )
