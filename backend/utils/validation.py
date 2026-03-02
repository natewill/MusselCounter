"""
Validation utilities for the backend
"""
from fastapi import HTTPException


def validate_file_size(file_size: int, max_size: int) -> None:
    """
    Validate file size
    
    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes
        
    Raises:
        HTTPException: If file is too large
    """
    if file_size and file_size > max_size:
        max_size_mb = max_size / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"File is too large. Maximum file size is {max_size_mb}MB."
        )
