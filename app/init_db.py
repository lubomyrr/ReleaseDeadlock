import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select, update

from app.database import engine
from app.ingestion import extract_patch_date
from app.models import Base, Document


def run_migrations(connection) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def init_db() -> None:
    try:
        async with engine.begin() as connection:
            await connection.run_sync(run_migrations)
            rows = await connection.execute(
                select(Document.id, Document.filename).where(Document.patch_date.is_(None))
            )
            dates_filled = 0
            for document_id, filename in rows.all():
                patch_date = extract_patch_date(filename)
                if patch_date is not None:
                    await connection.execute(
                        update(Document).where(Document.id == document_id).values(patch_date=patch_date)
                    )
                    dates_filled += 1
        print("Database initialized: " + ", ".join(Base.metadata.tables))
        print(f"Patch dates filled: {dates_filled}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
