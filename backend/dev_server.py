"""Developer entry point for running the FastAPI app with safe reload settings."""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn

_BACKEND_DIR = Path(__file__).parent.resolve()
_VENV_DIR = _BACKEND_DIR / "venv"


def main() -> None:
    """Run uvicorn with reload, excluding the local virtualenv and site-packages."""
    host = os.getenv("UVICORN_HOST", "127.0.0.1")
    port = int(os.getenv("UVICORN_PORT", "8000"))

    reload_excludes = [
        "venv/*",
        "venv/**",
        "**/site-packages/**",
        "**/__pycache__/**",
    ]

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[str(_BACKEND_DIR)],
        reload_excludes=reload_excludes,
        log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
