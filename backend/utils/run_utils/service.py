"""
Run-first orchestration service.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, Iterable

import aiofiles
import aiosqlite
from fastapi import HTTPException, UploadFile

from config import DEFAULT_THRESHOLD, UPLOAD_DIR
from utils.detection_counts import get_counts_by_run_image_for_run, get_counts_for_run_image
from utils.model_utils.inference import run_inference_on_image
from utils.model_utils.loader import load_model
from utils.security import sanitize_filename

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_run_state(run: aiosqlite.Row | dict[str, Any]) -> str:
    """
    Derived run state without storing a status column.
    """
    data = dict(run)

    if data.get("error_msg") or data.get("run_error"):
        return "failed"
    if int(data.get("total_images") or 0) == 0:
        return "pending"
    if int(data.get("processed_count") or 0) < int(data.get("total_images") or 0):
        return "running"
    return "completed"


async def get_run(db: aiosqlite.Connection, run_id: int):
    cursor = await db.execute(
        """
        SELECT
            r.*,
            m.name AS model_name,
            m.type AS model_type,
            m.weights_path AS weights_path
        FROM run r
        JOIN model m ON m.model_id = r.model_id
        WHERE r.run_id = ?
        """,
        (run_id,),
    )
    return await cursor.fetchone()


async def list_runs(db: aiosqlite.Connection):
    cursor = await db.execute(
        """
        SELECT
            r.*,
            m.name AS model_name,
            m.type AS model_type,
            (
                SELECT ri.stored_path
                FROM run_image ri
                WHERE ri.run_id = r.run_id
                ORDER BY ri.run_image_id ASC
                LIMIT 1
            ) AS first_image_path
        FROM run r
        JOIN model m ON m.model_id = r.model_id
        ORDER BY r.created_at DESC
        """
    )
    return await cursor.fetchall()


async def list_run_images(db: aiosqlite.Connection, run_id: int):
    cursor = await db.execute(
        """
        SELECT
            run_image_id,
            stored_path,
            live_mussel_count,
            dead_mussel_count,
            processed_at,
            error_msg
        FROM run_image
        WHERE run_id = ?
        ORDER BY run_image_id ASC
        """,
        (run_id,),
    )
    return await cursor.fetchall()


async def _validate_model_exists(db: aiosqlite.Connection, model_id: int):
    cursor = await db.execute("SELECT model_id FROM model WHERE model_id = ?", (model_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Model not found")


async def _write_upload(file: UploadFile, run_dir: Path) -> tuple[str, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file: missing filename")

    sanitized = sanitize_filename(file.filename)
    ext = Path(sanitized).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {sanitized}")

    if file.content_type and file.content_type.lower() not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=400, detail=f"Unsupported MIME type for {sanitized}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail=f"Empty file: {sanitized}")

    stem = Path(sanitized).stem
    suffix = Path(sanitized).suffix
    counter = 0

    while True:
        candidate = f"{stem}{'' if counter == 0 else f'_{counter}'}{suffix}"
        dest = run_dir / candidate
        try:
            async with aiofiles.open(dest, "xb") as f:
                await f.write(content)
            return candidate, str(dest)
        except FileExistsError:
            counter += 1


async def create_run_from_upload(
    db: aiosqlite.Connection,
    model_id: int,
    files: Iterable[UploadFile],
    threshold: float | None,
):
    file_list = list(files)
    if not file_list:
        raise HTTPException(status_code=400, detail="At least one image is required")

    await _validate_model_exists(db, model_id)
    threshold_value = DEFAULT_THRESHOLD if threshold is None else float(threshold)
    if threshold_value < 0.0 or threshold_value > 1.0:
        raise HTTPException(status_code=400, detail="Threshold must be between 0.0 and 1.0")

    run_id: int | None = None
    run_dir: Path | None = None

    await db.execute("BEGIN")
    try:
        created_at = _now()
        cursor = await db.execute(
            """
            INSERT INTO run (model_id, threshold, created_at, total_images, processed_count, live_mussel_count, error_msg)
            VALUES (?, ?, ?, 0, 0, 0, NULL)
            """,
            (model_id, threshold_value, created_at),
        )
        run_id = int(cursor.lastrowid)

        run_dir = UPLOAD_DIR / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        image_count = 0
        for file in file_list:
            image_count += 1
            _, stored_path = await _write_upload(file, run_dir)
            await db.execute(
                """
                INSERT INTO run_image (run_id, stored_path)
                VALUES (?, ?)
                """,
                (run_id, stored_path),
            )

        await db.execute(
            "UPDATE run SET total_images = ? WHERE run_id = ?",
            (image_count, run_id),
        )
        await db.commit()
    except HTTPException:
        await db.rollback()
        if run_dir and run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)
        raise
    except Exception as exc:
        await db.rollback()
        if run_dir and run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to create run: {exc}") from exc

    run = await get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to load created run")
    return run


async def _replace_detections(
    db: aiosqlite.Connection,
    run_id: int,
    run_image_id: int,
    polygons: list[dict[str, Any]],
):
    await db.execute(
        "DELETE FROM detection WHERE run_id = ? AND run_image_id = ?",
        (run_id, run_image_id),
    )

    if not polygons:
        return

    rows = []
    for polygon in polygons:
        bbox = polygon.get("bbox") or []
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue

        class_name = polygon.get("class")
        if class_name not in {"live", "dead"}:
            continue

        rows.append(
            (
                run_id,
                run_image_id,
                float(polygon.get("confidence", 0.0)),
                class_name,
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
                0,
            )
        )

    if rows:
        await db.executemany(
            """
            INSERT INTO detection (
                run_id, run_image_id, confidence, class,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2, manually_edited
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


async def process_run(run_id: int, db_factory):
    """
    Process one run sequentially.
    """
    async with db_factory() as db:
        run = await get_run(db, run_id)
        if not run:
            return

        # Only process runs that have remaining unprocessed images.
        if int(run["processed_count"] or 0) >= int(run["total_images"] or 0):
            return

        cursor = await db.execute(
            """
            SELECT
                run_image_id,
                stored_path,
                live_mussel_count,
                dead_mussel_count,
                processed_at,
                error_msg
            FROM run_image
            WHERE run_id = ? AND processed_at IS NULL
            ORDER BY run_image_id ASC
            """,
            (run_id,),
        )
        images = await cursor.fetchall()
        if not images:
            return

        try:
            model_device = await asyncio.to_thread(
                load_model,
                run["weights_path"],
                run["model_type"],
            )
        except Exception as exc:
            await db.execute(
                "UPDATE run SET error_msg = ? WHERE run_id = ?",
                (f"Failed to load model: {exc}", run_id),
            )
            await db.commit()
            return

        run = await get_run(db, run_id)
        threshold = float(run["threshold"])
        model_type = run["model_type"]

        processed_count = int(run["processed_count"] or 0)
        had_error = bool(run["error_msg"])

        for image in images:
            run_image_id = image["run_image_id"]
            image_path = image["stored_path"]
            processed_at = _now()

            if not Path(image_path).exists():
                had_error = True
                processed_count += 1
                await db.execute(
                    """
                    UPDATE run_image
                    SET live_mussel_count = 0,
                        dead_mussel_count = 0,
                        processed_at = ?,
                        error_msg = ?
                    WHERE run_image_id = ?
                    """,
                    (processed_at, f"File not found: {image_path}", run_image_id),
                )
                await db.execute(
                    "UPDATE run SET processed_count = ? WHERE run_id = ?",
                    (processed_count, run_id),
                )
                await db.commit()
                continue

            try:
                inference = await asyncio.to_thread(
                    run_inference_on_image,
                    model_device,
                    image_path,
                    model_type,
                )
                polygons = inference.get("polygons", [])
                await _replace_detections(db, run_id, run_image_id, polygons)
                live_count, dead_count = await get_counts_for_run_image(
                    db,
                    run_id,
                    run_image_id,
                    threshold,
                )
                processed_count += 1
                await db.execute(
                    """
                    UPDATE run_image
                    SET live_mussel_count = ?,
                        dead_mussel_count = ?,
                        processed_at = ?,
                        error_msg = NULL
                    WHERE run_image_id = ?
                    """,
                    (live_count, dead_count, processed_at, run_image_id),
                )
                await db.execute(
                    "UPDATE run SET processed_count = ? WHERE run_id = ?",
                    (processed_count, run_id),
                )
                await db.commit()
            except Exception as exc:
                had_error = True
                processed_count += 1
                await db.execute(
                    """
                    UPDATE run_image
                    SET live_mussel_count = 0,
                        dead_mussel_count = 0,
                        processed_at = ?,
                        error_msg = ?
                    WHERE run_image_id = ?
                    """,
                    (processed_at, f"Inference error: {exc}", run_image_id),
                )
                await db.execute(
                    "UPDATE run SET processed_count = ? WHERE run_id = ?",
                    (processed_count, run_id),
                )
                await db.commit()

        cursor = await db.execute(
            "SELECT SUM(live_mussel_count) FROM run_image WHERE run_id = ?",
            (run_id,),
        )
        row = await cursor.fetchone()
        total_live = int((row[0] or 0) if row else 0)

        await db.execute(
            "UPDATE run SET live_mussel_count = ?, error_msg = ? WHERE run_id = ?",
            (
                total_live,
                "One or more images failed during processing" if had_error else None,
                run_id,
            ),
        )
        await db.commit()


async def recalculate_run_threshold(db: aiosqlite.Connection, run_id: int, threshold: float):
    run = await get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if threshold < 0.0 or threshold > 1.0:
        raise HTTPException(status_code=400, detail="Threshold must be between 0.0 and 1.0")

    rows = await get_counts_by_run_image_for_run(db, run_id, threshold)
    count_map = {run_image_id: (live, dead) for run_image_id, live, dead in rows}

    images = await list_run_images(db, run_id)
    now = _now()

    payload_images = []
    total_live = 0
    total_dead = 0

    for image in images:
        run_image_id = image["run_image_id"]
        live_count, dead_count = count_map.get(run_image_id, (0, 0))
        total_live += live_count
        total_dead += dead_count
        await db.execute(
            """
            UPDATE run_image
            SET live_mussel_count = ?,
                dead_mussel_count = ?,
                processed_at = COALESCE(processed_at, ?)
            WHERE run_image_id = ?
            """,
            (live_count, dead_count, now, run_image_id),
        )

        payload_images.append(
            {
                "run_image_id": run_image_id,
                "live_count": live_count,
                "dead_count": dead_count,
                "error_msg": image["error_msg"],
            }
        )

    await db.execute(
        "UPDATE run SET threshold = ?, live_mussel_count = ? WHERE run_id = ?",
        (threshold, total_live, run_id),
    )
    await db.commit()

    return {
        "run_id": run_id,
        "threshold": threshold,
        "live_mussel_count": total_live,
        "dead_mussel_count": total_dead,
        "image_count": len(images),
        "images": payload_images,
    }


async def get_run_image_detail(db: aiosqlite.Connection, run_id: int, run_image_id: int):
    cursor = await db.execute(
        """
        SELECT
            r.run_id,
            r.threshold,
            r.total_images,
            r.processed_count,
            r.error_msg AS run_error,
            r.model_id,
            m.name AS model_name,
            m.type AS model_type,
            ri.run_image_id,
            ri.stored_path,
            ri.live_mussel_count,
            ri.dead_mussel_count,
            ri.processed_at,
            ri.error_msg
        FROM run r
        JOIN model m ON m.model_id = r.model_id
        JOIN run_image ri ON ri.run_id = r.run_id
        WHERE r.run_id = ? AND ri.run_image_id = ?
        """,
        (run_id, run_image_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run image not found")

    det_cursor = await db.execute(
        """
        SELECT detection_id, class, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2, manually_edited
        FROM detection
        WHERE run_id = ? AND run_image_id = ?
        ORDER BY detection_id ASC
        """,
        (run_id, run_image_id),
    )
    detections = await det_cursor.fetchall()

    polygons = [
        {
            "detection_id": det["detection_id"],
            "class": det["class"],
            "confidence": float(det["confidence"]),
            "bbox": [
                float(det["bbox_x1"]),
                float(det["bbox_y1"]),
                float(det["bbox_x2"]),
                float(det["bbox_y2"]),
            ],
            "manually_edited": bool(det["manually_edited"]),
        }
        for det in detections
    ]

    run_state = derive_run_state(row)

    return {
        "run_id": row["run_id"],
        "run_image_id": row["run_image_id"],
        "model_id": row["model_id"],
        "model_name": row["model_name"],
        "model_type": row["model_type"],
        "threshold": row["threshold"],
        "filename": Path(row["stored_path"]).name,
        "stored_path": row["stored_path"],
        "live_mussel_count": row["live_mussel_count"] or 0,
        "dead_mussel_count": row["dead_mussel_count"] or 0,
        "total_mussel_count": (row["live_mussel_count"] or 0) + (row["dead_mussel_count"] or 0),
        "processed_at": row["processed_at"],
        "error_msg": row["error_msg"],
        "polygons": polygons,
        "can_edit": run_state == "completed",
    }


async def update_detection_classification(
    db: aiosqlite.Connection,
    run_id: int,
    run_image_id: int,
    detection_id: int,
    new_class: str,
):
    run = await get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if derive_run_state(run) != "completed":
        raise HTTPException(status_code=409, detail="Edits are only allowed for completed runs")

    cursor = await db.execute(
        """
        SELECT detection_id FROM detection
        WHERE detection_id = ? AND run_id = ? AND run_image_id = ?
        """,
        (detection_id, run_id, run_image_id),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Detection not found")

    await db.execute(
        "UPDATE detection SET class = ?, manually_edited = 1 WHERE detection_id = ?",
        (new_class, detection_id),
    )

    live_count, dead_count = await get_counts_for_run_image(
        db,
        run_id,
        run_image_id,
        float(run["threshold"]),
    )

    await db.execute(
        "UPDATE run_image SET live_mussel_count = ?, dead_mussel_count = ? WHERE run_image_id = ?",
        (live_count, dead_count, run_image_id),
    )

    cursor = await db.execute(
        "SELECT SUM(live_mussel_count) FROM run_image WHERE run_id = ?",
        (run_id,),
    )
    row = await cursor.fetchone()
    total_live = int((row[0] or 0) if row else 0)

    await db.execute(
        "UPDATE run SET live_mussel_count = ? WHERE run_id = ?",
        (total_live, run_id),
    )
    await db.commit()

    return {
        "detection_id": detection_id,
        "new_class": new_class,
        "run_image_id": run_image_id,
        "live_mussel_count": live_count,
        "dead_mussel_count": dead_count,
        "run_live_mussel_count": total_live,
    }


async def delete_run(db: aiosqlite.Connection, run_id: int):
    run = await get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if derive_run_state(run) in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="Cannot delete an in-progress run")

    cursor = await db.execute("SELECT stored_path FROM run_image WHERE run_id = ?", (run_id,))
    image_rows = await cursor.fetchall()
    file_paths = [row["stored_path"] for row in image_rows]

    await db.execute("DELETE FROM run WHERE run_id = ?", (run_id,))
    await db.commit()

    for path in file_paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass

    run_dir = UPLOAD_DIR / f"run_{run_id}"
    shutil.rmtree(run_dir, ignore_errors=True)
