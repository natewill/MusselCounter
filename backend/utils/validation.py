"""
Validation utilities for the backend
"""
from typing import Union
from fastapi import HTTPException
from config import DEFAULT_THRESHOLD


def validate_threshold(threshold: Union[int, float, None]) -> float:
    """
    Validate threshold value (0.0 to 1.0)
    
    Args:
        threshold: Threshold value to validate
        
    Returns:
        Validated threshold as float
        
    Raises:
        HTTPException: If threshold is invalid
    """
    if threshold is None:
        return DEFAULT_THRESHOLD
    
    threshold_float = float(threshold)
    
    if threshold_float < 0.0 or threshold_float > 1.0:
        raise HTTPException(
            status_code=400,
            detail="Threshold must be a number between 0.0 and 1.0"
        )
    
    return threshold_float


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

