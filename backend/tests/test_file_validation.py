"""
Unit tests for file validation utilities
"""
import pytest
from utils.file_validation_lib import validate_image_content, validate_file_size


class TestValidateImageContent:
    """Tests for validate_image_content function"""

    def test_valid_png_image(self):
        """Test validation of PNG image by magic bytes"""
        # Valid PNG header
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        is_valid, error = validate_image_content(png_header, "test.png")
        assert is_valid is True
        assert error is None

    def test_valid_jpeg_image(self):
        """Test validation of JPEG image by magic bytes"""
        # Valid JPEG header
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        is_valid, error = validate_image_content(jpeg_header, "test.jpg")
        assert is_valid is True
        assert error is None

    def test_valid_gif_image_87a(self):
        """Test validation of GIF87a image by magic bytes"""
        gif_header = b'GIF87a' + b'\x00' * 10
        is_valid, error = validate_image_content(gif_header, "test.gif")
        assert is_valid is True
        assert error is None

    def test_valid_gif_image_89a(self):
        """Test validation of GIF89a image by magic bytes"""
        gif_header = b'GIF89a' + b'\x00' * 10
        is_valid, error = validate_image_content(gif_header, "test.gif")
        assert is_valid is True
        assert error is None

    def test_valid_bmp_image(self):
        """Test validation of BMP image by magic bytes"""
        bmp_header = b'BM' + b'\x00' * 10
        is_valid, error = validate_image_content(bmp_header, "test.bmp")
        assert is_valid is True
        assert error is None

    def test_valid_tiff_image_little_endian(self):
        """Test validation of TIFF image (little endian) by magic bytes"""
        tiff_header = b'II*\x00' + b'\x00' * 10
        is_valid, error = validate_image_content(tiff_header, "test.tiff")
        assert is_valid is True
        assert error is None

    def test_valid_tiff_image_big_endian(self):
        """Test validation of TIFF image (big endian) by magic bytes"""
        tiff_header = b'MM\x00*' + b'\x00' * 10
        is_valid, error = validate_image_content(tiff_header, "test.tiff")
        assert is_valid is True
        assert error is None

    def test_invalid_file_not_an_image(self):
        """Test that non-image file is rejected"""
        text_content = b'This is just text content, not an image'
        is_valid, error = validate_image_content(text_content, "test.txt")
        assert is_valid is False
        assert error is not None
        assert "not appear to be a valid image" in error

    def test_empty_file(self):
        """Test that empty file is rejected"""
        is_valid, error = validate_image_content(b'', "test.jpg")
        assert is_valid is False
        assert error is not None
        assert "too small or empty" in error

    def test_file_too_small(self):
        """Test that file with less than 4 bytes is rejected"""
        is_valid, error = validate_image_content(b'abc', "test.jpg")
        assert is_valid is False
        assert error is not None
        assert "too small or empty" in error

    def test_invalid_magic_bytes(self):
        """Test that file with invalid magic bytes is rejected"""
        invalid_content = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        is_valid, error = validate_image_content(invalid_content, "test.jpg")
        assert is_valid is False
        assert error is not None

    def test_pdf_file_rejected(self):
        """Test that PDF file is rejected"""
        pdf_header = b'%PDF-1.4' + b'\x00' * 10
        is_valid, error = validate_image_content(pdf_header, "test.pdf")
        assert is_valid is False
        assert error is not None

    def test_executable_rejected(self):
        """Test that executable file is rejected"""
        # Windows executable header
        exe_header = b'MZ' + b'\x00' * 10
        is_valid, error = validate_image_content(exe_header, "test.exe")
        assert is_valid is False
        assert error is not None


class TestValidateFileSizeFunction:
    """Tests for validate_file_size function from file_validation_lib"""

    def test_file_within_size_limit(self):
        """Test file within size limit is valid"""
        content = b'x' * 1000  # 1KB
        is_valid, error = validate_file_size(content, 2000)
        assert is_valid is True
        assert error is None

    def test_file_exactly_at_limit(self):
        """Test file exactly at size limit is valid"""
        content = b'x' * 1000
        is_valid, error = validate_file_size(content, 1000)
        assert is_valid is True
        assert error is None

    def test_file_exceeds_limit(self):
        """Test file exceeding size limit is invalid"""
        content = b'x' * 2000
        is_valid, error = validate_file_size(content, 1000)
        assert is_valid is False
        assert error is not None
        assert "exceeds maximum" in error

    def test_empty_file_size(self):
        """Test empty file passes size validation"""
        is_valid, error = validate_file_size(b'', 1000)
        assert is_valid is True
        assert error is None

    def test_large_file_with_large_limit(self):
        """Test large file with appropriate limit"""
        # 10MB file with 50MB limit
        content = b'x' * (10 * 1024 * 1024)
        is_valid, error = validate_file_size(content, 50 * 1024 * 1024)
        assert is_valid is True
        assert error is None

    def test_error_message_includes_size(self):
        """Test that error message includes the maximum size"""
        content = b'x' * 2000
        max_size = 1024  # 1KB
        is_valid, error = validate_file_size(content, max_size)
        assert is_valid is False
        # Should include size in MB
        assert "MB" in error
