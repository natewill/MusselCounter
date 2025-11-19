"""
Collection utility functions for managing collections and their images.
Handles collection creation, image retrieval with results, and collection operations.
"""
from collections import defaultdict
from datetime import datetime
import aiosqlite


async def create_collection(
    db: aiosqlite.Connection,
    name: str = None,
    description: str = None
) -> int:
    """
    Create a new collection.
    
    Args:
        db: Database connection
        name: Optional collection name
        description: Optional collection description
        
    Returns:
        Collection ID of the created collection
    """
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """INSERT INTO collection (name, description, created_at, updated_at)
           VALUES (?, ?, ?, ?)""",
        (name, description, now, now)
    )
    await db.commit()

    print(name, description, now)
    return cursor.lastrowid


async def get_collection(db: aiosqlite.Connection, collection_id: int):
    """
    Get collection information.
    
    Args:
        db: Database connection
        collection_id: Collection ID
        
    Returns:
        Row with collection data, or None if not found
    """
    cursor = await db.execute("SELECT * FROM collection WHERE collection_id = ?", (collection_id,))
    return await cursor.fetchone()


async def get_all_collections(db: aiosqlite.Connection):
    """
    Get all collections, ordered by creation date (newest first).
    
    Args:
        db: Database connection
        
    Returns:
        List of collection rows
    """
    cursor = await db.execute("SELECT * FROM collection ORDER BY created_at DESC")
    return await cursor.fetchall()


async def _attach_processed_models(db: aiosqlite.Connection, rows):
    """
    Helper function to add processed_model_ids to a list of images.
    For each image, finds all model IDs that have successfully processed it.
    
    Args:
        db: Database connection
        rows: List of image rows (dict-like objects)
        
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
                 AND ir.image_id IN ({placeholders})""",
        image_ids
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
        """SELECT i.*, ci.added_at, ci.is_duplicate
               FROM image i
               JOIN collection_image ci ON i.image_id = ci.image_id
               WHERE ci.collection_id = ?
               ORDER BY ci.added_at DESC""",
        (collection_id,)
    )
    images = await cursor.fetchall()
    return await _attach_processed_models(db, images)


async def get_collection_images_with_results(
    db: aiosqlite.Connection,
    collection_id: int,
    run_id: int,
    current_threshold: float = None
):
    """
    Return images in a collection with their latest result (optionally constrained by threshold).
    Latest is chosen by max(run.run_id) per image.
    """
    sql = """
    WITH latest_key AS (
        SELECT ir.image_id, MAX(r.run_id) AS max_run_id
        FROM image_result ir
        JOIN run r ON ir.run_id = r.run_id
        WHERE r.collection_id = ?
          AND (? IS NULL OR ABS(r.threshold - ?) < 0.001)
        GROUP BY ir.image_id
    )
    SELECT
        i.image_id,
        i.filename,
        i.stored_path,
        i.file_hash,
        i.width,
        i.height,
        i.created_at,
        i.updated_at,
        ci.added_at,
        ci.is_duplicate,
        l.live_mussel_count,
        l.dead_mussel_count,
        l.polygon_path,
        l.processed_at,
        l.error_msg,
        lr.threshold AS result_threshold
    FROM image i
    JOIN collection_image ci ON i.image_id = ci.image_id
    LEFT JOIN latest_key lk ON lk.image_id = i.image_id
    LEFT JOIN image_result l ON l.image_id = lk.image_id AND l.run_id = lk.max_run_id
    LEFT JOIN run lr ON lr.run_id = lk.max_run_id
    WHERE ci.collection_id = ?
    ORDER BY ci.added_at DESC,
             COALESCE(l.processed_at, '1970-01-01T00:00:00Z') DESC
    """
    cur = await db.execute(sql, (collection_id, current_threshold, current_threshold, collection_id))
    images = await cur.fetchall()
    return await _attach_processed_models(db, images)


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


async def update_collection(
    db: aiosqlite.Connection,
    collection_id: int,
    name: str = None,
    description: str = None
):
    """
    Update collection name and/or description.
    
    Args:
        db: Database connection
        collection_id: Collection ID to update
        name: Optional new name (only updates if provided)
        description: Optional new description (only updates if provided)
    """
    updates = []
    values = []
    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if updates:
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(collection_id)
        query = f"UPDATE collection SET {', '.join(updates)} WHERE collection_id = ?"
        await db.execute(query, values)
        await db.commit()
