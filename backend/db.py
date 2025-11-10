import aiosqlite
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Database file path
DB_PATH = os.getenv("DB_PATH", "mussel_counter.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


@asynccontextmanager
async def get_db():
    """Context manager for database connections"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable row factory to return dict-like rows
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    """Initialize the database by creating all tables from schema.sql"""
    # Read the schema file
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()
    
    # Execute the schema to create tables
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(schema)
        await db.commit()
        print(f"Database initialized at {DB_PATH}")

