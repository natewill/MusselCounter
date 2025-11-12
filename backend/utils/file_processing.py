"""
File processing utilities for uploads.
- Validates file content and size
- Deduplicates via content hash
- Saves safely (race-proof) under UPLOAD_DIR
"""
import hashlib
from pathlib import Path
from typing import Optional, Tuple

import aiosqlite
import aiofiles
from fastapi import UploadFile

from utils.logger import logger
from utils.security import sanitize_filename, validate_path_in_directory
from utils.file_validation_lib import validate_image_content, validate_file_size
from config import UPLOAD_DIR, MAX_FILE_SIZE


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

        # 2) read content once (simple + predictable); guard size
        content = await file.read()
        if not content:
            return None
        ok_size, _ = validate_file_size(content, MAX_FILE_SIZE)
        if not ok_size:
            return None

        # 3) content-type check (expects bytes + name)
        ok_img, _ = validate_image_content(content, sanitized)
        if not ok_img:
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
                # ensure the path is sane and exists
                p = Path(existing_path)
                validate_path_in_directory(p, UPLOAD_DIR)
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
                # final security check: dest stays inside UPLOAD_DIR
                validate_path_in_directory(dest, UPLOAD_DIR)
                async with aiofiles.open(dest, "xb") as f:  # 'x' = fail if exists (TOCTOU-safe)
                    await f.write(content)
                # success
                return (str(dest), sanitized, file_hash)
            except FileExistsError:
                counter += 1
                continue
            except Exception as e:
                logger.exception("Failed to save upload: %s", e)
                return None

    except Exception as e:
        logger.exception("process_single_file unexpected error: %s", e)
        return None