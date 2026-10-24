import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.rag import answer_question, generate_answer
from app.retrieval import SearchResult


class RagTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_results_skips_generation(self):
        with (
            patch("app.rag.search_chunks", new_callable=AsyncMock, return_value=[]),
            patch("app.rag.generate_answer", new_callable=AsyncMock) as generate,
        ):
            result = await answer_question("Unknown update?", AsyncMock())

        self.assertEqual(result, {
            "answer": "The retrieved patch notes do not contain this information.",
            "sources": [],
        })
        generate.assert_not_awaited()

    async def test_retrieved_context_and_sources_reach_answer(self):
        session = AsyncMock()
        chunk = SimpleNamespace(id=uuid4(), content="Damage increased from 65 to 70.")
        result = SearchResult(chunk, "patch_2026_10_05.md", 0.1)
        with (
            patch("app.rag.search_chunks", new_callable=AsyncMock, return_value=[result]) as search,
            patch("app.rag.generate_answer", new_callable=AsyncMock, return_value="Damage increased.") as generate,
        ):
            response = await answer_question("What changed?", session)

        search.assert_awaited_once_with(question="What changed?", session=session, top_k=3)
        generate.assert_awaited_once_with(
            "What changed?",
            f"Source: {result.filename}\nChunk ID: {chunk.id}\nContent: {chunk.content}",
            model="qwen3.5:4b",
        )
        self.assertEqual(response, {
            "answer": "Damage increased.",
            "sources": [{"filename": result.filename, "chunk_id": chunk.id}],
        })

    async def test_generate_answer_uses_model_response(self):
        response = SimpleNamespace(message=SimpleNamespace(content="Generated answer"))
        with patch("app.rag.client.chat", new_callable=AsyncMock, return_value=response) as chat:
            answer = await generate_answer("What changed?", "Patch context")

        self.assertEqual(answer, "Generated answer")
        self.assertEqual(chat.await_args.kwargs["model"], "qwen3.5:4b")
        self.assertIn("Patch context", chat.await_args.kwargs["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
