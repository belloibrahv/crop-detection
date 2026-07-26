"""
clean_corrupt_images.py
=======================
Scans every image in data/raw, tries to open + verify it with Pillow, and
removes files that cannot be decoded.  Also removes any file smaller than
1 KB (almost certainly a placeholder or failed download).

Run from repo root:
  ml/.venv/bin/python ml/clean_corrupt_images.py

Safe to re-run: only removes files that fail validation.
"""
import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

REPO    = Path(__file__).parent.parent
RAW     = REPO / "data" / "raw"
EXTS    = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
MIN_BYTES = 1024   # anything under 1 KB is useless


def collect_all_images() -> list[Path]:
    return [p for p in RAW.rglob("*") if p.suffix in EXTS and p.is_file()]


def is_valid(path: Path) -> bool:
    if path.stat().st_size < MIN_BYTES:
        return False
    try:
        with Image.open(path) as img:
            img.verify()          # checks header integrity
        # verify() leaves the file in a consumed state — re-open to check decode
        with Image.open(path) as img:
            img.convert("RGB")    # forces full pixel decode
        return True
    except (UnidentifiedImageError, OSError, SyntaxError, Exception):
        return False


def main():
    images = collect_all_images()
    print(f"Scanning {len(images):,} images in data/raw …")

    removed = 0
    errors  = []

    for path in tqdm(images, desc="Validating", unit="img"):
        if not is_valid(path):
            errors.append(path)
            path.unlink()
            removed += 1

    if errors:
        print(f"\nRemoved {removed} corrupt / too-small images:")
        for p in errors[:30]:
            print(f"  {p.relative_to(REPO)}")
        if len(errors) > 30:
            print(f"  … and {len(errors) - 30} more")
    else:
        print("\nAll images are valid — nothing removed.")

    print(f"\nDone. {len(images) - removed:,} images remain.")


if __name__ == "__main__":
    main()
