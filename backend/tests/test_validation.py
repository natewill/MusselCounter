"""
Unit tests for validation utilities
"""
import pytest
from fastapi import HTTPException
from utils.validation import (
    validate_threshold,
    validate_file_size,
    validate_collection_size
)


class TestValidateThreshold:
    """Tests for validate_threshold function"""

    def test_valid_threshold_float(self):
        """Test valid threshold values"""
        assert validate_threshold(0.5) == 0.5
        assert validate_threshold(0.0) == 0.0
        assert validate_threshold(1.0) == 1.0

    def test_valid_threshold_int(self):
        """Test threshold with integer input"""
        assert validate_threshold(0) == 0.0
        assert validate_threshold(1) == 1.0

    def test_none_returns_default(self):
        """Test that None returns default threshold"""
        result = validate_threshold(None)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_invalid_threshold_too_low(self):
        """Test threshold below 0.0 raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            validate_threshold(-0.1)
        assert exc_info.value.status_code == 400
        assert "between 0.0 and 1.0" in exc_info.value.detail

    def test_invalid_threshold_too_high(self):
        """Test threshold above 1.0 raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            validate_threshold(1.5)
        assert exc_info.value.status_code == 400
        assert "between 0.0 and 1.0" in exc_info.value.detail

    def test_edge_cases(self):
        """Test edge case values"""
        assert validate_threshold(0.0000001) == 0.0000001
        assert validate_threshold(0.9999999) == 0.9999999


class TestValidateFileSize:
    """Tests for validate_file_size function"""

    def test_valid_file_size(self):
        """Test file within size limit"""
        validate_file_size(1024, 2048)  # Should not raise

    def test_file_size_at_limit(self):
        """Test file exactly at size limit"""
        validate_file_size(2048, 2048)  # Should not raise

    def test_file_size_exceeds_limit(self):
        """Test file exceeding size limit"""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(3000, 2048)
        assert exc_info.value.status_code == 400
        assert "too large" in exc_info.value.detail.lower()

    def test_zero_file_size(self):
        """Test zero file size is allowed"""
        validate_file_size(0, 1024)  # Should not raise

    def test_none_file_size(self):
        """Test None file size is handled"""
        validate_file_size(None, 1024)  # Should not raise


class TestValidateCollectionSize:
    """Tests for validate_collection_size function"""

    def test_valid_collection_size(self):
        """Test collection within size limit"""
        validate_collection_size(5, 10)  # Should not raise

    def test_collection_size_at_limit(self):
        """Test collection exactly at size limit"""
        validate_collection_size(10, 10)  # Should not raise

    def test_collection_size_exceeds_limit(self):
        """Test collection exceeding size limit"""
        with pytest.raises(HTTPException) as exc_info:
            validate_collection_size(15, 10)
        assert exc_info.value.status_code == 400
        assert "Too many files" in exc_info.value.detail
        assert "10 files" in exc_info.value.detail

    def test_zero_collection_size(self):
        """Test zero collection size is allowed"""
        validate_collection_size(0, 10)  # Should not raise
