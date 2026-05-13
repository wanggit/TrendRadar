from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """系统全局配置"""

    # App
    APP_NAME: str = "TrendRadar SaaS"
    APP_VERSION: str = "7.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database (支持 MySQL 和 SQLite)
    # MySQL: mysql+aiomysql://user:pass@host:3306/dbname
    # SQLite (dev): sqlite+aiosqlite:///./trendradar.db
    DATABASE_URL: str = "mysql+aiomysql://root:123456@127.0.0.1:3306/trendradar"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-this-to-a-secure-random-string-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Global Config (用户不可修改)
    AI_MODEL: str = "qwen3.6-plus"
    AI_API_KEY: str = ""
    AI_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    AI_TEMPERATURE: float = 1.0
    AI_MAX_TOKENS: int = 5000
    AI_TIMEOUT: int = 120

    # Rate Limiting
    RATE_LIMIT_LOGIN: int = 5  # 每分钟最大登录尝试
    RATE_LIMIT_API: int = 100  # 每分钟最大 API 调用

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Z-Pay (统一支付网关)
    ZPAY_UID: str = ""
    ZPAY_KEY: str = ""
    ZPAY_API_URL: str = "https://zpayz.cn"

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # Frontend URL (for email links)
    FRONTEND_URL: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
