"""
Main FastAPI application entry point.

This module sets up the FastAPI application with:
- Database initialization on startup
- CORS middleware for frontend communication
- Exception handlers for error responses
- API routers for different endpoints (collections, models, runs, system)

The application uses SQLite for data storage and processes images through ML models
(R-CNN or YOLO) to count live and dead mussels in images.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from db import init_db
from config import CORS_ORIGINS, UPLOAD_DIR
from api.routers import collections, models, runs, system, images
from api.error_handlers import (
    validation_exception_handler,
    general_exception_handler
)
from fastapi.exceptions import RequestValidationError
from utils.logger import logger
from utils.resource_detector import pick_threads


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown tasks.
    
    On startup:
    - Initializes the SQLite database and creates all tables from schema.sql
    - Optimizes CPU threading for PyTorch operations
    
    On shutdown:
    - Currently no cleanup needed (SQLite handles connection closing automatically)
    """
    # Startup: Initialize database schema and tables
    logger.info("Starting Mussel Counter backend...")
    
    # Optimize CPU threading for PyTorch (only affects CPU mode, not GPU/MPS)
    threads = pick_threads()
    if threads:
        logger.info(f"Optimized PyTorch CPU threading: {threads} threads")
    
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown: (nothing needed for now - SQLite connections close automatically)
    logger.info("Shutting down Mussel Counter backend...")


# Create FastAPI app instance
# This is the main application object that handles all HTTP requests
app = FastAPI(
    title="Mussel Counter API",
    description="Backend API for mussel counting application",
    version="1.0.0",
    lifespan=lifespan  # Register lifespan manager for startup/shutdown
)

# Add CORS middleware to allow frontend (running on different port) to make requests
# Without this, browser would block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # List of allowed frontend URLs
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all request headers
)

# Register exception handlers for consistent error responses
# These catch exceptions and return JSON error responses instead of crashing
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # Invalid request data
app.add_exception_handler(Exception, general_exception_handler)  # All other unexpected errors

# Include API routers - each router handles a group of related endpoints
# Routers are organized by resource type (collections, models, runs, system)
app.include_router(system.router)  # Health check, DB version
app.include_router(collections.router)  # Collection management and image uploads
app.include_router(models.router)  # Model information
app.include_router(runs.router)  # Inference run management
app.include_router(images.router)  # Image detail and results

# Mount static files to serve uploaded images
# This allows frontend to access images via /uploads/{filename}
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

logger.info("FastAPI application initialized")
