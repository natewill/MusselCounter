"""
Image utils: hashing, dedup, and collection ops (SQLite, aiosqlite).
- Uses streaming MD5 (compatible with existing rows) to avoid loading whole files in RAM.
- Dedup via UNIQUE(file_hash) and UNIQUE(collection_id, image_id) + INSERT OR IGNORE.
"""

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import aiosqlite
import aiofiles

_CHUNK = 1 << 20  # 1 MiB


async def get_file_hash(file_path: str) -> str:
    """Async streaming MD5 for dedup (keeps compatibility with existing data)."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    h = hashlib.md5()
    async with aiofiles.open(p, "rb") as f:
        while chunk := await f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


async def find_image_by_hash(db: aiosqlite.Connection, file_hash: str):
    """Return a row (tuple) if found, else None."""
    async with db.execute(
        "SELECT image_id, stored_path, live_mussel_count, dead_mussel_count, stored_polygon_path "
        "FROM image WHERE file_hash = ? LIMIT 1",
        (file_hash,),
    ) as cur:
        return await cur.fetchone()


async def add_image_to_collection(
    db: aiosqlite.Connection,
    collection_id: int,
    image_path: str,
    filename: Optional[str] = None,
) -> int:
    """
    Upsert the image (by hash) and link it to the collection.
    Requires:
      - image(file_hash) UNIQUE
      - collection_image UNIQUE(collection_id, image_id)
    Returns image_id (existing or newly inserted).
    """
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"Image file not found: {p}")

    file_hash = await get_file_hash(str(p))
    now = datetime.now(timezone.utc).isoformat()

    await db.execute("BEGIN")
    try:
        # Insert image if new; ignore if exists.
        await db.execute(
            "INSERT OR IGNORE INTO image (filename, stored_path, file_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (filename or p.name, str(p), file_hash, now, now),
        )

        # Retrieve its id
        async with db.execute(
            "SELECT image_id FROM image WHERE file_hash = ? LIMIT 1", (file_hash,)
        ) as cur:
            row = await cur.fetchone()
        image_id = row[0]

        # Link to collection (ignored if already linked)
        await db.execute(
            "INSERT OR IGNORE INTO collection_image (collection_id, image_id, added_at) VALUES (?, ?, ?)",
            (collection_id, image_id, now),
        )

        await db.commit()
        return image_id
    except Exception:
        await db.rollback()
        raise


async def add_multiple_images_optimized(
    db: aiosqlite.Connection,
    collection_id: int,
    image_data: List[
        Tuple[str, str, str]
    ],  # (file_path, filename, file_hash) — hashes precomputed
) -> Tuple[List[int], int, int, List[int]]:
    """
    Bulk add with minimal queries.
    Returns: (image_ids (in input order), added_count, duplicate_count_in_collection, duplicate_image_ids)
      - duplicate_count counts images already linked to this collection *before* this call.
    """
    if not image_data:
        return ([], 0, 0, [])

    now = datetime.now(timezone.utc).isoformat()
    hashes = [h for _, _, h in image_data]

    await db.execute("BEGIN")
    try:
        # 1) Ensure all images exist (dedupe via UNIQUE(file_hash))
        to_insert = [
            (fn or Path(fp).name, fp, h, now, now) for (fp, fn, h) in image_data
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO image (filename, stored_path, file_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            to_insert,
        )

        # 2) Map file_hash -> image_id
        ph = ",".join("?" * len(hashes))
        async with db.execute(
            f"SELECT image_id, file_hash FROM image WHERE file_hash IN ({ph})", hashes
        ) as cur:
            rows = await cur.fetchall()
        hash_to_id = {r[1]: r[0] for r in rows}
        image_ids = [hash_to_id[h] for h in hashes]

        # 3) Link to collection, but only once per unique image_id
        unique_ids = sorted(set(image_ids))
        ph2 = ",".join("?" * len(unique_ids))
        async with db.execute(
            f"SELECT image_id FROM collection_image WHERE collection_id = ? AND image_id IN ({ph2})",
            (collection_id, *unique_ids),
        ) as cur:
            already_linked = {r[0] for r in await cur.fetchall()}

        # those already in collection (pre-existing duplicates)
        duplicate_image_ids = sorted(already_linked)
        duplicate_count = sum(1 for i in image_ids if i in already_linked)

        to_link = [(collection_id, i, now) for i in unique_ids if i not in already_linked]
        if to_link:
            await db.executemany(
                "INSERT OR IGNORE INTO collection_image (collection_id, image_id, added_at) VALUES (?, ?, ?)",
                to_link,
            )
        added_count = len(to_link)

        await db.commit()
        return (image_ids, added_count, duplicate_count, duplicate_image_ids)
    except Exception:
        await db.rollback()
        raise
