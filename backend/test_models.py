"""Quick test script to check models in database and API"""
import asyncio
import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "mussel_counter.db")

async def check_models():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM model")
        rows = await cursor.fetchall()
        
        if rows:
            print(f"Found {len(rows)} model(s) in database:")
            for row in rows:
                print(f"  - Model ID: {row['model_id']}")
                print(f"    Name: {row['name']}")
                print(f"    Type: {row['type']}")
                print(f"    Path: {row['weights_path']}")
                print()
        else:
            print("No models found in database!")

if __name__ == "__main__":
    asyncio.run(check_models())

