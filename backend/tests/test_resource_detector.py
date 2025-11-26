"""
Tests for resource detection - with proper mocking
"""
import pytest
import torch
import os
from unittest.mock import patch, Mock, MagicMock
from utils.resource_detector import calculate_batch_size_from_model


class TestCalculateBatchSizeProperly:
    """Tests with proper hardware mocking"""

    def create_mock_model(self, param_count):
        """Create model with specific param count"""
        model = Mock()
        params = []
        remaining = param_count
        while remaining > 0:
            size = min(remaining, 1000000)
            param = Mock()
            param.numel.return_value = size
            params.append(param)
            remaining -= size
        model.parameters.return_value = params
        return model

    def test_cpu_batch_sizes(self):
        """Test all CPU batch size tiers"""
        with patch('utils.resource_detector.torch.cuda.is_available', return_value=False):
            with patch('utils.resource_detector.torch.backends.mps.is_available', return_value=False):
                # Small model < 10M
                model = self.create_mock_model(5_000_000)
                batch = calculate_batch_size_from_model(model, torch.device("cpu"))
                assert batch == 4, f"Small model should get batch 4, got {batch}"
                
                # Medium model 10-30M
                model = self.create_mock_model(20_000_000)
                batch = calculate_batch_size_from_model(model, torch.device("cpu"))
                assert batch == 2, f"Medium model should get batch 2, got {batch}"
                
                # Large model 30-60M
                model = self.create_mock_model(50_000_000)
                batch = calculate_batch_size_from_model(model, torch.device("cpu"))
                assert batch == 1, f"Large model should get batch 1, got {batch}"
                
                # XLarge model > 60M
                model = self.create_mock_model(70_000_000)
                batch = calculate_batch_size_from_model(model, torch.device("cpu"))
                assert batch == 1, f"XLarge model should get batch 1, got {batch}"

    def test_gpu_batch_sizes(self):
        """Test all GPU batch size tiers"""
        with patch('utils.resource_detector.torch.cuda.is_available', return_value=True):
            # Small model
            model = self.create_mock_model(5_000_000)
            batch = calculate_batch_size_from_model(model, torch.device("cuda"))
            assert batch == 32
            
            # Medium model
            model = self.create_mock_model(20_000_000)
            batch = calculate_batch_size_from_model(model, torch.device("cuda"))
            assert batch == 16
            
            # Large model
            model = self.create_mock_model(50_000_000)
            batch = calculate_batch_size_from_model(model, torch.device("cuda"))
            assert batch == 8
            
            # XLarge model
            model = self.create_mock_model(70_000_000)
            batch = calculate_batch_size_from_model(model, torch.device("cuda"))
            assert batch == 4

    def test_mps_batch_sizes(self):
        """Test Apple Silicon batch size tiers"""
        with patch('utils.resource_detector.torch.cuda.is_available', return_value=False):
            with patch('utils.resource_detector.torch.backends.mps.is_available', return_value=True):
                # Small model
                model = self.create_mock_model(5_000_000)
                batch = calculate_batch_size_from_model(model, torch.device("mps"))
                assert batch == 16
                
                # Medium model
                model = self.create_mock_model(20_000_000)
                batch = calculate_batch_size_from_model(model, torch.device("mps"))
                assert batch == 8
