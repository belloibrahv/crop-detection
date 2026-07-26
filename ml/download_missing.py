"""
download_missing.py
===================
Downloads the datasets needed to fill the gaps in the current 14-class model:
  - Cassava leaf disease (5 classes) via Kaggle
  - Extra Rice disease classes via Kaggle
  - Crop Pest & Disease Detection (CCMT on Kaggle) for Maize extras

After running this, call rebuild_splits.py to regenerate clean splits.

Run from repo root:
  ml/.venv/bin/python ml/download_missing.py
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).parent.parent
RAW  = REPO / "data" / "raw"
TMP  = REPO / "data" / "tmp_downloads"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

# ── Target class paths ────────────────────────────────────────────────────────
# All classes we want data for
ALL_TARGETS = {
    "Cassava/Cassava Bacterial Blight",
    "Cassava/Cassava Brown Streak Disease",
    "Cassava/Cassava Green Mottle",
    "Cassava/Cassava Mosaic Disease",
    "Cassava/Cassava Healthy",
    "Maize/Maize Streak Virus",
    "Maize/Fall Armyworm Damage",
    "Rice/Rice Bacterial Leaf Blight",
    "Rice/Rice Brown Spot",
    "Rice/Rice Sheath Blight",
    "Rice/Rice Healthy",
}

# ── Cassava 2019 Kaggle competition label map ─────────────────────────────────
# nirmalsankalana/cassava-leaf-disease-classification uses numeric labels
CASSAVA_LABEL_MAP = {
    "0": "Cassava/Cassava Bacterial Blight",
    "1": "Cassava/Cassava Brown Streak Disease",
    "2": "Cassava/Cassava Green Mottle",
    "3": "Cassava/Cassava Mosaic Disease",
    "4": "Cassava/Cassava Healthy",
}

# ── Rice folder name map ──────────────────────────────────────────────────────
RICE_MAP = {
    # nirmalsankalana/rice-leaf-disease-image
    "Bacterial Leaf Blight":  "Rice/Rice Bacterial Leaf Blight",
    "BacterialLeafBlight":    "Rice/Rice Bacterial Leaf Blight",
    "Bacterialblight":        "Rice/Rice Bacterial Leaf Blight",
    "bacterial_leaf_blight":  "Rice/Rice Bacterial Leaf Blight",
    "Brown Spot":             "Rice/Rice Brown Spot",
    "BrownSpot":              "Rice/Rice Brown Spot",
    "Brownspot":              "Rice/Rice Brown Spot",
    "brown_spot":             "Rice/Rice Brown Spot",
    "Blast":                  "Rice/Rice Blast",
    "LeafBlast":              "Rice/Rice Blast",
    "Leafsmut":               "Rice/Rice Blast",
    "blast":                  "Rice/Rice Blast",
    "Sheath Blight":          "Rice/Rice Sheath Blight",
    "SheathBlight":           "Rice/Rice Sheath Blight",
    "sheath_blight":          "Rice/Rice Sheath Blight",
    "Healthy":                "Rice/Rice Healthy",
    "healthy":                "Rice/Rice Healthy",
    "Normal":                 "Rice/Rice Healthy",
}

# ── CCMT folder map for Maize extras ─────────────────────────────────────────
CCMT_MAP = {
    # nirmalsankalana/crop-pest-and-disease-detection mirrors CCMT
    "cassava_bacterial_blight":  "Cassava/Cassava Bacterial Blight",
    "cassava_brown_streak":      "Cassava/Cassava Brown Streak Disease",
    "cassava_green_mite":        "Cassava/Cassava Green Mottle",
    "cassava_mosaic":            "Cassava/Cassava Mosaic Disease",
    "cassava_healthy":           "Cassava/Cassava Healthy",
    "maize_streak_virus":        "Maize/Maize Streak Virus",
    "maize_fall_armyworm":       "Maize/Fall Armyworm Damage",
    "maize_leaf_blight":         "Maize/Maize Leaf Blight (Northern)",
    "maize_leaf_spot":           "Maize/Maize Leaf Spot (Gray)",
    "maize_common_rust":         "Maize/Maize Common Rust",
    "maize_healthy":             "Maize/Maize Healthy",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_dirs():
    for cls in ALL_TARGETS:
        (RAW / cls).mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)


def img_files(folder: Path) -> list:
    if not folder.exists():
        return []
    return [p for p in folder.iterdir() if p.suffix in IMG_EXTS]


def count(cls: str) -> int:
    return len(img_files(RAW / cls))


def safe_copy(src: Path, dest_dir: Path, prefix: str = ""):
    dest = dest_dir / f"{prefix}{src.name}"
    if not dest.exists():
        shutil.copy2(src, dest)
        return True
    return False


def kaggle_download(ref: str, dest: Path) -> bool:
    """Download a Kaggle dataset via kaggle CLI, streaming output live."""
    dest.mkdir(parents=True, exist_ok=True)
    cmd = ["ml/.venv/bin/kaggle", "datasets", "download", "-d", ref, "-p", str(dest), "--unzip"]
    print(f"  $ {' '.join(cmd)}")
    # Use Popen so progress is printed live and we don't buffer a 2GB response
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for line in proc.stdout:
            print(f"  {line}", end="", flush=True)
        proc.wait(timeout=3600)   # 1-hour ceiling for large datasets
    except subprocess.TimeoutExpired:
        proc.kill()
        print("  [WARN] Download timed out after 1 hour.")
        return False
    if proc.returncode != 0:
        print(f"  [WARN] kaggle download exited with code {proc.returncode}")
        return False
    print(f"  Downloaded to {dest}")
    return True


def import_from_folders(src_root: Path, folder_map: dict, prefix: str) -> int:
    """Recursively walk src_root, copy images to RAW using folder_map."""
    total = 0
    for folder in sorted(src_root.rglob("*")):
        if not folder.is_dir():
            continue
        target = folder_map.get(folder.name)
        if not target:
            # Try normalised key (lower, underscores)
            key_norm = folder.name.lower().replace(" ", "_").replace("-", "_")
            target = folder_map.get(key_norm)
        if not target:
            continue
        dest = RAW / target
        dest.mkdir(parents=True, exist_ok=True)
        for img in img_files(folder):
            if safe_copy(img, dest, prefix):
                total += 1
    return total


# ── Step 1: Cassava leaf disease dataset ─────────────────────────────────────

def step_cassava():
    print("\n[Cassava] nirmalsankalana/cassava-leaf-disease-classification")
    dest = TMP / "cassava"

    # Check if already downloaded
    csv_candidates = list(dest.rglob("*.csv")) if dest.exists() else []
    if not csv_candidates:
        ok = kaggle_download("nirmalsankalana/cassava-leaf-disease-classification", dest)
        if not ok:
            print("  [SKIP] Cassava download failed.")
            return
        csv_candidates = list(dest.rglob("*.csv"))

    # Find the train CSV — contains image_id and label columns
    train_csv = None
    for c in csv_candidates:
        if "train" in c.name.lower() and c.name.endswith(".csv"):
            train_csv = c
            break
    if not train_csv:
        # fallback: any CSV with image_id column
        for c in csv_candidates:
            with open(c) as f:
                header = f.readline()
            if "image_id" in header and "label" in header:
                train_csv = c
                break

    if not train_csv:
        print(f"  [WARN] Could not find train CSV in {dest}. Files: {[p.name for p in dest.rglob('*.csv')]}")
        # Try folder-based import as fallback
        n = import_from_folders(dest, {
            "cbb": "Cassava/Cassava Bacterial Blight",
            "cbsd": "Cassava/Cassava Brown Streak Disease",
            "cgm": "Cassava/Cassava Green Mottle",
            "cmd": "Cassava/Cassava Mosaic Disease",
            "healthy": "Cassava/Cassava Healthy",
        }, "cassava_")
        print(f"  Folder import: {n} images")
        return

    # Find image directory
    img_dir = None
    for candidate in ["train_images", "train", "images"]:
        p = train_csv.parent / candidate
        if p.exists() and any(p.iterdir()):
            img_dir = p
            break
    if not img_dir:
        # Search recursively for a directory with many jpgs
        for d in dest.rglob("*"):
            if d.is_dir() and len(img_files(d)) > 100:
                img_dir = d
                break

    if not img_dir:
        print(f"  [WARN] Could not find image directory near {train_csv}")
        return

    print(f"  CSV: {train_csv}")
    print(f"  Images dir: {img_dir}")

    imported = {cls: 0 for cls in CASSAVA_LABEL_MAP.values()}
    skipped  = 0
    with open(train_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_id = row.get("image_id", "")
            label  = str(row.get("label", ""))
            target = CASSAVA_LABEL_MAP.get(label)
            if not target:
                skipped += 1
                continue
            src = img_dir / img_id
            if not src.exists():
                # try adding .jpg
                src = img_dir / f"{img_id}.jpg"
            if not src.exists():
                skipped += 1
                continue
            dest_dir = RAW / target
            dest_dir.mkdir(parents=True, exist_ok=True)
            if safe_copy(src, dest_dir, "cassava_"):
                imported[target] += 1

    for cls, n in imported.items():
        print(f"  {cls}: +{n}")
    if skipped:
        print(f"  Skipped/not found: {skipped}")


# ── Step 2: Rice disease dataset ─────────────────────────────────────────────

def step_rice():
    print("\n[Rice] nirmalsankalana/rice-leaf-disease-image")
    dest = TMP / "rice"

    already = sum(count(c) for c in [
        "Rice/Rice Bacterial Leaf Blight", "Rice/Rice Brown Spot",
        "Rice/Rice Sheath Blight", "Rice/Rice Healthy"
    ])
    if already > 500 and dest.exists() and any(dest.rglob("*.jpg")):
        print(f"  Already have {already} rice images, re-importing from cache.")
    else:
        ok = kaggle_download("nirmalsankalana/rice-leaf-disease-image", dest)
        if not ok:
            print("  [SKIP] Rice download failed.")
            return

    n = import_from_folders(dest, RICE_MAP, "rice_")
    print(f"  Rice: +{n} images imported")

    # Print per-class counts
    for cls in ["Rice/Rice Bacterial Leaf Blight", "Rice/Rice Brown Spot",
                "Rice/Rice Sheath Blight", "Rice/Rice Healthy", "Rice/Rice Blast"]:
        print(f"    {cls}: {count(cls)} total")


# ── Step 3: Crop Pest & Disease (Kaggle CCMT mirror) ─────────────────────────

def step_ccmt_kaggle():
    print("\n[CCMT/Kaggle] nirmalsankalana/crop-pest-and-disease-detection")
    dest = TMP / "ccmt_kaggle"

    existing_maize_streak = count("Maize/Maize Streak Virus")
    existing_faw          = count("Maize/Fall Armyworm Damage")
    if existing_maize_streak > 200 and existing_faw > 200:
        print(f"  Maize Streak: {existing_maize_streak}, FAW: {existing_faw} — already sufficient, skipping download.")
        return

    ok = kaggle_download("nirmalsankalana/crop-pest-and-disease-detection", dest)
    if not ok:
        print("  [SKIP] CCMT Kaggle download failed.")
        return

    # This dataset uses folder names like "maize_streak_virus", "cassava_mosaic" etc.
    n = import_from_folders(dest, CCMT_MAP, "ccmt_")
    print(f"  CCMT Kaggle: +{n} images imported")


# ── Step 4: Augment any class still below 300 ────────────────────────────────

def step_augment_thin(target_min: int = 300):
    """Augment any class that has real images but below target_min."""
    import random
    from PIL import Image, ImageEnhance, ImageFilter

    print("\n[Augmentation] Filling classes below 300 images …")
    rng   = random.Random(42)
    total = 0

    all_classes = []
    for crop_dir in sorted(RAW.iterdir()):
        if not crop_dir.is_dir():
            continue
        for disease_dir in sorted(crop_dir.iterdir()):
            if disease_dir.is_dir():
                all_classes.append(f"{crop_dir.name}/{disease_dir.name}")

    for cls in all_classes:
        imgs = img_files(RAW / cls)
        n    = len(imgs)
        if n == 0 or n >= target_min:
            continue
        needed = target_min - n
        added  = 0
        while added < needed:
            src = rng.choice(imgs)
            try:
                img = Image.open(src).convert("RGB")
            except Exception:
                continue
            if rng.random() < 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if rng.random() < 0.3:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img = img.rotate(rng.uniform(-25, 25), expand=False)
            img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.7, 1.3))
            img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.8, 1.2))
            img = ImageEnhance.Color(img).enhance(rng.uniform(0.8, 1.2))
            w, h   = img.size
            sc     = rng.uniform(0.85, 1.0)
            nw, nh = int(w * sc), int(h * sc)
            l      = rng.randint(0, max(0, w - nw))
            t      = rng.randint(0, max(0, h - nh))
            img    = img.crop((l, t, l + nw, t + nh)).resize((w, h), Image.LANCZOS)
            img.save(RAW / cls / f"aug_{added:06d}.jpg", "JPEG", quality=88)
            added += 1
        print(f"  {cls}: {n} → {n + added}")
        total += added

    print(f"  Total augmented: {total}")


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 64)
    print("DATASET SUMMARY (all classes)")
    print("=" * 64)
    grand = 0
    for crop_dir in sorted(RAW.iterdir()):
        if not crop_dir.is_dir():
            continue
        for disease_dir in sorted(crop_dir.iterdir()):
            if not disease_dir.is_dir():
                continue
            cls = f"{crop_dir.name}/{disease_dir.name}"
            n   = count(cls)
            flag = "⚠  " if n < 100 else ("→  " if n < 300 else "✓  ")
            print(f"  {flag}{cls:<50} {n:>6}")
            grand += n
    print(f"\n  Total: {grand:,} images across all classes")
    print("\nClasses still at 0 images require manual collection (Yam).")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 64)
    print("AgroScan NG — Download Missing Datasets")
    print("=" * 64)

    ensure_dirs()

    step_cassava()
    step_rice()
    step_ccmt_kaggle()
    step_augment_thin(target_min=300)

    print_summary()

    print("""
Done. Next steps:
  1. Rebuild splits:
       ml/.venv/bin/python ml/rebuild_splits.py

  2. Train on Kaggle/Colab GPU:
       See ml/train_colab.py for the ready-to-run notebook script

  3. Or train locally (slow on CPU):
       ml/.venv/bin/python ml/train.py \\
         --train-csv data/splits/train.csv \\
         --val-csv   data/splits/val.csv   \\
         --output    inference/models/v1
""")
