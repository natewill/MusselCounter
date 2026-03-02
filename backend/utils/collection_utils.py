"""
Collection utility functions for managing collections and their images.
Handles collection retrieval, image retrieval with results, and collection operations.
"""
from collections import defaultdict
import aiosqlite


async def _get_base_collection_images(db: aiosqlite.Connection, collection_id: int):
    """
    Fetch base image rows for a collection in newest-added order.
    """
    cursor = await db.execute(
        """SELECT i.*, ci.added_at
               FROM image i
               JOIN collection_image ci ON i.image_id = ci.image_id
               WHERE ci.collection_id = ?
               ORDER BY ci.added_at DESC""",
        (collection_id,),
    )
    return await cursor.fetchall()


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
                  AND r.status IN ('completed', 'completed_with_errors')
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
                  AND r.status IN ('completed', 'completed_with_errors')
                ORDER BY r.run_id DESC
                LIMIT 1
            ), 0) AS live_mussel_count,
            (
                SELECT i.stored_path
                FROM collection_image ci
                JOIN image i ON i.image_id = ci.image_id
                WHERE ci.collection_id = c.collection_id
                ORDER BY ci.added_at DESC
                LIMIT 1
            ) AS first_image_path,
            (
                SELECT r.status
                FROM run r
                WHERE r.collection_id = c.collection_id
                  AND r.status IN ('completed', 'completed_with_errors')
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
    For each image, finds all model IDs that have a successful terminal run
    in this collection ('completed' or 'completed_with_errors').
    
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
               WHERE r.status IN ('completed', 'completed_with_errors')
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
    images = await _get_base_collection_images(db, collection_id)
    return await _attach_processed_models(db, images, collection_id)


async def get_collection_images_with_results(
    db: aiosqlite.Connection,
    collection_id: int,
    run_id: int,
):
    """
    Return images in a collection with their inference results.

    Results are scoped strictly to the provided run_id.
    """
    # 1) Base images in collection.
    base_images = await _get_base_collection_images(db, collection_id)
    if not base_images:
        return []

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


async def get_latest_run(
    db: aiosqlite.Connection,
    collection_id: int,
    model_id: int | None = None,
):
    """
    Get the most recent run for a collection, optionally filtered by model_id.
    """
    if model_id is None:
        cursor = await db.execute(
            "SELECT * FROM run WHERE collection_id = ? ORDER BY run_id DESC LIMIT 1",
            (collection_id,),
        )
        return await cursor.fetchone()

    cursor = await db.execute(
        "SELECT * FROM run WHERE collection_id = ? AND model_id = ? ORDER BY run_id DESC LIMIT 1",
        (collection_id, model_id),
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
