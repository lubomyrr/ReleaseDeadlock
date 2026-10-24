import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from ollama import ResponseError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.main import app


class AskEndpointTests(unittest.TestCase):
    def setUp(self):
        self.session = AsyncMock(spec=AsyncSession)

        async def override_session():
            yield self.session

        self.enterContext(patch.dict(app.dependency_overrides, {get_session: override_session}))
        self.mock_answer = self.enterContext(patch("app.main.answer_question", new_callable=AsyncMock))
        self.client = self.enterContext(TestClient(app))

    def test_ask_returns_answer_and_sources(self):
        question = "What changed about Scrap Grenade damage?"
        chunk_id = UUID("e4f82c4a-0458-458d-8ab0-6c2ac629c0ea")
        answer = "Damage increased from 65 to 70 [patch_2026_10_05.md]."

        self.mock_answer.return_value = {
            "answer": answer,
            "sources": [{"filename": "patch_2026_10_05.md", "chunk_id": chunk_id}],
        }
        response = self.client.post("/ask", json={"question": question})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "answer": answer,
            "sources": [{"filename": "patch_2026_10_05.md", "chunk_id": str(chunk_id)}],
        })
        self.mock_answer.assert_awaited_once_with(
            question=question, session=self.session, top_k=3,
        )

    def test_ask_rejects_missing_empty_and_blank_questions(self):
        for payload in ({}, {"question": ""}, {"question": " \t\n"}):
            with self.subTest(payload=payload):
                response = self.client.post("/ask", json=payload)
                self.assertEqual(response.status_code, 422)
        self.mock_answer.assert_not_awaited()

    def test_search_rejects_empty_and_blank_questions(self):
        with patch("app.main.search_chunks", new_callable=AsyncMock) as search:
            for question in ("", " \t\n"):
                with self.subTest(question=question):
                    response = self.client.get("/search", params={"question": question})
                    self.assertEqual(response.status_code, 422)
            search.assert_not_awaited()

    def test_ask_handles_ollama_errors(self):
        cases = (
            (ConnectionError("offline"), 503, "Ollama unavailable"),
            (httpx.ConnectError("offline"), 503, "Ollama unavailable"),
            (httpx.ReadTimeout("timeout"), 504, "Ollama request timed out"),
            (TimeoutError(), 504, "Ollama request timed out"),
            (ResponseError("model missing", status_code=404), 503, "Ollama model unavailable"),
            (ResponseError("internal failure", status_code=500), 503, "Ollama generation failed"),
        )
        for error, status, detail in cases:
            with self.subTest(error=error):
                self.mock_answer.side_effect = error
                response = self.client.post("/ask", json={"question": "What changed?"})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json(), {"detail": detail})


if __name__ == "__main__":
    unittest.main()
