"""
File processing utilities for uploads.
- Validates file content
- Deduplicates via content hash
- Saves safely (race-proof) under UPLOAD_DIR
"""
import hashlib
from pathlib import Path
from typing import Optional, Tuple

import aiosqlite
import aiofiles
from fastapi import UploadFile

from utils.security import sanitize_filename
from config import UPLOAD_DIR


async def process_single_file(
    file: UploadFile,
    db: aiosqlite.Connection
) -> Optional[Tuple[str, str, str]]:
    """
    Returns (file_path, sanitized_filename, file_hash) or None on validation failure.
    """
    try:
        # 1) filename
        if not file.filename:
            return None
        try:
            sanitized = sanitize_filename(file.filename)
        except Exception:
            return None

        # 2) read content once (simple + predictable)
        content = await file.read()
        if not content:
            return None

        # 3) basic type check by extension and MIME
        file_ext = Path(sanitized).suffix.lower()
        allowed_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif'}
        allowed_mimes = {'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff', 'image/x-tiff'}
        if file_ext not in allowed_exts:
            return None
        if file.content_type and file.content_type.lower() not in allowed_mimes:
            return None

        # 4) hash for dedupe
        file_hash = hashlib.md5(content).hexdigest()  # fine for dedupe; switch to blake2 if you want

        # 5) check existing by hash (assume default aiosqlite row_factory -> tuples)
        async with db.execute(
            "SELECT stored_path FROM image WHERE file_hash = ? LIMIT 1",
            (file_hash,)
        ) as cur:
            row = await cur.fetchone()

        if row:
            existing_path = row[0]  # tuple access; not row["stored_path"] unless row_factory=Row
            try:
                p = Path(existing_path)
                if p.exists():
                    return (str(p), sanitized, file_hash)
            except Exception:
                # invalid/missing on disk -> proceed to save a new copy
                pass

        # 6) choose a unique destination (race-safe using exclusive create)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stem = Path(sanitized).stem
        suffix = Path(sanitized).suffix or ""
        counter = 0
        while True:
            name = f"{stem}{'' if counter == 0 else f'_{counter}'}{suffix}"
            dest = UPLOAD_DIR / name
            try:
                async with aiofiles.open(dest, "xb") as f:  # 'x' = fail if exists (TOCTOU-safe)
                    await f.write(content)
                # success
                return (str(dest), sanitized, file_hash)
            except FileExistsError:
                counter += 1
                continue
            except Exception:
                return None

    except Exception:
        return None
