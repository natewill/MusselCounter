"""
Error handlers for the API.

These handlers catch exceptions and return consistent JSON error responses.
FastAPI automatically routes exceptions to the appropriate handler based on exception type.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from utils.logger import logger


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation errors (invalid request data).
    
    This is triggered when FastAPI's automatic validation fails (e.g., wrong data types,
    missing required fields, invalid enum values). Returns 422 Unprocessable Entity.
    """
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions (catch-all for any unhandled errors).
    
    This catches any exception that wasn't handled by a more specific handler.
    Logs the full error with stack trace for debugging, but returns a simple
    error message to the client (for security - don't expose internal details).
    """
    # Log full error details with stack trace for debugging
    logger.error(f"Unexpected error: {exc} (path: {request.url.path})", exc_info=True)
    # Return simple error message to client (don't expose internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )

