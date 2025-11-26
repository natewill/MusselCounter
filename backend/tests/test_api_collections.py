"""
Integration tests for collections API endpoints
"""
import pytest
import io
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.integration
class TestCollectionsEndpoints:
    """Tests for /api/collections endpoints"""

    @pytest.mark.asyncio
    async def test_create_collection_minimal(self):
        """Test POST /api/collections with minimal data"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/collections",
                json={"name": "Test Collection"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "collection_id" in data
            assert isinstance(data["collection_id"], int)
            assert data["collection_id"] > 0

    @pytest.mark.asyncio
    async def test_create_collection_with_description(self):
        """Test POST /api/collections with name and description"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/collections",
                json={
                    "name": "Test Collection with Desc",
                    "description": "This is a test collection"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "collection_id" in data

    @pytest.mark.asyncio
    async def test_get_all_collections(self):
        """Test GET /api/collections returns list"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/collections")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_collection_not_found(self):
        """Test GET /api/collections/{id} with non-existent ID"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/collections/99999")
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_collection_invalid_id(self):
        """Test GET /api/collections/{id} with invalid ID"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/collections/-1")
            assert response.status_code == 400

            response = await client.get("/api/collections/0")
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_images_to_nonexistent_collection(self):
        """Test POST /api/collections/{id}/upload-images to non-existent collection"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            files = {
                "files": ("test.jpg", io.BytesIO(b"fake image"), "image/jpeg")
            }
            response = await client.post(
                "/api/collections/99999/upload-images",
                files=files
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_images_no_files(self):
        """Test POST /api/collections/{id}/upload-images without files"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First create a collection
            create_response = await client.post(
                "/api/collections",
                json={"name": "Test Upload Collection"}
            )
            collection_id = create_response.json()["collection_id"]

            # Try to upload with no files
            response = await client.post(
                f"/api/collections/{collection_id}/upload-images"
            )
            assert response.status_code == 422  # Unprocessable entity

    @pytest.mark.asyncio
    async def test_upload_images_invalid_type(self):
        """Test POST /api/collections/{id}/upload-images with invalid file type"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First create a collection
            create_response = await client.post(
                "/api/collections",
                json={"name": "Test Upload Collection"}
            )
            collection_id = create_response.json()["collection_id"]

            # Try to upload non-image file
            files = {
                "files": ("test.txt", io.BytesIO(b"not an image"), "text/plain")
            }
            response = await client.post(
                f"/api/collections/{collection_id}/upload-images",
                files=files
            )
            # Should either reject (400) or return with validation errors
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_delete_image_from_nonexistent_collection(self):
        """Test DELETE /api/collections/{id}/images/{image_id} with non-existent collection"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.delete("/api/collections/99999/images/1")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_image(self):
        """Test DELETE /api/collections/{id}/images/{image_id} with non-existent image"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First create a collection
            create_response = await client.post(
                "/api/collections",
                json={"name": "Test Delete Collection"}
            )
            collection_id = create_response.json()["collection_id"]

            # Try to delete non-existent image
            response = await client.delete(
                f"/api/collections/{collection_id}/images/99999"
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_collection_workflow(self):
        """Test complete collection workflow: create -> get -> verify data"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # 1. Create collection
            create_response = await client.post(
                "/api/collections",
                json={
                    "name": "Workflow Test Collection",
                    "description": "Testing complete workflow"
                }
            )
            assert create_response.status_code == 200
            collection_id = create_response.json()["collection_id"]

            # 2. Get the collection
            get_response = await client.get(f"/api/collections/{collection_id}")
            assert get_response.status_code == 200
            data = get_response.json()

            # 3. Verify collection data
            assert data["collection"]["collection_id"] == collection_id
            assert data["collection"]["name"] == "Workflow Test Collection"
            assert data["collection"]["description"] == "Testing complete workflow"
            assert "images" in data
            assert isinstance(data["images"], list)
            assert len(data["images"]) == 0  # No images uploaded yet

    @pytest.mark.asyncio
    async def test_get_collection_with_valid_id(self):
        """Test GET /api/collections/{id} with valid collection ID returns collection data"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Create a collection first
            create_response = await client.post(
                "/api/collections",
                json={
                    "name": "Test Collection",
                    "description": "Test description"
                }
            )
            collection_id = create_response.json()["collection_id"]

            # Get the collection
            response = await client.get(f"/api/collections/{collection_id}")
            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "collection" in data
            assert "images" in data
            assert "latest_run" in data
            assert "all_runs" in data
            assert "server_time" in data

            # Verify collection data
            assert data["collection"]["collection_id"] == collection_id
            assert data["collection"]["name"] == "Test Collection"
            assert data["collection"]["description"] == "Test description"

            # New collection should have no runs
            assert data["latest_run"] is None
            assert isinstance(data["all_runs"], list)
            assert len(data["all_runs"]) == 0

    @pytest.mark.asyncio
    async def test_create_multiple_collections(self):
        """Test creating multiple collections and retrieving all"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Create multiple collections
            collection_ids = []
            for i in range(3):
                response = await client.post(
                    "/api/collections",
                    json={"name": f"Collection {i}"}
                )
                assert response.status_code == 200
                collection_ids.append(response.json()["collection_id"])

            # Get all collections
            response = await client.get("/api/collections")
            assert response.status_code == 200
            collections = response.json()

            # Verify we got at least our 3 collections
            assert len(collections) >= 3

            # Verify our collections are in the list
            names = [c["name"] for c in collections]
            for i in range(3):
                assert f"Collection {i}" in names

    @pytest.mark.asyncio
    async def test_collection_has_timestamps(self):
        """Test that created collection has proper timestamp fields"""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Create collection
            response = await client.post(
                "/api/collections",
                json={"name": "Timestamp Test"}
            )
            collection_id = response.json()["collection_id"]

            # Get collection
            get_response = await client.get(f"/api/collections/{collection_id}")
            data = get_response.json()

            # Verify timestamps exist and are ISO format
            collection = data["collection"]
            assert "created_at" in collection
            assert "updated_at" in collection
            # ISO format should have 'T' in it
            assert "T" in collection["created_at"]
            assert "T" in collection["updated_at"]
