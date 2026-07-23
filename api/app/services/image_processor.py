"""
image_processor.py — Post-validation image processing for AgroScan NG.

Provides two operations applied after image_validator.validate_image():
  1. strip_exif()   — re-encodes the image through Pillow, removing all EXIF
                      metadata (incl. GPS coordinates) to protect farmer privacy
                      (Security requirement, SRS Section 17).
  2. make_thumbnail() — resizes to THUMB_SIZE, saves to UPLOAD_DIR, and returns
                         the URL path for storage in DiagnosisRecord (FR-9).
"""
import io
import os
import uuid
from PIL import Image

THUMB_SIZE = (128, 128)
UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'uploads/thumbnails')
UPLOAD_URL_PREFIX = os.getenv('UPLOAD_URL_PREFIX', '/uploads/thumbnails')


def strip_exif(raw_bytes: bytes) -> bytes:
    """
    Re-encode image bytes through Pillow to remove all EXIF metadata.
    Returns clean JPEG bytes safe to pass to the inference service and store.
    """
    img = Image.open(io.BytesIO(raw_bytes)).convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    return buf.getvalue()


def make_thumbnail(raw_bytes: bytes) -> str:
    """
    Create a 128x128 JPEG thumbnail, save it under UPLOAD_DIR with a UUID
    filename, and return the URL path string.

    Raises OSError if the directory cannot be written to.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    img = Image.open(io.BytesIO(raw_bytes)).convert('RGB')
    img.thumbnail(THUMB_SIZE, Image.LANCZOS)

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    img.save(filepath, format='JPEG', quality=85)

    return f"{UPLOAD_URL_PREFIX}/{filename}"
