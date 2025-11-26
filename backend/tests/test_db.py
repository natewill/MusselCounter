"""
Unit tests for database utilities
"""
import pytest
import aiosqlite
import tempfile
import os
from pathlib import Path
from db import get_db, init_db, get_db_version, _initialize_models
from unittest.mock import patch


class TestGetDb:
    """Tests for get_db context manager"""

    @pytest.mark.asyncio
    async def test_get_db_connection(self):
        """Test that get_db provides a valid connection"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with patch('db.DB_PATH', db_path):
                async with get_db() as db:
                    assert isinstance(db, aiosqlite.Connection)
                    # Test we can execute queries
                    cursor = await db.execute("SELECT 1")
                    result = await cursor.fetchone()
                    assert result[0] == 1
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_get_db_row_factory(self):
        """Test that get_db sets up row factory for dict-like access"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with patch('db.DB_PATH', db_path):
                async with get_db() as db:
                    # Create a test table
                    await db.execute("""
                        CREATE TABLE test_table (
                            id INTEGER PRIMARY KEY,
                            name TEXT
                        )
                    """)
                    await db.execute("INSERT INTO test_table (id, name) VALUES (1, 'test')")
                    await db.commit()
                    
                    # Fetch using row factory
                    cursor = await db.execute("SELECT * FROM test_table")
                    row = await cursor.fetchone()
                    
                    # Should be able to access by column name
                    assert row['id'] == 1
                    assert row['name'] == 'test'
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_get_db_closes_connection(self):
        """Test that connection is properly closed after context"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with patch('db.DB_PATH', db_path):
                async with get_db() as db:
                    connection = db
                
                # After exiting context, connection should be closed
                # Trying to use it should fail
                with pytest.raises(Exception):
                    await connection.execute("SELECT 1")
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestInitDb:
    """Tests for init_db function"""

    @pytest.mark.asyncio
    async def test_init_db_creates_database(self):
        """Test that init_db creates database file"""
        with tempfile.NamedTemporaryFile(delete=True, suffix=".db") as tmp:
            db_path = tmp.name
        
        # Database should not exist
        assert not os.path.exists(db_path)
        
        try:
            with patch('db.DB_PATH', db_path):
                with patch('db.RESET_DB_ON_STARTUP', True):
                    with patch('db._initialize_models', return_value=None):
                        await init_db()
            
            # Database should now exist
            assert os.path.exists(db_path)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_init_db_creates_metadata_table(self):
        """Test that init_db creates db_metadata table"""
        with tempfile.NamedTemporaryFile(delete=True, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with patch('db.DB_PATH', db_path):
                with patch('db.RESET_DB_ON_STARTUP', True):
                    with patch('db._initialize_models', return_value=None):
                        await init_db()
            
            # Check metadata table exists
            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'"
                )
                result = await cursor.fetchone()
                assert result is not None
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_init_db_stores_timestamp(self):
        """Test that init_db stores initialization timestamp"""
        with tempfile.NamedTemporaryFile(delete=True, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with patch('db.DB_PATH', db_path):
                with patch('db.RESET_DB_ON_STARTUP', True):
                    with patch('db._initialize_models', return_value=None):
                        await init_db()
            
            # Check timestamp was stored
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT value FROM db_metadata WHERE key = 'db_init_timestamp'"
                )
                result = await cursor.fetchone()
                assert result is not None
                assert result['value'] is not None
                # Should be ISO format timestamp
                assert 'T' in result['value']
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_init_db_skips_if_exists_and_no_reset(self):
        """Test that init_db skips initialization if DB exists and reset flag is False"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
            # Write something to the file to mark it as existing
            tmp.write(b"existing")
        
        original_size = os.path.getsize(db_path)
        
        try:
            with patch('db.DB_PATH', db_path):
                with patch('db.RESET_DB_ON_STARTUP', False):
                    await init_db()
            
            # File should remain unchanged
            assert os.path.getsize(db_path) == original_size
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_init_db_recreates_if_reset_flag_set(self):
        """Test that init_db recreates database if reset flag is True"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
            tmp.write(b"old data")
        
        try:
            with patch('db.DB_PATH', db_path):
                with patch('db.RESET_DB_ON_STARTUP', True):
                    with patch('db._initialize_models', return_value=None):
                        await init_db()
            
            # Database should be recreated (different size/content)
            assert os.path.exists(db_path)
            # SQLite databases have a specific header
            with open(db_path, 'rb') as f:
                header = f.read(16)
                assert header.startswith(b'SQLite format 3')
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestGetDbVersion:
    """Tests for get_db_version function"""

    @pytest.mark.asyncio
    async def test_get_db_version_returns_timestamp(self):
        """Test that get_db_version returns stored timestamp"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            # Create database with metadata
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE db_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                await db.execute(
                    "INSERT INTO db_metadata (key, value) VALUES (?, ?)",
                    ("db_init_timestamp", "2024-01-01T00:00:00")
                )
                await db.commit()
            
            # Get version
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                version = await get_db_version(db)
                assert version == "2024-01-01T00:00:00"
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_get_db_version_returns_none_if_not_set(self):
        """Test that get_db_version returns None if timestamp not set"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            # Create database without metadata
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE db_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                await db.commit()
            
            # Get version (should be None)
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                version = await get_db_version(db)
                assert version is None
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestInitializeModels:
    """Tests for _initialize_models function"""

    @pytest.mark.asyncio
    async def test_initialize_models_skips_if_no_directory(self):
        """Test that _initialize_models skips if models directory doesn't exist"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            async with aiosqlite.connect(db_path) as db:
                # Create model table
                await db.execute("""
                    CREATE TABLE model (
                        model_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        weights_path TEXT NOT NULL,
                        description TEXT,
                        optimal_batch_size INTEGER,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                await db.commit()
                
                # Call with non-existent models directory
                with patch('db.MODELS_DIR', Path('/nonexistent/path')):
                    await _initialize_models(db)
                
                # Should not have added any models
                cursor = await db.execute("SELECT COUNT(*) FROM model")
                count = await cursor.fetchone()
                assert count[0] == 0
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_initialize_models_skips_if_no_model_files(self):
        """Test that _initialize_models skips if no model files found"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with tempfile.TemporaryDirectory() as models_dir:
                async with aiosqlite.connect(db_path) as db:
                    # Create model table
                    await db.execute("""
                        CREATE TABLE model (
                            model_id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            type TEXT NOT NULL,
                            weights_path TEXT NOT NULL,
                            description TEXT,
                            optimal_batch_size INTEGER,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                    """)
                    await db.commit()
                    
                    # Call with empty models directory
                    with patch('db.MODELS_DIR', Path(models_dir)):
                        await _initialize_models(db)
                    
                    # Should not have added any models
                    cursor = await db.execute("SELECT COUNT(*) FROM model")
                    count = await cursor.fetchone()
                    assert count[0] == 0
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_initialize_models_adds_yolo_model(self):
        """Test that _initialize_models correctly identifies and adds YOLO model"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with tempfile.TemporaryDirectory() as models_dir:
                # Create a fake YOLO model file
                model_path = Path(models_dir) / "yolo_model.pt"
                model_path.write_text("fake model")
                
                async with aiosqlite.connect(db_path) as db:
                    db.row_factory = aiosqlite.Row
                    
                    # Create model table
                    await db.execute("""
                        CREATE TABLE model (
                            model_id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            type TEXT NOT NULL,
                            weights_path TEXT NOT NULL,
                            description TEXT,
                            optimal_batch_size INTEGER,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                    """)
                    await db.commit()
                    
                    # Initialize models
                    with patch('db.MODELS_DIR', Path(models_dir)):
                        await _initialize_models(db)
                    
                    # Check model was added
                    cursor = await db.execute("SELECT * FROM model")
                    model = await cursor.fetchone()
                    assert model is not None
                    assert model['name'] == 'yolo_model'
                    assert model['type'] == 'YOLO'
                    assert 'yolo_model.pt' in model['weights_path']
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_initialize_models_adds_rcnn_model(self):
        """Test that _initialize_models correctly identifies and adds Faster R-CNN model"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with tempfile.TemporaryDirectory() as models_dir:
                # Create a fake Faster R-CNN model file
                model_path = Path(models_dir) / "faster_rcnn_model.pth"
                model_path.write_text("fake model")
                
                async with aiosqlite.connect(db_path) as db:
                    db.row_factory = aiosqlite.Row
                    
                    # Create model table
                    await db.execute("""
                        CREATE TABLE model (
                            model_id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            type TEXT NOT NULL,
                            weights_path TEXT NOT NULL,
                            description TEXT,
                            optimal_batch_size INTEGER,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                    """)
                    await db.commit()
                    
                    # Initialize models
                    with patch('db.MODELS_DIR', Path(models_dir)):
                        await _initialize_models(db)
                    
                    # Check model was added
                    cursor = await db.execute("SELECT * FROM model")
                    model = await cursor.fetchone()
                    assert model is not None
                    assert model['name'] == 'faster_rcnn_model'
                    assert model['type'] == 'Faster R-CNN'
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    @pytest.mark.asyncio
    async def test_initialize_models_skips_existing_models(self):
        """Test that _initialize_models doesn't add duplicate models"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            with tempfile.TemporaryDirectory() as models_dir:
                # Create a fake model file
                model_path = Path(models_dir) / "test_model.pt"
                model_path.write_text("fake model")
                
                async with aiosqlite.connect(db_path) as db:
                    db.row_factory = aiosqlite.Row
                    
                    # Create model table
                    await db.execute("""
                        CREATE TABLE model (
                            model_id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            type TEXT NOT NULL,
                            weights_path TEXT NOT NULL,
                            description TEXT,
                            optimal_batch_size INTEGER,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                    """)
                    
                    # Add model manually
                    await db.execute(
                        """INSERT INTO model (name, type, weights_path, description, optimal_batch_size, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        ("test_model", "YOLO", str(model_path), "existing", 8, "2024-01-01", "2024-01-01")
                    )
                    await db.commit()
                    
                    # Initialize models (should skip existing)
                    with patch('db.MODELS_DIR', Path(models_dir)):
                        await _initialize_models(db)
                    
                    # Check only one model exists
                    cursor = await db.execute("SELECT COUNT(*) FROM model")
                    count = await cursor.fetchone()
                    assert count[0] == 1
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
