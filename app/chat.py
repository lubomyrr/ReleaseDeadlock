"""History || every agent invocation starts with fresh limits."""

from uuid import UUID

from sqlalchemy import delete, select

from app.agent import answer_question as run_agent
from app.database import SessionLocal
from app.models import ChatTurn

MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 8000


def history_messages(turns) -> list[dict]:
    messages, size = [], 0
    for turn in turns:  #Newest first, keep complete "question/answer" pairs
        size += len(turn.question) + len(turn.answer)
        if size > MAX_HISTORY_CHARS:
            break
        messages[:0] = [
            {"role": "user", "content": turn.question},
            {"role": "assistant", "content": turn.answer},
        ]
    return messages


async def answer_question(question: str, session_id: UUID) -> dict:
    recent = select(ChatTurn).where(ChatTurn.session_id == session_id).order_by(ChatTurn.id.desc()).limit(MAX_HISTORY_TURNS)
    async with SessionLocal() as session:
        turns = (await session.scalars(recent)).all()
    result = await run_agent(question, history=history_messages(turns))
    async with SessionLocal() as session:
        session.add(ChatTurn(session_id=session_id, question=question, answer=result["answer"]))
        await session.flush()
        keep = select(ChatTurn.id).where(ChatTurn.session_id == session_id).order_by(ChatTurn.id.desc()).limit(MAX_HISTORY_TURNS)
        await session.execute(delete(ChatTurn).where(ChatTurn.session_id == session_id, ChatTurn.id.not_in(keep)))
        await session.commit()
    return result
