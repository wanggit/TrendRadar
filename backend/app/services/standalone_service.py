from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsItem
from app.models.rss import RSSItem


class StandaloneService:
    """
    Manages the standalone display area configuration and data retrieval.
    The standalone area shows selected platforms/RSS feeds independently
    from the main keyword-filtered news.
    """

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def get_standalone_items(self, standalone_config: dict) -> dict:
        """
        Get items for the standalone display area.

        Args:
            standalone_config: {
                "platforms": ["zhihu", "weibo"],
                "rss_feeds": ["feed-1", "feed-2"],
                "max_items": 5
            }

        Returns:
            {
                "platforms": {source_id: [items]},
                "rss_feeds": {feed_id: [items]}
            }
        """
        max_items = standalone_config.get("max_items", 5)
        selected_platforms = standalone_config.get("platforms", [])
        selected_rss_feeds = standalone_config.get("rss_feeds", [])

        result = {
            "platforms": {},
            "rss_feeds": {},
        }

        for source_id in selected_platforms:
            items = await self._get_platform_items(source_id, limit=max_items)
            if items:
                result["platforms"][source_id] = items

        for feed_id in selected_rss_feeds:
            items = await self._get_rss_items(feed_id, limit=max_items)
            if items:
                result["rss_feeds"][feed_id] = items

        return result

    async def _get_platform_items(self, source_id: str, limit: int = 5) -> list[dict]:
        """Get recent news items for a specific platform source."""
        from sqlalchemy import select
        from app.models.news import Platform

        platform_result = await self.db.execute(
            select(Platform).where(
                Platform.user_id == self.user_id,
                Platform.source_id == source_id,
                Platform.enabled == True,
            )
        )
        platform = platform_result.scalar_one_or_none()
        if not platform:
            return []

        from sqlalchemy import select
        news_result = await self.db.execute(
            select(NewsItem)
            .where(
                NewsItem.user_id == self.user_id,
                NewsItem.platform_id == platform.id,
            )
            .order_by(NewsItem.crawl_time.desc())
            .limit(limit)
        )
        items = news_result.scalars().all()

        return [
            {
                "id": item.id,
                "title": item.translated_title or item.title,
                "url": item.url,
                "rank": item.rank,
                "hot_value": item.hot_value,
                "crawl_time": item.crawl_time.isoformat() if item.crawl_time else None,
            }
            for item in items
        ]

    async def _get_rss_items(self, feed_id: str, limit: int = 5) -> list[dict]:
        """Get recent RSS items for a specific feed. feed_id is a string feed_key."""
        from sqlalchemy import select
        from app.models.rss import RSSFeed

        feed_result = await self.db.execute(
            select(RSSFeed).where(
                RSSFeed.user_id == self.user_id,
                RSSFeed.feed_key == feed_id,
                RSSFeed.enabled == True,
            )
        )
        feed = feed_result.scalar_one_or_none()
        if not feed:
            return []

        from sqlalchemy import select
        rss_result = await self.db.execute(
            select(RSSItem)
            .where(
                RSSItem.user_id == self.user_id,
                RSSItem.feed_id == feed.id,
            )
            .order_by(RSSItem.published_at.desc())
            .limit(limit)
        )
        items = rss_result.scalars().all()

        return [
            {
                "id": item.id,
                "title": item.translated_title or item.title,
                "url": item.url,
                "summary": item.translated_summary or item.summary,
                "author": item.author,
                "published_at": item.published_at.isoformat() if item.published_at else None,
            }
            for item in items
        ]
