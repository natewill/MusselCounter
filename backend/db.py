import aiosqlite
import os
from contextlib import asynccontextmanager

# Database file path
DB_PATH = os.getenv("DB_PATH", "mussel_counter.db")


@asynccontextmanager
async def get_db():
    """Context manager for database connections"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable row factory to return dict-like rows
        db.row_factory = aiosqlite.Row
        yield db

