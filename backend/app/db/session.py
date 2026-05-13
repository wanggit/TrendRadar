from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import get_settings

settings = get_settings()

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Async engine (for FastAPI)
engine_kwargs = {
    "url": settings.DATABASE_URL,
    "echo": settings.DEBUG,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_pre_ping": True,
    })

engine = create_async_engine(**engine_kwargs)

session_kwargs = {
    "bind": engine,
    "class_": AsyncSession,
    "expire_on_commit": False,
}

async_session_factory = async_sessionmaker(**session_kwargs)


# Sync engine (for Celery tasks)
def get_sync_engine():
    """Get a synchronous SQLAlchemy engine for Celery tasks."""
    url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "").replace("+aiomysql", "+pymysql")
    sync_kwargs = {
        "url": url,
        "echo": settings.DEBUG,
    }
    if not url.startswith("sqlite"):
        sync_kwargs.update({
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_pre_ping": True,
        })
    if url.startswith("sqlite"):
        sync_kwargs["connect_args"] = {"timeout": 30}
    return create_engine(**sync_kwargs)


sync_session_factory = sessionmaker(
    bind=get_sync_engine(),
    class_=Session,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
