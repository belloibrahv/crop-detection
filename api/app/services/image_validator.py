"""
Image validation service.
Checks MIME type (by magic bytes), file size, and minimum resolution
before submitting an uploaded image to the inference service.
"""
import io
from PIL import Image
from flask import current_app

# Allowed MIME signatures: (magic bytes offset, bytes to match, mime label)
_SIGNATURES = [
    (0, b'\xff\xd8\xff', 'image/jpeg'),
    (0, b'\x89PNG\r\n\x1a\n', 'image/png'),
]

MAX_SIZE_BYTES = 8 * 1024 * 1024   # 8 MB  (FR-1)
MIN_DIMENSION  = 224                # pixels (FR-2)


class ImageValidationError(Exception):
    """Raised when an uploaded image fails validation."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_image(file_storage) -> bytes:
    """
    Validate a Flask FileStorage object.

    Returns the raw image bytes if valid.
    Raises ImageValidationError with a short code and human-readable message
    if any check fails.

    Checks (in order):
      1. File size  ≤ MAX_SIZE_BYTES
      2. MIME type  is JPEG or PNG (by magic bytes, not just extension)
      3. Image can be opened by Pillow (not corrupt)
      4. Both dimensions ≥ MIN_DIMENSION
    """
    raw = file_storage.read()
    file_storage.seek(0)   # reset so caller can re-read if needed

    # 1. Size check
    if len(raw) > MAX_SIZE_BYTES:
        raise ImageValidationError(
            'file_too_large',
            f'Image must be smaller than {MAX_SIZE_BYTES // (1024*1024)} MB.'
        )

    # 2. Magic-byte MIME check
    detected = _detect_mime(raw)
    if detected not in ('image/jpeg', 'image/png'):
        raise ImageValidationError(
            'invalid_file_type',
            'Only JPEG and PNG images are accepted.'
        )

    # 3. Pillow open (catches corrupt files)
    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()           # raises on corrupt data
        image = Image.open(io.BytesIO(raw))   # re-open after verify() exhausts the stream
    except Exception:
        raise ImageValidationError(
            'image_corrupt',
            'The uploaded file could not be read as an image. Please try a different photo.'
        )

    # 4. Minimum resolution
    width, height = image.size
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise ImageValidationError(
            'image_too_small',
            f'Image must be at least {MIN_DIMENSION}×{MIN_DIMENSION} pixels.'
        )

    return raw


def _detect_mime(data: bytes) -> str:
    for offset, signature, mime in _SIGNATURES:
        if data[offset:offset + len(signature)] == signature:
            return mime
    return 'application/octet-stream'
