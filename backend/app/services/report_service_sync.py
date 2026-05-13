from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.news import NewsItem
from app.models.rss import RSSItem


class ReportServiceSync:
    """
    Handles report mode logic: current, daily, incremental.
    Determines which news items to include in a push based on the report mode.
    """

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_items_for_report(
        self,
        report_mode: str = "current",
        limit: int = 50,
        last_push_time: datetime | None = None,
    ) -> dict:
        """
        Get news and RSS items for a push report.

        Args:
            report_mode: "current", "daily", or "incremental"
            limit: Maximum number of items per category
            last_push_time: Timestamp of last push (for incremental mode)

        Returns:
            {
                "news": [NewsItem dicts],
                "rss": [RSSItem dicts],
                "mode": report_mode,
                "generated_at": ISO timestamp
            }
        """
        news_items = []
        rss_items = []

        if report_mode == "current":
            news_items = self._get_latest_news(limit)
            rss_items = self._get_latest_rss(limit)

        elif report_mode == "daily":
            news_items = self._get_daily_news(limit)
            rss_items = self._get_daily_rss(limit)

        elif report_mode == "incremental":
            news_items = self._get_incremental_news(limit, last_push_time)
            rss_items = self._get_incremental_rss(limit, last_push_time)

        return {
            "news": news_items,
            "rss": rss_items,
            "mode": report_mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_latest_news(self, limit: int) -> list[dict]:
        """Get the most recent news items (current snapshot)."""
        from sqlalchemy import select

        result = self.db.execute(
            select(NewsItem)
            .where(NewsItem.user_id == self.user_id)
            .order_by(NewsItem.crawl_time.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [self._news_to_dict(item) for item in items]

    def _get_latest_rss(self, limit: int) -> list[dict]:
        """Get the most recent RSS items."""
        from sqlalchemy import select

        result = self.db.execute(
            select(RSSItem)
            .where(RSSItem.user_id == self.user_id)
            .order_by(RSSItem.published_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [self._rss_to_dict(item) for item in items]

    def _get_daily_news(self, limit: int) -> list[dict]:
        """Get news items from today."""
        from sqlalchemy import select
        from datetime import timedelta

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        result = self.db.execute(
            select(NewsItem)
            .where(
                NewsItem.user_id == self.user_id,
                NewsItem.crawl_time >= today_start,
            )
            .order_by(NewsItem.crawl_time.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [self._news_to_dict(item) for item in items]

    def _get_daily_rss(self, limit: int) -> list[dict]:
        """Get RSS items from today."""
        from sqlalchemy import select

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        result = self.db.execute(
            select(RSSItem)
            .where(
                RSSItem.user_id == self.user_id,
                RSSItem.published_at >= today_start,
            )
            .order_by(RSSItem.published_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [self._rss_to_dict(item) for item in items]

    def _get_incremental_news(self, limit: int, last_push_time: datetime | None) -> list[dict]:
        """Get news items since last push."""
        from sqlalchemy import select

        if not last_push_time:
            return self._get_latest_news(limit)

        result = self.db.execute(
            select(NewsItem)
            .where(
                NewsItem.user_id == self.user_id,
                NewsItem.crawl_time > last_push_time,
            )
            .order_by(NewsItem.crawl_time.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [self._news_to_dict(item) for item in items]

    def _get_incremental_rss(self, limit: int, last_push_time: datetime | None) -> list[dict]:
        """Get RSS items since last push."""
        from sqlalchemy import select

        if not last_push_time:
            return self._get_latest_rss(limit)

        result = self.db.execute(
            select(RSSItem)
            .where(
                RSSItem.user_id == self.user_id,
                RSSItem.published_at > last_push_time,
            )
            .order_by(RSSItem.published_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [self._rss_to_dict(item) for item in items]

    @staticmethod
    def _news_to_dict(item: NewsItem) -> dict:
        return {
            "id": item.id,
            "title": item.translated_title or item.title,
            "original_title": item.title,
            "url": item.url,
            "rank": item.rank,
            "hot_value": item.hot_value,
            "platform_id": item.platform_id,
            "crawl_time": item.crawl_time.isoformat() if item.crawl_time else None,
        }

    @staticmethod
    def _rss_to_dict(item: RSSItem) -> dict:
        return {
            "id": item.id,
            "title": item.translated_title or item.title,
            "original_title": item.title,
            "url": item.url,
            "summary": item.translated_summary or item.summary,
            "author": item.author,
            "feed_id": item.feed_id,
            "published_at": item.published_at.isoformat() if item.published_at else None,
        }
