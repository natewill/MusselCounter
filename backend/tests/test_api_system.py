"""
Integration tests for system API endpoints
"""
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.integration
class TestSystemEndpoints:
    """Tests for system/health check endpoints"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns health check message"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "running" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_db_version_endpoint(self):
        """Test database version endpoint returns version info"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/db-version")
            assert response.status_code == 200
            data = response.json()
            assert "db_version" in data
            # db_version can be None if not set, or a string timestamp
            assert data["db_version"] is None or isinstance(data["db_version"], str)

    @pytest.mark.asyncio
    async def test_endpoints_return_json(self):
        """Test system endpoints return proper JSON content type"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/")
            assert "application/json" in response.headers["content-type"]

            response = await client.get("/api/db-version")
            assert "application/json" in response.headers["content-type"]
