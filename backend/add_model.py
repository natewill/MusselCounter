"""
Script to add a model to the database for testing.
Usage: python add_model.py
"""

import asyncio
import aiosqlite
from datetime import datetime
from pathlib import Path
import os

# Database path
DB_PATH = os.getenv("DB_PATH", "mussel_counter.db")

# Model information
MODEL_NAME = "Fast R-CNN - Mussel Detection"
MODEL_TYPE = "RCNN"  # or "FasterRCNN" - both work
MODEL_PATH = "data/models/fast_rcnn_weights.pth"
MODEL_DESCRIPTION = "Faster R-CNN model for mussel detection (live and dead)"


async def add_model():
    """Add the model to the database"""
    # Check if model file exists
    if not Path(MODEL_PATH).exists():
        print(f"ERROR: Model file not found at {MODEL_PATH}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Please make sure the model file exists at: {MODEL_PATH}")
        return

    # Connect to database
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if model already exists (by path)
        cursor = await db.execute(
            "SELECT model_id, name FROM model WHERE weights_path = ?", (MODEL_PATH,)
        )
        existing = await cursor.fetchone()

        if existing:
            print(f"Model already exists in database:")
            print(f"  Model ID: {existing[0]}")
            print(f"  Name: {existing[1]}")
            print(f"  Path: {MODEL_PATH}")
            return

        # Insert model
        now = datetime.now().isoformat()
        cursor = await db.execute(
            """INSERT INTO model (name, type, weights_path, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (MODEL_NAME, MODEL_TYPE, MODEL_PATH, MODEL_DESCRIPTION, now, now),
        )
        model_id = cursor.lastrowid
        await db.commit()

        print(f"✅ Model added successfully!")
        print(f"  Model ID: {model_id}")
        print(f"  Name: {MODEL_NAME}")
        print(f"  Type: {MODEL_TYPE}")
        print(f"  Path: {MODEL_PATH}")
        print(f"\nYou can now use this model in the frontend model picker!")


if __name__ == "__main__":
    asyncio.run(add_model())
