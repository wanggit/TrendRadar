from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.data_service import DataService
from app.schemas.data import (
    PlatformResponse,
    NewsItemResponse,
    NewsListResponse,
    RSSFeedResponse,
    RSSItemResponse,
    RSSListResponse,
    PlatformCreateRequest,
    RSSFeedCreateRequest,
)

router = APIRouter(prefix="/data", tags=["data"])


class BulkDeleteRequest(BaseModel):
    ids: list[int]


@router.get("/platforms", response_model=list[PlatformResponse])
async def list_platforms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    return await service.get_platforms()


@router.post("/platforms", response_model=PlatformResponse)
async def create_platform(
    data: PlatformCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    return await service.upsert_platform(data.source_id, data.name, data.enabled)


@router.delete("/platforms/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    deleted = await service.delete_platform(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Platform not found")


@router.get("/news", response_model=NewsListResponse)
async def list_news(
    limit: int = Query(50, le=200),
    offset: int = 0,
    platform_id: int | None = None,
    keyword: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    items = await service.get_news_items(limit=limit, offset=offset, platform_id=platform_id, keyword=keyword)
    total = await service.count_news_items(platform_id=platform_id, keyword=keyword)
    return NewsListResponse(total=total, items=[NewsItemResponse.model_validate(i) for i in items])


@router.delete("/news/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    deleted = await service.delete_news_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="News item not found")


@router.post("/news/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_news(
    data: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    count = await service.bulk_delete_news_items(data.ids)
    return {"deleted": count}


@router.get("/rss/feeds", response_model=list[RSSFeedResponse])
async def list_rss_feeds(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    return await service.get_rss_feeds()


@router.post("/rss/feeds", response_model=RSSFeedResponse)
async def create_rss_feed(
    data: RSSFeedCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    return await service.add_rss_feed(data.feed_url, data.name, data.max_age_days, data.feed_key)


@router.put("/rss/feeds/{feed_id}", response_model=RSSFeedResponse)
async def update_rss_feed(
    feed_id: int,
    data: RSSFeedCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    return await service.update_rss_feed(feed_id, data.feed_url, data.name, data.max_age_days, data.feed_key, data.enabled)


@router.delete("/rss/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rss_feed(
    feed_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    deleted = await service.delete_rss_feed(feed_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="RSS feed not found")


@router.get("/rss/items", response_model=RSSListResponse)
async def list_rss_items(
    limit: int = Query(50, le=200),
    offset: int = 0,
    feed_id: int | None = None,
    keyword: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    items = await service.get_rss_items(limit=limit, offset=offset, feed_id=feed_id, keyword=keyword)
    total = await service.count_rss_items(feed_id=feed_id, keyword=keyword)
    return RSSListResponse(total=total, items=[RSSItemResponse.model_validate(i) for i in items])


@router.delete("/rss/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rss_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    deleted = await service.delete_rss_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="RSS item not found")


@router.post("/rss/items/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_rss_items(
    data: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DataService(db, current_user.id)
    count = await service.bulk_delete_rss_items(data.ids)
    return {"deleted": count}
