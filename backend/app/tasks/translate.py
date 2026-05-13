from app.celery_app import celery_app
from app.db.session import get_sync_engine
from app.services.config_service import ConfigService
from app.services.ai_service_sync import AIService
from app.services.data_service_sync import DataServiceSync
from sqlalchemy.orm import Session


@celery_app.task(bind=True, name="app.tasks.translate.content", queue="translate")
def translate_content(self, user_id: int) -> dict:
    """
    Translate news/RSS content using AI for a user.

    Args:
        user_id: User ID

    Returns:
        {"status": "success", "translated": N, "errors": [...]}
    """
    engine = get_sync_engine()
    with Session(engine) as db:
        data_service = DataServiceSync(db, user_id)
        config_service = ConfigService(db)

        config = config_service.get_or_create_user_config(user_id)
        translation_config = config.ai_translation

        if not translation_config.get("enabled", False):
            return {"status": "skipped", "reason": "translation disabled"}

        target_language = translation_config.get("language", "中文")
        scope = translation_config.get("scope", {"hotlist": True, "rss": True, "standalone": True})

        ai_service = AIService()
        if not ai_service.is_configured():
            return {"status": "skipped", "reason": "AI API Key not configured"}

        translated_count = 0
        errors = []

        if scope.get("hotlist", True):
            news_items = data_service.get_news_items(limit=200)
            for item in news_items:
                if item.translated_title:
                    continue
                try:
                    translated_title = ai_service.translate(item.title, target_language)
                    item.translated_title = translated_title
                    translated_count += 1
                except Exception as e:
                    errors.append({"item": item.title, "error": str(e)})

        if scope.get("rss", True):
            rss_items = data_service.get_rss_items(limit=200)
            for item in rss_items:
                if item.translated_title:
                    continue
                try:
                    translated_title = ai_service.translate(item.title, target_language)
                    item.translated_title = translated_title
                    if item.summary:
                        item.translated_summary = ai_service.translate(item.summary, target_language)
                    translated_count += 1
                except Exception as e:
                    errors.append({"item": item.title, "error": str(e)})

        db.commit()

        return {
            "status": "success",
            "translated": translated_count,
            "errors": errors[:10],
        }
