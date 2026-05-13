from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import auth, users, config, data, tasks, payment, audit
from app.db.init_db import init_db

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup():
        await init_db()

    app.include_router(auth.router, prefix=settings.API_PREFIX)
    app.include_router(users.router, prefix=settings.API_PREFIX)
    app.include_router(config.router, prefix=settings.API_PREFIX)
    app.include_router(data.router, prefix=settings.API_PREFIX)
    app.include_router(tasks.router, prefix=settings.API_PREFIX)
    app.include_router(payment.router, prefix=settings.API_PREFIX)
    app.include_router(audit.router, prefix=settings.API_PREFIX)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
