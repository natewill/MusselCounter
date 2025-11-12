"""
Database connection and initialization utilities.

This module provides:
- Database connection management (context manager for automatic cleanup)
- Database initialization (creates tables from schema.sql)
- Database version tracking (to detect schema changes)
"""

import aiosqlite
from contextlib import asynccontextmanager
from config import DB_PATH, SCHEMA_PATH
from utils.logger import logger
from pathlib import Path
from datetime import datetime


async def _initialize_models(db: aiosqlite.Connection):
    """
    Initialize database with default models from models/ directory.
    Detects optimal batch size for each model during startup.
    """
    models_dir = Path("models")
    if not models_dir.exists():
        logger.info("No models/ directory found. Skipping model initialization.")
        return
    
    model_files = list(models_dir.glob("*.pt")) + list(models_dir.glob("*.pth"))
    if not model_files:
        logger.info("No model files found in models/ directory")
        return
    
    from utils.model_utils import load_model
    
    for model_file in model_files:
        # Infer model type from filename
        filename_lower = model_file.name.lower()
        if "yolo" in filename_lower:
            model_type = "YOLO"
        elif "rcnn" in filename_lower or "faster" in filename_lower:
            model_type = "Faster R-CNN"
        else:
            model_type = "YOLO"  # Default to YOLO
        
        # Check if model already exists
        cursor = await db.execute(
            "SELECT model_id FROM model WHERE weights_path = ?",
            (str(model_file),)
        )
        existing = await cursor.fetchone()
        
        if not existing:
            # Load model and detect optimal batch size (one-time during startup)
            logger.info(f"Adding model: {model_file.name} ({model_type})")
            optimal_bs = 8  # Default fallback
            try:
                _, _, optimal_bs = load_model(str(model_file), model_type, detect_batch_size=True)
                logger.info(f"✓ {model_file.name} - optimal batch size: {optimal_bs}")
            except Exception as e:
                logger.warning(f"Failed to detect batch size for {model_file.name}, using default {optimal_bs}: {e}")
            
            now = datetime.now().isoformat()
            await db.execute(
                """INSERT INTO model (name, type, weights_path, description, optimal_batch_size, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    model_file.stem,
                    model_type,
                    str(model_file),
                    f"Auto-detected {model_type} model",
                    optimal_bs,
                    now,
                    now
                )
            )
    
    await db.commit()


@asynccontextmanager
async def get_db():
    """
    Context manager for database connections.
    
    Provides a database connection that automatically:
    - Opens connection when entering context
    - Sets row factory to return dict-like rows (access columns by name)
    - Closes connection when exiting context
    
    Usage:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM batch")
            rows = await cursor.fetchall()
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable row factory to return dict-like rows (access by column name)
        # Without this, rows would be tuples accessed by index
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """
    Initialize the database by creating all tables from schema.sql.
    
    This function:
    1. Deletes existing database if found (development mode - in production use migrations)
    2. Reads schema.sql and executes it to create all tables
    3. Creates db_metadata table for tracking database version
    4. Stores initialization timestamp in metadata
    
    Note: In production, you'd want proper database migrations instead of
    deleting and recreating the database.
    """
    from datetime import datetime
    import os

    # Check if database exists and has old schema
    # For development: delete old database to recreate with new schema
    # In production, you'd want proper migrations instead
    if os.path.exists(DB_PATH):
        logger.info(
            f"Existing database found at {DB_PATH}. Deleting to recreate with new schema..."
        )
        os.remove(DB_PATH)

    # Read the schema file containing CREATE TABLE statements
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()

    # Execute the schema to create all tables
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(schema)  # Execute all SQL statements in schema file

        # Create metadata table to store database version/reset timestamp
        # This allows the frontend to detect when database was reset and refresh data
        # IF NOT EXISTS prevents error if table already exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Check if metadata already exists (for existing databases that weren't reset)
        cursor = await db.execute(
            "SELECT value FROM db_metadata WHERE key = ?", ("db_init_timestamp",)
        )
        existing_metadata = await cursor.fetchone()

        if not existing_metadata:
            # Store database initialization timestamp (new database or existing without metadata)
            # Frontend can check this to detect database resets
            init_timestamp = datetime.now().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("db_init_timestamp", init_timestamp),
            )
            await db.commit()
            logger.info(
                f"Database initialized at {DB_PATH} with timestamp {init_timestamp}"
            )
        else:
            # Database already has metadata, don't update it
            # This preserves the original initialization timestamp
            logger.info(
                f"Database already initialized at {DB_PATH} "
                f"(timestamp: {existing_metadata['value']})"
            )
        
        # Initialize models from models/ directory (happens once per database init)
        await _initialize_models(db)


async def get_db_version(db: aiosqlite.Connection) -> str | None:
    """Get the database version/timestamp"""
    cursor = await db.execute(
        "SELECT value FROM db_metadata WHERE key = ?", ("db_init_timestamp",)
    )
    row = await cursor.fetchone()
    return row["value"] if row else None
