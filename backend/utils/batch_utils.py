from datetime import datetime
import aiosqlite


async def create_batch(
    db: aiosqlite.Connection,
    name: str = None,
    description: str = None
) -> int:
    """
    Create a new batch.
    
    Args:
        db: Database connection
        name: Optional batch name
        description: Optional batch description
        
    Returns:
        Batch ID of the created batch
    """
    now = datetime.now().isoformat()
    
    cursor = await db.execute(
        """INSERT INTO batch (name, description, created_at, updated_at)
           VALUES (?, ?, ?, ?)""",
        (name, description, now, now)
    )
    batch_id = cursor.lastrowid
    await db.commit()
    
    return batch_id


async def get_batch(db: aiosqlite.Connection, batch_id: int):
    """
    Get batch information.
    
    Args:
        db: Database connection
        batch_id: Batch ID
        
    Returns:
        Row with batch data, or None if not found
    """
    cursor = await db.execute(
        "SELECT * FROM batch WHERE batch_id = ?",
        (batch_id,)
    )
    return await cursor.fetchone()


async def get_all_batches(db: aiosqlite.Connection):
    """
    Get all batches.
    
    Args:
        db: Database connection
        
    Returns:
        List of batch rows
    """
    cursor = await db.execute(
        "SELECT * FROM batch ORDER BY created_at DESC"
    )
    return await cursor.fetchall()


async def get_batch_images(db: aiosqlite.Connection, batch_id: int):
    """
    Get all images in a batch.
    
    Args:
        db: Database connection
        batch_id: Batch ID
        
    Returns:
        List of image rows for this batch
    """
    cursor = await db.execute(
        """SELECT i.* FROM image i
           INNER JOIN batch_image bi ON i.image_id = bi.image_id
           WHERE bi.batch_id = ?
           ORDER BY bi.added_at ASC""",
        (batch_id,)
    )
    return await cursor.fetchall()


async def get_latest_run(db: aiosqlite.Connection, batch_id: int):
    """
    Get the latest run for a batch (highest run_id = newest).
    
    Args:
        db: Database connection
        batch_id: Batch ID
        
    Returns:
        Row with latest run data, or None if no runs exist
    """
    cursor = await db.execute(
        "SELECT * FROM run WHERE batch_id = ? ORDER BY run_id DESC LIMIT 1",
        (batch_id,)
    )
    return await cursor.fetchone()


async def get_all_runs(db: aiosqlite.Connection, batch_id: int):
    """
    Get all runs for a batch (for history).
    
    Args:
        db: Database connection
        batch_id: Batch ID
        
    Returns:
        List of run rows, ordered by newest first
    """
    cursor = await db.execute(
        "SELECT * FROM run WHERE batch_id = ? ORDER BY run_id DESC",
        (batch_id,)
    )
    return await cursor.fetchall()


async def update_batch(
    db: aiosqlite.Connection,
    batch_id: int,
    name: str = None,
    description: str = None
):
    """
    Update batch information.
    
    Args:
        db: Database connection
        batch_id: Batch ID
        name: Optional new name
        description: Optional new description
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
        values.append(batch_id)
        
        await db.execute(
            f"UPDATE batch SET {', '.join(updates)} WHERE batch_id = ?",
            values
        )
        await db.commit()

