import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine, async_session_factory
from app.db.base import Base
from app.services.user_service import UserService


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        service = UserService(session)
        admin = await service.create_superuser(
            email="admin@trendradar.com",
            password="admin123456",
            nickname="Admin",
        )
        print(f"Superuser created: {admin.email}")

        demo = await service.get_by_email("demo@test.com")
        if not demo:
            from app.schemas.user import UserCreate
            demo = await service.create(UserCreate(
                email="demo@test.com",
                password="demo123456",
                nickname="Demo User",
            ))
            print(f"Demo user created: {demo.email}")
        else:
            print(f"Demo user already exists: {demo.email}")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(init_db())
