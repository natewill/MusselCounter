"""
Unit tests for model loader functions with mocked PyTorch
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import torch

from utils.model_utils.loader import (
    _load_checkpoint,
    load_rcnn_model,
    load_yolo_model,
    load_model,
)


class TestLoadCheckpoint:
    """Tests for _load_checkpoint helper function"""

    def test_load_checkpoint_direct_state_dict(self):
        """Test loading checkpoint that is already a state dict"""
        # Create a fake state dict
        fake_state_dict = {"layer1.weight": torch.randn(10, 10)}
        
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
            torch.save(fake_state_dict, tmp.name)
            tmp_path = tmp.name
        
        try:
            device = torch.device("cpu")
            result = _load_checkpoint(tmp_path, device)
            
            # Should return the state dict directly
            assert "layer1.weight" in result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_load_checkpoint_with_model_state_dict_key(self):
        """Test loading checkpoint with 'model_state_dict' key"""
        fake_state_dict = {"layer1.weight": torch.randn(5, 5)}
        checkpoint = {
            "model_state_dict": fake_state_dict,
            "optimizer_state_dict": {},
            "epoch": 10,
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
            torch.save(checkpoint, tmp.name)
            tmp_path = tmp.name
        
        try:
            device = torch.device("cpu")
            result = _load_checkpoint(tmp_path, device)
            
            # Should extract model_state_dict
            assert "layer1.weight" in result
            # Should not include optimizer or epoch
            assert "optimizer_state_dict" not in result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_load_checkpoint_with_state_dict_key(self):
        """Test loading checkpoint with 'state_dict' key"""
        fake_state_dict = {"layer1.weight": torch.randn(3, 3)}
        checkpoint = {
            "state_dict": fake_state_dict,
            "other_data": "value",
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
            torch.save(checkpoint, tmp.name)
            tmp_path = tmp.name
        
        try:
            device = torch.device("cpu")
            result = _load_checkpoint(tmp_path, device)
            
            # Should extract state_dict
            assert "layer1.weight" in result
            assert "other_data" not in result
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestLoadRCNNModel:
    """Tests for load_rcnn_model function"""

    @patch('utils.model_utils.loader.fasterrcnn_resnet50_fpn')
    @patch('utils.resource_detector.calculate_batch_size_from_model')
    @patch('utils.model_utils.loader._load_checkpoint')
    def test_load_rcnn_model_success(self, mock_checkpoint, mock_batch_size, mock_rcnn):
        """Test successful R-CNN model loading"""
        # Setup mocks
        mock_model = MagicMock()
        mock_rcnn.return_value = mock_model
        mock_checkpoint.return_value = {}  # Empty state dict
        mock_batch_size.return_value = 4
        
        # Create a fake weights file
        with tempfile.NamedTemporaryFile(suffix='.pth', delete=False) as tmp:
            tmp.write(b"fake weights")
            tmp_path = tmp.name
        
        try:
            model, device, batch_size = load_rcnn_model(tmp_path, "Faster R-CNN")
            
            # Verify model was created with correct parameters
            mock_rcnn.assert_called_once_with(
                pretrained=False,
                weights_backbone=None,
                num_classes=3  # background, live, dead
            )
            
            # Verify model was put in eval mode
            mock_model.eval.assert_called_once()
            
            # Verify batch size was calculated
            assert batch_size == 4
            
            # Verify device is set
            assert isinstance(device, torch.device)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch('utils.model_utils.loader.fasterrcnn_resnet50_fpn')
    @patch('utils.model_utils.loader._load_checkpoint')
    def test_load_rcnn_model_checkpoint_load_fails(self, mock_checkpoint, mock_rcnn):
        """Test R-CNN loading handles checkpoint loading errors"""
        mock_model = MagicMock()
        mock_rcnn.return_value = mock_model
        mock_checkpoint.side_effect = RuntimeError("Checkpoint corrupted")
        
        with tempfile.NamedTemporaryFile(suffix='.pth', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with pytest.raises(RuntimeError) as exc_info:
                load_rcnn_model(tmp_path, "Faster R-CNN")
            
            assert "Failed to load R-CNN model weights" in str(exc_info.value)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch('utils.model_utils.loader.fasterrcnn_resnet50_fpn')
    @patch('utils.resource_detector.calculate_batch_size_from_model')
    @patch('utils.model_utils.loader._load_checkpoint')
    @patch('torch.cuda.is_available')
    def test_load_rcnn_uses_cuda_when_available(
        self, mock_cuda_available, mock_checkpoint, mock_batch_size, mock_rcnn
    ):
        """Test that R-CNN uses CUDA when available"""
        mock_cuda_available.return_value = True
        mock_model = MagicMock()
        mock_rcnn.return_value = mock_model
        mock_checkpoint.return_value = {}
        mock_batch_size.return_value = 8
        
        with tempfile.NamedTemporaryFile(suffix='.pth', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            model, device, batch_size = load_rcnn_model(tmp_path, "Faster R-CNN")
            
            # Should use CUDA device
            assert device.type == "cuda"
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestLoadYOLOModel:
    """Tests for load_yolo_model function"""

    @patch('ultralytics.YOLO')
    @patch('utils.resource_detector.calculate_batch_size_from_model')
    def test_load_yolo_model_success(self, mock_batch_size, mock_yolo_class):
        """Test successful YOLO model loading"""
        # Setup mock YOLO model
        mock_model = MagicMock()
        mock_model.model = MagicMock()
        mock_yolo_class.return_value = mock_model
        mock_batch_size.return_value = 4
        
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
            tmp.write(b"fake yolo weights")
            tmp_path = tmp.name
        
        try:
            model, device, batch_size = load_yolo_model(tmp_path, "YOLO")
            
            # Verify YOLO was instantiated with weights path
            mock_yolo_class.assert_called_once_with(tmp_path)
            
            # Verify model was put in eval mode
            mock_model.model.eval.assert_called_once()
            
            # Verify batch size
            assert batch_size == 4
            
            # Verify device
            assert isinstance(device, torch.device)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_load_yolo_handles_missing_ultralytics(self):
        """Test that loading YOLO without ultralytics raises helpful error"""
        # Simulate ImportError by making the import fail
        with patch('ultralytics.YOLO', side_effect=ImportError("No module named 'ultralytics'")):
            with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
                tmp_path = tmp.name

            try:
                with pytest.raises(ImportError) as exc_info:
                    load_yolo_model(tmp_path, "YOLO")

                assert "ultralytics" in str(exc_info.value).lower()
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    @patch('ultralytics.YOLO')
    @patch('utils.resource_detector.calculate_batch_size_from_model')
    def test_load_yolo_handles_fuse_error_gracefully(self, mock_batch_size, mock_yolo_class):
        """Test that YOLO loading handles layer fusing errors gracefully"""
        mock_model = MagicMock()
        mock_model.model = MagicMock()
        
        # Make fuse raise AttributeError
        def fuse_error(*args, **kwargs):
            raise AttributeError("'Conv' object has no attribute 'bn'")
        
        mock_model.model.fuse = fuse_error
        mock_yolo_class.return_value = mock_model
        mock_batch_size.return_value = 4
        
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Should not raise error, should handle it gracefully
            model, device, batch_size = load_yolo_model(tmp_path, "YOLO")
            
            # Should still load successfully
            assert model is not None
            assert batch_size == 4
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestLoadModelRouter:
    """Tests for load_model router function"""

    @patch('utils.model_utils.loader.load_rcnn_model')
    def test_load_model_routes_to_rcnn(self, mock_load_rcnn):
        """Test that 'RCNN' model type routes to R-CNN loader"""
        mock_load_rcnn.return_value = (Mock(), torch.device("cpu"), 4)
        
        with tempfile.NamedTemporaryFile(suffix='.pth') as tmp:
            model, device, batch_size = load_model(tmp.name, "RCNN")
            
            mock_load_rcnn.assert_called_once_with(tmp.name, "RCNN")

    @patch('utils.model_utils.loader.load_rcnn_model')
    def test_load_model_routes_faster_rcnn(self, mock_load_rcnn):
        """Test that 'Faster R-CNN' routes to R-CNN loader"""
        mock_load_rcnn.return_value = (Mock(), torch.device("cpu"), 4)
        
        with tempfile.NamedTemporaryFile(suffix='.pth') as tmp:
            load_model(tmp.name, "Faster R-CNN")
            
            mock_load_rcnn.assert_called_once()

    @patch('utils.model_utils.loader.load_yolo_model')
    def test_load_model_routes_to_yolo(self, mock_load_yolo):
        """Test that 'YOLO' model type routes to YOLO loader"""
        mock_load_yolo.return_value = (Mock(), torch.device("cpu"), 4)
        
        with tempfile.NamedTemporaryFile(suffix='.pt') as tmp:
            model, device, batch_size = load_model(tmp.name, "YOLO")
            
            mock_load_yolo.assert_called_once_with(tmp.name, "YOLO")

    @patch('utils.model_utils.loader.load_yolo_model')
    def test_load_model_case_insensitive(self, mock_load_yolo):
        """Test that model type matching is case-insensitive"""
        mock_load_yolo.return_value = (Mock(), torch.device("cpu"), 4)
        
        with tempfile.NamedTemporaryFile(suffix='.pt') as tmp:
            # Try different cases
            load_model(tmp.name, "yolo")
            load_model(tmp.name, "YOLO")
            load_model(tmp.name, "YoLo")
            
            assert mock_load_yolo.call_count == 3

    def test_load_model_unsupported_type_raises_error(self):
        """Test that unsupported model type raises ValueError"""
        with tempfile.NamedTemporaryFile(suffix='.pt') as tmp:
            with pytest.raises(ValueError) as exc_info:
                load_model(tmp.name, "UnsupportedModel")
            
            assert "Unsupported model type" in str(exc_info.value)

    def test_load_model_ssd_not_implemented(self):
        """Test that SSD model raises NotImplementedError"""
        with tempfile.NamedTemporaryFile(suffix='.pt') as tmp:
            with pytest.raises(NotImplementedError):
                load_model(tmp.name, "SSD")

    def test_load_model_cnn_not_implemented(self):
        """Test that CNN model raises NotImplementedError"""
        with tempfile.NamedTemporaryFile(suffix='.pt') as tmp:
            with pytest.raises(NotImplementedError):
                load_model(tmp.name, "CNN")
