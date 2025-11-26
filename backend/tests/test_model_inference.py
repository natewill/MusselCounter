"""
Unit tests for model inference functions with mocked PyTorch models
"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
from PIL import Image

from utils.model_utils.inference import (
    _rectangle,
    _result,
    run_rcnn_inference,
    run_rcnn_inference_batch,
    run_yolo_inference,
    run_yolo_inference_batch,
    run_inference_on_image,
)


class TestRectangleHelper:
    """Tests for _rectangle helper function"""

    def test_rectangle_converts_bbox_to_polygon(self):
        """Test that bounding box is converted to 4-point polygon"""
        box = [100, 200, 150, 250]
        result = _rectangle(box)
        
        # Should return 4 corner points
        assert len(result) == 4
        
        # Verify corners: top-left, top-right, bottom-right, bottom-left
        assert result[0] == [100.0, 200.0]  # Top-left
        assert result[1] == [150.0, 200.0]  # Top-right
        assert result[2] == [150.0, 250.0]  # Bottom-right
        assert result[3] == [100.0, 250.0]  # Bottom-left

    def test_rectangle_with_float_coordinates(self):
        """Test rectangle with float coordinates"""
        box = [10.5, 20.7, 30.2, 40.9]
        result = _rectangle(box)
        
        assert result[0] == [10.5, 20.7]
        assert result[1] == [30.2, 20.7]
        assert result[2] == [30.2, 40.9]
        assert result[3] == [10.5, 40.9]

    def test_rectangle_with_zero_coordinates(self):
        """Test rectangle at origin"""
        box = [0, 0, 10, 10]
        result = _rectangle(box)
        
        assert result[0] == [0.0, 0.0]
        assert result[1] == [10.0, 0.0]
        assert result[2] == [10.0, 10.0]
        assert result[3] == [0.0, 10.0]


class TestResultHelper:
    """Tests for _result helper function"""

    def test_result_creates_correct_dict(self):
        """Test that result dict has correct structure"""
        polygons = [{"coords": [[0, 0], [1, 1]], "class": "live"}]
        size = (1920, 1080)
        
        result = _result(5, 3, polygons, size)
        
        assert result["live_count"] == 5
        assert result["dead_count"] == 3
        assert result["polygons"] == polygons
        assert result["image_width"] == 1920
        assert result["image_height"] == 1080
        assert result["polygon_path"] is None

    def test_result_with_empty_polygons(self):
        """Test result with no detections"""
        result = _result(0, 0, [], (800, 600))
        
        assert result["live_count"] == 0
        assert result["dead_count"] == 0
        assert result["polygons"] == []
        assert result["image_width"] == 800
        assert result["image_height"] == 600


class TestRCNNInference:
    """Tests for R-CNN inference functions"""

    @pytest.fixture
    def mock_rcnn_model(self):
        """Create a mock R-CNN model that returns fake predictions"""
        model = MagicMock()
        
        # Mock prediction output
        # R-CNN returns a list of dicts with 'boxes', 'scores', 'labels'
        mock_prediction = {
            'boxes': Mock(),
            'scores': Mock(),
            'labels': Mock(),
        }
        
        # Setup mock tensors that can be converted to numpy
        mock_boxes = np.array([[100, 100, 200, 200], [300, 300, 400, 400]])
        mock_scores = np.array([0.95, 0.87])
        mock_labels = np.array([1, 2])  # 1=live, 2=dead
        
        mock_prediction['boxes'].cpu().numpy.return_value = mock_boxes
        mock_prediction['scores'].cpu().numpy.return_value = mock_scores
        mock_prediction['labels'].cpu().numpy.return_value = mock_labels
        
        model.return_value = [mock_prediction]
        
        return model

    @pytest.fixture
    def temp_test_image(self):
        """Create a temporary test image"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create a simple RGB image
            img = Image.new('RGB', (640, 480), color='red')
            img.save(tmp.name)
            yield tmp.name
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)

    def test_run_rcnn_inference_single_image(self, mock_rcnn_model, temp_test_image):
        """Test R-CNN inference on single image"""
        import torch
        device = torch.device("cpu")
        model_tuple = (mock_rcnn_model, device, 4)
        
        result = run_rcnn_inference(model_tuple, temp_test_image)
        
        # Verify structure
        assert "live_count" in result
        assert "dead_count" in result
        assert "polygons" in result
        assert "image_width" in result
        assert "image_height" in result
        
        # Verify counts (from our mock: 1 live, 1 dead)
        assert result["live_count"] == 1
        assert result["dead_count"] == 1
        
        # Verify polygons
        assert len(result["polygons"]) == 2
        assert result["polygons"][0]["class"] == "live"
        assert result["polygons"][1]["class"] == "dead"

    def test_run_rcnn_inference_batch(self, mock_rcnn_model, temp_test_image):
        """Test R-CNN batch inference on multiple images"""
        import torch
        device = torch.device("cpu")
        model_tuple = (mock_rcnn_model, device, 4)
        
        # Mock model to return predictions for multiple images
        mock_prediction = {
            'boxes': Mock(),
            'scores': Mock(),
            'labels': Mock(),
        }
        mock_boxes = np.array([[100, 100, 200, 200]])
        mock_scores = np.array([0.95])
        mock_labels = np.array([1])
        
        mock_prediction['boxes'].cpu().numpy.return_value = mock_boxes
        mock_prediction['scores'].cpu().numpy.return_value = mock_scores
        mock_prediction['labels'].cpu().numpy.return_value = mock_labels
        
        mock_rcnn_model.return_value = [mock_prediction, mock_prediction]
        
        results = run_rcnn_inference_batch(model_tuple, [temp_test_image, temp_test_image])
        
        # Should return results for both images
        assert len(results) == 2
        
        # Each result should have correct structure
        for result in results:
            assert "live_count" in result
            assert "dead_count" in result
            assert "polygons" in result


class TestYOLOInference:
    """Tests for YOLO inference functions"""

    @pytest.fixture
    def mock_yolo_model(self):
        """Create a mock YOLO model that returns fake detections"""
        model = MagicMock()
        
        # Mock YOLO detection box
        mock_box = Mock()
        mock_box.conf = [Mock()]
        mock_box.conf[0].cpu().numpy.return_value = 0.92
        mock_box.cls = [Mock()]
        mock_box.cls[0].cpu().numpy.return_value = 0  # 0=live in YOLO
        mock_box.xyxy = [Mock()]
        mock_box.xyxy[0].cpu().numpy.return_value = np.array([50, 50, 150, 150])
        
        # Mock YOLO result
        mock_detection = Mock()
        mock_detection.boxes = [mock_box]
        
        model.return_value = [mock_detection]
        
        return model

    @pytest.fixture
    def temp_test_image(self):
        """Create a temporary test image"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (640, 480), color='blue')
            img.save(tmp.name)
            yield tmp.name
            Path(tmp.name).unlink(missing_ok=True)

    def test_run_yolo_inference_single_image(self, mock_yolo_model, temp_test_image):
        """Test YOLO inference on single image"""
        import torch
        device = torch.device("cpu")
        model_tuple = (mock_yolo_model, device, 4)
        
        result = run_yolo_inference(model_tuple, temp_test_image)
        
        # Verify structure
        assert "live_count" in result
        assert "dead_count" in result
        assert "polygons" in result
        assert "image_width" in result
        assert "image_height" in result
        
        # Verify we got detections
        assert result["live_count"] == 1
        assert len(result["polygons"]) == 1
        assert result["polygons"][0]["class"] == "live"

    def test_run_yolo_inference_batch(self, temp_test_image):
        """Test YOLO batch inference"""
        import torch

        # Create separate mock for batch test
        mock_yolo_model = MagicMock()

        # Create mock boxes for two images
        mock_box1 = Mock()
        mock_box1.conf = [Mock()]
        mock_box1.conf[0].cpu().numpy.return_value = 0.92
        mock_box1.cls = [Mock()]
        mock_box1.cls[0].cpu().numpy.return_value = 0
        mock_box1.xyxy = [Mock()]
        mock_box1.xyxy[0].cpu().numpy.return_value = np.array([50, 50, 150, 150])

        mock_box2 = Mock()
        mock_box2.conf = [Mock()]
        mock_box2.conf[0].cpu().numpy.return_value = 0.88
        mock_box2.cls = [Mock()]
        mock_box2.cls[0].cpu().numpy.return_value = 1  # dead
        mock_box2.xyxy = [Mock()]
        mock_box2.xyxy[0].cpu().numpy.return_value = np.array([100, 100, 200, 200])

        # Create two separate detection results
        mock_detection1 = Mock()
        mock_detection1.boxes = [mock_box1]

        mock_detection2 = Mock()
        mock_detection2.boxes = [mock_box2]

        mock_yolo_model.return_value = [mock_detection1, mock_detection2]

        device = torch.device("cpu")
        model_tuple = (mock_yolo_model, device, 4)

        results = run_yolo_inference_batch(model_tuple, [temp_test_image, temp_test_image])

        # Should return results for both images
        assert len(results) == 2
        
        for result in results:
            assert "live_count" in result
            assert "polygons" in result


class TestInferenceRouter:
    """Tests for run_inference_on_image router function"""

    @pytest.fixture
    def mock_model_tuple(self):
        """Create a generic mock model tuple"""
        model = MagicMock()
        device = Mock()
        device.type = "cpu"
        return (model, device, 4)

    @pytest.fixture
    def temp_test_image(self):
        """Create a temporary test image"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (100, 100), color='green')
            img.save(tmp.name)
            yield tmp.name
            Path(tmp.name).unlink(missing_ok=True)

    def test_routes_to_rcnn_for_rcnn_model(self, mock_model_tuple, temp_test_image):
        """Test that 'RCNN' model type routes to R-CNN inference"""
        with patch('utils.model_utils.inference.run_rcnn_inference') as mock_rcnn:
            mock_rcnn.return_value = {"live_count": 1, "dead_count": 0}
            
            result = run_inference_on_image(mock_model_tuple, temp_test_image, "RCNN")
            
            # Verify R-CNN function was called
            mock_rcnn.assert_called_once()
            assert result["live_count"] == 1

    def test_routes_to_rcnn_for_faster_rcnn_model(self, mock_model_tuple, temp_test_image):
        """Test that 'Faster R-CNN' model type routes to R-CNN inference"""
        with patch('utils.model_utils.inference.run_rcnn_inference') as mock_rcnn:
            mock_rcnn.return_value = {"live_count": 2, "dead_count": 1}
            
            result = run_inference_on_image(mock_model_tuple, temp_test_image, "Faster R-CNN")
            
            mock_rcnn.assert_called_once()
            assert result["live_count"] == 2

    def test_routes_to_yolo_for_yolo_model(self, mock_model_tuple, temp_test_image):
        """Test that 'YOLO' model type routes to YOLO inference"""
        with patch('utils.model_utils.inference.run_yolo_inference') as mock_yolo:
            mock_yolo.return_value = {"live_count": 3, "dead_count": 2}
            
            result = run_inference_on_image(mock_model_tuple, temp_test_image, "YOLO")
            
            mock_yolo.assert_called_once()
            assert result["live_count"] == 3

    def test_case_insensitive_model_type(self, mock_model_tuple, temp_test_image):
        """Test that model type matching is case-insensitive"""
        with patch('utils.model_utils.inference.run_yolo_inference') as mock_yolo:
            mock_yolo.return_value = {"live_count": 1, "dead_count": 1}
            
            # Try different cases
            run_inference_on_image(mock_model_tuple, temp_test_image, "yolo")
            run_inference_on_image(mock_model_tuple, temp_test_image, "YOLO")
            run_inference_on_image(mock_model_tuple, temp_test_image, "YoLo")
            
            assert mock_yolo.call_count == 3

    def test_unsupported_model_type_raises_error(self, mock_model_tuple, temp_test_image):
        """Test that unsupported model type raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            run_inference_on_image(mock_model_tuple, temp_test_image, "UnsupportedModel")
        
        assert "Unsupported model type" in str(exc_info.value)

    def test_ssd_not_implemented(self, mock_model_tuple, temp_test_image):
        """Test that SSD model raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            run_inference_on_image(mock_model_tuple, temp_test_image, "SSD")

    def test_cnn_not_implemented(self, mock_model_tuple, temp_test_image):
        """Test that CNN model raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            run_inference_on_image(mock_model_tuple, temp_test_image, "CNN")


class TestInferenceLogicValidation:
    """Tests that verify actual inference logic, not just mocks"""

    def test_rectangle_produces_closed_polygon(self):
        """Test that rectangle creates a properly closed 4-point polygon"""
        box = [10, 20, 30, 40]
        polygon = _rectangle(box)
        
        # Should have exactly 4 points
        assert len(polygon) == 4
        
        # Should form a closed rectangle (verify coordinates)
        # Top-left corner
        assert polygon[0][0] == 10 and polygon[0][1] == 20
        # Top-right corner
        assert polygon[1][0] == 30 and polygon[1][1] == 20
        # Bottom-right corner
        assert polygon[2][0] == 30 and polygon[2][1] == 40
        # Bottom-left corner
        assert polygon[3][0] == 10 and polygon[3][1] == 40
        
        # Width should be 20 (30-10)
        width = polygon[1][0] - polygon[0][0]
        assert width == 20
        
        # Height should be 20 (40-20)
        height = polygon[2][1] - polygon[1][1]
        assert height == 20

    def test_result_calculates_correct_structure(self):
        """Test that result dict has all required fields and correct types"""
        result = _result(3, 2, [], (640, 480))
        
        # Check all required keys exist
        required_keys = ['live_count', 'dead_count', 'polygons', 'polygon_path', 'image_width', 'image_height']
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
        
        # Check types
        assert isinstance(result['live_count'], int)
        assert isinstance(result['dead_count'], int)
        assert isinstance(result['polygons'], list)
        assert isinstance(result['image_width'], int)
        assert isinstance(result['image_height'], int)
        
        # Check values
        assert result['live_count'] == 3
        assert result['dead_count'] == 2
        assert result['image_width'] == 640
        assert result['image_height'] == 480

    def test_rcnn_labels_mapping_is_correct(self):
        """Test that RCNN label constants match expected values"""
        from utils.model_utils.inference import RCNN_LABELS
        
        # R-CNN should have labels: 1=live, 2=dead (0=background is not in dict)
        assert RCNN_LABELS[1] == "live"
        assert RCNN_LABELS[2] == "dead"
        assert 0 not in RCNN_LABELS  # Background shouldn't be in labels
        assert len(RCNN_LABELS) == 2  # Should only have 2 classes

    def test_yolo_labels_mapping_is_correct(self):
        """Test that YOLO label constants match expected values"""
        from utils.model_utils.inference import YOLO_LABELS
        
        # YOLO should have labels: 0=live, 1=dead
        assert YOLO_LABELS[0] == "live"
        assert YOLO_LABELS[1] == "dead"
        assert len(YOLO_LABELS) == 2

    def test_polygon_coordinates_are_floats(self):
        """Test that polygon coordinates are converted to floats"""
        # Use integer input
        box = [100, 200, 150, 250]
        polygon = _rectangle(box)
        
        # All coordinates should be floats
        for point in polygon:
            assert isinstance(point[0], float), f"X coordinate {point[0]} is not float"
            assert isinstance(point[1], float), f"Y coordinate {point[1]} is not float"

    def test_inference_router_partial_matching(self):
        """Test that model type matching works with partial strings"""
        import torch
        mock_model = MagicMock()
        device = torch.device("cpu")
        model_tuple = (mock_model, device, 4)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (100, 100), color='green')
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Test partial matches - should route correctly
            with patch('utils.model_utils.inference.run_rcnn_inference') as mock_rcnn:
                mock_rcnn.return_value = {"live_count": 1}
                
                # All these should route to R-CNN
                run_inference_on_image(model_tuple, tmp_path, "rcnn")
                run_inference_on_image(model_tuple, tmp_path, "faster_rcnn")
                run_inference_on_image(model_tuple, tmp_path, "Faster R-CNN")
                
                assert mock_rcnn.call_count == 3
                
            with patch('utils.model_utils.inference.run_yolo_inference') as mock_yolo:
                mock_yolo.return_value = {"live_count": 1}
                
                # All these should route to YOLO
                run_inference_on_image(model_tuple, tmp_path, "yolo")
                run_inference_on_image(model_tuple, tmp_path, "YOLOv8")
                run_inference_on_image(model_tuple, tmp_path, "YOLO v5")
                
                assert mock_yolo.call_count == 3
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_unsupported_model_error_message_is_helpful(self):
        """Test that unsupported model type gives helpful error"""
        import torch
        mock_model = MagicMock()
        device = torch.device("cpu")
        model_tuple = (mock_model, device, 4)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (100, 100))
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                run_inference_on_image(model_tuple, tmp_path, "InvalidModelType")
            
            # Error should mention the unsupported type
            assert "InvalidModelType" in str(exc_info.value)
            # Error should list supported types
            assert "Supported types" in str(exc_info.value)
            # Should mention at least YOLO and RCNN
            error_msg = str(exc_info.value).lower()
            assert "yolo" in error_msg or "rcnn" in error_msg
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestInferenceBugCatching:
    """Tests designed to catch common bugs in inference code"""

    def test_rcnn_counts_match_polygon_length(self):
        """Verify that RCNN live+dead counts equal number of polygons"""
        import torch
        
        # Create mock that returns specific detections
        mock_model = MagicMock()
        
        # 3 live (label=1), 2 dead (label=2), 1 background (label=0)
        mock_prediction = {
            'boxes': Mock(),
            'scores': Mock(),
            'labels': Mock(),
        }
        
        mock_boxes = np.array([
            [10, 10, 20, 20],  # live
            [30, 30, 40, 40],  # live
            [50, 50, 60, 60],  # live
            [70, 70, 80, 80],  # dead
            [90, 90, 100, 100],  # dead
            [110, 110, 120, 120],  # background (should be filtered)
        ])
        mock_scores = np.array([0.9, 0.9, 0.9, 0.9, 0.9, 0.9])
        mock_labels = np.array([1, 1, 1, 2, 2, 0])  # 0=background
        
        mock_prediction['boxes'].cpu().numpy.return_value = mock_boxes
        mock_prediction['scores'].cpu().numpy.return_value = mock_scores
        mock_prediction['labels'].cpu().numpy.return_value = mock_labels
        
        mock_model.return_value = [mock_prediction]
        
        device = torch.device("cpu")
        model_tuple = (mock_model, device, 4)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (200, 200), color='white')
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            result = run_rcnn_inference(model_tuple, tmp_path)
            
            # Should have 3 live + 2 dead = 5 polygons (background filtered out)
            assert result['live_count'] == 3, f"Expected 3 live, got {result['live_count']}"
            assert result['dead_count'] == 2, f"Expected 2 dead, got {result['dead_count']}"
            assert len(result['polygons']) == 5, f"Expected 5 polygons, got {len(result['polygons'])}"
            
            # Counts should match polygon classes
            live_polygons = [p for p in result['polygons'] if p['class'] == 'live']
            dead_polygons = [p for p in result['polygons'] if p['class'] == 'dead']
            
            assert len(live_polygons) == 3, "Mismatch in live polygon count"
            assert len(dead_polygons) == 2, "Mismatch in dead polygon count"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_polygon_bbox_consistency(self):
        """Test that polygon coords match the original bbox"""
        box = [100.5, 200.3, 150.7, 250.9]
        polygon = _rectangle(box)
        
        # Extract bbox from polygon
        x_coords = [p[0] for p in polygon]
        y_coords = [p[1] for p in polygon]
        
        reconstructed_bbox = [
            min(x_coords),  # x1
            min(y_coords),  # y1
            max(x_coords),  # x2
            max(y_coords),  # y2
        ]
        
        # Should match original (within float precision)
        assert abs(reconstructed_bbox[0] - box[0]) < 0.001
        assert abs(reconstructed_bbox[1] - box[1]) < 0.001
        assert abs(reconstructed_bbox[2] - box[2]) < 0.001
        assert abs(reconstructed_bbox[3] - box[3]) < 0.001

    def test_empty_detections_return_zero_counts(self):
        """Test that no detections results in zero counts"""
        import torch
        
        # Mock model that returns no detections
        mock_model = MagicMock()
        
        mock_prediction = {
            'boxes': Mock(),
            'scores': Mock(),
            'labels': Mock(),
        }
        
        # Empty arrays
        mock_prediction['boxes'].cpu().numpy.return_value = np.array([]).reshape(0, 4)
        mock_prediction['scores'].cpu().numpy.return_value = np.array([])
        mock_prediction['labels'].cpu().numpy.return_value = np.array([])
        
        mock_model.return_value = [mock_prediction]
        
        device = torch.device("cpu")
        model_tuple = (mock_model, device, 4)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (100, 100))
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            result = run_rcnn_inference(model_tuple, tmp_path)
            
            assert result['live_count'] == 0, "Should have 0 live detections"
            assert result['dead_count'] == 0, "Should have 0 dead detections"
            assert len(result['polygons']) == 0, "Should have no polygons"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_result_preserves_image_dimensions(self):
        """Test that result dict correctly stores image dimensions"""
        # Various image sizes
        test_sizes = [
            (640, 480),
            (1920, 1080),
            (100, 100),
            (4000, 3000),
        ]
        
        for width, height in test_sizes:
            result = _result(1, 1, [], (width, height))
            
            assert result['image_width'] == width, f"Width mismatch for {width}x{height}"
            assert result['image_height'] == height, f"Height mismatch for {width}x{height}"

    def test_confidence_values_are_preserved(self):
        """Test that confidence scores from model are preserved in polygons"""
        import torch
        
        mock_model = MagicMock()
        
        # Specific confidence scores to test
        test_scores = [0.99, 0.87, 0.65, 0.42]
        
        mock_prediction = {
            'boxes': Mock(),
            'scores': Mock(),
            'labels': Mock(),
        }
        
        mock_boxes = np.array([[i*10, i*10, (i+1)*10, (i+1)*10] for i in range(4)])
        mock_scores = np.array(test_scores)
        mock_labels = np.array([1, 1, 2, 2])
        
        mock_prediction['boxes'].cpu().numpy.return_value = mock_boxes
        mock_prediction['scores'].cpu().numpy.return_value = mock_scores
        mock_prediction['labels'].cpu().numpy.return_value = mock_labels
        
        mock_model.return_value = [mock_prediction]
        
        device = torch.device("cpu")
        model_tuple = (mock_model, device, 4)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (100, 100))
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            result = run_rcnn_inference(model_tuple, tmp_path)
            
            # Check that confidence values are preserved
            confidences = [p['confidence'] for p in result['polygons']]
            
            assert len(confidences) == 4
            for i, expected_conf in enumerate(test_scores):
                assert abs(confidences[i] - expected_conf) < 0.001, \
                    f"Confidence {i} mismatch: expected {expected_conf}, got {confidences[i]}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)
