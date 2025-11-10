import aiosqlite


async def get_all_models(db: aiosqlite.Connection):
    """
    Get all models.
    
    Args:
        db: Database connection
        
    Returns:
        List of model rows
    """
    cursor = await db.execute(
        "SELECT * FROM model ORDER BY created_at DESC"
    )
    return await cursor.fetchall()


async def get_model(db: aiosqlite.Connection, model_id: int):
    """
    Get model information.
    
    Args:
        db: Database connection
        model_id: Model ID
        
    Returns:
        Row with model data, or None if not found
    """
    cursor = await db.execute(
        "SELECT * FROM model WHERE model_id = ?",
        (model_id,)
    )
    return await cursor.fetchone()

