"""
Pytest configuration and shared fixtures
"""
import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests"""
    return tmp_path


@pytest.fixture
def sample_image_path(temp_dir):
    """Create a sample image file for testing"""
    image_path = temp_dir / "test_image.jpg"
    # Create a minimal valid JPEG (not a real image, but enough for basic tests)
    image_path.write_bytes(b'\xFF\xD8\xFF\xE0\x00\x10JFIF')
    return image_path
