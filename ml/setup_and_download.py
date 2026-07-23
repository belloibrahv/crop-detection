"""
setup_and_download.py
---------------------
One-shot script that:
  1. Prompts for / validates Kaggle credentials
  2. Downloads all five data sources
  3. Organises images into data/raw/<Crop>/<Disease>/
  4. Augments thin classes to 300 images minimum
  5. Runs stratified 70/15/15 split → data/splits/

Run from repo root:
  cd /Users/kudirat/Desktop/work-stuff/Tasued/crop-detection
  ml/.venv/bin/python ml/setup_and_download.py
"""

import csv
import io
import json
import os
import random
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from tqdm import tqdm

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO   = Path(__file__).parent.parent
RAW    = REPO / "data" / "raw"
TMP    = REPO / "data" / "tmp"
SPLITS = REPO / "data" / "splits"

# ─── Class directory map ──────────────────────────────────────────────────────
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

PLANTVILLAGE_MAP = {
    "Tomato___Early_blight":              "Tomato/Tomato Early Blight",
    "Tomato___Late_blight":               "Tomato/Tomato Late Blight",
    "Tomato___Bacterial_spot":            "Tomato/Tomato Bacterial Spot",
    "Tomato___Leaf_Mold":                 "Tomato/Tomato Leaf Mould",
    "Tomato___Septoria_leaf_spot":        "Tomato/Tomato Septoria Leaf Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato/Tomato Yellow Leaf Curl Virus",
    "Tomato___Tomato_mosaic_virus":       "Tomato/Tomato Mosaic Virus",
    "Tomato___healthy":                   "Tomato/Tomato Healthy",
    "Corn_(maize)___Northern_Leaf_Blight":               "Maize/Maize Leaf Blight (Northern)",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Maize/Maize Leaf Spot (Gray)",
    "Corn_(maize)___Common_rust_":                       "Maize/Maize Common Rust",
    "Corn_(maize)___healthy":                            "Maize/Maize Healthy",
}

CASSAVA_2020_MAP = {
    "0": "Cassava/Cassava Bacterial Blight",
    "1": "Cassava/Cassava Brown Streak Disease",
    "2": "Cassava/Cassava Green Mottle",
    "3": "Cassava/Cassava Mosaic Disease",
    "4": "Cassava/Cassava Healthy",
}

RICE_FOLDER_MAP = {
    "Blast":             "Rice/Rice Blast",
    "LeafBlast":         "Rice/Rice Blast",
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

TARGET_MIN = 300
IMG_EXTS   = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def ensure_dirs():
    for c in ALL_CLASSES:
        (RAW / c).mkdir(parents=True, exist_ok=True)
    SPLITS.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)


def img_files(folder: Path):
    return [p for p in folder.iterdir() if p.suffix in IMG_EXTS] if folder.exists() else []


def safe_copy(src: Path, dest_dir: Path, prefix: str = ""):
    dest = dest_dir / f"{prefix}{src.name}"
    if not dest.exists():
        shutil.copy2(src, dest)


def count(cls: str) -> int:
    return len(img_files(RAW / cls))


def kaggle_dl(kind: str, identifier: str, dest: Path) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    if kind == "competition":
        cmd = f"kaggle competitions download -c {identifier} -p {dest}"
    else:
        cmd = f"kaggle datasets download -d {identifier} -p {dest} --unzip"
    print(f"  $ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(r.stdout[-800:] if r.stdout else "")
    if r.returncode != 0:
        print(f"  [WARN] {r.stderr[-400:]}")
    return r.returncode == 0


def unzip_all(folder: Path):
    for zf in folder.glob("*.zip"):
        print(f"  Unzipping {zf.name} …")
        with zipfile.ZipFile(zf) as z:
            z.extractall(folder)
        zf.unlink()


# ─── Dataset importers ────────────────────────────────────────────────────────

def import_plantvillage(pv_root: Path):
    print("\n[PlantVillage] Importing Tomato + Maize …")
    # Try raw/color first, then bare root
    color = pv_root / "raw" / "color"
    if not color.exists():
        color = pv_root
    total = 0
    for folder in sorted(color.iterdir()) if color.exists() else []:
        if not folder.is_dir():
            continue
        target = PLANTVILLAGE_MAP.get(folder.name)
        if not target:
            continue
        dest = RAW / target
        imgs = img_files(folder)
        for img in tqdm(imgs, desc=folder.name, leave=False):
            safe_copy(img, dest, "pv_")
        total += len(imgs)
    print(f"  {total:,} images imported from PlantVillage.")


def import_cassava_2020(cass_dir: Path):
    train_csv = cass_dir / "train.csv"
    imgs_dir  = cass_dir / "train_images"
    if not train_csv.exists() or not imgs_dir.exists():
        print("  [SKIP] Cassava 2020: train_images/ not found.")
        return
    print("\n[Cassava 2020] Importing …")
    total = 0
    with open(train_csv) as f:
        rows = list(csv.DictReader(f))
    for row in tqdm(rows, desc="cassava"):
        label  = str(row.get("label", ""))
        target = CASSAVA_2020_MAP.get(label)
        if not target:
            continue
        src = imgs_dir / row["image_id"]
        if src.exists():
            safe_copy(src, RAW / target, "c20_")
            total += 1
    print(f"  {total:,} images imported from Cassava 2020.")


def import_rice(rice_root: Path):
    print("\n[Rice] Importing …")
    total = 0
    for folder in rice_root.rglob("*"):
        if not folder.is_dir():
            continue
        target = RICE_FOLDER_MAP.get(folder.name)
        if not target:
            continue
        dest = RAW / target
        imgs = img_files(folder)
        for img in tqdm(imgs, desc=folder.name, leave=False):
            safe_copy(img, dest, "rice_")
        total += len(imgs)
    print(f"  {total:,} images imported from Rice dataset.")


def import_mendeley_rice(dl_dir: Path):
    """Mendeley Rice Leaf Diseases (dwtn3c6w6p) — 3 classes."""
    MEND_RICE = {
        "Bacterial Blight": "Rice/Rice Bacterial Leaf Blight",
        "Brown Spot":       "Rice/Rice Brown Spot",
        "Leaf Smut":        "Rice/Rice Blast",  # closest available
    }
    print("\n[Mendeley Rice] Importing …")
    total = 0
    for folder in dl_dir.rglob("*"):
        if not folder.is_dir():
            continue
        target = MEND_RICE.get(folder.name)
        if not target:
            continue
        imgs = img_files(folder)
        for img in tqdm(imgs, desc=folder.name, leave=False):
            safe_copy(img, RAW / target, "mr_")
        total += len(imgs)
    print(f"  {total:,} images imported from Mendeley Rice.")


def import_ccmt(ccmt_root: Path):
    """CCMT (Mendeley bwh3zbpkpv) — Cassava/Maize/Tomato."""
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
    print("\n[CCMT] Importing …")
    total = 0
    for folder in ccmt_root.rglob("*"):
        if not folder.is_dir():
            continue
        key    = folder.name.lower()
        target = CCMT_MAP.get(key)
        if target is None and key == "healthy":
            parent = folder.parent.name.lower()
            target = CROP_HEALTHY.get(parent)
        if not target:
            continue
        imgs = img_files(folder)
        for img in tqdm(imgs, desc=folder.name, leave=False):
            safe_copy(img, RAW / target, "ccmt_")
        total += len(imgs)
    print(f"  {total:,} images imported from CCMT.")


# ─── Augmentation ─────────────────────────────────────────────────────────────

def augment_class(cls: str, target: int, rng: random.Random):
    d    = RAW / cls
    imgs = img_files(d)
    n    = len(imgs)
    if n == 0:
        return 0
    needed = target - n
    if needed <= 0:
        return 0
    aug_i = 0
    while aug_i < needed:
        src = rng.choice(imgs)
        try:
            img = Image.open(src).convert("RGB")
        except Exception:
            continue
        # pipeline
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
        w, h   = img.size
        sc     = rng.uniform(0.82, 1.0)
        nw, nh = int(w * sc), int(h * sc)
        l      = rng.randint(0, w - nw)
        t      = rng.randint(0, h - nh)
        img    = img.crop((l, t, l + nw, t + nh)).resize((w, h), Image.LANCZOS)
        img.save(d / f"aug_{aug_i:06d}.jpg", format="JPEG", quality=88)
        aug_i += 1
    return needed


def augment_all():
    print("\n[Augmentation] Filling thin classes …")
    rng   = random.Random(42)
    total = 0
    for cls in ALL_CLASSES:
        n = count(cls)
        if n == 0:
            print(f"  ⚠  {cls}: 0 real images — collect real photos first.")
            continue
        if n < TARGET_MIN:
            added = augment_class(cls, TARGET_MIN, rng)
            print(f"  {cls}: {n} → {n + added}")
            total += added
    print(f"  Total augmented: {total:,}")


# ─── Splits ───────────────────────────────────────────────────────────────────

def make_splits(seed: int = 42):
    print("\n[Splits] Building 70/15/15 stratified split …")
    rng  = random.Random(seed)
    rows = {"train": [], "val": [], "test": []}
    for cls in ALL_CLASSES:
        imgs = img_files(RAW / cls)
        if not imgs:
            continue
        rng.shuffle(imgs)
        n  = len(imgs)
        n1 = int(n * 0.70)
        n2 = int(n * 0.85)
        rows["train"] += [(str(p), cls) for p in imgs[:n1]]
        rows["val"]   += [(str(p), cls) for p in imgs[n1:n2]]
        rows["test"]  += [(str(p), cls) for p in imgs[n2:]]

    for split, data in rows.items():
        rng.shuffle(data)
        out = SPLITS / f"{split}.csv"
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "label"])
            w.writerows(data)
        print(f"  {split:5s}: {len(data):,} rows → {out}")


# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "=" * 62)
    print("DATASET SUMMARY")
    print("=" * 62)
    grand = 0
    for cls in ALL_CLASSES:
        n    = count(cls)
        flag = "⚠  " if n < TARGET_MIN else "✓  "
        print(f"  {flag}{cls:<45} {n:>6}")
        grand += n
    print(f"\n  Total: {grand:,} images")
    print(f"  Output: {RAW.resolve()}")


# ─── Kaggle auth check ────────────────────────────────────────────────────────

def check_kaggle_auth() -> bool:
    r = subprocess.run("kaggle datasets list --max-size 1 2>&1",
                       shell=True, capture_output=True, text=True)
    return "401" not in r.stderr and "Authentication" not in r.stdout


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 62)
    print("AgroScan NG — Full Data Acquisition & Split")
    print("=" * 62)

    ensure_dirs()

    # ── Kaggle auth check ─────────────────────────────────────────────────────
    kaggle_ok = check_kaggle_auth()
    if not kaggle_ok:
        print("""
[!] Kaggle credentials not found.

To download Cassava 2020 (~26 k images) and Rice datasets:
  1. Go to: https://www.kaggle.com/settings
  2. API section → click "Create New Token"
  3. Save the downloaded kaggle.json to: ~/.kaggle/kaggle.json
  4. Run: chmod 600 ~/.kaggle/kaggle.json
  5. Accept competition rules at:
       https://www.kaggle.com/competitions/cassava-leaf-disease-classification/data
  6. Re-run this script.

Continuing with non-Kaggle sources only …
""")

    # ── 1. PlantVillage (already cloning in background via git) ───────────────
    pv_dir = TMP / "plantvillage"
    color  = pv_dir / "raw" / "color"
    # Check if the git pull already finished
    if color.exists() and any(color.iterdir()):
        import_plantvillage(pv_dir)
    else:
        print("\n[1] PlantVillage still cloning (or not started) — skipping for now.")
        print(f"    Will import if found at: {pv_dir}")
        # Try importing whatever is already there
        if pv_dir.exists():
            import_plantvillage(pv_dir)

    # ── 2. Cassava 2020 (Kaggle competition) ─────────────────────────────────
    cass_dir = TMP / "cassava2020"
    if kaggle_ok:
        print("\n[2] Downloading Cassava 2020 competition …")
        if not (cass_dir / "train_images").exists():
            ok = kaggle_dl("competition", "cassava-leaf-disease-classification", cass_dir)
            if ok:
                unzip_all(cass_dir)
        import_cassava_2020(cass_dir)
    else:
        if (cass_dir / "train_images").exists():
            import_cassava_2020(cass_dir)

    # ── 3. Rice disease (Kaggle datasets) ────────────────────────────────────
    rice_dir = TMP / "rice"
    if kaggle_ok:
        print("\n[3] Downloading Rice Leaf Disease datasets …")
        if not any(rice_dir.rglob("*.jpg")):
            # Primary source
            ok = kaggle_dl("dataset", "minhhuy510/rice-leaf-diseases-dataset", rice_dir)
            if not ok:
                # Fallback
                kaggle_dl("dataset", "shayanriyaz/riceleafsdiseases", rice_dir)
            # Secondary: more rice data
            kaggle_dl("dataset", "nstanto/rice-diseases-image-dataset", rice_dir)
        import_rice(rice_dir)
    else:
        if rice_dir.exists():
            import_rice(rice_dir)

    # ── 4. Mendeley Rice (no auth needed — try API) ───────────────────────────
    mend_rice_dir = TMP / "mendeley_rice"
    if not any(mend_rice_dir.rglob("*.jpg")):
        print("\n[4] Attempting Mendeley Rice download …")
        _mendeley_dl("dwtn3c6w6p", mend_rice_dir)
    import_mendeley_rice(mend_rice_dir)

    # ── 5. CCMT (Mendeley — no auth needed) ──────────────────────────────────
    ccmt_dir = TMP / "ccmt"
    if not any(ccmt_dir.rglob("*.jpg")):
        print("\n[5] Attempting CCMT (Mendeley) download …")
        _mendeley_dl("bwh3zbpkpv", ccmt_dir)
    if ccmt_dir.exists():
        import_ccmt(ccmt_dir)

    # ── 6. Augment thin classes ───────────────────────────────────────────────
    augment_all()

    # ── 7. Build splits ───────────────────────────────────────────────────────
    make_splits()

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary()
    print("""
Next step — train the model:
  ml/.venv/bin/python ml/train.py \\
    --train-csv data/splits/train.csv \\
    --val-csv   data/splits/val.csv \\
    --output    inference/models/v1
""")


def _mendeley_dl(dataset_id: str, dest: Path):
    """Download all files from a Mendeley Data dataset via public API."""
    import urllib.request
    dest.mkdir(parents=True, exist_ok=True)
    api_url = f"https://data.mendeley.com/api/datasets/{dataset_id}/files"
    try:
        import urllib.request
        with urllib.request.urlopen(api_url, timeout=20) as r:
            files = json.loads(r.read())
    except Exception as e:
        print(f"  [WARN] Mendeley API failed: {e}")
        return
    for f in files:
        url  = (f.get("content_details") or {}).get("download_url") or f.get("download_url")
        name = f.get("filename", "file.zip")
        if not url:
            continue
        out = dest / name
        if out.exists():
            continue
        print(f"  Downloading {name} ({f.get('size', '?')} bytes) …")
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(out, "wb") as fp:
                shutil.copyfileobj(r, fp)
            if out.suffix == ".zip":
                with zipfile.ZipFile(out) as z:
                    z.extractall(dest)
                out.unlink()
        except Exception as e:
            print(f"  [WARN] {e}")


if __name__ == "__main__":
    main()
