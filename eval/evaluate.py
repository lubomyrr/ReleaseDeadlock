import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def main():
    from app.database import SessionLocal

    async with SessionLocal() as session:
        metrics = await evaluate_retrieval(session)
        print(metrics)


def calculate_metrics(
    expected: list[str],
    retrieved: list[list[str]],
) -> dict[str, float]:
    correct = 0
    mrr_sum = 0
    if not expected:
        raise ValueError("Expected list cannot be empty.")
    if len(expected) != len(retrieved):
        raise ValueError("Expected and retrieved lists must have the same length.")
    for expected_doc, retrieved_docs in zip(expected, retrieved):
        if expected_doc in retrieved_docs[:3]:
            correct += 1

        for rank, doc in enumerate(retrieved_docs[:3], start=1):
            if doc == expected_doc:
                mrr_sum += 1 / rank
                break

    recall = correct / len(expected)
    mrr = mrr_sum / len(expected)
    return {"recall": recall, "mrr": mrr}


async def evaluate_retrieval(session: "AsyncSession") -> dict[str, float]:
    from app.retrieval import search_chunks

    path = Path(__file__).resolve().parent / "questions.json"
    questions = json.loads(path.read_text(encoding="utf-8"))
    expected = []
    retrieved = []

    for item in questions:
        question = item["question"]
        expected_doc = item["expected_document"]
        results = await search_chunks(question, session, top_k=3)
        filenames = [result.filename for result in results]
        print(f"Question: {question}")
        print(f"Expected: {expected_doc}")
        print(f"Retrieved: {filenames}")

        expected.append(expected_doc)
        retrieved.append(filenames)
    return calculate_metrics(expected, retrieved)


if __name__ == "__main__":
    asyncio.run(main())

