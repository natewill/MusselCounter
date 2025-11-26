"""
Integration tests for image utilities with real file operations
"""
import pytest
import tempfile
import aiosqlite
from pathlib import Path
from PIL import Image
import hashlib

from utils.image_utils import (
    get_file_hash,
    find_image_by_hash,
    add_image_to_collection,
    add_multiple_images_optimized,
)


@pytest.fixture
async def test_db():
    """Create a test database with required schema"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    async with aiosqlite.connect(db_path) as db:
        # Create required tables
        await db.execute("""
            CREATE TABLE image (
                image_id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                live_mussel_count INTEGER DEFAULT 0,
                dead_mussel_count INTEGER DEFAULT 0,
                stored_polygon_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        await db.execute("""
            CREATE TABLE collection_image (
                collection_id INTEGER NOT NULL,
                image_id INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (collection_id, image_id)
            )
        """)
        
        await db.commit()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_image():
    """Create a test image file"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name)
        yield tmp.name
        Path(tmp.name).unlink(missing_ok=True)


class TestGetFileHash:
    """Tests for get_file_hash function"""

    @pytest.mark.asyncio
    async def test_hash_is_consistent(self, test_image):
        """Test that hashing same file twice gives same result"""
        hash1 = await get_file_hash(test_image)
        hash2 = await get_file_hash(test_image)
        
        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_hash_is_md5(self, test_image):
        """Test that hash is valid MD5 format"""
        file_hash = await get_file_hash(test_image)
        
        # MD5 hashes are 32 hex characters
        assert len(file_hash) == 32
        assert all(c in '0123456789abcdef' for c in file_hash.lower())

    @pytest.mark.asyncio
    async def test_different_files_different_hashes(self):
        """Test that different files produce different hashes"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp1:
            img1 = Image.new('RGB', (100, 100), color='red')
            img1.save(tmp1.name)
            path1 = tmp1.name
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp2:
            img2 = Image.new('RGB', (100, 100), color='blue')  # Different color
            img2.save(tmp2.name)
            path2 = tmp2.name
        
        try:
            hash1 = await get_file_hash(path1)
            hash2 = await get_file_hash(path2)
            
            assert hash1 != hash2
        finally:
            Path(path1).unlink(missing_ok=True)
            Path(path2).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_hash_matches_manual_calculation(self, test_image):
        """Test that our hash matches standard MD5"""
        # Calculate hash manually
        md5 = hashlib.md5()
        with open(test_image, 'rb') as f:
            md5.update(f.read())
        expected = md5.hexdigest()
        
        # Get hash from function
        actual = await get_file_hash(test_image)
        
        assert actual == expected

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises_error(self):
        """Test that missing file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            await get_file_hash("/nonexistent/path/to/file.jpg")

    @pytest.mark.asyncio
    async def test_large_file_hash(self):
        """Test hashing works with larger files"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create larger image (2MB+)
            img = Image.new('RGB', (2000, 2000), color='green')
            img.save(tmp.name, quality=95)
            path = tmp.name
        
        try:
            file_hash = await get_file_hash(path)
            
            # Should still produce valid hash
            assert len(file_hash) == 32
            assert file_hash.isalnum()
        finally:
            Path(path).unlink(missing_ok=True)


class TestFindImageByHash:
    """Tests for find_image_by_hash function"""

    @pytest.mark.asyncio
    async def test_find_existing_image(self, test_db, test_image):
        """Test finding an image that exists in database"""
        file_hash = await get_file_hash(test_image)
        
        async with aiosqlite.connect(test_db) as db:
            # Insert an image
            await db.execute(
                """INSERT INTO image (filename, stored_path, file_hash, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("test.jpg", test_image, file_hash, "2024-01-01", "2024-01-01")
            )
            await db.commit()
            
            # Find it
            result = await find_image_by_hash(db, file_hash)
            
            assert result is not None
            assert result[1] == test_image  # stored_path

    @pytest.mark.asyncio
    async def test_find_nonexistent_image(self, test_db):
        """Test that nonexistent hash returns None"""
        async with aiosqlite.connect(test_db) as db:
            result = await find_image_by_hash(db, "nonexistent_hash_12345")
            
            assert result is None


class TestAddImageToCollection:
    """Tests for add_image_to_collection function"""

    @pytest.mark.asyncio
    async def test_add_new_image(self, test_db, test_image):
        """Test adding a new image to collection"""
        async with aiosqlite.connect(test_db) as db:
            image_id = await add_image_to_collection(db, 1, test_image, "test.jpg")
            
            # Verify image was added
            assert image_id > 0
            
            # Verify in database
            cursor = await db.execute("SELECT * FROM image WHERE image_id = ?", (image_id,))
            row = await cursor.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_add_duplicate_image_reuses_id(self, test_db, test_image):
        """Test that adding same image twice reuses existing ID"""
        async with aiosqlite.connect(test_db) as db:
            # Add first time
            id1 = await add_image_to_collection(db, 1, test_image)
            
            # Add same image again
            id2 = await add_image_to_collection(db, 1, test_image)
            
            # Should reuse same ID
            assert id1 == id2

    @pytest.mark.asyncio
    async def test_add_image_to_multiple_collections(self, test_db, test_image):
        """Test adding same image to different collections"""
        async with aiosqlite.connect(test_db) as db:
            # Add to collection 1
            id1 = await add_image_to_collection(db, 1, test_image)
            
            # Add to collection 2
            id2 = await add_image_to_collection(db, 2, test_image)
            
            # Same image ID, different collections
            assert id1 == id2
            
            # Verify linked to both collections
            cursor = await db.execute(
                "SELECT COUNT(*) FROM collection_image WHERE image_id = ?",
                (id1,)
            )
            count = (await cursor.fetchone())[0]
            assert count == 2

    @pytest.mark.asyncio
    async def test_add_nonexistent_file_raises_error(self, test_db):
        """Test that adding nonexistent file raises FileNotFoundError"""
        async with aiosqlite.connect(test_db) as db:
            with pytest.raises(FileNotFoundError):
                await add_image_to_collection(db, 1, "/nonexistent/file.jpg")


class TestAddMultipleImagesOptimized:
    """Tests for bulk image adding"""

    @pytest.mark.asyncio
    async def test_add_multiple_new_images(self, test_db):
        """Test adding multiple new images at once"""
        # Create multiple test images
        images = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                img = Image.new('RGB', (50, 50), color=('red', 'green', 'blue')[i])
                img.save(tmp.name)
                images.append(tmp.name)
        
        try:
            # Compute hashes
            image_data = []
            for path in images:
                file_hash = await get_file_hash(path)
                image_data.append((path, Path(path).name, file_hash))
            
            async with aiosqlite.connect(test_db) as db:
                ids, added, dupes, dupe_ids = await add_multiple_images_optimized(
                    db, 1, image_data
                )
                
                # Should add all 3 images
                assert len(ids) == 3
                assert added == 3
                assert dupes == 0
                assert len(dupe_ids) == 0
        finally:
            for path in images:
                Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_add_with_duplicates(self, test_db, test_image):
        """Test adding images where some are duplicates"""
        file_hash = await get_file_hash(test_image)
        
        async with aiosqlite.connect(test_db) as db:
            # Add image once
            await add_image_to_collection(db, 1, test_image)
            
            # Try adding same image again in bulk
            image_data = [
                (test_image, "test.jpg", file_hash),
                (test_image, "test2.jpg", file_hash),  # Same hash
            ]
            
            ids, added, dupes, dupe_ids = await add_multiple_images_optimized(
                db, 1, image_data
            )
            
            # Both should map to same ID
            assert ids[0] == ids[1]
            # Already in collection
            assert added == 0
            assert dupes == 2

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, test_db):
        """Test that empty list returns empty results"""
        async with aiosqlite.connect(test_db) as db:
            ids, added, dupes, dupe_ids = await add_multiple_images_optimized(
                db, 1, []
            )
            
            assert ids == []
            assert added == 0
            assert dupes == 0
            assert dupe_ids == []
