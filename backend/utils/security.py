"""
Security utilities for input validation and sanitization.
"""
from pathlib import Path
from fastapi import HTTPException
from pathvalidate import sanitize_filename as _sanitize_filename, ValidationError


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename - remove path components and dangerous chars.
    
    Uses pathvalidate library to safely sanitize filenames according to
    platform-specific rules (Windows, Linux, macOS).
    
    Args:
        filename: Original filename (may contain path components)
        
    Returns:
        Sanitized filename safe for use in file system
        
    Raises:
        HTTPException: If filename is empty or cannot be sanitized
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")
    
    try:
        # Extract just the filename (remove any path components)
        filename_only = Path(filename).name
        # Use pathvalidate to sanitize according to platform rules
        sanitized = _sanitize_filename(filename_only, platform="auto")
        
        if not sanitized:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        return sanitized
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid filename: {str(e)}")
