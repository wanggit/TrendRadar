from datetime import datetime
from pydantic import BaseModel, Field


class PlatformResponse(BaseModel):
    id: int
    source_id: str
    name: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformCreateRequest(BaseModel):
    source_id: str
    name: str
    enabled: bool = True


class NewsItemResponse(BaseModel):
    id: int
    platform_id: int
    title: str
    url: str
    rank: int | None = None
    hot_value: float | None = None
    crawl_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    total: int
    items: list[NewsItemResponse]


class RSSFeedResponse(BaseModel):
    id: int
    feed_url: str
    name: str | None = None
    feed_key: str | None = None
    enabled: bool
    max_age_days: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RSSFeedCreateRequest(BaseModel):
    feed_url: str
    name: str | None = None
    feed_key: str | None = None
    max_age_days: int = 1
    enabled: bool = True


class RSSItemResponse(BaseModel):
    id: int
    feed_id: int
    title: str
    url: str
    summary: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    crawl_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class RSSListResponse(BaseModel):
    total: int = 0
    items: list[RSSItemResponse]
