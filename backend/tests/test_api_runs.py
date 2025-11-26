"""
Integration tests for runs API endpoints
"""
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.integration
class TestRunsEndpoints:
    """Tests for /api/runs and /api/collections/{id}/run endpoints"""

    @pytest.mark.asyncio
    async def test_get_run_not_found(self):
        """Test GET /api/runs/{id} with non-existent run"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/runs/99999")
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_run_invalid_id(self):
        """Test GET /api/runs/{id} with invalid ID"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Negative ID
            response = await client.get("/api/runs/-1")
            assert response.status_code == 400

            # Zero ID
            response = await client.get("/api/runs/0")
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_start_run_collection_not_found(self):
        """Test POST /api/collections/{id}/run with non-existent collection"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/collections/99999/run",
                json={"model_id": 1}
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_start_run_model_not_found(self):
        """Test POST /api/collections/{id}/run with non-existent model"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First create a collection
            create_response = await client.post(
                "/api/collections",
                json={"name": "Test Run Collection"}
            )
            collection_id = create_response.json()["collection_id"]

            # Try to start run with non-existent model
            response = await client.post(
                f"/api/collections/{collection_id}/run",
                json={"model_id": 99999}
            )
            assert response.status_code == 404
            data = response.json()
            assert "model" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_run_invalid_threshold(self):
        """Test POST /api/collections/{id}/run with invalid threshold"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First create a collection
            create_response = await client.post(
                "/api/collections",
                json={"name": "Test Run Collection"}
            )
            collection_id = create_response.json()["collection_id"]

            # Try invalid thresholds
            # Threshold > 1.0
            response = await client.post(
                f"/api/collections/{collection_id}/run",
                json={"model_id": 1, "threshold": 1.5}
            )
            assert response.status_code in [400, 422]

            # Threshold < 0.0
            response = await client.post(
                f"/api/collections/{collection_id}/run",
                json={"model_id": 1, "threshold": -0.5}
            )
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_start_run_missing_model_id(self):
        """Test POST /api/collections/{id}/run without model_id"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First create a collection
            create_response = await client.post(
                "/api/collections",
                json={"name": "Test Run Collection"}
            )
            collection_id = create_response.json()["collection_id"]

            # Try to start run without model_id
            response = await client.post(
                f"/api/collections/{collection_id}/run",
                json={}
            )
            assert response.status_code == 422  # Unprocessable entity

    @pytest.mark.asyncio
    async def test_stop_run_not_found(self):
        """Test POST /api/runs/{id}/stop with non-existent run"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post("/api/runs/99999/stop")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stop_run_invalid_id(self):
        """Test POST /api/runs/{id}/stop with invalid ID"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post("/api/runs/-1/stop")
            assert response.status_code == 400

            response = await client.post("/api/runs/0/stop")
            assert response.status_code == 400
