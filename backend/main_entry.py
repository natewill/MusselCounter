"""
Entry point for PyInstaller build.
Starts uvicorn programmatically instead of via CLI.
"""
import os
import sys
import uvicorn


def main():
    # Get configuration from environment or use defaults
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('BACKEND_PORT', '8000'))

    # Import the FastAPI app
    from main import app

    # Run uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
