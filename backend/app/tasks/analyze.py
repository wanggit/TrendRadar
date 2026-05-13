from app.celery_app import celery_app
from app.db.session import get_sync_engine
from app.services.task_log_sync import update_task_status, add_task_log_entry
from app.services.config_service_sync import ConfigServiceSync
from app.services.deep_analysis_service_sync import DeepAnalysisServiceSync
from app.models.ai_report import AIReport
from app.models.user import User, UserTier
from app.core.constants import TIER_LIMITS
from sqlalchemy.orm import Session
from sqlalchemy import select


@celery_app.task(bind=True, name="app.tasks.analyze.news", queue="analyze")
def analyze_news(self, user_id: int) -> dict:
    task_id = self.request.id

    update_task_status(task_id, "running", progress=0, current_step="开始分析")
    add_task_log_entry(task_id, "info", "开始 AI 深度分析任务")

    engine = get_sync_engine()
    with Session(engine) as db:
        user_result = db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            limits = TIER_LIMITS.get(user.tier, TIER_LIMITS[UserTier.FREE])
            if not limits.get("ai_enabled", False):
                msg = f"AI 分析功能未对 {user.tier.value} 用户开放"
                add_task_log_entry(task_id, "warning", msg)
                update_task_status(task_id, "success", progress=100, current_step="完成（AI 未开放）", result={
                    "status": "success", "skipped": True, "error": msg, "analyzed": 0,
                })
                return {"status": "success", "skipped": True, "error": msg, "analyzed": 0}

        config_service = ConfigServiceSync(db)

        config = config_service.get_or_create_user_config(user_id)

        ai_analysis_config = config.ai_analysis or {}
        filter_config = config.filter_strategy or config.filter or {}
        ai_filter_config = config.ai_filter or {}

        method = filter_config.get("method", "ai")
        max_news = ai_analysis_config.get("max_news_for_analysis", 150)

        add_task_log_entry(task_id, "info", f"加载配置，最大分析数量: {max_news}, 方法: {method}")
        update_task_status(task_id, "running", progress=10, current_step="加载数据")

        if method == "keyword":
            update_task_status(task_id, "running", progress=30, current_step="关键词分析中")
            add_task_log_entry(task_id, "info", "开始关键词匹配分析")
            from app.services.data_service_sync import DataServiceSync
            data_service = DataServiceSync(db, user_id)
            news_items = data_service.get_news_items(limit=max_news)
            result = _analyze_with_keywords(news_items, config.frequency_words)

            report = AIReport(
                user_id=user_id,
                task_id=task_id,
                method="keyword",
                success=True,
                tags=result.get("tags", {}),
                filtered_count=result.get("filtered", 0),
                analyzed_news=result.get("analyzed", 0),
            )
            db.add(report)
            db.flush()
            db.refresh(report)

            result["report_id"] = report.id

            update_task_status(task_id, "success", progress=100, current_step="关键词分析完成", result=result)
            return result

        update_task_status(task_id, "running", progress=30, current_step="AI 深度分析中")
        add_task_log_entry(task_id, "info", "开始 AI 深度智能分析")

        ai_config = config_service.get_system_ai_config()
        ai_config_dict = ai_config.model_dump() if hasattr(ai_config, 'model_dump') else ai_config

        prompt_content = ai_analysis_config.get("prompt_content", "")
        if not prompt_content:
            prompt_content = config_service.get_ai_prompt(user_id, "analysis")

        deep_service = DeepAnalysisServiceSync(db, user_id)
        result = deep_service.analyze(
            ai_config=ai_config_dict,
            ai_analysis_config=ai_analysis_config,
            prompt_content=prompt_content,
            max_news=max_news,
        )

        if result.skipped:
            add_task_log_entry(task_id, "warning", result.error)
            update_task_status(task_id, "success", progress=100, current_step="完成（无数据）", result={
                "status": "success", "skipped": True, "error": result.error, "analyzed": 0,
            })
            return {"status": "success", "skipped": True, "error": result.error, "analyzed": 0}

        report = AIReport(
            user_id=user_id,
            task_id=task_id,
            core_trends=result.core_trends,
            sentiment_controversy=result.sentiment_controversy,
            signals=result.signals,
            rss_insights=result.rss_insights,
            outlook_strategy=result.outlook_strategy,
            standalone_summaries=result.standalone_summaries,
            raw_response=result.raw_response,
            success=result.success,
            error=result.error if not result.success else None,
            method="ai",
            total_news=result.total_news,
            analyzed_news=result.analyzed_news,
            hotlist_count=result.hotlist_count,
            rss_count=result.rss_count,
        )
        db.add(report)
        db.flush()
        db.refresh(report)

        add_task_log_entry(task_id, "info", f"分析报告已保存 (ID: {report.id})")

        db.commit()

        task_result = {
            "status": "success" if result.success else "error",
            "report_id": report.id,
            "analyzed": result.analyzed_news,
            "total_news": result.total_news,
            "hotlist_count": result.hotlist_count,
            "rss_count": result.rss_count,
            "success": result.success,
            "error": result.error if not result.success else None,
            "method": "ai",
        }

        if result.success:
            update_task_status(task_id, "success", progress=100, current_step="AI 深度分析完成", result=task_result)
        else:
            update_task_status(task_id, "failure", progress=100, current_step="AI 分析失败", error_message=result.error, result=task_result)

        return task_result


def _analyze_with_keywords(news_items, frequency_words: str) -> dict:
    """Analyze news using keyword matching."""
    if not frequency_words:
        return {
            "status": "success",
            "analyzed": len(news_items),
            "tags": {},
            "filtered": 0,
            "method": "keyword",
        }

    keywords = [line.strip() for line in frequency_words.split('\n') if line.strip() and not line.startswith('#')]
    tags = {}
    matched_count = 0

    for item in news_items:
        for kw in keywords:
            if kw.lower() in item.title.lower():
                tags[kw] = tags.get(kw, 0) + 1
                matched_count += 1
                break

    return {
        "status": "success",
        "analyzed": len(news_items),
        "tags": dict(sorted(tags.items(), key=lambda x: -x[1])[:20]),
        "filtered": matched_count,
        "method": "keyword",
    }
