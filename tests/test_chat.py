import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import delete

from app.chat import answer_question, history_messages
from app.database import SessionLocal, engine
from app.models import ChatTurn


class ChatTests(unittest.TestCase):
    def test_history_budget_keeps_recent_complete_pairs_in_order(self):
        turns = [SimpleNamespace(question="new", answer="reply"), SimpleNamespace(question="old", answer="reply")]
        with patch("app.chat.MAX_HISTORY_CHARS", 8):
            self.assertEqual(history_messages(turns), [
                {"role": "user", "content": "new"}, {"role": "assistant", "content": "reply"},
            ])


@unittest.skipUnless(os.getenv("TEST_POSTGRES_TOOLS") == "1", "Requires PostgreSQL migrations")
class ChatPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def test_followup_uses_only_its_own_session(self):
        first, second = uuid4(), uuid4()
        try:
            with patch("app.chat.run_agent", new_callable=AsyncMock, return_value={"answer": "Baba answer", "sources": []}) as agent:
                await answer_question("Tell me about Baba", first)
                await answer_question("And her cooldown?", first)
                await answer_question("Who are we discussing?", second)
            self.assertEqual(agent.await_args_list[0].kwargs["history"], [])
            self.assertEqual(agent.await_args_list[1].kwargs["history"], [
                {"role": "user", "content": "Tell me about Baba"},
                {"role": "assistant", "content": "Baba answer"},
            ])
            self.assertEqual(agent.await_args_list[2].kwargs["history"], [])
        finally:
            async with SessionLocal() as session:
                await session.execute(delete(ChatTurn).where(ChatTurn.session_id.in_([first, second])))
                await session.commit()
            await engine.dispose()
