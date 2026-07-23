"""
download_kaggle.py
==================
Downloads Kaggle-only datasets (Cassava 2020 + more Rice).
Requires ~/.kaggle/kaggle.json to be present.

Steps to get it:
  1. Visit https://www.kaggle.com/settings → API → "Create New Token"
  2. mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
  3. chmod 600 ~/.kaggle/kaggle.json
  4. Accept Cassava competition rules:
       https://www.kaggle.com/competitions/cassava-leaf-disease-classification/data

Then run:
  ml/.venv/bin/python ml/download_kaggle.py
"""

import csv
import os
import random
import shutil
import sys
import zipfile
from pathlib import Path

import kagglehub
from PIL import Image, ImageEnhance, ImageFilter
from tqdm import tqdm

REPO   = Path(__file__).parent.parent
RAW    = REPO / "data" / "raw"
TMP    = REPO / "data" / "tmp"
SPLITS = REPO / "data" / "splits"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

ALL_CLASSES = [
    "Cassava/Cassava Mosaic Disease",
    "Cassava/Cassava Bacterial Blight",
    "Cassava/Cassava Brown Streak Disease",
    "Cassava/Cassava Green Mottle",
    "Cassava/Cassava Healthy",
    "Maize/Maize Streak Virus",
    "Maize/Maize Leaf Blight (Northern)",
    "Maize/Maize Leaf Spot (Gray)",
    "Maize/Maize Common Rust",
    "Maize/Fall Armyworm Damage",
    "Maize/Maize Healthy",
    "Yam/Yam Anthracnose",
    "Yam/Yam Mosaic Virus",
    "Yam/Yam Dry Rot",
    "Yam/Yam Leaf Spot",
    "Yam/Yam Healthy",
    "Tomato/Tomato Early Blight",
    "Tomato/Tomato Late Blight",
    "Tomato/Tomato Bacterial Spot",
    "Tomato/Tomato Leaf Mould",
    "Tomato/Tomato Septoria Leaf Spot",
    "Tomato/Tomato Yellow Leaf Curl Virus",
    "Tomato/Tomato Mosaic Virus",
    "Tomato/Tomato Healthy",
    "Rice/Rice Blast",
    "Rice/Rice Bacterial Leaf Blight",
    "Rice/Rice Brown Spot",
    "Rice/Rice Sheath Blight",
    "Rice/Rice Healthy",
]

CASSAVA_LABEL_MAP = {
    "0": "Cassava/Cassava Bacterial Blight",
    "1": "Cassava/Cassava Brown Streak Disease",
    "2": "Cassava/Cassava Green Mottle",
    "3": "Cassava/Cassava Mosaic Disease",
    "4": "Cassava/Cassava Healthy",
}

RICE_FOLDER_MAP = {
    "Blast":             "Rice/Rice Blast",
    "LeafBlast":         "Rice/Rice Blast",
    "leaf_blast":        "Rice/Rice Blast",
    "BrownSpot":         "Rice/Rice Brown Spot",
    "Brown_spot":        "Rice/Rice Brown Spot",
    "Hispa":             "Rice/Rice Brown Spot",
    "BacterialBlight":   "Rice/Rice Bacterial Leaf Blight",
    "Bacterialblight":   "Rice/Rice Bacterial Leaf Blight",
    "bacterial_leaf_blight": "Rice/Rice Bacterial Leaf Blight",
    "healthy":           "Rice/Rice Healthy",
    "Healthy":           "Rice/Rice Healthy",
    "Normal":            "Rice/Rice Healthy",
}


def imgs(d: Path):
    if not d.exists():
        return []
    return [p for p in d.iterdir() if p.suffix in IMG_EXTS]


def safe_copy(src: Path, dest_dir: Path, prefix: str = ""):
    dest = dest_dir / f"{prefix}{src.name}"
    if not dest.exists():
        shutil.copy2(src, dest)


def count(cls: str) -> int:
    return len(imgs(RAW / cls))


def kh_dataset(ref: str, dest: Path) -> bool:
    print(f"  kagglehub: {ref}")
    try:
        path = kagglehub.dataset_download(ref)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(Path(path), dest, dirs_exist_ok=True)
        return True
    except Exception as e:
        print(f"  [WARN] {e}")
        return False


def kh_competition(name: str, dest: Path) -> bool:
    print(f"  kagglehub competition: {name}")
    try:
        path = kagglehub.competition_download(name)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(Path(path), dest, dirs_exist_ok=True)
        # unzip any archives
        for zf in dest.rglob("*.zip"):
            print(f"  Unzipping {zf.name} …")
            with zipfile.ZipFile(zf) as z:
                z.extractall(zf.parent)
            zf.unlink()
        return True
    except Exception as e:
        print(f"  [WARN] {e}")
        return False


def import_cassava_2020(cass_root: Path) -> int:
    train_csv = cass_root / "train.csv"
    imgs_dir  = cass_root / "train_images"
    if not train_csv.exists() or not imgs_dir.exists():
        print("  [SKIP] train_images/ not found")
        return 0
    total = 0
    with open(train_csv) as f:
        rows = list(csv.DictReader(f))
    for row in tqdm(rows, desc="  Cassava 2020", leave=True):
        label  = str(row.get("label", ""))
        target = CASSAVA_LABEL_MAP.get(label)
        if not target:
            continue
        src = imgs_dir / row["image_id"]
        if src.exists():
            safe_copy(src, RAW / target, "c20_")
            total += 1
    return total


def import_rice_recursive(rice_root: Path, prefix: str = "rice_") -> int:
    total = 0
    for folder in rice_root.rglob("*"):
        if not folder.is_dir():
            continue
        target = RICE_FOLDER_MAP.get(folder.name)
        if not target:
            continue
        for img in tqdm(imgs(folder), desc=f"  {folder.name}", leave=False):
            safe_copy(img, RAW / target, prefix)
            total += 1
    return total


def rebuild_splits(seed: int = 42):
    """Rebuild splits including the new Cassava/Rice data."""
    SPLITS.mkdir(parents=True, exist_ok=True)
    print("\nRebuilding 70/15/15 splits with all data …")
    rng  = random.Random(seed)
    rows = {"train": [], "val": [], "test": []}
    for cls in ALL_CLASSES:
        files = imgs(RAW / cls)
        if not files:
            continue
        rng.shuffle(files)
        n  = len(files)
        n1 = int(n * 0.70)
        n2 = int(n * 0.85)
        rows["train"] += [(str(p), cls) for p in files[:n1]]
        rows["val"]   += [(str(p), cls) for p in files[n1:n2]]
        rows["test"]  += [(str(p), cls) for p in files[n2:]]
    for split, data in rows.items():
        rng.shuffle(data)
        out = SPLITS / f"{split}.csv"
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "label"])
            w.writerows(data)
        print(f"  {split:5s}: {len(data):,} rows")


def print_summary():
    print("\n" + "=" * 64)
    print("FULL DATASET SUMMARY")
    print("=" * 64)
    grand = 0
    for cls in ALL_CLASSES:
        n    = count(cls)
        flag = "⚠  " if n < 300 else "✓  "
        print(f"  {flag}{cls:<46} {n:>6}")
        grand += n
    print(f"\n  Total: {grand:,} images across {len(ALL_CLASSES)} classes")


def check_credentials():
    token = Path.home() / ".kaggle" / "kaggle.json"
    if not token.exists():
        print("""
ERROR: Kaggle credentials not found at ~/.kaggle/kaggle.json

Steps:
  1. Go to: https://www.kaggle.com/settings
  2. API section → "Create New Token" (downloads kaggle.json)
  3. Run these commands:
       mkdir -p ~/.kaggle
       mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
       chmod 600 ~/.kaggle/kaggle.json
  4. Accept competition rules at:
       https://www.kaggle.com/competitions/cassava-leaf-disease-classification/data
  5. Re-run this script.
""")
        sys.exit(1)
    print("  Kaggle credentials found ✓")


if __name__ == "__main__":
    print("=" * 64)
    print("AgroScan NG — Kaggle Dataset Download")
    print("=" * 64)

    check_credentials()

    # ── 1. Cassava 2020 (~26k real farmer photos) ─────────────────────────────
    print("\n[1] Cassava Leaf Disease 2020 (~26k images) …")
    cass_dir = TMP / "cassava2020"
    if not (cass_dir / "train_images").exists():
        ok = kh_competition("cassava-leaf-disease-classification", cass_dir)
        if not ok:
            # fallback: dataset mirror
            kh_dataset("gauravduttakiit/cassava-leaf-disease-classification", cass_dir)
    n = import_cassava_2020(cass_dir)
    print(f"  Cassava 2020: {n:,} images imported.")

    # ── 2. Rice datasets ──────────────────────────────────────────────────────
    print("\n[2] Rice Leaf Disease datasets …")
    rice_dir = TMP / "rice_kaggle"
    if not any(rice_dir.rglob("*.jpg")):
        kh_dataset("minhhuy510/rice-leaf-diseases-dataset", rice_dir)
        kh_dataset("shayanriyaz/riceleafsdiseases", rice_dir)
        kh_dataset("nstanto/rice-diseases-image-dataset", rice_dir)
    n = import_rice_recursive(rice_dir)
    print(f"  Rice: {n:,} images imported.")

    # ── 3. Additional Maize (Seasonal Corn, Mendeley via Kaggle) ─────────────
    print("\n[3] Additional Maize data …")
    maize_dir = TMP / "maize_extra"
    if not any(maize_dir.rglob("*.jpg")):
        kh_dataset("smaranjitghose/corn-or-maize-leaf-disease-dataset", maize_dir)
    MAIZE_EXTRA_MAP = {
        "Blight":       "Maize/Maize Leaf Blight (Northern)",
        "Common_Rust":  "Maize/Maize Common Rust",
        "Gray_Leaf_Spot": "Maize/Maize Leaf Spot (Gray)",
        "Healthy":      "Maize/Maize Healthy",
    }
    n = 0
    for folder in maize_dir.rglob("*"):
        if not folder.is_dir():
            continue
        target = MAIZE_EXTRA_MAP.get(folder.name)
        if not target:
            continue
        for img in imgs(folder):
            safe_copy(img, RAW / target, "me_")
            n += 1
    print(f"  Maize extra: {n:,} images imported.")

    # ── 4. Rebuild splits with all data ───────────────────────────────────────
    rebuild_splits()
    print_summary()

    print("""
All data downloaded! Start training:

  cd /Users/kudirat/Desktop/work-stuff/Tasued/crop-detection
  ml/.venv/bin/python ml/train.py \\
    --train-csv data/splits/train.csv \\
    --val-csv   data/splits/val.csv \\
    --output    inference/models/v1

Estimated time on Apple Silicon (Metal GPU): ~2-4 hours
""")
