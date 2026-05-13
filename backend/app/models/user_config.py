from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, relationship

from app.db.base import Base


class UserConfig(Base):
    __tablename__ = "user_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # 基础设置
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")

    # 热榜平台配置 (JSON)
    # NOTE: This JSON column is DEPRECATED. The Platform table is the sole source of truth.
    # Kept for backward compatibility with config export/import. Crawl tasks read from Platform table.
    platforms: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"enabled": True, "sources": []},
    )

    # RSS 配置 (JSON)
    # NOTE: Feed definitions are stored in the rss_feeds table. This JSON column only holds
    # global settings (enabled, freshness_filter). Crawl tasks read from rss_feeds table.
    rss: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "enabled": True,
            "feeds": [],
            "freshness_filter": {"enabled": True, "max_age_days": 1},
        },
    )

    # 报告模式配置 (JSON)
    report: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "mode": "current",
            "display_mode": "keyword",
            "sort_by_position_first": False,
            "rank_threshold": 5,
            "max_news_per_keyword": 0,
        },
    )

    # 筛选策略 (JSON)
    filter_strategy: Mapped[dict] = mapped_column(
        "filter",
        JSON,
        default=lambda: {"method": "ai", "priority_sort_enabled": True},
    )

    # AI 筛选配置 (JSON)
    ai_filter: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "batch_size": 200,
            "batch_interval": 2,
            "min_score": 0.7,
            "reclassify_threshold": 0.6,
        },
    )

    # 推送区域配置 (JSON)
    display: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "region_order": ["new_items", "hotlist", "rss", "standalone", "ai_analysis"],
            "regions": {
                "hotlist": True,
                "new_items": False,
                "rss": True,
                "standalone": False,
                "ai_analysis": True,
            },
            "standalone": {
                "platforms": ["zhihu", "wallstreetcn-hot"],
                "rss_feeds": [],
                "max_items": 20,
            },
        },
    )

    # 通知渠道配置 (JSON)
    notification: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "enabled": True,
            "channels": {
                "feishu": {"webhook_url": ""},
                "dingtalk": {"webhook_url": ""},
                "wework": {"webhook_url": "", "msg_type": "markdown"},
                "telegram": {"bot_token": "", "chat_id": ""},
                "email": {"from": "", "password": "", "to": "", "smtp_server": "", "smtp_port": ""},
                "ntfy": {"server_url": "https://ntfy.sh", "topic": "", "token": ""},
                "bark": {"url": ""},
                "slack": {"webhook_url": ""},
                "generic_webhook": {"webhook_url": "", "payload_template": ""},
            },
        },
    )

    # 调度配置 (JSON)
    schedule: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"enabled": True, "preset": "morning_evening"},
    )

    # 时间线配置 (JSON)
    timeline: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"presets": {}, "custom": {}},
    )

    # 关键词配置 (TEXT)
    frequency_words: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    # AI 分析配置 (JSON)
    ai_analysis: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "enabled": True,
            "language": "Chinese",
            "mode": "follow_report",
            "max_news_for_analysis": 150,
            "include_rss": False,
            "include_standalone": True,
            "include_rank_timeline": True,
        },
    )

    # AI 翻译配置 (JSON)
    ai_translation: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "enabled": True,
            "language": "中文",
            "scope": {"hotlist": False, "rss": True, "standalone": True},
        },
    )

    # 存储配置 (JSON)
    storage: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "backend": "local",
            "formats": {"sqlite": True, "txt": False, "html": True},
            "local": {"data_dir": "output", "retention_days": 0},
        },
    )

    # 高级配置 (JSON)
    advanced: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "debug": False,
            "crawler": {"request_interval": 2000, "use_proxy": False, "default_proxy": "http://127.0.0.1:10801"},
            "weight": {"rank": 0.6, "frequency": 0.3, "hotness": 0.1},
        },
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="config")
