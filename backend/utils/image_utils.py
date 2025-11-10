import hashlib
from pathlib import Path
from datetime import datetime
import aiosqlite

# We use a MD5 hash to make sure we don't add the same image twice 
# The MD5 hash is a string that is unique to the file content.
def get_file_hash(file_path: str) -> str:
    """
    Generate MD5 hash of file content for deduplication.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        MD5 hash as hexadecimal string
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    return hashlib.md5(file_data).hexdigest()


async def find_image_by_hash(db: aiosqlite.Connection, file_hash: str):
    """
    Check if an image with this hash already exists in database (globally).
    
    Args:
        db: Database connection
        file_hash: MD5 hash to search for
        
    Returns:
        Row with image data if found, None otherwise
    """
    cursor = await db.execute(
        """SELECT image_id, stored_path, 
                  live_mussel_count, dead_mussel_count, stored_polygon_path 
           FROM image 
           WHERE file_hash = ? 
           LIMIT 1""",
        (file_hash,)
    )
    return await cursor.fetchone()


async def add_image_to_batch(
    db: aiosqlite.Connection,
    batch_id: int,
    image_path: str,
    filename: str = None
) -> int:
    """
    Add an image to a batch with hash-based deduplication.
    
    Args:
        db: Database connection
        batch_id: Batch ID to add image to
        image_path: Path to the image file
        filename: Optional filename (defaults to image_path.name)
        
    Returns:
        Image ID (new or existing)
            
    Raises:
        FileNotFoundError: If image file doesn't exist
    """
    # Validate file exists
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Generate hash
    file_hash = get_file_hash(str(image_path))
    
    # Check if image with this hash exists globally (anywhere)
    existing_image = await find_image_by_hash(db, file_hash)
    
    if existing_image:
        image_id = existing_image['image_id']
        
        # Check if this image is already linked to this batch
        cursor = await db.execute(
            "SELECT * FROM batch_image WHERE batch_id = ? AND image_id = ?",
            (batch_id, image_id)
        )
        already_linked = await cursor.fetchone()
        
        if already_linked:
            # Image already in this batch
            return image_id
        
        # Image exists globally but not in this batch - link it
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO batch_image (batch_id, image_id, added_at) VALUES (?, ?, ?)",
            (batch_id, image_id, now)
        )
        await db.commit()
        
        return image_id
    
    # New image - create it and link to batch
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """INSERT INTO image 
           (filename, stored_path, file_hash, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            filename or image_path.name,
            str(image_path),
            file_hash,
            now,
            now
        )
    )
    image_id = cursor.lastrowid
    
    # Link image to batch
    await db.execute(
        "INSERT INTO batch_image (batch_id, image_id, added_at) VALUES (?, ?, ?)",
        (batch_id, image_id, now)
    )
    await db.commit()
    
    return image_id


async def add_multiple_images(
    db: aiosqlite.Connection,
    batch_id: int,
    image_paths: list[str]
) -> list[int]:
    """
    Add multiple images to a batch.
    
    Args:
        db: Database connection
        batch_id: Batch ID to add images to
        image_paths: List of image file paths
        
    Returns:
        List of image IDs (new and duplicates)
    """
    image_ids = []
    
    for image_path in image_paths:
        image_id = await add_image_to_batch(db, batch_id, image_path)
        image_ids.append(image_id)
    
    return image_ids


async def validate_image_path(image_path: str) -> tuple[bool, str]:
    """
    Validate that an image file exists and is accessible.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Tuple of (is_valid, error_message)
        is_valid is True if file exists, False otherwise
        error_message is empty if valid, contains error if not
    """
    path = Path(image_path)
    
    if not path.exists():
        return False, f"File not found: {image_path}"
    
    if not path.is_file():
        return False, f"Path is not a file: {image_path}"
    
    # Check if it's readable
    try:
        with open(path, 'rb') as f:
            f.read(1)  # Try to read at least 1 byte
    except PermissionError:
        return False, f"Permission denied: {image_path}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"
    
    return True, ""

