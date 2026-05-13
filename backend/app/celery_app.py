from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "trendradar",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_routes={
        "app.tasks.crawl.*": {"queue": "crawl"},
        "app.tasks.analyze.*": {"queue": "analyze"},
        "app.tasks.push.*": {"queue": "push"},
        "app.tasks.translate.*": {"queue": "translate"},
    },
    task_queues={
        "crawl": {"exchange": "crawl", "routing_key": "crawl"},
        "analyze": {"exchange": "analyze", "routing_key": "analyze"},
        "push": {"exchange": "push", "routing_key": "push"},
        "translate": {"exchange": "translate", "routing_key": "translate"},
        "priority": {"exchange": "priority", "routing_key": "priority"},
        "default": {"exchange": "default", "routing_key": "default"},
    },
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_max_loop_interval=60,
    beat_schedule={
        "check-trial-expiry": {
            "task": "app.tasks.trial_reminder.check_and_expire_trials",
            "schedule": crontab(hour=0, minute=0),
        },
        "send-trial-reminder": {
            "task": "app.tasks.trial_reminder.send_trial_reminders",
            "schedule": crontab(hour=9, minute=0),
        },
        "cleanup-expired-data": {
            "task": "app.tasks.data_cleanup.cleanup_expired_data",
            "schedule": crontab(hour=2, minute=0),
        },
        "check-subscription-expiry": {
            "task": "app.tasks.subscription_check.check_and_expire_subscriptions",
            "schedule": crontab(hour=0, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
