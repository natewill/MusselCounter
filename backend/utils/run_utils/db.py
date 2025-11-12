"""
Database utilities for run management
"""
import aiosqlite
from datetime import datetime
from typing import Optional


async def get_or_create_run(
    db: aiosqlite.Connection,
    collection_id: int,
    model_id: int,
    threshold: float = 0.5
) -> tuple[int, bool]:
    """
    Get existing run or create new one for this collection+model+threshold combo.
    A run is uniquely identified by (collection_id, model_id, threshold).
    
    Args:
        db: Database connection
        collection_id: Collection ID to run inference on
        model_id: Model ID to use for inference
        threshold: Threshold score for classification (default 0.5)
        
    Returns:
        Tuple of (run_id, was_created) - was_created is True if new run created, False if existing
    """
    # Check if run exists for this configuration
    cursor = await db.execute(
        """SELECT run_id, status FROM run 
           WHERE collection_id = ? AND model_id = ? 
           AND ABS(threshold - ?) < 0.001
           LIMIT 1""",
        (collection_id, model_id, threshold)
    )
    row = await cursor.fetchone()
    
    if row:
        run_id, status = row[0], row[1]
        # Only reset if not currently running (avoid duplicate concurrent processing)
        if status not in ('pending', 'running'):
            await db.execute(
                """UPDATE run SET status = 'pending', started_at = ? 
                   WHERE run_id = ?""",
                (datetime.now().isoformat(), run_id)
            )
            await db.commit()
        return (run_id, False)
    
    # Create new run
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """INSERT INTO run (collection_id, model_id, started_at, status, threshold)
           VALUES (?, ?, ?, ?, ?)""",
        (collection_id, model_id, now, 'pending', threshold)
    )
    run_id = cursor.lastrowid
    await db.commit()
    return (run_id, True)


async def get_run(
    db: aiosqlite.Connection,
    run_id: int
) -> Optional[aiosqlite.Row]:
    """
    Get run record from database.
    
    Args:
        db: Database connection
        run_id: Run ID
        
    Returns:
        Row with run data, or None if not found
    """
    cursor = await db.execute(
        "SELECT * FROM run WHERE run_id = ?",
        (run_id,)
    )
    return await cursor.fetchone()


async def update_run_status(
    db: aiosqlite.Connection,
    run_id: int,
    status: str,
    error_msg: Optional[str] = None
) -> None:
    """
    Update run status and optionally error message.
    
    Args:
        db: Database connection
        run_id: Run ID
        status: New status ('pending', 'running', 'completed', 'failed')
        error_msg: Optional error message
    """
    # Build update query safely (column names are hardcoded, not user input)
    updates = []
    values = []
    
    updates.append("status = ?")
    values.append(status)
    
    if error_msg is not None:
        updates.append("error_msg = ?")
        values.append(error_msg)
    
    # Set finished_at if status is completed or failed
    if status in ('completed', 'failed', 'completed_with_errors'):
        updates.append("finished_at = ?")
        values.append(datetime.now().isoformat())
    
    values.append(run_id)
    
    # Safe: column names are hardcoded, only values are parameterized
    query = f"UPDATE run SET {', '.join(updates)} WHERE run_id = ?"
    await db.execute(query, values)
    await db.commit()

