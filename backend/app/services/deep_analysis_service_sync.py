"""
Deep Analysis Service - Full AI analysis replicating CLI AIAnalyzer logic.

Produces structured reports with 5 core sections:
- core_trends: Core hot trends and public opinion态势
- sentiment_controversy: Public opinion direction and controversies
- signals: Anomalies and weak signals
- rss_insights: RSS deep insights
- outlook_strategy: Forecast and strategic recommendations
- standalone_summaries: Per-source summaries
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.news import Platform, NewsItem
from app.models.rss import RSSFeed, RSSItem
from app.services.ai_service_sync import AIService

logger = logging.getLogger(__name__)


@dataclass
class DeepAnalysisResult:
    core_trends: str = ""
    sentiment_controversy: str = ""
    signals: str = ""
    rss_insights: str = ""
    outlook_strategy: str = ""
    standalone_summaries: dict = field(default_factory=dict)

    raw_response: str = ""
    success: bool = False
    skipped: bool = False
    error: str = ""

    total_news: int = 0
    analyzed_news: int = 0
    hotlist_count: int = 0
    rss_count: int = 0
    filtered_count: int = 0
    tags: dict = field(default_factory=dict)
    method: str = "ai"


class DeepAnalysisServiceSync:
    """Deep AI analysis service for backend SaaS mode (sync version for Celery)."""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def analyze(
        self,
        ai_config: dict,
        ai_analysis_config: dict,
        prompt_content: str,
        max_news: int = 150,
    ) -> DeepAnalysisResult:
        """
        Execute deep AI analysis.

        Args:
            ai_config: AI model config (model, api_key, api_base, etc.)
            ai_analysis_config: Analysis config (language, mode, include_rss, etc.)
            prompt_content: Prompt template with [system] and [user] sections
            max_news: Maximum news items to analyze

        Returns:
            DeepAnalysisResult with structured analysis
        """
        language = ai_analysis_config.get("language", "Chinese")
        include_rss = ai_analysis_config.get("include_rss", False)
        include_standalone = ai_analysis_config.get("include_standalone", True)
        include_rank_timeline = ai_analysis_config.get("include_rank_timeline", True)

        system_prompt, user_prompt_template = self._parse_prompt_content(prompt_content)

        hotlist_stats, hotlist_total = self._prepare_hotlist_stats(max_news, include_rank_timeline)
        rss_stats, rss_total = self._prepare_rss_stats(max_news - hotlist_total) if include_rss else ([], 0)

        total_news = hotlist_total + rss_total
        if not hotlist_stats and not rss_stats:
            return DeepAnalysisResult(
                success=False,
                skipped=True,
                error="没有可分析的热点新闻数据，请先执行抓取任务",
                total_news=0,
            )

        news_content = self._build_news_content(hotlist_stats)
        rss_content = self._build_rss_content(rss_stats)

        platforms = [s["platform"] for s in hotlist_stats]
        keywords = self._extract_keywords(hotlist_stats)

        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace("{report_mode}", ai_analysis_config.get("mode", "follow_report"))
        user_prompt = user_prompt.replace("{report_type}", "AI 深度分析")
        user_prompt = user_prompt.replace("{current_time}", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        user_prompt = user_prompt.replace("{news_count}", str(hotlist_total))
        user_prompt = user_prompt.replace("{rss_count}", str(rss_total))
        user_prompt = user_prompt.replace("{platforms}", ", ".join(platforms) if platforms else "多平台")
        user_prompt = user_prompt.replace("{keywords}", ", ".join(keywords[:20]) if keywords else "无")
        user_prompt = user_prompt.replace("{news_content}", news_content)
        user_prompt = user_prompt.replace("{rss_content}", rss_content)
        user_prompt = user_prompt.replace("{language}", language)

        standalone_content = ""
        if include_standalone:
            standalone_content = self._prepare_standalone(max_news)
        user_prompt = user_prompt.replace("{standalone_content}", standalone_content)

        ai_service = AIService(
            model=ai_config.get("model"),
            api_key=ai_config.get("api_key"),
            api_base=ai_config.get("api_base"),
            temperature=ai_config.get("temperature"),
            max_tokens=ai_config.get("max_tokens", 8000),
            timeout=ai_config.get("timeout", 180),
        )

        if not ai_service.is_configured():
            return DeepAnalysisResult(
                success=False,
                error="AI API Key 未配置，请在系统设置中配置有效的 AI API Key",
            )

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            response = ai_service.chat(messages, max_tokens=8000)
            result = self._parse_response(response)

            if not result.success and result.error and "JSON" in result.error:
                retry_result = self._retry_fix_json(ai_service, response, result.error)
                if retry_result and retry_result.success:
                    result = retry_result

            result.total_news = total_news
            result.hotlist_count = hotlist_total
            result.rss_count = rss_total
            result.analyzed_news = hotlist_total + rss_total

            if not include_rss:
                result.rss_insights = "未开启RSS分析"

            return result

        except Exception as e:
            logger.error(f"Deep AI analysis failed: {e}", exc_info=True)
            return DeepAnalysisResult(
                success=False,
                error=f"AI 分析失败: {type(e).__name__}: {str(e)[:200]}",
                total_news=total_news,
                hotlist_count=hotlist_total,
                rss_count=rss_total,
            )

    def _parse_prompt_content(self, content: str) -> tuple[str, str]:
        system_prompt = ""
        user_prompt = ""

        if "[system]" in content and "[user]" in content:
            parts = content.split("[user]")
            system_part = parts[0]
            user_part = parts[1] if len(parts) > 1 else ""

            if "[system]" in system_part:
                system_prompt = system_part.split("[system]")[1].strip()

            user_prompt = user_part.strip()
        else:
            user_prompt = content.strip()

        return system_prompt, user_prompt

    def _prepare_hotlist_stats(self, max_news: int, include_rank_timeline: bool) -> tuple[list[dict], int]:
        """
        Fetch news items grouped by platform, building stats similar to CLI.
        """
        result = self.db.execute(
            select(Platform)
            .where(Platform.user_id == self.user_id, Platform.enabled == True)
            .order_by(Platform.id)
        )
        platforms = result.scalars().all()

        if not platforms:
            return [], 0

        stats = []
        total_count = 0

        for platform in platforms:
            news_result = self.db.execute(
                select(NewsItem)
                .where(NewsItem.user_id == self.user_id, NewsItem.platform_id == platform.id)
                .order_by(NewsItem.crawl_time.desc())
                .limit(max_news)
            )
            items = news_result.scalars().all()

            if not items:
                continue

            titles = []
            for item in items:
                if total_count >= max_news:
                    break

                title_data = {
                    "title": item.title,
                    "source": platform.source_id,
                    "source_name": platform.name,
                    "rank": item.rank,
                    "ranks": [item.rank] if item.rank else [],
                    "first_time": item.crawl_time.strftime("%H:%M") if item.crawl_time else "",
                    "last_time": item.crawl_time.strftime("%H:%M") if item.crawl_time else "",
                    "count": 1,
                    "content": getattr(item, 'content', '') or '',
                }

                if include_rank_timeline and item.rank:
                    title_data["rank_timeline"] = [
                        {"time": item.crawl_time.strftime("%H:%M"), "rank": item.rank}
                    ] if item.crawl_time else []

                titles.append(title_data)
                total_count += 1

            if titles:
                stats.append({
                    "platform": platform.name,
                    "source_id": platform.source_id,
                    "word": platform.name,
                    "titles": titles,
                })

        return stats, total_count

    def _prepare_rss_stats(self, remaining: int) -> tuple[list[dict], int]:
        """Fetch RSS items grouped by feed."""
        if remaining <= 0:
            return [], 0

        result = self.db.execute(
            select(RSSFeed)
            .where(RSSFeed.user_id == self.user_id, RSSFeed.enabled == True)
            .order_by(RSSFeed.id)
        )
        feeds = result.scalars().all()

        if not feeds:
            return [], 0

        stats = []
        total_count = 0

        for feed in feeds:
            if total_count >= remaining:
                break

            items_result = self.db.execute(
                select(RSSItem)
                .where(RSSItem.user_id == self.user_id, RSSItem.feed_id == feed.id)
                .order_by(RSSItem.published_at.desc())
                .limit(remaining - total_count)
            )
            items = items_result.scalars().all()

            if not items:
                continue

            titles = []
            for item in items:
                if total_count >= remaining:
                    break

                time_display = ""
                if item.published_at:
                    time_display = item.published_at.strftime("%Y-%m-%d %H:%M")

                titles.append({
                    "title": item.title,
                    "source_name": feed.name,
                    "feed_name": feed.name,
                    "time_display": time_display,
                    "content": item.summary or "",
                })
                total_count += 1

            if titles:
                stats.append({
                    "feed": feed.name,
                    "word": feed.name,
                    "titles": titles,
                })

        return stats, total_count

    def _build_news_content(self, stats: list[dict]) -> str:
        """Build news content text for prompt."""
        lines = []
        for stat in stats:
            word = stat.get("word", "")
            titles = stat.get("titles", [])
            if word and titles:
                lines.append(f"\n**{word}** ({len(titles)}条)")
                for t in titles:
                    title = t.get("title", "")
                    if not title:
                        continue

                    source = t.get("source_name", t.get("source", ""))
                    if source:
                        line = f"- [{source}] {title}"
                    else:
                        line = f"- {title}"

                    ranks = t.get("ranks", [])
                    if ranks:
                        min_rank = min(ranks)
                        max_rank = max(ranks)
                        rank_str = f"{min_rank}" if min_rank == max_rank else f"{min_rank}-{max_rank}"
                    else:
                        rank_str = "-"

                    first_time = t.get("first_time", "")
                    last_time = t.get("last_time", "")
                    time_str = self._format_time_range(first_time, last_time)

                    appear_count = t.get("count", 1)

                    line += f" | 排名:{rank_str} | 时间:{time_str} | 出现:{appear_count}次"

                    rank_timeline = t.get("rank_timeline", [])
                    if rank_timeline:
                        timeline_str = self._format_rank_timeline(rank_timeline)
                        line += f" | 轨迹:{timeline_str}"

                    # Include content/summary if available
                    content = t.get("content", "") or t.get("summary", "")
                    if content and len(content) > 20:
                        # Truncate to avoid prompt overflow
                        if len(content) > 300:
                            content = content[:300] + "..."
                        line += f"\n  内容摘要: {content}"

                    lines.append(line)

        return "\n".join(lines)

    def _build_rss_content(self, stats: list[dict]) -> str:
        """Build RSS content text for prompt."""
        lines = []
        for stat in stats:
            word = stat.get("word", "")
            titles = stat.get("titles", [])
            if word and titles:
                lines.append(f"\n**{word}** ({len(titles)}条)")
                for t in titles:
                    title = t.get("title", "")
                    if not title:
                        continue

                    source = t.get("source_name", t.get("feed_name", ""))
                    if source:
                        line = f"- [{source}] {title}"
                    else:
                        line = f"- {title}"

                    time_display = t.get("time_display", "")
                    if time_display:
                        line += f" | {time_display}"

                    # Include RSS summary if available
                    content = t.get("content", "")
                    if content and len(content) > 20:
                        if len(content) > 300:
                            content = content[:300] + "..."
                        line += f"\n  摘要: {content}"

                    lines.append(line)

        return "\n".join(lines)

    def _prepare_standalone(self, max_items: int) -> str:
        """Prepare standalone section content from platforms and RSS feeds."""
        lines = []

        result = self.db.execute(
            select(Platform)
            .where(Platform.user_id == self.user_id, Platform.enabled == True)
            .order_by(Platform.id)
        )
        platforms = result.scalars().all()

        for platform in platforms[:3]:
            news_result = self.db.execute(
                select(NewsItem)
                .where(NewsItem.user_id == self.user_id, NewsItem.platform_id == platform.id)
                .order_by(NewsItem.crawl_time.desc())
                .limit(max_items)
            )
            items = news_result.scalars().all()

            if not items:
                continue

            lines.append(f"### [{platform.name}]")
            for item in items[:max_items]:
                line = f"- {item.title}"
                if item.rank:
                    line += f" | 排名:{item.rank}"
                if item.crawl_time:
                    line += f" | 时间:{item.crawl_time.strftime('%H:%M')}"
                lines.append(line)
            lines.append("")

        return "\n".join(lines)

    def _format_time_range(self, first_time: str, last_time: str) -> str:
        if first_time == last_time or not last_time:
            return first_time
        return f"{first_time}~{last_time}"

    def _format_rank_timeline(self, rank_timeline: list[dict]) -> str:
        if not rank_timeline:
            return "-"

        parts = []
        for item in rank_timeline:
            time_str = item.get("time", "")
            rank = item.get("rank")
            if rank is None:
                parts.append(f"0({time_str})")
            else:
                parts.append(f"{rank}({time_str})")

        return "→".join(parts)

    def _extract_keywords(self, stats: list[dict]) -> list[str]:
        """Extract top keywords/titles from stats."""
        keywords = []
        for stat in stats:
            titles = stat.get("titles", [])
            for t in titles[:3]:
                title = t.get("title", "")
                if title:
                    keywords.append(title)
        return keywords[:20]

    def _parse_response(self, response: str) -> DeepAnalysisResult:
        """Parse AI response JSON."""
        result = DeepAnalysisResult(raw_response=response)

        if not response or not response.strip():
            result.error = "AI 返回空响应"
            return result

        json_str = response

        if "```json" in response:
            parts = response.split("```json", 1)
            if len(parts) > 1:
                code_block = parts[1]
                end_idx = code_block.find("```")
                if end_idx != -1:
                    json_str = code_block[:end_idx]
                else:
                    json_str = code_block
        elif "```" in response:
            parts = response.split("```", 2)
            if len(parts) >= 2:
                json_str = parts[1]

        json_str = json_str.strip()
        if not json_str:
            result.error = "提取的 JSON 内容为空"
            result.core_trends = response[:500] + "..." if len(response) > 500 else response
            result.success = True
            return result

        data = None
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            try:
                from json_repair import repair_json
                repaired = repair_json(json_str, return_objects=True)
                if isinstance(repaired, dict):
                    data = repaired
                    logger.info("JSON repair successful (json_repair)")
            except Exception:
                pass

        if data is None:
            result.error = "JSON 解析失败，AI 返回格式不正确"
            result.core_trends = json_str[:500] + "..." if len(json_str) > 500 else json_str
            result.success = True
            return result

        try:
            result.core_trends = data.get("core_trends", "")
            result.sentiment_controversy = data.get("sentiment_controversy", "")
            result.signals = data.get("signals", "")
            result.rss_insights = data.get("rss_insights", "")
            result.outlook_strategy = data.get("outlook_strategy", "")

            summaries = data.get("standalone_summaries", {})
            if isinstance(summaries, dict):
                result.standalone_summaries = {str(k): str(v) for k, v in summaries.items()}

            result.success = True
        except (KeyError, TypeError, AttributeError) as e:
            result.error = f"字段提取错误: {type(e).__name__}: {e}"
            result.core_trends = json_str[:500] + "..." if len(json_str) > 500 else json_str
            result.success = True

        return result

    def _retry_fix_json(self, ai_service: AIService, original_response: str, error_msg: str) -> DeepAnalysisResult | None:
        """Retry JSON fix."""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个 JSON 修复助手。用户会提供一段格式有误的 JSON 和错误信息，"
                    "你需要修复 JSON 格式错误并返回正确的 JSON。"
                    "只返回纯 JSON，不要包含 markdown 代码块标记或任何说明文字。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"以下 JSON 解析失败：\n\n"
                    f"错误：{error_msg}\n\n"
                    f"原始内容：\n{original_response}\n\n"
                    f"请修复以上 JSON 中的格式问题，保持原始内容语义不变，只修复格式。"
                    f"直接返回修复后的纯 JSON。"
                ),
            },
        ]

        try:
            response = ai_service.chat(messages, max_tokens=8000)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"JSON fix retry failed: {e}")
            return None
