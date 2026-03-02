"""
Collection utility functions for managing collections and their images.
Handles collection retrieval, image retrieval with results, and collection operations.
"""
from collections import defaultdict
import aiosqlite


async def get_collection(db: aiosqlite.Connection, collection_id: int):
    """
    Get collection information.
    
    Args:
        db: Database connection
        collection_id: Collection ID
        
    Returns:
        Row with collection data, or None if not found
    """
    cursor = await db.execute(
        """
        SELECT
            c.collection_id,
            c.name,
            c.description,
            c.created_at,
            (
                SELECT COUNT(*)
                FROM collection_image ci
                WHERE ci.collection_id = c.collection_id
            ) AS image_count,
            COALESCE((
                SELECT r.live_mussel_count
                FROM run r
                WHERE r.collection_id = c.collection_id
                ORDER BY r.run_id DESC
                LIMIT 1
            ), 0) AS live_mussel_count
        FROM collection c
        WHERE c.collection_id = ?
        """,
        (collection_id,),
    )
    return await cursor.fetchone()


async def get_all_collections(db: aiosqlite.Connection):
    """
    Get all collections, ordered by creation date (newest first).
    
    Args:
        db: Database connection
        
    Returns:
        List of collection rows
    """
    cursor = await db.execute(
        """
        SELECT
            c.collection_id,
            c.name,
            c.description,
            c.created_at,
            (
                SELECT COUNT(*)
                FROM collection_image ci
                WHERE ci.collection_id = c.collection_id
            ) AS image_count,
            COALESCE((
                SELECT r.live_mussel_count
                FROM run r
                WHERE r.collection_id = c.collection_id
                ORDER BY r.run_id DESC
                LIMIT 1
            ), 0) AS live_mussel_count,
            (
                SELECT i.stored_path
                FROM collection_image ci
                JOIN image i ON i.image_id = ci.image_id
                WHERE ci.collection_id = c.collection_id
                ORDER BY ci.added_at ASC
                LIMIT 1
            ) AS first_image_path,
            (
                SELECT r.status
                FROM run r
                WHERE r.collection_id = c.collection_id
                ORDER BY r.run_id DESC
                LIMIT 1
            ) AS latest_run_status,
            (
                SELECT COUNT(*)
                FROM run r
                WHERE r.collection_id = c.collection_id
            ) AS run_count
        FROM collection c
        ORDER BY c.created_at DESC
        """
    )
    return await cursor.fetchall()


async def _attach_processed_models(db: aiosqlite.Connection, rows, collection_id: int):
    """
    Helper function to add processed_model_ids to a list of images.
    For each image, finds all model IDs that have successfully processed it
    in runs belonging to the specified collection.
    
    Args:
        db: Database connection
        rows: List of image rows (dict-like objects)
        collection_id: Collection ID to filter runs by
        
    Returns:
        List of images with processed_model_ids added
    """
    if not rows:
        return []
    image_ids = [row['image_id'] for row in rows]
    placeholders = ','.join(['?'] * len(image_ids))
    cursor = await db.execute(
        f"""SELECT DISTINCT ir.image_id, r.model_id
               FROM image_result ir
               JOIN run r ON ir.run_id = r.run_id
               WHERE r.status = 'completed'
                 AND r.collection_id = ?
                 AND ir.image_id IN ({placeholders})""",
        (collection_id, *image_ids)
    )
    model_map = defaultdict(list)
    for row in await cursor.fetchall():
        model_map[row['image_id']].append(row['model_id'])
    return [dict(row, processed_model_ids=model_map.get(row['image_id'], [])) for row in rows]


async def get_collection_images(db: aiosqlite.Connection, collection_id: int):
    """
    Get all images in a collection, ordered by when they were added (newest first).
    
    Args:
        db: Database connection
        collection_id: Collection ID
        
    Returns:
        List of image rows with processed_model_ids added
    """
    cursor = await db.execute(
        """SELECT i.*, ci.added_at
               FROM image i
               JOIN collection_image ci ON i.image_id = ci.image_id
               WHERE ci.collection_id = ?
               ORDER BY ci.added_at DESC""",
        (collection_id,)
    )
    images = await cursor.fetchall()
    return await _attach_processed_models(db, images, collection_id)


async def get_collection_images_with_results(
    db: aiosqlite.Connection,
    collection_id: int,
    run_id: int | None,
    current_threshold: float | None = None
):
    """
    Return images in a collection with their inference results.
    
    If run_id is provided, results are scoped strictly to that run to avoid mixing
    data from other runs. If run_id is None, falls back to selecting the latest
    run per image (optionally filtered by threshold) for backwards compatibility.
    """
    # 1) Base images in collection.
    base_cursor = await db.execute(
        """
        SELECT
            i.image_id,
            i.filename,
            i.stored_path,
            i.file_hash,
            i.created_at,
            ci.added_at
        FROM image i
        JOIN collection_image ci ON i.image_id = ci.image_id
        WHERE ci.collection_id = ?
        ORDER BY ci.added_at DESC
        """,
        (collection_id,),
    )
    base_images = await base_cursor.fetchall()
    if not base_images:
        return await _attach_processed_models(db, [], collection_id)

    image_ids = [row["image_id"] for row in base_images]
    placeholders = ",".join(["?"] * len(image_ids))

    # Defaults for LEFT JOIN-like behavior.
    result_by_image = {
        image_id: {
            "live_mussel_count": None,
            "dead_mussel_count": None,
            "processed_at": None,
            "error_msg": None,
            "result_threshold": None,
        }
        for image_id in image_ids
    }

    if run_id is not None:
        # 2a) Results for an explicit run.
        run_cursor = await db.execute(
            "SELECT threshold FROM run WHERE run_id = ?",
            (run_id,),
        )
        run_row = await run_cursor.fetchone()
        run_threshold = run_row["threshold"] if run_row else None

        result_cursor = await db.execute(
            f"""
            SELECT image_id, live_mussel_count, dead_mussel_count, processed_at, error_msg
            FROM image_result
            WHERE run_id = ? AND image_id IN ({placeholders})
            """,
            (run_id, *image_ids),
        )
        for row in await result_cursor.fetchall():
            result_by_image[row["image_id"]] = {
                "live_mussel_count": row["live_mussel_count"],
                "dead_mussel_count": row["dead_mussel_count"],
                "processed_at": row["processed_at"],
                "error_msg": row["error_msg"],
                "result_threshold": run_threshold,
            }
    else:
        # 2b) Latest run per image (optionally threshold-filtered), then fetch those results.
        latest_cursor = await db.execute(
            f"""
            SELECT ir.image_id, MAX(ir.run_id) AS run_id
            FROM image_result ir
            JOIN run r ON r.run_id = ir.run_id
            WHERE r.collection_id = ?
              AND (? IS NULL OR ABS(r.threshold - ?) < 0.001)
              AND ir.image_id IN ({placeholders})
            GROUP BY ir.image_id
            """,
            (collection_id, current_threshold, current_threshold, *image_ids),
        )
        latest_rows = await latest_cursor.fetchall()

        if latest_rows:
            latest_run_by_image = {row["image_id"]: row["run_id"] for row in latest_rows}
            run_ids = sorted({row["run_id"] for row in latest_rows})
            run_placeholders = ",".join(["?"] * len(run_ids))

            threshold_cursor = await db.execute(
                f"SELECT run_id, threshold FROM run WHERE run_id IN ({run_placeholders})",
                run_ids,
            )
            threshold_by_run = {row["run_id"]: row["threshold"] for row in await threshold_cursor.fetchall()}

            result_cursor = await db.execute(
                f"""
                SELECT image_id, run_id, live_mussel_count, dead_mussel_count, processed_at, error_msg
                FROM image_result
                WHERE run_id IN ({run_placeholders}) AND image_id IN ({placeholders})
                """,
                (*run_ids, *image_ids),
            )
            for row in await result_cursor.fetchall():
                image_id = row["image_id"]
                if latest_run_by_image.get(image_id) != row["run_id"]:
                    continue
                result_by_image[image_id] = {
                    "live_mussel_count": row["live_mussel_count"],
                    "dead_mussel_count": row["dead_mussel_count"],
                    "processed_at": row["processed_at"],
                    "error_msg": row["error_msg"],
                    "result_threshold": threshold_by_run.get(row["run_id"]),
                }

    # 3) Merge base image metadata with result payload.
    merged_images = []
    for row in base_images:
        image_dict = dict(row)
        image_dict.update(result_by_image[row["image_id"]])
        merged_images.append(image_dict)

    # Preserve previous ordering semantics:
    # newest add first, then newest processed_at (NULLs treated as very old).
    merged_images.sort(
        key=lambda r: (
            r["added_at"],
            r["processed_at"] or "1970-01-01T00:00:00Z",
        ),
        reverse=True,
    )

    return await _attach_processed_models(db, merged_images, collection_id)


async def remove_image_from_collection(
    db: aiosqlite.Connection,
    collection_id: int,
    image_id: int
) -> bool:
    """
    Remove an image from a collection (does not delete the image itself).

    Args:
        db: Database connection
        collection_id: Collection ID
        image_id: Image ID to remove

    Returns:
        True if image was removed, False if it wasn't in the collection
    """
    cursor = await db.execute(
        "DELETE FROM collection_image WHERE collection_id = ? AND image_id = ?",
        (collection_id, image_id)
    )

    await db.commit()
    return cursor.rowcount > 0


async def get_latest_run(db: aiosqlite.Connection, collection_id: int):
    """
    Get the most recent run for a collection.
    
    Args:
        db: Database connection
        collection_id: Collection ID
        
    Returns:
        Row with run data, or None if no runs exist
    """
    cursor = await db.execute(
        "SELECT * FROM run WHERE collection_id = ? ORDER BY run_id DESC LIMIT 1",
        (collection_id,)
    )
    return await cursor.fetchone()


async def get_latest_run_by_model(db: aiosqlite.Connection, collection_id: int, model_id: int):
    """
    Get the most recent run for a collection with a specific model.
    
    Args:
        db: Database connection
        collection_id: Collection ID
        model_id: Model ID to filter by
        
    Returns:
        Row with run data, or None if no runs exist for that model
    """
    cursor = await db.execute(
        "SELECT * FROM run WHERE collection_id = ? AND model_id = ? ORDER BY run_id DESC LIMIT 1",
        (collection_id, model_id)
    )
    return await cursor.fetchone()


async def get_all_runs(db: aiosqlite.Connection, collection_id: int):
    """
    Get all runs for a collection, ordered by run_id (newest first).
    
    Args:
        db: Database connection
        collection_id: Collection ID
        
    Returns:
        List of run rows
    """
    cursor = await db.execute(
        "SELECT * FROM run WHERE collection_id = ? ORDER BY run_id DESC",
        (collection_id,)
    )
    return await cursor.fetchall()
