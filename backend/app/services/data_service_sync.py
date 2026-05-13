from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.news import Platform, NewsItem
from app.models.rss import RSSFeed, RSSItem


class DataServiceSync:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    # ───────────────────────────────────────────────────────────
    # Platform Methods
    # ───────────────────────────────────────────────────────────
    def get_platforms(self) -> Sequence[Platform]:
        result = self.db.execute(
            select(Platform).where(
                Platform.user_id == self.user_id
            ).order_by(Platform.id)
        )
        return result.scalars().all()

    def get_platform_by_source(self, source_id: str) -> Platform | None:
        result = self.db.execute(
            select(Platform).where(
                Platform.user_id == self.user_id,
                Platform.source_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    def upsert_platform(self, source_id: str, name: str, enabled: bool = True) -> Platform:
        platform = self.get_platform_by_source(source_id)
        if platform:
            platform.name = name
            platform.enabled = enabled
        else:
            platform = Platform(
                user_id=self.user_id,
                source_id=source_id,
                name=name,
                enabled=enabled,
            )
            self.db.add(platform)
        self.db.flush()
        self.db.refresh(platform)
        return platform

    def delete_platform(self, source_id: str) -> bool:
        platform = self.get_platform_by_source(source_id)
        if platform:
            self.db.delete(platform)
            self.db.flush()
            return True
        return False

    # ───────────────────────────────────────────────────────────
    # NewsItem Methods
    # ───────────────────────────────────────────────────────────
    def get_news_items(
        self,
        limit: int = 50,
        offset: int = 0,
        platform_id: int | None = None,
        keyword: str | None = None,
    ) -> Sequence[NewsItem]:
        query = select(NewsItem).where(NewsItem.user_id == self.user_id)

        if platform_id:
            query = query.where(NewsItem.platform_id == platform_id)
        if keyword:
            query = query.where(NewsItem.title.ilike(f"%{keyword}%"))

        query = query.order_by(NewsItem.crawl_time.desc()).limit(limit).offset(offset)
        result = self.db.execute(query)
        return result.scalars().all()

    def count_news_items(
        self,
        platform_id: int | None = None,
        keyword: str | None = None,
    ) -> int:
        query = select(func.count(NewsItem.id)).where(NewsItem.user_id == self.user_id)
        if platform_id:
            query = query.where(NewsItem.platform_id == platform_id)
        if keyword:
            query = query.where(NewsItem.title.ilike(f"%{keyword}%"))
        result = self.db.execute(query)
        return result.scalar()

    def add_news_item(
        self,
        platform_id: int,
        title: str,
        url: str,
        rank: int | None = None,
        hot_value: float | None = None,
    ) -> NewsItem:
        item = NewsItem(
            user_id=self.user_id,
            platform_id=platform_id,
            title=title,
            url=url,
            rank=rank,
            hot_value=hot_value,
            crawl_time=datetime.now(timezone.utc),
        )
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    # ───────────────────────────────────────────────────────────
    # RSSFeed Methods
    # ───────────────────────────────────────────────────────────
    def get_rss_feeds(self) -> Sequence[RSSFeed]:
        result = self.db.execute(
            select(RSSFeed).where(
                RSSFeed.user_id == self.user_id
            ).order_by(RSSFeed.id)
        )
        return result.scalars().all()

    def get_rss_feed_by_url(self, feed_url: str) -> RSSFeed | None:
        result = self.db.execute(
            select(RSSFeed).where(
                RSSFeed.user_id == self.user_id,
                RSSFeed.feed_url == feed_url,
            )
        )
        return result.scalar_one_or_none()

    def add_rss_feed(self, feed_url: str, name: str | None = None, max_age_days: int = 1, feed_key: str | None = None) -> RSSFeed:
        existing = self.get_rss_feed_by_url(feed_url)
        if existing:
            existing.name = name or existing.name
            existing.feed_key = feed_key or existing.feed_key
            existing.max_age_days = max_age_days
            self.db.flush()
            self.db.refresh(existing)
            return existing

        feed = RSSFeed(
            user_id=self.user_id,
            feed_url=feed_url,
            name=name or feed_url,
            feed_key=feed_key,
            max_age_days=max_age_days,
        )
        self.db.add(feed)
        self.db.flush()
        self.db.refresh(feed)
        return feed

    def get_rss_feed_by_id(self, feed_id: int) -> RSSFeed | None:
        result = self.db.execute(
            select(RSSFeed).where(
                RSSFeed.user_id == self.user_id,
                RSSFeed.id == feed_id,
            )
        )
        return result.scalar_one_or_none()

    def update_rss_feed(self, feed_id: int, feed_url: str, name: str | None = None, max_age_days: int = 1, feed_key: str | None = None, enabled: bool | None = None) -> RSSFeed:
        feed = self.get_rss_feed_by_id(feed_id)
        if not feed:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="RSS feed not found")
        feed.feed_url = feed_url
        feed.name = name or feed_url
        feed.feed_key = feed_key
        feed.max_age_days = max_age_days
        if enabled is not None:
            feed.enabled = enabled
        self.db.flush()
        self.db.refresh(feed)
        return feed

    def delete_rss_feed(self, feed_id: int) -> bool:
        feed = self.get_rss_feed_by_id(feed_id)
        if feed:
            self.db.delete(feed)
            self.db.flush()
            return True
        return False

    # ───────────────────────────────────────────────────────────
    # RSSItem Methods
    # ───────────────────────────────────────────────────────────
    def get_rss_items(
        self,
        limit: int = 50,
        offset: int = 0,
        feed_id: int | None = None,
        keyword: str | None = None,
    ) -> Sequence[RSSItem]:
        query = select(RSSItem).where(RSSItem.user_id == self.user_id)

        if feed_id:
            query = query.where(RSSItem.feed_id == feed_id)
        if keyword:
            query = query.where(RSSItem.title.ilike(f"%{keyword}%"))

        query = query.order_by(RSSItem.published_at.desc()).limit(limit).offset(offset)
        result = self.db.execute(query)
        return result.scalars().all()

    def add_rss_item(
        self,
        feed_id: int,
        title: str,
        url: str,
        summary: str | None = None,
        author: str | None = None,
        published_at: datetime | None = None,
    ) -> RSSItem:
        item = RSSItem(
            user_id=self.user_id,
            feed_id=feed_id,
            title=title,
            url=url,
            summary=summary,
            author=author,
            published_at=published_at or datetime.now(timezone.utc),
            crawl_time=datetime.now(timezone.utc),
        )
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def count_rss_items(
        self,
        feed_id: int | None = None,
        keyword: str | None = None,
    ) -> int:
        query = select(func.count(RSSItem.id)).where(RSSItem.user_id == self.user_id)
        if feed_id:
            query = query.where(RSSItem.feed_id == feed_id)
        if keyword:
            query = query.where(RSSItem.title.ilike(f"%{keyword}%"))
        result = self.db.execute(query)
        return result.scalar()
