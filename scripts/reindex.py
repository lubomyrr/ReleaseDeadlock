"""Rebuild indexed chunks from data/raw without creating duplicate documents."""

import asyncio
from pathlib import Path

from app.database import SessionLocal, engine
from app.ingestion import ingest_document

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


async def main():
    try:
        async with SessionLocal() as session:
            for path in sorted(RAW_DIR.glob("patch_*.md")):
                _, count = await ingest_document(
                    path.name, path.read_text(encoding="utf-8"), session, reindex=True,
                )
                print(f"{path.name}: {count} chunks", flush=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())