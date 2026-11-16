import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion import hash_document, ingest_document, split_document
from app.models import Document


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


class ChunkingTests(unittest.TestCase):
    def test_hero_context_survives_chunk_boundaries(self):
        for filename, fact, hero in (
            ("patch_2026_10_14.md", "Cooldown from 30s to 25s", "Deadman Danny"),
            ("patch_2026_10_05.md", "Damage Reduction reduced from 15% to 10%", "Rat King"),
        ):
            with self.subTest(hero=hero):
                chunks = split_document((RAW_DIR / filename).read_text(encoding="utf-8"))
                matching = [chunk for chunk in chunks if fact in chunk]
                self.assertTrue(matching)
                self.assertTrue(all(hero in chunk.split("\n\n", 1)[0] for chunk in matching))

    def test_chunks_do_not_cross_hero_sections(self):
        content = "## Heroes\n\n### Baba\n\n" + "Barrier reduced. " * 60 + "\n\n### Deadman Danny\n\nCooldown reduced."
        chunks = split_document(content)
        self.assertTrue(all("Baba" in chunk for chunk in chunks if "Barrier reduced." in chunk))
        self.assertTrue(all("Baba" not in chunk for chunk in chunks if "Cooldown reduced." in chunk))


class ReindexTests(unittest.IsolatedAsyncioTestCase):
    async def test_reindex_replaces_chunks_and_preserves_document(self):
        document = Document(id=uuid4(), filename="patch_2026_10_14.md", content_hash="existing")
        document.chunks = []
        session = AsyncMock(spec=AsyncSession)
        session.scalar.return_value = document
        with patch("app.ingestion.generate_embeddings", return_value=[[0.0] * 384]):
            saved, count = await ingest_document(document.filename, "## Heroes\n\n### Baba\n\nBarrier reduced.", session, reindex=True)
        self.assertIs(saved, document)
        self.assertEqual(count, 1)
        self.assertEqual(document.content_hash, hash_document("## Heroes\n\n### Baba\n\nBarrier reduced."))
        self.assertIn("Baba", document.chunks[0].content)
        session.execute.assert_awaited_once()
        session.refresh.assert_awaited_once_with(document, ["chunks"])
        session.commit.assert_awaited_once()

    async def test_duplicate_upload_does_not_reindex(self):
        document = Document(id=uuid4(), filename="existing.md", content_hash="existing")
        session = AsyncMock(spec=AsyncSession)
        session.scalar.return_value = document
        with patch("app.ingestion.generate_embeddings") as embed:
            saved, count = await ingest_document("existing.md", "content", session)
        self.assertIs(saved, document)
        self.assertEqual(count, 0)
        embed.assert_not_called()
        session.execute.assert_not_awaited()
