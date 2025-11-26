"""
Unit tests for security utilities
"""
import pytest
from pathlib import Path
from fastapi import HTTPException
from utils.security import (
    sanitize_filename,
    validate_path_in_directory,
    validate_integer_id
)


class TestSanitizeFilename:
    """Tests for sanitize_filename function"""

    def test_simple_filename(self):
        """Test sanitization of simple filename"""
        result = sanitize_filename("image.jpg")
        assert result == "image.jpg"

    def test_filename_with_spaces(self):
        """Test filename with spaces"""
        result = sanitize_filename("my image file.jpg")
        assert "my" in result and "image" in result

    def test_filename_with_path_components(self):
        """Test filename with path components is stripped"""
        result = sanitize_filename("/path/to/image.jpg")
        assert result == "image.jpg"

        result = sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_filename_with_dangerous_chars(self):
        """Test dangerous characters are sanitized"""
        # pathvalidate sanitizes platform-specific dangerous chars
        # Behavior varies by platform, so we just verify it doesn't crash
        # and that the result is a non-empty string
        result = sanitize_filename("test<>:|?.jpg")
        assert isinstance(result, str)
        assert len(result) > 0
        # Path separators should always be removed
        assert "/" not in result
        assert "\\" not in result

    def test_empty_filename(self):
        """Test empty filename raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("")
        assert exc_info.value.status_code == 400
        assert "cannot be empty" in exc_info.value.detail.lower()

    def test_none_filename(self):
        """Test None filename raises exception"""
        with pytest.raises(HTTPException):
            sanitize_filename(None)


class TestValidatePathInDirectory:
    """Tests for validate_path_in_directory function"""

    def test_valid_path_in_directory(self, temp_dir):
        """Test valid path within allowed directory"""
        file_path = temp_dir / "subdir" / "file.txt"
        result = validate_path_in_directory(file_path, temp_dir)
        assert result.is_relative_to(temp_dir)

    def test_path_traversal_attack(self, temp_dir):
        """Test path traversal is blocked"""
        malicious_path = temp_dir / ".." / ".." / "etc" / "passwd"
        with pytest.raises(HTTPException) as exc_info:
            validate_path_in_directory(malicious_path, temp_dir)
        assert exc_info.value.status_code == 403
        assert "denied" in exc_info.value.detail.lower()

    def test_path_exactly_at_directory(self, temp_dir):
        """Test path exactly at allowed directory"""
        result = validate_path_in_directory(temp_dir, temp_dir)
        assert result == temp_dir.resolve()

    def test_symbolic_link_outside_directory(self, temp_dir):
        """Test symbolic links are resolved and validated"""
        # This test may behave differently on different OS
        outside_dir = temp_dir.parent / "outside"
        outside_dir.mkdir(exist_ok=True)

        symlink_path = temp_dir / "link"
        try:
            symlink_path.symlink_to(outside_dir)
            with pytest.raises(HTTPException):
                validate_path_in_directory(symlink_path, temp_dir)
        except OSError:
            # Skip if symlinks not supported
            pytest.skip("Symlinks not supported on this system")


class TestValidateIntegerId:
    """Tests for validate_integer_id function"""

    def test_valid_id(self):
        """Test valid integer IDs"""
        assert validate_integer_id(1) == 1
        assert validate_integer_id(100) == 100
        assert validate_integer_id(999999) == 999999

    def test_id_at_min_value(self):
        """Test ID at minimum value"""
        assert validate_integer_id(1) == 1

    def test_id_below_min_value(self):
        """Test ID below minimum raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            validate_integer_id(0)
        assert exc_info.value.status_code == 400
        assert "Invalid ID" in exc_info.value.detail

    def test_id_negative(self):
        """Test negative ID raises exception"""
        with pytest.raises(HTTPException):
            validate_integer_id(-1)

    def test_id_at_max_value(self):
        """Test ID at maximum value"""
        max_val = 2**31 - 1
        assert validate_integer_id(max_val) == max_val

    def test_id_above_max_value(self):
        """Test ID above maximum raises exception"""
        with pytest.raises(HTTPException):
            validate_integer_id(2**31)

    def test_custom_min_max(self):
        """Test custom min/max values"""
        assert validate_integer_id(5, min_value=5, max_value=10) == 5
        assert validate_integer_id(10, min_value=5, max_value=10) == 10

        with pytest.raises(HTTPException):
            validate_integer_id(4, min_value=5, max_value=10)

        with pytest.raises(HTTPException):
            validate_integer_id(11, min_value=5, max_value=10)
