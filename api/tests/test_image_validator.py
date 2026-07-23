"""
Unit tests for app/services/image_validator.py
"""
import io
import pytest
from PIL import Image as PILImage
from werkzeug.datastructures import FileStorage

from app.services.image_validator import validate_image, ImageValidationError, MAX_SIZE_BYTES, MIN_DIMENSION


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_jpeg(width=256, height=256) -> bytes:
    img = PILImage.new('RGB', (width, height), (80, 150, 60))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


def _make_png(width=256, height=256) -> bytes:
    img = PILImage.new('RGB', (width, height), (60, 120, 80))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _storage(data: bytes, name='leaf.jpg', content_type='image/jpeg') -> FileStorage:
    return FileStorage(stream=io.BytesIO(data), filename=name, content_type=content_type)


# ── Happy path ────────────────────────────────────────────────────────────────

def test_valid_jpeg_passes():
    raw = validate_image(_storage(_make_jpeg()))
    assert len(raw) > 0


def test_valid_png_passes():
    raw = validate_image(_storage(_make_png(), name='leaf.png', content_type='image/png'))
    assert len(raw) > 0


# ── File type ─────────────────────────────────────────────────────────────────

def test_gif_rejected():
    img = PILImage.new('RGB', (256, 256))
    buf = io.BytesIO()
    img.save(buf, format='GIF')
    with pytest.raises(ImageValidationError) as exc:
        validate_image(_storage(buf.getvalue(), name='leaf.gif', content_type='image/gif'))
    assert exc.value.code == 'invalid_file_type'


def test_wrong_extension_but_valid_jpeg_passes():
    """Extension is ignored; only magic bytes matter."""
    raw = validate_image(_storage(_make_jpeg(), name='leaf.png', content_type='image/jpeg'))
    assert len(raw) > 0


def test_truncated_data_raises_corrupt():
    with pytest.raises(ImageValidationError) as exc:
        validate_image(_storage(b'\xff\xd8\xff' + b'\x00' * 10))
    assert exc.value.code == 'image_corrupt'


# ── Size ──────────────────────────────────────────────────────────────────────

def test_oversized_file_rejected():
    oversized = b'\xff\xd8\xff' + b'\x00' * (MAX_SIZE_BYTES + 1)
    with pytest.raises(ImageValidationError) as exc:
        validate_image(_storage(oversized))
    assert exc.value.code == 'file_too_large'


# ── Resolution ────────────────────────────────────────────────────────────────

def test_too_small_image_rejected():
    tiny = _make_jpeg(width=100, height=100)
    with pytest.raises(ImageValidationError) as exc:
        validate_image(_storage(tiny))
    assert exc.value.code == 'image_too_small'


def test_exactly_minimum_size_passes():
    raw = validate_image(_storage(_make_jpeg(width=MIN_DIMENSION, height=MIN_DIMENSION)))
    assert len(raw) > 0
