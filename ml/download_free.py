"""
download_free.py
Downloads all datasets that don't require Kaggle auth:
  - Mendeley Rice Leaf Diseases (CC BY 4.0)
  - Mendeley CCMT Crop Pest & Disease (CC BY 4.0)
  - Kaggle PlantVillage mirror (public, via kagglehub anonymous)

Run while you're setting up Kaggle credentials:
  ml/.venv/bin/python ml/download_free.py
"""

import csv
import json
import os
import random
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from tqdm import tqdm

REPO   = Path(__file__).parent.parent
RAW    = REPO / "data" / "raw"
TMP    = REPO / "data" / "tmp"

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

RICE_FOLDER_MAP = {
    "Blast":          "Rice/Rice Blast",
    "BrownSpot":      "Rice/Rice Brown Spot",
    "Brown_spot":     "Rice/Rice Brown Spot",
    "BacterialBlight":"Rice/Rice Bacterial Leaf Blight",
    "healthy":        "Rice/Rice Healthy",
    "Healthy":        "Rice/Rice Healthy",
    "Bacterial Blight":"Rice/Rice Bacterial Leaf Blight",
    "Brown Spot":     "Rice/Rice Brown Spot",
    "Leaf Smut":      "Rice/Rice Blast",  # closest visual match
    "Leafsmut":     "Rice/Rice Blast",  # Added for dataset
}

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
CCMT_HEALTHY = {
    "cassava": "Cassava/Cassava Healthy",
    "maize":   "Maize/Maize Healthy",
    "tomato":  "Tomato/Tomato Healthy",
}


def ensure_dirs():
    for c in ALL_CLASSES:
        (RAW / c).mkdir(parents=True, exist_ok=True)
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


def download_url(url: str, dest: Path, desc: str = "") -> bool:
    """Stream-download url → dest with a progress bar."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agroscan/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=desc or dest.name, leave=False
            ) as bar:
                while chunk := resp.read(65536):
                    f.write(chunk)
                    bar.update(len(chunk))
        return True
    except Exception as e:
        print(f"  [WARN] Download failed: {e}")
        if dest.exists():
            dest.unlink()
        return False


def mendeley_download(dataset_id: str, dest: Path) -> bool:
    """Download all files from a Mendeley Data dataset via public REST API."""
    dest.mkdir(parents=True, exist_ok=True)
    api_url = f"https://data.mendeley.com/api/datasets/{dataset_id}/files"
    print(f"  Querying Mendeley API: {dataset_id}")
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "agroscan/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            files = json.loads(r.read())
    except Exception as e:
        print(f"  [WARN] Mendeley API error: {e}")
        return False

    ok = False
    for f in files:
        cd = f.get("content_details") or {}
        url  = cd.get("download_url") or f.get("download_url") or ""
        name = f.get("filename", "")
        size = cd.get("size") or f.get("size", 0)
        if not url or not name:
            continue
        out = dest / name
        if out.exists() and out.stat().st_size > 1000:
            print(f"  Already have {name} — skipping.")
            ok = True
            continue
        print(f"  Downloading {name} ({size / 1e6:.1f} MB) …")
        if download_url(url, out, name):
            if out.suffix == ".zip":
                print(f"  Extracting {name} …")
                with zipfile.ZipFile(out) as z:
                    z.extractall(dest)
                out.unlink()
            ok = True
    return ok


def import_from_dir_recursive(src: Path, folder_map: dict, healthy_map: dict = None,
                               prefix: str = "") -> int:
    """Walk src recursively, copy images to RAW by matching folder names."""
    total = 0
    for folder in sorted(src.rglob("*")):
        if not folder.is_dir():
            continue
        key    = folder.name.lower()
        # Try exact key match
        target = folder_map.get(folder.name) or folder_map.get(key)
        # Try healthy map
        if target is None and key == "healthy" and healthy_map:
            parent = folder.parent.name.lower()
            target = healthy_map.get(parent)
        if not target:
            continue
        files = imgs(folder)
        for img in tqdm(files, desc=f"  {folder.name}", leave=False):
            safe_copy(img, RAW / target, prefix)
        total += len(files)
    return total


# ── 1. Download PlantVillage via kagglehub (anonymous works for public datasets)
def step_plantvillage():
    print("\n[1] PlantVillage Dataset (Tomato + Maize, ~22k images) …")
    pv_dir = TMP / "plantvillage"
    if not any(pv_dir.rglob("*.jpg")):
        try:
            import kagglehub
            path = kagglehub.dataset_download("abdallahalidev/plantvillage-dataset")
            src  = Path(path)
            print(f"  Downloaded to {src}")
        except Exception as e:
            print(f"  [WARN] kagglehub download failed: {e}")
            print("  Trying alternate mirror …")
            _try_pv_alternate(pv_dir)
    else:
        src = Path(kagglehub.get_cached_path("abdallahalidev/plantvillage-dataset")) # Assuming cached path is similar
        print(f"  Already downloaded ({sum(1 for _ in src.rglob('*.jpg'))} files cached)")

    # Import
    color = src / "plantvillage dataset" / "color"
    if not color.exists():
        color = src
    total = 0
    if color.exists():
        for folder in sorted(color.iterdir()):
            if not folder.is_dir():
                continue
            target = PV_MAP.get(folder.name)
            if not target:
                continue
            files = imgs(folder)
            for img in tqdm(files, desc=f"  {folder.name}", leave=False):
                safe_copy(img, RAW / target, "pv_")
            total += len(files)
    print(f"  PlantVillage: {total:,} images imported.")


def _try_pv_alternate(pv_dir: Path):
    """Fallback: download PlantVillage color.zip from alternate host."""
    urls = [
        "https://storage.googleapis.com/plantvillage-dataset/plantvillage_dataset.zip",
    ]
    for url in urls:
        out = pv_dir / "plantvillage.zip"
        if download_url(url, out, "PlantVillage"):
            with zipfile.ZipFile(out) as z:
                z.extractall(pv_dir)
            out.unlink()
            return
    print("  [WARN] All PlantVillage fallbacks failed.")


# ── 2. Mendeley Rice Leaf Diseases (dwtn3c6w6p) — 3 classes, CC BY 4.0
def step_mendeley_rice():
    print("\n[2] Mendeley Rice Leaf Diseases (CC BY 4.0) …")
    dest = TMP / "mendeley_rice"
    if not any(dest.rglob("*.jpg")):
        mendeley_download("dwtn3c6w6p", dest)
    n = import_from_dir_recursive(dest / "rice leaf diseases dataset", RICE_FOLDER_MAP, prefix="mr_")
    print(f"  Mendeley Rice: {n:,} images imported.")


def _get_ccmt_class_from_filename(filename: str) -> str | None:
    parts = filename.lower().split('_')
    if len(parts) < 3:
        return None

    # Example: 0cassava_train_bspot.JPG -> cassava, bspot
    crop_name = parts[0][1:]  # remove the leading number '0'
    disease_part = '_'.join(parts[2:]).split('.')[0]  # remove split part and extension

    # Try to match disease part directly or with modifications
    target_disease = CCMT_MAP.get(disease_part)
    if target_disease:
        return target_disease

    # Try healthy map
    if disease_part == "healthy" and crop_name in CCMT_HEALTHY:
        return CCMT_HEALTHY[crop_name]

    return None


# ── 3. Mendeley CCMT (bwh3zbpkpv) — Cassava/Maize/Tomato, CC BY 4.0
def step_mendeley_ccmt():
    print("\n[3] CCMT Crop Pest & Disease (Mendeley, CC BY 4.0) …")
    dest = TMP / "ccmt"
    if not any(dest.rglob("*.jpg")):
        mendeley_download("bwh3zbpkpv", dest)
    n = 0
    for img_path in tqdm(imgs(dest), desc="  CCMT", leave=False):
        class_name = _get_ccmt_class_from_filename(img_path.name)
        if class_name:
            safe_copy(img_path, RAW / class_name, prefix="ccmt_")
            n += 1

    print(f"  CCMT: {n:,} images imported.")


# ── 4. Augment thin classes ──────────────────────────────────────────────────
def step_augment(target_min: int = 300):
    print("\n[4] Augmenting thin classes …")
    rng   = random.Random(42)
    total = 0
    for cls in ALL_CLASSES:
        n = count(cls)
        if n == 0:
            print(f"  ⚠  {cls}: 0 real images.")
            continue
        if n < target_min:
            needed = target_min - n
            src_imgs = imgs(RAW / cls)
            added = 0
            while added < needed:
                src = rng.choice(src_imgs)
                try:
                    img = Image.open(src).convert("RGB")
                except Exception:
                    continue
                if rng.random() < 0.5:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                img = img.rotate(rng.uniform(-30, 30), expand=False)
                img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.7, 1.3))
                img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.8, 1.2))
                img = ImageEnhance.Color(img).enhance(rng.uniform(0.8, 1.2))
                w, h = img.size
                sc   = rng.uniform(0.82, 1.0)
                nw, nh = int(w * sc), int(h * sc)
                l, t = rng.randint(0, w - nw), rng.randint(0, h - nh)
                img = img.crop((l, t, l + nw, t + nh)).resize((w, h), Image.LANCZOS)
                img.save(RAW / cls / f"aug_{added:06d}.jpg", "JPEG", quality=88)
                added += 1
            print(f"  {cls}: {n} → {n + added}")
            total += added
    print(f"  Total augmented: {total:,}")


# ── 5. Build splits ──────────────────────────────────────────────────────────
def step_splits(seed: int = 42):
    splits_dir = REPO / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    print("\n[5] Building 70/15/15 stratified splits …")
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
        out = splits_dir / f"{split}.csv"
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "label"])
            w.writerows(data)
        print(f"  {split:5s}: {len(data):,} rows → {out}")


def print_summary():
    print("\n" + "=" * 64)
    print("DATASET SUMMARY")
    print("=" * 64)
    grand = 0
    for cls in ALL_CLASSES:
        n    = count(cls)
        flag = "⚠  " if n < 300 else "✓  "
        print(f"  {flag}{cls:<46} {n:>6}")
        grand += n
    print(f"\n  Total: {grand:,} images")


if __name__ == "__main__":
    ensure_dirs()
    step_plantvillage()
    step_mendeley_rice()
    step_mendeley_ccmt()
    step_augment()
    step_splits()
    print_summary()
    print("""
Free datasets done. For Cassava (~26k images) and more Rice data run:
  ml/.venv/bin/python ml/download_all.py
after setting up ~/.kaggle/kaggle.json
""")
