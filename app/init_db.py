import asyncio

from sqlalchemy import text

from app.database import engine
from app.models import Base


async def init_db() -> None:
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(Base.metadata.create_all)
        print("Database initialized: " + ", ".join(Base.metadata.tables))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
