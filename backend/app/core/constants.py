from app.models.user import UserTier

TIER_LIMITS: dict[UserTier, dict] = {
    UserTier.FREE: {
        "max_platforms": 3,
        "max_keyword_groups": 5,
        "max_push_per_day": 4,
        "max_notification_channels": 1,
        "ai_enabled": False,
        "data_retention_days": 30,
        "celery_queue": "default",
    },
    UserTier.PRO: {
        "max_platforms": 15,
        "max_keyword_groups": -1,
        "max_push_per_day": 48,
        "max_notification_channels": 3,
        "ai_enabled": True,
        "data_retention_days": 30,
        "celery_queue": "priority",
    },
    UserTier.ENTERPRISE: {
        "max_platforms": -1,
        "max_keyword_groups": -1,
        "max_push_per_day": -1,
        "max_notification_channels": -1,
        "ai_enabled": True,
        "data_retention_days": 365,
        "celery_queue": "priority",
    },
}

PRODUCT_PRICES: dict[str, dict] = {
    "monthly": {"days": 30, "price": 49.00, "label": "月卡"},
    "quarterly": {"days": 90, "price": 129.00, "label": "季卡"},
    "yearly": {"days": 365, "price": 399.00, "label": "年卡"},
}

TRIAL_DAYS = 7
