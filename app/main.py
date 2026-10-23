from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

app = FastAPI()

class HealthCheck(BaseModel):
    status: str = "ok"

@app.get("/health", status_code=200, response_model=HealthCheck)
async def health_check(session: Annotated[AsyncSession, Depends(get_session)]):
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL unavailable") from exc
    return HealthCheck(status="ok")