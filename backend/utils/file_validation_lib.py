"""
File content validation
"""
from typing import Optional, Tuple

ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff', 'image/x-tiff'}
IMAGE_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'png',
    b'\xff\xd8\xff': 'jpeg',
    b'GIF87a': 'gif', b'GIF89a': 'gif',
    b'BM': 'bmp',
    b'II*\x00': 'tiff', b'MM\x00*': 'tiff',
}


def validate_image_content(content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """Validate file content using library or magic bytes"""
    if not content or len(content) < 4:
        return False, "File is too small or empty"
    
    # Try library first
    try:
        import magic
        mime = magic.Magic(mime=True).from_buffer(content)
        if mime.lower() in ALLOWED_MIME_TYPES:
            return True, None
    except (ImportError, Exception):
        pass
    
    try:
        import filetype
        kind = filetype.guess(content)
        if kind and kind.mime.lower() in ALLOWED_MIME_TYPES:
            return True, None
    except (ImportError, Exception):
        pass
    
    # Fallback: magic bytes
    sig = content[:12]
    if any(sig.startswith(s) for s in IMAGE_SIGNATURES):
        return True, None
    
    return False, "File does not appear to be a valid image format"


def validate_file_size(content: bytes, max_size: int) -> Tuple[bool, Optional[str]]:
    """Validate file size"""
    if len(content) > max_size:
        return False, f"File size exceeds maximum of {max_size / 1024 / 1024}MB"
    return True, None

