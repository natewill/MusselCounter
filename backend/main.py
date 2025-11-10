from fastapi import FastAPI
from contextlib import asynccontextmanager
from db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: (nothing needed for now)


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Backend running!"}