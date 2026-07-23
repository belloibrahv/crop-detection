"""
download_all.py
===============
Downloads all training data for AgroScan NG, organises it into
data/raw/<Crop>/<Disease>/, augments thin classes, and writes splits.

Prerequisites:
  ml/.venv/bin/python ml/kaggle_login.py   # one-time browser OAuth

Then run:
  ml/.venv/bin/python ml/download_all.py
"""

import csv
import json
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

IMG_EXTS   = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}
TARGET_MIN = 300

# ── All 29 AgroScan classes ───────────────────────────────────────────────────
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

# ── Source mappings ───────────────────────────────────────────────────────────

PV_MAP = {
    "Tomato___Early_blight":               "Tomato/Tomato Early Blight",
    "Tomato___Late_blight":                "Tomato/Tomato Late Blight",
    "Tomato___Bacterial_spot":             "Tomato/Tomato Bacterial Spot",
    "Tomato___Leaf_Mold":                  "Tomato/Tomato Leaf Mould",
    "Tomato___Septoria_leaf_spot":         "Tomato/Tomato Septoria Leaf Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato/Tomato Yellow Leaf Curl Virus",
    "Tomato___Tomato_mosaic_virus":        "Tomato/Tomato Mosaic Virus",
    "Tomato___healthy":                    "Tomato/Tomato Healthy",
    "Corn_(maize)___Northern_Leaf_Blight":               "Maize/Maize Leaf Blight (Northern)",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Maize/Maize Leaf Spot (Gray)",
    "Corn_(maize)___Common_rust_":                       "Maize/Maize Common Rust",
    "Corn_(maize)___healthy":                            "Maize/Maize Healthy",
}

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


# ── Utilities ─────────────────────────────────────────────────────────────────

def ensure_dirs():
    for c in ALL_CLASSES:
        (RAW / c).mkdir(parents=True, exist_ok=True)
    SPLITS.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)


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


# ── Importers ─────────────────────────────────────────────────────────────────

def import_plantvillage(pv_root: Path):
    # Root is now the copied directory, which contains "plantvillage dataset"
    color = pv_root / "plantvillage dataset" / "color"
    total = 0
    if not color.exists():
        print(f"  [WARN] PlantVillage 'color' dir not found at {color} — skipping.")
        return 0
    for folder in sorted(color.iterdir()):
        if not folder.is_dir():
            continue
        target = PV_MAP.get(folder.name)
        if not target:
            continue
        dest = RAW / target
        files = imgs(folder)
        for f in tqdm(files, desc=f"  PV {folder.name}", leave=False):
            safe_copy(f, dest, "pv_")
        total += len(files)
    print(f"  PlantVillage: {total:,} images imported.")
    return total


def import_cassava_2020(cass_root: Path):
    train_csv = cass_root / "train.csv"
    imgs_dir  = cass_root / "train_images"
    if not train_csv.exists() or not imgs_dir.exists():
        print("  Cassava 2020: train_images not found — skipping.")
        return 0
    total = 0
    with open(train_csv) as f:
        rows = list(csv.DictReader(f))
    for row in tqdm(rows, desc="  Cassava 2020", leave=False):
        label  = str(row.get("label", ""))
        target = CASSAVA_LABEL_MAP.get(label)
        if not target:
            continue
        src = imgs_dir / row["image_id"]
        if src.exists():
            safe_copy(src, RAW / target, "c20_")
            total += 1
    print(f"  Cassava 2020: {total:,} images imported.")
    return total


def import_rice_recursive(rice_root: Path, prefix: str = "rice_"):
    total = 0
    for folder in rice_root.rglob("*"):
        if not folder.is_dir():
            continue
        target = RICE_FOLDER_MAP.get(folder.name)
        if not target:
            continue
        files = imgs(folder)
        for f in tqdm(files, desc=f"  Rice {folder.name}", leave=False):
            safe_copy(f, RAW / target, prefix)
        total += len(files)
    return total


def unzip_all(folder: Path):
    for zf in sorted(folder.glob("*.zip")):
        print(f"  Unzipping {zf.name} …")
        with zipfile.ZipFile(zf) as z:
            z.extractall(folder)
        zf.unlink()


# ── Download helpers ──────────────────────────────────────────────────────────

def kh_download(dataset_ref: str, dest: Path):
    """Download a Kaggle dataset into dest/ using kagglehub."""
    print(f"  Downloading {dataset_ref} …")
    try:
        path = kagglehub.dataset_download(dataset_ref)
        # kagglehub caches to ~/.cache/kagglehub; symlink/copy to our dest
        src = Path(path)
        dest.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or not any(dest.rglob("*")):
            shutil.copytree(src, dest, dirs_exist_ok=True)
        print(f"  → {dest}")
        return True
    except Exception as e:
        print(f"  [WARN] {e}")
        return False


def kh_competition(competition: str, dest: Path):
    """Download a Kaggle competition dataset."""
    print(f"  Downloading competition: {competition} …")
    try:
        path = kagglehub.competition_download(competition)
        src  = Path(path)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, dirs_exist_ok=True)
        unzip_all(dest)
        print(f"  → {dest}")
        return True
    except Exception as e:
        print(f"  [WARN] {e}")
        return False


# ── Augmentation ──────────────────────────────────────────────────────────────

def augment_class(cls: str, target: int, rng: random.Random) -> int:
    d      = RAW / cls
    files  = imgs(d)
    n      = len(files)
    needed = target - n
    if needed <= 0 or n == 0:
        return 0
    added = 0
    while added < needed:
        src = rng.choice(files)
        try:
            img = Image.open(src).convert("RGB")
        except Exception:
            continue
        if rng.random() < 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if rng.random() < 0.3:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img = img.rotate(rng.uniform(-30, 30), expand=False)
        img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.7, 1.3))
        img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.8, 1.2))
        img = ImageEnhance.Color(img).enhance(rng.uniform(0.8, 1.2))
        if rng.random() < 0.3:
            img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.2)))
        w, h = img.size
        sc   = rng.uniform(0.82, 1.0)
        nw, nh = int(w * sc), int(h * sc)
        l, t = rng.randint(0, w - nw), rng.randint(0, h - nh)
        img = img.crop((l, t, l + nw, t + nh)).resize((w, h), Image.LANCZOS)
        img.save(d / f"aug_{added:06d}.jpg", format="JPEG", quality=88)
        added += 1
    return added


def augment_all():
    print("\n[Augmentation] Filling thin classes to minimum …")
    rng   = random.Random(42)
    total = 0
    for cls in ALL_CLASSES:
        n = count(cls)
        if n == 0:
            print(f"  ⚠  {cls}: 0 images — cannot augment. Add real photos first.")
            continue
        if n < TARGET_MIN:
            added = augment_class(cls, TARGET_MIN, rng)
            print(f"  {cls}: {n} → {n + added}")
            total += added
    print(f"  Total augmented: {total:,}")


# ── Splits ────────────────────────────────────────────────────────────────────

def make_splits(seed: int = 42):
    print("\n[Splits] Building 70/15/15 stratified split …")
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
        print(f"  {split:5s}: {len(data):,} rows → {out}")


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 64)
    print("DATASET SUMMARY")
    print("=" * 64)
    grand = 0
    for cls in ALL_CLASSES:
        n    = count(cls)
        flag = "⚠  " if n < TARGET_MIN else "✓  "
        print(f"  {flag}{cls:<46} {n:>6}")
        grand += n
    print(f"\n  Total: {grand:,} images across {len(ALL_CLASSES)} classes")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 64)
    print("AgroScan NG — Full Dataset Acquisition Pipeline")
    print("=" * 64)
    ensure_dirs()

    # ── 1. PlantVillage ───────────────────────────────────────────────────────
    print("\n[1/5] PlantVillage (Tomato + Maize — ~22k images)")
    pv_dir = TMP / "plantvillage"
    if not any(pv_dir.rglob("*")):
        path = kagglehub.dataset_download("abdallahalidev/plantvillage-dataset")
        pv_root_downloaded = Path(path)
        print(f"  Downloaded to {pv_root_downloaded}")
        # Copy contents to our tmp dir to unify access
        shutil.copytree(pv_root_downloaded, pv_dir, dirs_exist_ok=True)
    import_plantvillage(pv_dir)


# ── 2. Cassava 2020 ───────────────────────────────────────────────────────
    print("\n[2/5] Cassava Leaf Disease 2020 (all 5 classes — ~26k images)")
    cass_dir = TMP / "cassava2020"
    if not (cass_dir / "train_images").exists():
        # Try competition download first; if user hasn't accepted rules, try dataset mirror
        ok = kh_competition("cassava-leaf-disease-classification", cass_dir)
        if not ok:
            # Public mirror on Kaggle datasets
            kh_download("gauravduttakiit/cassava-leaf-disease-classification", cass_dir)
    import_cassava_2020(cass_dir)

    # ── 3. Rice datasets ──────────────────────────────────────────────────────
    print("\n[3/5] Rice Leaf Disease datasets (~5k images)")
    rice_dir = TMP / "rice"
    if not any(rice_dir.rglob("*.jpg")):
        ok = kh_download("minhhuy510/rice-leaf-diseases-dataset", rice_dir)
        if not ok:
            kh_download("shayanriyaz/riceleafsdiseases", rice_dir)
        # Second rice source for more data
        kh_download("nstanto/rice-diseases-image-dataset", rice_dir)
    n = import_rice_recursive(rice_dir)
    print(f"  Rice: {n:,} images imported.")

    # ── 4. CCMT (Mendeley via Kaggle mirror) ──────────────────────────────────
    print("\n[4/5] CCMT Dataset (Cassava + Maize + Tomato supplemental)")
    ccmt_dir = TMP / "ccmt"
    if not any(ccmt_dir.rglob("*.jpg")):
        kh_download("davidefuma/ccmt-crop-pest-and-disease", ccmt_dir)
    # Import using CCMT-style folder names
    CCMT_MAP = {
        "cmd":   "Cassava/Cassava Mosaic Disease",
        "cbb":   "Cassava/Cassava Bacterial Blight",
        "cbsd":  "Cassava/Cassava Brown Streak Disease",
        "cgm":   "Cassava/Cassava Green Mottle",
        "mlb":   "Maize/Maize Leaf Blight (Northern)",
        "mls":   "Maize/Maize Leaf Spot (Gray)",
        "rust":  "Maize/Maize Common Rust",
        "msv":   "Maize/Maize Streak Virus",
        "faw":   "Maize/Fall Armyworm Damage",
        "teb":   "Tomato/Tomato Early Blight",
        "tlb":   "Tomato/Tomato Late Blight",
        "tbs":   "Tomato/Tomato Bacterial Spot",
        "tlm":   "Tomato/Tomato Leaf Mould",
        "tsp":   "Tomato/Tomato Septoria Leaf Spot",
        "tylcv": "Tomato/Tomato Yellow Leaf Curl Virus",
        "tmv":   "Tomato/Tomato Mosaic Virus",
    }
    CROP_HEALTHY = {
        "cassava": "Cassava/Cassava Healthy",
        "maize":   "Maize/Maize Healthy",
        "tomato":  "Tomato/Tomato Healthy",
    }
    ccmt_total = 0
    for folder in ccmt_dir.rglob("*"):
        if not folder.is_dir():
            continue
        key    = folder.name.lower()
        target = CCMT_MAP.get(key)
        if target is None and key == "healthy":
            target = CROP_HEALTHY.get(folder.parent.name.lower())
        if not target:
            continue
        files = imgs(folder)
        for f in tqdm(files, desc=f"  CCMT {folder.name}", leave=False):
            safe_copy(f, RAW / target, "ccmt_")
        ccmt_total += len(files)
    print(f"  CCMT: {ccmt_total:,} images imported.")

    # ── 5. Augment thin classes ───────────────────────────────────────────────
    print("\n[5/5] Augmenting thin classes …")
    augment_all()

    # ── Build splits ──────────────────────────────────────────────────────────
    make_splits()

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary()

    print(f"""
All done! Next step — start training:

  cd {REPO}
  ml/.venv/bin/python ml/train.py \\
    --train-csv data/splits/train.csv \\
    --val-csv   data/splits/val.csv \\
    --output    inference/models/v1

Training will take ~1–3 hours on Apple Silicon (Metal GPU).
""")


if __name__ == "__main__":
    main()
