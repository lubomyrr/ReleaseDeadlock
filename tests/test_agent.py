import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.agent import answer_question


class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_unverified_model_answer_is_not_returned(self):
        response = SimpleNamespace(message=SimpleNamespace(
            tool_calls=[], content="Scrap Grenade damage is 999.",
        ))
        with patch("app.agent.client.chat", new_callable=AsyncMock, return_value=response):
            result = await answer_question("What is Scrap Grenade damage?")
        self.assertNotIn("999", result["answer"])
        self.assertIn("couldn't verify", result["answer"])
        self.assertEqual(result["sources"], [])

    async def test_answer_without_tool_result_is_not_verified(self):
        response = SimpleNamespace(message=SimpleNamespace(tool_calls=[], content="Hello!"))
        with patch("app.agent.client.chat", new_callable=AsyncMock, return_value=response) as chat:
            result = await answer_question("Hello!")
        chat.assert_awaited_once()
        self.assertIn("couldn't verify", result["answer"])

    async def test_search_results_reach_generation_and_dates_are_preserved(self):
        for dates in (
            {"date_to": "2026-10-14"},
            {"date_from": "2026-10-14"},
            {"date_from": "2026-10-14", "date_to": "2026-10-14"},
        ):
            with self.subTest(dates=dates):
                arguments = {"query": "Strix Salvo cooldown", "hero": "Deadman Danny", **dates}
                call = SimpleNamespace(function=SimpleNamespace(name="search_patch_notes", arguments=arguments))
                response = SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))
                source = {"filename": "patch_2026_10_14.md", "chunk_id": "chunk-1"}
                search_result = {"data": [{"content": "Cooldown from 30s to 25s"}], "sources": [source], "errors": []}
                with (
                    patch("app.agent.client.chat", new_callable=AsyncMock, side_effect=[
                        response, SimpleNamespace(message=SimpleNamespace(content="25s [patch_2026_10_14.md]")),
                    ]) as chat,
                    patch("app.agent.search_patch_notes", new_callable=AsyncMock, return_value=search_result) as search,
                ):
                    result = await answer_question("Tell me about Strix Salvo cooldown")
                search.assert_awaited_once_with(**arguments)
                self.assertEqual(result["sources"], [source])
                tool_message = chat.await_args.kwargs["messages"][-1]
                self.assertEqual(tool_message["role"], "tool")
                self.assertIn("30s to 25s", tool_message["content"])

    async def test_empty_search_cannot_produce_unverified_answer(self):
        call = SimpleNamespace(function=SimpleNamespace(name="search_patch_notes", arguments={"query": "unknown"}))
        response = SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))
        with (
            patch("app.agent.client.chat", new_callable=AsyncMock, side_effect=[
                response, SimpleNamespace(message=SimpleNamespace(tool_calls=[], content="Unverified")),
            ]) as chat,
            patch("app.agent.search_patch_notes", new_callable=AsyncMock, return_value={"data": [], "sources": [], "errors": []}),
        ):
            result = await answer_question("Unknown change?")
        self.assertEqual(chat.await_count, 2)
        self.assertNotIn("Unverified", result["answer"])
        self.assertEqual(result["sources"], [])
