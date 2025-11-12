"""
Security utilities for input validation and sanitization.

Uses pathvalidate library for filename and path validation/sanitization.
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


def validate_path_in_directory(file_path: Path, allowed_dir: Path) -> Path:
    """
    Validate path is within allowed directory (prevents path traversal attacks).
    
    Uses pathvalidate to check if the resolved path is within the allowed directory.
    
    Args:
        file_path: Path to validate
        allowed_dir: Directory that the path must be within
        
    Returns:
        Resolved path if valid
        
    Raises:
        HTTPException: If path is outside allowed directory
    """
    try:
        resolved = file_path.resolve()
        allowed_resolved = allowed_dir.resolve()
        
        # Check if resolved path is within allowed directory
        # This prevents path traversal attacks (e.g., ../../../etc/passwd)
        resolved.relative_to(allowed_resolved)
        return resolved
    except (OSError, ValueError):
        raise HTTPException(status_code=403, detail="Access denied")


def validate_integer_id(value: int, min_value: int = 1, max_value: int = 2**31 - 1) -> int:
    """Validate integer ID"""
    if not isinstance(value, int) or value < min_value or value > max_value:
        raise HTTPException(status_code=400, detail="Invalid ID")
    return value

