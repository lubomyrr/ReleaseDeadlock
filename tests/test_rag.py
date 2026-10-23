import asyncio

from app.rag import generate_answer


async def main():
    context = """
Source: [test_patch.md]
Deadlock Patch Notes, October 5, 2026.
Rat King: Scrap Grenade damage increased from 65 to 70.
"""

    questions = [
        "What happened to Rat King's Scrap Grenade damage?",
        "Which new map was added?",
    ]

    for question in questions:
        answer = await generate_answer(question, context)
        print(f"\nQuestion: {question}\nAnswer: {answer}")


if __name__ == "__main__":
    asyncio.run(main())