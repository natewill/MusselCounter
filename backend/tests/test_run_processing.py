"""
Unit tests for run processing workflows
"""
import pytest
import tempfile
import aiosqlite
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from utils.run_utils.image_processor import (
    _record_error,
    _get_counts_from_db,
    _save_polygons,
)
from utils.run_utils.collection_processor import (
    _fail,
    _batch_infer,
)


class TestRecordError:
    """Tests for _record_error function"""

    @pytest.mark.asyncio
    async def test_record_error_creates_result_entry(self):
        """Test that error is recorded in database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Create database with required schema
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE image_result (
                        run_id INTEGER,
                        image_id INTEGER,
                        live_mussel_count INTEGER,
                        dead_mussel_count INTEGER,
                        polygon_path TEXT,
                        processed_at TEXT,
                        error_msg TEXT,
                        PRIMARY KEY (run_id, image_id)
                    )
                """)
                await db.commit()
            
            # Record an error
            result = await _record_error(db_path, 1, 100, "Test error message")
            
            # Should return failure tuple
            assert result == (100, False, 0, 0)
            
            # Verify error was recorded in database
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM image_result WHERE run_id = ? AND image_id = ?",
                    (1, 100)
                )
                row = await cursor.fetchone()
                
                assert row is not None
                assert row['error_msg'] == "Test error message"
                assert row['live_mussel_count'] == 0
                assert row['dead_mussel_count'] == 0
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_record_error_replaces_existing_result(self):
        """Test that recording error replaces existing result"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Create database and insert initial result
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE image_result (
                        run_id INTEGER,
                        image_id INTEGER,
                        live_mussel_count INTEGER,
                        dead_mussel_count INTEGER,
                        polygon_path TEXT,
                        processed_at TEXT,
                        error_msg TEXT,
                        PRIMARY KEY (run_id, image_id)
                    )
                """)
                
                # Insert initial result
                await db.execute(
                    """INSERT INTO image_result
                       (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (1, 200, 5, 3, datetime.now(timezone.utc).isoformat())
                )
                await db.commit()
            
            # Record an error (should replace)
            await _record_error(db_path, 1, 200, "New error")
            
            # Verify error replaced old result
            async with aiosqlite.connect(db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM image_result WHERE run_id = ? AND image_id = ?",
                    (1, 200)
                )
                row = await cursor.fetchone()
                
                assert row['error_msg'] == "New error"
                assert row['live_mussel_count'] == 0
                assert row['dead_mussel_count'] == 0
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestGetCountsFromDb:
    """Tests for _get_counts_from_db function"""

    @pytest.mark.asyncio
    async def test_get_counts_filters_by_threshold(self):
        """Test that counts are filtered by confidence threshold"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Create database with detection table
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE detection (
                        run_id INTEGER,
                        image_id INTEGER,
                        class TEXT,
                        original_class TEXT,
                        confidence REAL
                    )
                """)
                
                # Insert detections with various confidences
                detections = [
                    (1, 100, None, 'live', 0.95),  # Above threshold
                    (1, 100, None, 'live', 0.85),  # Above threshold
                    (1, 100, None, 'live', 0.45),  # Below threshold
                    (1, 100, None, 'dead', 0.92),  # Above threshold
                    (1, 100, None, 'dead', 0.30),  # Below threshold
                ]
                
                await db.executemany(
                    "INSERT INTO detection (run_id, image_id, class, original_class, confidence) VALUES (?, ?, ?, ?, ?)",
                    detections
                )
                await db.commit()
            
            # Get counts with threshold = 0.5
            live_count, dead_count = await _get_counts_from_db(db_path, 1, 100, 0.5)
            
            # Should count only detections above threshold
            assert live_count == 2  # 0.95 and 0.85
            assert dead_count == 1  # 0.92
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_counts_respects_manual_overrides(self):
        """Test that manual class overrides are always counted"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE detection (
                        run_id INTEGER,
                        image_id INTEGER,
                        class TEXT,
                        original_class TEXT,
                        confidence REAL
                    )
                """)
                
                # Insert detections - some with manual overrides (class IS NOT NULL)
                detections = [
                    (1, 100, 'live', 'dead', 0.20),    # Manual override: dead->live (low conf)
                    (1, 100, 'dead', 'live', 0.95),    # Manual override: live->dead (high conf)
                    (1, 100, None, 'live', 0.95),      # Auto: live (high conf)
                    (1, 100, None, 'dead', 0.30),      # Auto: dead (low conf, filtered)
                ]
                
                await db.executemany(
                    "INSERT INTO detection (run_id, image_id, class, original_class, confidence) VALUES (?, ?, ?, ?, ?)",
                    detections
                )
                await db.commit()
            
            # Get counts with threshold = 0.5
            live_count, dead_count = await _get_counts_from_db(db_path, 1, 100, 0.5)
            
            # Manual overrides: 1 live, 1 dead
            # Auto (above threshold): 1 live
            # Auto (below threshold): 0 dead
            assert live_count == 2  # 1 manual + 1 auto
            assert dead_count == 1  # 1 manual + 0 auto
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_counts_returns_zero_for_no_detections(self):
        """Test that zero counts are returned when no detections exist"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE detection (
                        run_id INTEGER,
                        image_id INTEGER,
                        class TEXT,
                        original_class TEXT,
                        confidence REAL
                    )
                """)
                await db.commit()
            
            # Get counts for non-existent image
            live_count, dead_count = await _get_counts_from_db(db_path, 1, 999, 0.5)
            
            assert live_count == 0
            assert dead_count == 0
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestSavePolygons:
    """Tests for _save_polygons function"""

    def test_save_polygons_creates_file(self):
        """Test that polygon file is created with correct data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('utils.run_utils.image_processor.Path') as mock_path:
                # Mock the polygon directory
                mock_polygon_dir = Mock()
                mock_polygon_dir.mkdir = Mock()
                mock_polygon_file = Path(tmpdir) / "100.json"
                mock_polygon_dir.__truediv__ = Mock(return_value=mock_polygon_file)
                mock_path.return_value = mock_polygon_dir
                
                result = {
                    "polygons": [
                        {"coords": [[0, 0], [1, 1]], "class": "live", "confidence": 0.9}
                    ],
                    "live_count": 1,
                    "dead_count": 0,
                    "image_width": 640,
                    "image_height": 480,
                }
                
                polygon_path = _save_polygons(100, result, 0.5)
                
                # Should return path string
                assert polygon_path is not None
                assert "100.json" in str(polygon_path)

    def test_save_polygons_returns_none_for_empty_polygons(self):
        """Test that None is returned when no polygons exist"""
        result = {
            "polygons": [],
            "live_count": 0,
            "dead_count": 0,
        }
        
        polygon_path = _save_polygons(100, result, 0.5)
        
        assert polygon_path is None

    def test_save_polygons_returns_none_for_missing_polygons_key(self):
        """Test that None is returned when polygons key is missing"""
        result = {
            "live_count": 0,
            "dead_count": 0,
        }
        
        polygon_path = _save_polygons(100, result, 0.5)
        
        assert polygon_path is None


class TestFailHelper:
    """Tests for _fail helper function"""

    @pytest.mark.asyncio
    async def test_fail_logs_error_and_calls_update(self):
        """Test that _fail logs error and calls update_run_status"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            async with aiosqlite.connect(db_path) as db:
                # Create minimal run table
                await db.execute("""
                    CREATE TABLE run (
                        run_id INTEGER PRIMARY KEY,
                        status TEXT,
                        error_msg TEXT,
                        finished_at TEXT
                    )
                """)
                await db.execute(
                    "INSERT INTO run (run_id, status) VALUES (?, ?)",
                    (1, 'running')
                )
                await db.commit()

                # Call _fail
                with patch('utils.run_utils.collection_processor.logger') as mock_logger:
                    await _fail(db, 1, "Test error message")

                    # Verify error was logged
                    mock_logger.error.assert_called_once()
                    assert "Test error message" in str(mock_logger.error.call_args)

                # Verify status was updated
                cursor = await db.execute(
                    "SELECT status, error_msg FROM run WHERE run_id = ?",
                    (1,)
                )
                row = await cursor.fetchone()

                assert row[0] == 'failed'
                assert row[1] == "Test error message"
        finally:
            Path(db_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_fail_with_custom_status(self):
        """Test that _fail can set custom status"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            async with aiosqlite.connect(db_path) as db:
                await db.execute("""
                    CREATE TABLE run (
                        run_id INTEGER PRIMARY KEY,
                        status TEXT,
                        error_msg TEXT,
                        finished_at TEXT
                    )
                """)
                await db.execute(
                    "INSERT INTO run (run_id, status) VALUES (?, ?)",
                    (1, 'running')
                )
                await db.commit()

                # Call _fail with custom status
                await _fail(db, 1, "Cancelled by user", status='cancelled')

                cursor = await db.execute(
                    "SELECT status, error_msg FROM run WHERE run_id = ?",
                    (1,)
                )
                row = await cursor.fetchone()

                # Should update with custom status, but since 'cancelled' is not
                # in the list of completion statuses, finished_at won't be set
                assert row[0] == 'cancelled'
                assert row[1] == "Cancelled by user"
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestBatchInfer:
    """Tests for _batch_infer function"""

    @pytest.mark.asyncio
    async def test_batch_infer_routes_to_yolo(self):
        """Test that YOLO model type routes to YOLO inference"""
        with patch('utils.run_utils.collection_processor.run_yolo_inference_batch') as mock_yolo:
            mock_yolo.return_value = [
                {"live_count": 2, "dead_count": 1, "polygons": []}
            ]
            
            mock_model = Mock()
            mock_device = Mock()
            model_tuple = (mock_model, mock_device, 4)
            
            results = await _batch_infer("YOLO", model_tuple, ["/fake/path.jpg"])
            
            # Should call YOLO inference
            mock_yolo.assert_called_once()
            assert len(results) == 1
            assert results[0]["live_count"] == 2

    @pytest.mark.asyncio
    async def test_batch_infer_routes_to_rcnn(self):
        """Test that R-CNN model type routes to R-CNN inference"""
        with patch('utils.run_utils.collection_processor.run_rcnn_inference_batch') as mock_rcnn:
            mock_rcnn.return_value = [
                {"live_count": 3, "dead_count": 2, "polygons": []}
            ]
            
            mock_model = Mock()
            mock_device = Mock()
            model_tuple = (mock_model, mock_device, 4)
            
            results = await _batch_infer("Faster R-CNN", model_tuple, ["/fake/path.jpg"])
            
            # Should call R-CNN inference
            mock_rcnn.assert_called_once()
            assert len(results) == 1
            assert results[0]["live_count"] == 3

    @pytest.mark.asyncio
    async def test_batch_infer_handles_multiple_images(self):
        """Test batch inference with multiple images"""
        with patch('utils.run_utils.collection_processor.run_yolo_inference_batch') as mock_yolo:
            mock_yolo.return_value = [
                {"live_count": 2, "dead_count": 1, "polygons": []},
                {"live_count": 4, "dead_count": 3, "polygons": []},
                {"live_count": 1, "dead_count": 0, "polygons": []},
            ]
            
            mock_model = Mock()
            model_tuple = (mock_model, Mock(), 4)
            
            results = await _batch_infer(
                "YOLO",
                model_tuple,
                ["/path1.jpg", "/path2.jpg", "/path3.jpg"]
            )
            
            # Should return results for all images
            assert len(results) == 3
            assert results[0]["live_count"] == 2
            assert results[1]["live_count"] == 4
            assert results[2]["live_count"] == 1
