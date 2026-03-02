"""
Image utils: dedup and collection ops (SQLite, aiosqlite).
- Dedup via UNIQUE(file_hash) and UNIQUE(collection_id, image_id) + INSERT OR IGNORE.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import aiosqlite


async def add_multiple_images_optimized(
    db: aiosqlite.Connection,
    collection_id: int,
    image_data: List[
        Tuple[str, str, str]
    ],  # (file_path, filename, file_hash) — hashes precomputed
) -> Tuple[List[int], int, int, List[int]]:
    """
    Add many images to a collection with clear, sequential SQL steps.

    Returns: (image_ids (in input order), added_count, duplicate_count_in_collection, duplicate_image_ids)
      - duplicate_count counts images already linked to this collection *before* this call.
    """
    if not image_data:
        return ([], 0, 0, [])

    now = datetime.now(timezone.utc).isoformat()
    image_ids: List[int] = []

    await db.execute("BEGIN")
    try:
        # 1) Ensure each image exists and collect IDs in input order.
        for file_path, filename, file_hash in image_data:
            await db.execute(
                "INSERT OR IGNORE INTO image (filename, stored_path, file_hash) VALUES (?, ?, ?)",
                (filename or Path(file_path).name, file_path, file_hash),
            )
            async with db.execute(
                "SELECT image_id FROM image WHERE file_hash = ? LIMIT 1",
                (file_hash,),
            ) as cur:
                row = await cur.fetchone()
            if not row:
                raise RuntimeError(f"Failed to resolve image_id for hash {file_hash}")
            image_ids.append(row[0])

        # 2) Check which unique image IDs were already linked before this call.
        unique_ids = sorted(set(image_ids))
        already_linked = set()
        for image_id in unique_ids:
            async with db.execute(
                "SELECT 1 FROM collection_image WHERE collection_id = ? AND image_id = ? LIMIT 1",
                (collection_id, image_id),
            ) as cur:
                if await cur.fetchone():
                    already_linked.add(image_id)

        duplicate_image_ids = sorted(already_linked)
        duplicate_count = sum(1 for image_id in image_ids if image_id in already_linked)

        # 3) Link only IDs that were not already linked.
        added_count = 0
        for image_id in unique_ids:
            if image_id in already_linked:
                continue
            await db.execute(
                "INSERT INTO collection_image (collection_id, image_id, added_at) VALUES (?, ?, ?)",
                (collection_id, image_id, now),
            )
            added_count += 1

        await db.commit()
        return (image_ids, added_count, duplicate_count, duplicate_image_ids)
    except Exception:
        await db.rollback()
        raise
