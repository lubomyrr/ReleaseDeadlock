from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()

class HealthCheck(BaseModel):
    status: str = "ok"

@app.get("/health", status_code=200, response_model=HealthCheck)
async def health_check():
    return HealthCheck(status="ok")