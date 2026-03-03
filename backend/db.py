"""
Database connection and initialization utilities.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os

import aiosqlite

from config import DB_PATH, SCHEMA_PATH, RESET_DB_ON_STARTUP

SCHEMA_VERSION = "run_first_v4"


async def _is_legacy_schema(db: aiosqlite.Connection) -> bool:
    """
    True when old collection-based tables are present/missing new run_image table.
    """
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='run_image'"
    )
    return await cursor.fetchone() is None


async def _read_schema_version(db: aiosqlite.Connection) -> str | None:
    cursor = await db.execute(
        "SELECT value FROM db_metadata WHERE key = ?",
        ("schema_version",),
    )
    row = await cursor.fetchone()
    return row["value"] if row else None


@asynccontextmanager
async def get_db():
    """
    Async DB connection context manager with row access by column name.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """
    Initialize DB using schema.sql.

    Behavior:
    - If RESET_DB_ON_STARTUP is true: recreate DB.
    - If DB is legacy schema: recreate DB (no migration path by design).
    - If schema_version mismatches: recreate DB.
    """
    db_exists = os.path.exists(DB_PATH)
    must_recreate = RESET_DB_ON_STARTUP

    if db_exists and not must_recreate:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            try:
                if await _is_legacy_schema(db):
                    must_recreate = True
                else:
                    version = await _read_schema_version(db)
                    if version != SCHEMA_VERSION:
                        must_recreate = True
            except Exception:
                must_recreate = True

    if db_exists and must_recreate:
        os.remove(DB_PATH)
        db_exists = False

    if db_exists and not must_recreate:
        return

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(schema)

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS db_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
            ("db_init_timestamp", now),
        )
        await db.execute(
            "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        await db.commit()


async def get_db_version(db: aiosqlite.Connection) -> str | None:
    """
    Database init timestamp for frontend cache invalidation.
    """
    cursor = await db.execute(
        "SELECT value FROM db_metadata WHERE key = ?",
        ("db_init_timestamp",),
    )
    row = await cursor.fetchone()
    return row["value"] if row else None
