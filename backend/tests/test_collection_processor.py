"""
Rigorous integration tests for collection_processor.py - the brain of the system.

This tests the entire ML inference orchestration pipeline including:
- Model loading and validation
- Image preparation and duplicate detection
- Batch processing with semaphores
- Real-time progress updates
- Error handling and recovery
- Result aggregation
"""
import pytest
import tempfile
import aiosqlite
import asyncio
from pathlib import Path
from PIL import Image
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from utils.run_utils.collection_processor import (
    _fail,
    _batch_infer,
    _setup_run_and_load_model,
    _prepare_images,
    _handle_all_images_processed,
    _process_batch_inference,
    _process_single_images,
    _finalize_run,
    process_collection_run,
)


@pytest.fixture
async def test_db():
    """Create test database with full schema"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        # Collections table
        await db.execute("""
            CREATE TABLE collection (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                live_mussel_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Images table
        await db.execute("""
            CREATE TABLE image (
                image_id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                width INTEGER,
                height INTEGER,
                live_mussel_count INTEGER DEFAULT 0,
                dead_mussel_count INTEGER DEFAULT 0,
                stored_polygon_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Collection-Image junction
        await db.execute("""
            CREATE TABLE collection_image (
                collection_id INTEGER NOT NULL,
                image_id INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (collection_id, image_id)
            )
        """)

        # Models table
        await db.execute("""
            CREATE TABLE model (
                model_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                weights_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Runs table
        await db.execute("""
            CREATE TABLE run (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                model_id INTEGER NOT NULL,
                threshold REAL NOT NULL,
                status TEXT NOT NULL,
                total_images INTEGER DEFAULT 0,
                processed_count INTEGER DEFAULT 0,
                live_mussel_count INTEGER DEFAULT 0,
                error_msg TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Image results table
        await db.execute("""
            CREATE TABLE image_result (
                run_id INTEGER NOT NULL,
                image_id INTEGER NOT NULL,
                live_mussel_count INTEGER DEFAULT 0,
                dead_mussel_count INTEGER DEFAULT 0,
                polygon_path TEXT,
                processed_at TEXT NOT NULL,
                error_msg TEXT,
                PRIMARY KEY (run_id, image_id)
            )
        """)

        # Detections table
        await db.execute("""
            CREATE TABLE detection (
                detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                image_id INTEGER NOT NULL,
                class TEXT NOT NULL,
                confidence REAL NOT NULL,
                x1 REAL NOT NULL,
                y1 REAL NOT NULL,
                x2 REAL NOT NULL,
                y2 REAL NOT NULL
            )
        """)

        await db.commit()

    yield db_path

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_image():
    """Create a test image file"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp.name)
        yield tmp.name
        Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def mock_model_device():
    """Mock model device tuple (model, device, batch_size)"""
    mock_model = Mock()
    mock_device = Mock()
    mock_device.type = "cpu"
    return (mock_model, mock_device, 4)


class TestFailHelper:
    """Tests for _fail() error handling"""

    @pytest.mark.asyncio
    async def test_fail_logs_and_updates_status(self, test_db):
        """Test that _fail updates status and logs error"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create a run
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'running', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            # Call _fail
            await _fail(db, 1, "Test error message")

            # Verify status updated
            cursor = await db.execute("SELECT status, error_msg FROM run WHERE run_id = 1")
            row = await cursor.fetchone()

            assert row[0] == 'failed'
            assert row[1] == "Test error message"

    @pytest.mark.asyncio
    async def test_fail_with_custom_status(self, test_db):
        """Test _fail with custom status"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'running', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            await _fail(db, 1, "Cancelled by user", status='cancelled')

            cursor = await db.execute("SELECT status FROM run WHERE run_id = 1")
            status = (await cursor.fetchone())[0]

            assert status == 'cancelled'


class TestBatchInfer:
    """Tests for _batch_infer() batch inference wrapper"""

    @pytest.mark.asyncio
    async def test_batch_infer_calls_yolo(self, test_image):
        """Test that batch_infer calls YOLO for YOLO models"""
        mock_model_device = (Mock(), Mock(), 4)

        with patch('utils.run_utils.collection_processor.run_yolo_inference_batch') as mock_yolo:
            mock_yolo.return_value = [{'live_count': 5, 'dead_count': 2, 'polygons': []}]

            results = await _batch_infer('YOLO', mock_model_device, [test_image])

            assert mock_yolo.called
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_batch_infer_calls_rcnn(self, test_image):
        """Test that batch_infer calls R-CNN for R-CNN models"""
        mock_model_device = (Mock(), Mock(), 4)

        with patch('utils.run_utils.collection_processor.run_rcnn_inference_batch') as mock_rcnn:
            mock_rcnn.return_value = [{'live_count': 3, 'dead_count': 1, 'polygons': []}]

            results = await _batch_infer('Faster R-CNN', mock_model_device, [test_image])

            assert mock_rcnn.called
            assert len(results) == 1


class TestSetupRunAndLoadModel:
    """Tests for _setup_run_and_load_model() initialization"""

    @pytest.mark.asyncio
    async def test_setup_with_valid_run(self, test_db, test_image):
        """Test successful setup with valid run and model"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create model
            await db.execute(
                "INSERT INTO model (model_id, name, type, weights_path, created_at, updated_at) "
                "VALUES (1, 'Test Model', 'YOLO', ?, '2024-01-01', '2024-01-01')",
                (test_image,)  # Use test_image as fake weights
            )

            # Create collection
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test Collection', '2024-01-01', '2024-01-01')"
            )

            # Create run
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'pending', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            # Mock load_model
            with patch('utils.run_utils.collection_processor.load_model') as mock_load:
                mock_load.return_value = (Mock(), Mock(), 4)

                result = await _setup_run_and_load_model(db, 1)

                assert result is not None
                run, model_device, collection_id, model_id, threshold, model_type, weights_path = result
                assert collection_id == 1
                assert model_id == 1
                assert threshold == 0.5
                assert model_type == 'YOLO'

    @pytest.mark.asyncio
    async def test_setup_with_missing_run(self, test_db):
        """Test that missing run returns None and updates status"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            result = await _setup_run_and_load_model(db, 999)

            assert result is None

    @pytest.mark.asyncio
    async def test_setup_with_missing_model(self, test_db):
        """Test that missing model returns None"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create collection
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )

            # Create run with non-existent model
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 999, 0.5, 'pending', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            result = await _setup_run_and_load_model(db, 1)

            assert result is None

    @pytest.mark.asyncio
    async def test_setup_with_missing_weights_file(self, test_db):
        """Test that missing weights file returns None"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create model with non-existent weights
            await db.execute(
                "INSERT INTO model (model_id, name, type, weights_path, created_at, updated_at) "
                "VALUES (1, 'Test', 'YOLO', '/nonexistent/weights.pt', '2024-01-01', '2024-01-01')"
            )

            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )

            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'pending', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            result = await _setup_run_and_load_model(db, 1)

            assert result is None


class TestPrepareImages:
    """Tests for _prepare_images() image preparation"""

    @pytest.mark.asyncio
    async def test_prepare_with_no_images(self, test_db):
        """Test that empty collection returns None"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Empty', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            result = await _prepare_images(db, 1, 1)

            assert result is None

    @pytest.mark.asyncio
    async def test_prepare_filters_already_processed(self, test_db, test_image):
        """Test that already-processed images are filtered out"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create collection
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )

            # Create 3 images
            for i in range(1, 4):
                await db.execute(
                    "INSERT INTO image (image_id, filename, stored_path, file_hash, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, '2024-01-01', '2024-01-01')",
                    (i, f"img{i}.jpg", test_image, f"hash{i}")
                )
                await db.execute(
                    "INSERT INTO collection_image (collection_id, image_id, added_at) VALUES (1, ?, '2024-01-01')",
                    (i,)
                )

            # Mark image 1 and 2 as already processed
            await db.execute(
                "INSERT INTO image_result (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at) "
                "VALUES (1, 1, 5, 2, '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO image_result (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at) "
                "VALUES (1, 2, 3, 1, '2024-01-01')"
            )
            await db.commit()

            images_to_process, total_images, images_already_done = await _prepare_images(db, 1, 1)

            assert total_images == 3
            assert images_already_done == 2
            assert len(images_to_process) == 1
            assert images_to_process[0]['image_id'] == 3


class TestHandleAllImagesProcessed:
    """Tests for _handle_all_images_processed() recalculation"""

    @pytest.mark.asyncio
    async def test_recalculates_totals_and_marks_completed(self, test_db):
        """Test that all-processed case recalculates and completes"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create collection and run
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'running', '2024-01-01', '2024-01-01', '2024-01-01')"
            )

            # Add some results
            await db.execute(
                "INSERT INTO image_result (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at) "
                "VALUES (1, 1, 10, 5, '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO image_result (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at) "
                "VALUES (1, 2, 8, 3, '2024-01-01')"
            )
            await db.commit()

            await _handle_all_images_processed(db, 1, 1, 2)

            # Verify run updated
            cursor = await db.execute("SELECT status, total_images, processed_count, live_mussel_count FROM run WHERE run_id = 1")
            row = await cursor.fetchone()

            assert row[0] == 'completed'
            assert row[1] == 2  # total_images
            assert row[2] == 2  # processed_count
            assert row[3] == 18  # live_mussel_count (10 + 8)

            # Verify collection updated
            cursor = await db.execute("SELECT live_mussel_count FROM collection WHERE collection_id = 1")
            collection_count = (await cursor.fetchone())[0]

            assert collection_count == 18


class TestFinalizeRun:
    """Tests for _finalize_run() result aggregation"""

    @pytest.mark.asyncio
    async def test_finalize_with_all_successes(self, test_db):
        """Test finalization when all images succeed"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create collection and run
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'running', '2024-01-01', '2024-01-01', '2024-01-01')"
            )

            # Add results
            await db.execute(
                "INSERT INTO image_result (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at) "
                "VALUES (1, 1, 5, 2, '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO image_result (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at) "
                "VALUES (1, 2, 3, 1, '2024-01-01')"
            )
            await db.commit()

            # Results format: (image_id, success, live_count, dead_count)
            results = [
                (1, True, 5, 2),
                (2, True, 3, 1),
            ]

            await _finalize_run(db, 1, 1, results, images_processed_in_this_run=2, images_already_done=0)

            # Verify run status is 'completed' (not 'completed_with_errors')
            cursor = await db.execute("SELECT status, live_mussel_count FROM run WHERE run_id = 1")
            row = await cursor.fetchone()

            assert row[0] == 'completed'
            assert row[1] == 8  # 5 + 3

    @pytest.mark.asyncio
    async def test_finalize_with_some_failures(self, test_db):
        """Test finalization when some images fail"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'running', '2024-01-01', '2024-01-01', '2024-01-01')"
            )

            # Only 1 result (1 failed)
            await db.execute(
                "INSERT INTO image_result (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at) "
                "VALUES (1, 1, 5, 2, '2024-01-01')"
            )
            await db.commit()

            results = [
                (1, True, 5, 2),
                (2, False, 0, 0),  # Failed
            ]

            await _finalize_run(db, 1, 1, results, images_processed_in_this_run=2, images_already_done=0)

            cursor = await db.execute("SELECT status FROM run WHERE run_id = 1")
            status = (await cursor.fetchone())[0]

            assert status == 'completed_with_errors'


class TestProcessCollectionRunIntegration:
    """Integration tests for the main process_collection_run() orchestrator"""

    @pytest.mark.asyncio
    async def test_full_run_workflow(self, test_db, test_image):
        """Test complete workflow from start to finish"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Setup: Create model, collection, images, run
            await db.execute(
                "INSERT INTO model (model_id, name, type, weights_path, created_at, updated_at) "
                "VALUES (1, 'Test Model', 'YOLO', ?, '2024-01-01', '2024-01-01')",
                (test_image,)
            )

            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test Collection', '2024-01-01', '2024-01-01')"
            )

            # Add 2 images
            for i in range(1, 3):
                await db.execute(
                    "INSERT INTO image (image_id, filename, stored_path, file_hash, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, '2024-01-01', '2024-01-01')",
                    (i, f"img{i}.jpg", test_image, f"hash{i}")
                )
                await db.execute(
                    "INSERT INTO collection_image (collection_id, image_id, added_at) VALUES (1, ?, '2024-01-01')",
                    (i,)
                )

            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'pending', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            # Mock model loading and inference
            mock_model_device = (Mock(), Mock(), 4)
            mock_results = [
                {'live_count': 5, 'dead_count': 2, 'polygons': [{'coords': [[0,0],[1,0],[1,1],[0,1]], 'confidence': 0.95, 'class': 'live', 'bbox': [0,0,1,1]}], 'image_width': 100, 'image_height': 100},
                {'live_count': 3, 'dead_count': 1, 'polygons': [{'coords': [[0,0],[1,0],[1,1],[0,1]], 'confidence': 0.85, 'class': 'live', 'bbox': [0,0,1,1]}], 'image_width': 100, 'image_height': 100},
            ]

            with patch('utils.run_utils.collection_processor.DB_PATH', test_db):
                with patch('utils.run_utils.collection_processor.load_model') as mock_load:
                    with patch('utils.run_utils.collection_processor.run_yolo_inference_batch') as mock_infer:
                        with patch('utils.run_utils.collection_processor._save_detections_to_db') as mock_save:
                            with patch('utils.run_utils.collection_processor._get_counts_from_db') as mock_counts:
                                mock_load.return_value = mock_model_device
                                mock_infer.return_value = mock_results
                                mock_save.return_value = None
                                # Return counts based on threshold filtering
                                mock_counts.side_effect = [(5, 2), (3, 1)]

                                # Run the processor
                                await process_collection_run(db, 1)

            # Verify run completed
            cursor = await db.execute("SELECT status, processed_count, total_images FROM run WHERE run_id = 1")
            row = await cursor.fetchone()

            assert row[0] == 'completed'
            assert row[1] == 2  # processed_count
            assert row[2] == 2  # total_images

    @pytest.mark.asyncio
    async def test_run_with_missing_model_fails(self, test_db):
        """Test that missing model causes run to fail gracefully"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )

            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 999, 0.5, 'pending', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            await process_collection_run(db, 1)

            # Verify run marked as failed
            cursor = await db.execute("SELECT status, error_msg FROM run WHERE run_id = 1")
            row = await cursor.fetchone()

            assert row[0] == 'failed'
            assert 'not found' in row[1].lower()

    @pytest.mark.asyncio
    async def test_run_with_no_images_fails(self, test_db, test_image):
        """Test that run with no images fails gracefully"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Create empty collection
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Empty', '2024-01-01', '2024-01-01')"
            )

            await db.execute(
                "INSERT INTO model (model_id, name, type, weights_path, created_at, updated_at) "
                "VALUES (1, 'Test', 'YOLO', ?, '2024-01-01', '2024-01-01')",
                (test_image,)
            )

            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'pending', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            with patch('utils.run_utils.collection_processor.load_model') as mock_load:
                mock_load.return_value = (Mock(), Mock(), 4)

                await process_collection_run(db, 1)

            cursor = await db.execute("SELECT status FROM run WHERE run_id = 1")
            status = (await cursor.fetchone())[0]

            assert status == 'failed'


class TestErrorRecovery:
    """Tests for error handling and recovery"""

    @pytest.mark.asyncio
    async def test_inference_error_marks_run_failed(self, test_db, test_image):
        """Test that inference errors are caught and run fails gracefully"""
        async with aiosqlite.connect(test_db) as db:
            db.row_factory = aiosqlite.Row
            # Setup complete run
            await db.execute(
                "INSERT INTO model (model_id, name, type, weights_path, created_at, updated_at) "
                "VALUES (1, 'Test', 'YOLO', ?, '2024-01-01', '2024-01-01')",
                (test_image,)
            )
            await db.execute(
                "INSERT INTO collection (collection_id, name, created_at, updated_at) "
                "VALUES (1, 'Test', '2024-01-01', '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO image (image_id, filename, stored_path, file_hash, created_at, updated_at) "
                "VALUES (1, 'img1.jpg', ?, 'hash1', '2024-01-01', '2024-01-01')",
                (test_image,)
            )
            await db.execute(
                "INSERT INTO collection_image (collection_id, image_id, added_at) VALUES (1, 1, '2024-01-01')"
            )
            await db.execute(
                "INSERT INTO run (run_id, collection_id, model_id, threshold, status, started_at, created_at, updated_at) "
                "VALUES (1, 1, 1, 0.5, 'pending', '2024-01-01', '2024-01-01', '2024-01-01')"
            )
            await db.commit()

            # Mock model loading to succeed, but inference to fail
            with patch('utils.run_utils.collection_processor.load_model') as mock_load:
                with patch('utils.run_utils.collection_processor.run_yolo_inference_batch') as mock_infer:
                    mock_load.return_value = (Mock(), Mock(), 4)
                    mock_infer.side_effect = Exception("GPU out of memory")

                    await process_collection_run(db, 1)

            # Verify run marked as failed
            cursor = await db.execute("SELECT status, error_msg FROM run WHERE run_id = 1")
            row = await cursor.fetchone()

            assert row[0] == 'failed'
            assert 'GPU out of memory' in row[1]
