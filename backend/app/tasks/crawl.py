import time
import random
import json
import logging
from datetime import datetime, timezone

import requests

from app.celery_app import celery_app
from app.services.task_log_sync import update_task_status, add_task_log_entry
from app.db.session import get_sync_engine
from app.models.news import Platform, NewsItem
from app.models.rss import RSSFeed, RSSItem
from sqlalchemy.orm import Session
from sqlalchemy import select

logger = logging.getLogger(__name__)


NEWSNOW_API_URL = "https://newsnow.busiyi.world/api/s"

CONTENT_FETCH_LIMIT = 10  # Max items to fetch content per platform (reduced for speed)

# Platforms to skip entirely due to 0% content success rate
SKIP_PLATFORMS = ['zhihu', 'douyin', 'toutiao', 'producthunt']

# High-success platforms to prioritize (processed first)
PRIORITY_PLATFORMS = ['36kr', 'coolapk', 'github', 'tieba', 'sspai', 'v2ex']


def _fetch_and_save_content(session: Session, task_id: str, user_id: int, platform_id: int, url_title_pairs: list[tuple[str, str]], platform_name: str):
    """Fetch article content using Scrapling and save to DB."""
    from app.services.scrapling_fetcher import ScraplingFetcher

    fetched = 0
    skipped = 0
    failed = 0

    # Skip search-based platforms entirely (no content possible)
    search_platforms = ['微博热搜', '百度热搜', 'B站热搜']
    if platform_name in search_platforms:
        add_task_log_entry(task_id, "info", f"{platform_name} 跳过正文抓取（搜索链接平台）")
        return

    for url, title in url_title_pairs:
        # Skip search/redirect URLs
        if ScraplingFetcher.should_skip(url):
            skipped += 1
            continue

        try:
            result = ScraplingFetcher.fetch(url, use_dynamic=True)
            if result.success and result.content:
                news_item = session.execute(
                    select(NewsItem).where(
                        NewsItem.user_id == user_id,
                        NewsItem.platform_id == platform_id,
                        NewsItem.url == url,
                        (NewsItem.content == "") | (NewsItem.content.is_(None)),
                    )
                ).scalars().first()

                if news_item:
                    news_item.content = result.content
                    fetched += 1
                    logger.debug(f"Content fetched ({result.fetcher_type}): {title[:30]}...")
                else:
                    skipped += 1
            else:
                failed += 1
                logger.debug(f"Content failed for {title[:30]}: {result.error}")

            # Rate limit between requests
            time.sleep(0.2)

        except Exception as e:
            logger.debug(f"Failed to fetch content for {title}: {e}")
            failed += 1
            continue

    total = len(url_title_pairs)
    if fetched > 0 or failed > 0:
        msg = f"{platform_name} 正文: {fetched} 成功, {failed} 失败, {skipped} 跳过"
        add_task_log_entry(task_id, "info", msg)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://newsnow.busiyi.world/",
    "Origin": "https://newsnow.busiyi.world/",
}


def _get_enabled_platforms_from_db(user_id: int) -> list[dict]:
    """Read enabled platforms from the Platform table for a user."""
    engine = get_sync_engine()
    with Session(engine) as session:
        result = session.execute(
            select(Platform).where(
                Platform.user_id == user_id,
                Platform.enabled == True,
            ).order_by(Platform.id)
        )
        platforms = result.scalars().all()
        return [{"source_id": p.source_id, "name": p.name} for p in platforms]


def _fetch_platform_news(source_id: str, max_retries: int = 2) -> list[dict]:
    """
    Fetch real hot-list news from NewsNow API.

    Returns list of {"title": str, "url": str, "rank": int}.
    """
    url = f"{NEWSNOW_API_URL}?id={source_id}&latest"

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status")
            if status not in ("success", "cache"):
                raise ValueError(f"API status: {status}")

            items = data.get("items", [])
            results = []
            for idx, item in enumerate(items, 1):
                title = item.get("title", "").strip()
                if not title:
                    continue
                results.append({
                    "title": title,
                    "url": item.get("url", "") or item.get("mobileUrl", ""),
                    "rank": idx,
                })
            return results

        except Exception as e:
            if attempt < max_retries:
                wait = random.uniform(2, 4) + attempt
                time.sleep(wait)
            else:
                raise RuntimeError(f"Failed after {max_retries + 1} attempts: {e}")

    return []


@celery_app.task(bind=True, name="app.tasks.crawl.platforms", queue="crawl")
def crawl_platforms(self, user_id: int, platform_configs: list[dict]) -> dict:
    """
    Crawl hot-list platforms for a user using the NewsNow API.

    Args:
        user_id: User ID
        platform_configs: List of platform configs [{"source_id": "weibo", "name": "微博"}, ...]
            If empty, reads enabled platforms from the database.

    Returns:
        {"status": "success", "crawled": N, "errors": [...]}
    """
    task_id = self.request.id

    if not platform_configs:
        platform_configs = _get_enabled_platforms_from_db(user_id)

    # Filter out skipped platforms
    original_count = len(platform_configs)
    platform_configs = [p for p in platform_configs if p.get("source_id") not in SKIP_PLATFORMS]
    skipped_count = original_count - len(platform_configs)

    if skipped_count > 0:
        skipped_names = [p.get("name", p.get("source_id")) for p in platform_configs if p.get("source_id") in SKIP_PLATFORMS]
        add_task_log_entry(task_id, "info", f"跳过 {skipped_count} 个低成功率平台: {', '.join(skipped_names)}")

    # Sort: priority platforms first, then others
    def platform_priority(p):
        source_id = p.get("source_id", "")
        if source_id in PRIORITY_PLATFORMS:
            return 0  # High priority
        return 1  # Normal priority

    platform_configs.sort(key=platform_priority)

    total = len(platform_configs)
    result = {"status": "success", "crawled": 0, "errors": []}

    if total == 0:
        update_task_status(task_id, "success", progress=100, current_step="无启用的平台", result=result)
        add_task_log_entry(task_id, "warning", "没有启用的平台，跳过抓取")
        return result

    update_task_status(task_id, "running", progress=0, current_step="开始抓取")
    add_task_log_entry(task_id, "info", f"开始抓取 {total} 个平台")
    add_task_log_entry(task_id, "info", "Scrapling integration active - v2")

    for idx, platform_cfg in enumerate(platform_configs):
        source_id = platform_cfg.get("source_id")
        name = platform_cfg.get("name", source_id)
        progress = int((idx / total) * 100)

        update_task_status(task_id, "running", progress=progress, current_step=f"正在抓取: {name}")
        add_task_log_entry(task_id, "info", f"[{idx+1}/{total}] 开始抓取 {name}")

        try:
            real_news = _fetch_platform_news(source_id)

            if not real_news:
                add_task_log_entry(task_id, "warning", f"[{idx+1}/{total}] {name} 返回 0 条数据")
                continue

            engine = get_sync_engine()
            with Session(engine) as session:
                # Upsert platform
                platform = session.execute(
                    select(Platform).where(
                        Platform.user_id == user_id,
                        Platform.source_id == source_id,
                    )
                ).scalar_one_or_none()

                if platform:
                    platform.name = name
                    platform.enabled = True
                else:
                    platform = Platform(
                        user_id=user_id,
                        source_id=source_id,
                        name=name,
                        enabled=True,
                    )
                    session.add(platform)
                session.flush()

                # Add news items
                for news in real_news:
                    item = NewsItem(
                        user_id=user_id,
                        platform_id=platform.id,
                        title=news["title"],
                        url=news["url"],
                        rank=news["rank"],
                        crawl_time=datetime.now(timezone.utc),
                    )
                    session.add(item)

                session.commit()

                # Fetch content for top items (limit to avoid rate limits)
                content_urls = [(news["url"], news["title"]) for news in real_news[:20] if news.get("url")]
                add_task_log_entry(task_id, "info", f"[{idx+1}/{total}] {name} 准备抓取正文, URLs: {len(content_urls)}")
                if content_urls:
                    add_task_log_entry(task_id, "info", f"[{idx+1}/{total}] {name} 正在抓取正文 ({len(content_urls)} 条)...")
                    _fetch_and_save_content(session, task_id, user_id, platform.id, content_urls, name)
                    session.commit()
            result["crawled"] += len(real_news)

            add_task_log_entry(task_id, "success", f"[{idx+1}/{total}] {name} 抓取成功，获取 {len(real_news)} 条")
            time.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            result["errors"].append({"platform": source_id, "error": str(e)})
            add_task_log_entry(task_id, "error", f"[{idx+1}/{total}] {name} 抓取失败: {str(e)}")

    final_progress = 100
    update_task_status(
        task_id,
        "success",
        progress=final_progress,
        current_step="抓取完成",
        result=result,
    )
    add_task_log_entry(task_id, "info", f"抓取完成，共获取 {result['crawled']} 条，失败 {len(result['errors'])} 个")

    return result


@celery_app.task(bind=True, name="app.tasks.crawl.rss", queue="crawl")
def crawl_rss(self, user_id: int, rss_configs: list[dict]) -> dict:
    """
    Crawl RSS feeds for a user using the real RSSFetcher.

    Args:
        user_id: User ID
        rss_configs: List of RSS configs [{"feed_url": "...", "name": "...", "max_age_days": 1, "feed_key": "..."}, ...]

    Returns:
        {"status": "success", "crawled": N, "errors": [...]}
    """
    task_id = self.request.id
    total = len(rss_configs)
    result = {"status": "success", "crawled": 0, "errors": []}

    update_task_status(task_id, "running", progress=0, current_step="开始抓取 RSS")
    add_task_log_entry(task_id, "info", f"开始抓取 {total} 个 RSS 源")

    for idx, rss_cfg in enumerate(rss_configs):
        feed_url = rss_cfg.get("feed_url") or rss_cfg.get("url")
        name = rss_cfg.get("name", feed_url)
        max_age_days = rss_cfg.get("max_age_days", 1)
        feed_key = rss_cfg.get("feed_key")

        if not feed_url:
            add_task_log_entry(task_id, "warning", f"[{idx+1}/{total}] 跳过无效 RSS 配置（缺少 feed_url）: {name}")
            result["errors"].append({"feed": name, "error": "缺少 feed_url"})
            continue

        progress = int((idx / total) * 100)

        update_task_status(task_id, "running", progress=progress, current_step=f"正在抓取: {name}")
        add_task_log_entry(task_id, "info", f"[{idx+1}/{total}] 开始抓取 RSS: {name}")

        try:
            engine = get_sync_engine()
            with Session(engine) as session:
                # Check for existing feed by URL to avoid duplicates
                existing_feed = session.execute(
                    select(RSSFeed).where(
                        RSSFeed.user_id == user_id,
                        RSSFeed.feed_url == feed_url,
                    )
                ).scalar_one_or_none()

                if existing_feed:
                    feed = existing_feed
                    feed.name = name or feed.name
                    feed.feed_key = feed_key or feed.feed_key
                    feed.max_age_days = max_age_days
                else:
                    feed = RSSFeed(
                        user_id=user_id,
                        feed_url=feed_url,
                        name=name or feed_url,
                        feed_key=feed_key,
                        max_age_days=max_age_days,
                    )
                    session.add(feed)
                session.flush()

                # Fetch real RSS feed
                resp = requests.get(
                    feed_url,
                    headers={"User-Agent": "TrendRadar/2.0 RSS Reader"},
                    timeout=15,
                )
                resp.raise_for_status()

                # Parse XML/Atom feed
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)

                # Handle RSS 2.0
                items_elem = root.findall(".//item")
                # Handle Atom
                if not items_elem:
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    items_elem = root.findall(".//atom:entry", ns)

                crawled_count = 0
                for item_elem in items_elem[:50]:  # limit to 50 items per feed
                    # RSS 2.0
                    title_elem = item_elem.find("title")
                    link_elem = item_elem.find("link")
                    desc_elem = item_elem.find("description")
                    pub_elem = item_elem.find("pubDate")
                    author_elem = item_elem.find("author")

                    # Atom fallback
                    if title_elem is None:
                        ns = {"atom": "http://www.w3.org/2005/Atom"}
                        title_elem = item_elem.find("atom:title", ns)
                        link_elem = item_elem.find("atom:link[@rel='alternate']", ns)
                        if link_elem is None:
                            link_elem = item_elem.find("atom:link", ns)
                        desc_elem = item_elem.find("atom:summary", ns)
                        if desc_elem is None:
                            desc_elem = item_elem.find("atom:content", ns)
                        pub_elem = item_elem.find("atom:published", ns)
                        if pub_elem is None:
                            pub_elem = item_elem.find("atom:updated", ns)
                        author_elem = item_elem.find("atom:author/atom:name", ns)

                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    if not title:
                        continue

                    url = ""
                    if link_elem is not None:
                        url = link_elem.text or link_elem.get("href", "")

                    summary = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                    author = author_elem.text.strip() if author_elem is not None and author_elem.text else ""

                    published_at = None
                    if pub_elem is not None and pub_elem.text:
                        try:
                            from email.utils import parsedate_to_datetime
                            published_at = parsedate_to_datetime(pub_elem.text)
                        except Exception:
                            try:
                                published_at = datetime.fromisoformat(pub_elem.text.replace("Z", "+00:00"))
                            except Exception:
                                pass

                    existing = session.execute(
                        select(RSSItem.id).where(
                            RSSItem.user_id == user_id,
                            RSSItem.title == title,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        continue

                    rss_item = RSSItem(
                        user_id=user_id,
                        feed_id=feed.id,
                        title=title,
                        url=url,
                        summary=summary,
                        author=author,
                        published_at=published_at or datetime.now(timezone.utc),
                        crawl_time=datetime.now(timezone.utc),
                    )
                    session.add(rss_item)
                    crawled_count += 1

                session.commit()
            result["crawled"] += crawled_count

            add_task_log_entry(task_id, "success", f"[{idx+1}/{total}] {name} 抓取成功，获取 {crawled_count} 条")
            time.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            result["errors"].append({"feed": feed_url, "error": str(e)})
            add_task_log_entry(task_id, "error", f"[{idx+1}/{total}] {name} 抓取失败: {str(e)}")

    final_progress = 100
    update_task_status(
        task_id,
        "success",
        progress=final_progress,
        current_step="RSS 抓取完成",
        result=result,
    )
    add_task_log_entry(task_id, "info", f"RSS 抓取完成，共获取 {result['crawled']} 条，失败 {len(result['errors'])} 个")

    return result
