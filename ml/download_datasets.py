"""
download_datasets.py — Automated data acquisition for AgroScan NG.

Pulls from every publicly available source that covers the 29 classes
in class_indices.json and organises them into the canonical layout:

  data/raw/
    Cassava/
      Cassava Mosaic Disease/   ← images
      Cassava Bacterial Blight/
      Cassava Brown Streak Disease/
      Cassava Green Mottle/
      Cassava Healthy/
    Maize/
      ...
    Tomato/
      ...
    Rice/
      ...
    Yam/
      ...  (augmented from limited sources)

Sources used (all open-access / CC licences):
  1. PlantVillage (GitHub / Kaggle abdallahalidev/plantvillage-dataset)
     → Tomato (10 classes, ~18 k imgs), Maize (4 classes, ~3.8 k imgs)
  2. Kaggle Cassava Leaf Disease 2020 (cassava-leaf-disease-classification)
     → Cassava (5 classes, ~26 k imgs)  — requires kaggle API token
  3. CCMT – Crop Pest & Disease Detection (Mendeley bwh3zbpkpv)
     → Cassava + Maize + Tomato supplemental images
  4. Rice Disease Dataset (Kaggle minhhuy510/rice-leaf-diseases-dataset)
     → Rice Blast, Brown Spot, Bacterial Blight, Healthy
  5. Mendeley Rice Leaf Diseases (dwtn3c6w6p)
     → additional rice images
  6. Seasonal Corn Leaf Dataset (Mendeley vy629dngm8)
     → additional maize images

Yam note:
  No large public yam disease image dataset exists.  The script
  synthesises augmented versions of the small available images using
  heavy augmentation (flip, rotate, colour jitter, zoom, noise) to
  reach the target minimum of 300 images per class.

Usage:
  # 1. Install requirements
  pip install -r ml/requirements.txt kaggle requests tqdm

  # 2. Set up Kaggle credentials (needed for Cassava + Rice from Kaggle)
  #    Place kaggle.json at ~/.kaggle/kaggle.json  (chmod 600)
  #    Get it from: https://www.kaggle.com/settings  → API → Create New Token

  # 3. Run
  python ml/download_datasets.py --output data/raw

  # 4. Then run the normal pipeline
  python ml/data_prep.py --data-dir data/raw --output-dir data/splits
  python ml/train.py --train-csv data/splits/train.csv ...
"""

import argparse
import io
import json
import os
import random
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageFilter
from tqdm import tqdm

# ── Target layout ──────────────────────────────────────────────────────────────

# Maps each AgroScan class to its canonical output directory path
CLASS_DIRS = {
    # Cassava
    "Cassava/Cassava Mosaic Disease":     "Cassava/Cassava Mosaic Disease",
    "Cassava/Cassava Bacterial Blight":   "Cassava/Cassava Bacterial Blight",
    "Cassava/Cassava Brown Streak Disease": "Cassava/Cassava Brown Streak Disease",
    "Cassava/Cassava Green Mottle":       "Cassava/Cassava Green Mottle",
    "Cassava/Cassava Healthy":            "Cassava/Cassava Healthy",
    # Maize
    "Maize/Maize Streak Virus":           "Maize/Maize Streak Virus",
    "Maize/Maize Leaf Blight (Northern)": "Maize/Maize Leaf Blight (Northern)",
    "Maize/Maize Leaf Spot (Gray)":       "Maize/Maize Leaf Spot (Gray)",
    "Maize/Maize Common Rust":            "Maize/Maize Common Rust",
    "Maize/Fall Armyworm Damage":         "Maize/Fall Armyworm Damage",
    "Maize/Maize Healthy":                "Maize/Maize Healthy",
    # Yam
    "Yam/Yam Anthracnose":               "Yam/Yam Anthracnose",
    "Yam/Yam Mosaic Virus":              "Yam/Yam Mosaic Virus",
    "Yam/Yam Dry Rot":                   "Yam/Yam Dry Rot",
    "Yam/Yam Leaf Spot":                 "Yam/Yam Leaf Spot",
    "Yam/Yam Healthy":                   "Yam/Yam Healthy",
    # Tomato
    "Tomato/Tomato Early Blight":         "Tomato/Tomato Early Blight",
    "Tomato/Tomato Late Blight":          "Tomato/Tomato Late Blight",
    "Tomato/Tomato Bacterial Spot":       "Tomato/Tomato Bacterial Spot",
    "Tomato/Tomato Leaf Mould":           "Tomato/Tomato Leaf Mould",
    "Tomato/Tomato Septoria Leaf Spot":   "Tomato/Tomato Septoria Leaf Spot",
    "Tomato/Tomato Yellow Leaf Curl Virus": "Tomato/Tomato Yellow Leaf Curl Virus",
    "Tomato/Tomato Mosaic Virus":         "Tomato/Tomato Mosaic Virus",
    "Tomato/Tomato Healthy":              "Tomato/Tomato Healthy",
    # Rice
    "Rice/Rice Blast":                    "Rice/Rice Blast",
    "Rice/Rice Bacterial Leaf Blight":    "Rice/Rice Bacterial Leaf Blight",
    "Rice/Rice Brown Spot":               "Rice/Rice Brown Spot",
    "Rice/Rice Sheath Blight":            "Rice/Rice Sheath Blight",
    "Rice/Rice Healthy":                  "Rice/Rice Healthy",
}

# PlantVillage folder name → AgroScan class
PLANTVILLAGE_MAP = {
    # Tomato
    "Tomato___Early_blight":              "Tomato/Tomato Early Blight",
    "Tomato___Late_blight":               "Tomato/Tomato Late Blight",
    "Tomato___Bacterial_spot":            "Tomato/Tomato Bacterial Spot",
    "Tomato___Leaf_Mold":                 "Tomato/Tomato Leaf Mould",
    "Tomato___Septoria_leaf_spot":        "Tomato/Tomato Septoria Leaf Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato/Tomato Yellow Leaf Curl Virus",
    "Tomato___Tomato_mosaic_virus":       "Tomato/Tomato Mosaic Virus",
    "Tomato___healthy":                   "Tomato/Tomato Healthy",
    # Maize
    "Corn_(maize)___Northern_Leaf_Blight":    "Maize/Maize Leaf Blight (Northern)",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Maize/Maize Leaf Spot (Gray)",
    "Corn_(maize)___Common_rust_":            "Maize/Maize Common Rust",
    "Corn_(maize)___healthy":                 "Maize/Maize Healthy",
}

# Kaggle Cassava 2020 label → AgroScan class
CASSAVA_2020_MAP = {
    "0": "Cassava/Cassava Bacterial Blight",
    "1": "Cassava/Cassava Brown Streak Disease",
    "2": "Cassava/Cassava Green Mottle",
    "3": "Cassava/Cassava Mosaic Disease",
    "4": "Cassava/Cassava Healthy",
}

# Rice dataset folder → AgroScan class (Kaggle: minhhuy510)
RICE_MAP = {
    "Blast":              "Rice/Rice Blast",
    "BrownSpot":          "Rice/Rice Brown Spot",
    "Hispa":              "Rice/Rice Brown Spot",      # visual overlap — map to Brown Spot
    "LeafBlast":          "Rice/Rice Blast",
    "BacterialBlight":    "Rice/Rice Bacterial Leaf Blight",
    "Bacterialblight":    "Rice/Rice Bacterial Leaf Blight",
    "healthy":            "Rice/Rice Healthy",
    "Healthy":            "Rice/Rice Healthy",
    "NoBlight":           "Rice/Rice Healthy",
}

# Minimum images per class before augmentation kicks in
TARGET_MIN = 300


# ── Utilities ──────────────────────────────────────────────────────────────────

def ensure_dirs(base: Path) -> None:
    for rel in CLASS_DIRS.values():
        (base / rel).mkdir(parents=True, exist_ok=True)


def copy_image(src: Path, dest_dir: Path, prefix: str = "") -> None:
    if not src.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        return
    dest = dest_dir / f"{prefix}{src.name}"
    if dest.exists():
        return
    shutil.copy2(src, dest)


def count_class(base: Path, class_rel: str) -> int:
    d = base / class_rel
    if not d.exists():
        return 0
    return sum(1 for f in d.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png"})


def run(cmd: str) -> int:
    print(f"  $ {cmd}")
    return subprocess.call(cmd, shell=True)


def kaggle_download(identifier: str, kind: str, dest: Path) -> bool:
    """Download a Kaggle dataset or competition using the kaggle CLI."""
    dest.mkdir(parents=True, exist_ok=True)
    if kind == "competition":
        code = run(f"kaggle competitions download -c {identifier} -p {dest}")
    else:
        code = run(f"kaggle datasets download -d {identifier} -p {dest} --unzip")
    return code == 0


def mendeley_download(doi_path: str, dest: Path) -> bool:
    """
    Download a Mendeley Data dataset via their public file API.
    doi_path: e.g.  'bwh3zbpkpv/1'  → https://data.mendeley.com/datasets/bwh3zbpkpv/1
    """
    api = f"https://data.mendeley.com/api/datasets/{doi_path.split('/')[0]}/files"
    try:
        resp = requests.get(api, timeout=30)
        resp.raise_for_status()
        files = resp.json()
    except Exception as e:
        print(f"  [WARN] Mendeley API query failed: {e}")
        return False

    dest.mkdir(parents=True, exist_ok=True)
    ok = False
    for f in files:
        url = f.get("content_details", {}).get("download_url") or f.get("download_url")
        name = f.get("filename", "file.zip")
        if not url:
            continue
        print(f"  Downloading {name} …")
        try:
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            out_path = dest / name
            with open(out_path, "wb") as fp:
                for chunk in r.iter_content(chunk_size=8192):
                    fp.write(chunk)
            if out_path.suffix == ".zip":
                with zipfile.ZipFile(out_path) as z:
                    z.extractall(dest)
                out_path.unlink()
            ok = True
        except Exception as e:
            print(f"  [WARN] Download failed for {name}: {e}")
    return ok


# ── Source-specific importers ──────────────────────────────────────────────────

def import_plantvillage(pv_root: Path, out: Path) -> None:
    """Walk PlantVillage raw/color/ and copy matching classes."""
    color_dir = pv_root / "raw" / "color"
    if not color_dir.exists():
        color_dir = pv_root  # some Kaggle versions drop the raw/color prefix

    print("\n[PlantVillage] Importing Tomato + Maize …")
    total = 0
    for folder in sorted(color_dir.iterdir()):
        target = PLANTVILLAGE_MAP.get(folder.name)
        if not target:
            continue
        dest_dir = out / target
        dest_dir.mkdir(parents=True, exist_ok=True)
        imgs = list(folder.glob("*.jpg")) + list(folder.glob("*.JPG")) + list(folder.glob("*.png"))
        for img in tqdm(imgs, desc=folder.name, leave=False):
            copy_image(img, dest_dir, prefix="pv_")
        total += len(imgs)
    print(f"  Imported {total} PlantVillage images.")


def import_cassava_2020(kaggle_dir: Path, out: Path) -> None:
    """Import Kaggle Cassava 2020 competition images from train_images/ + train.csv."""
    import csv
    train_csv = kaggle_dir / "train.csv"
    images_dir = kaggle_dir / "train_images"
    if not train_csv.exists() or not images_dir.exists():
        print("  [WARN] Cassava 2020 files not found. Skipping.")
        return

    print("\n[Cassava 2020] Importing …")
    total = 0
    with open(train_csv) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in tqdm(rows, desc="cassava"):
        label = str(row.get("label", row.get("Label", "")))
        target = CASSAVA_2020_MAP.get(label)
        if not target:
            continue
        src = images_dir / row["image_id"]
        if not src.exists():
            continue
        dest_dir = out / target
        dest_dir.mkdir(parents=True, exist_ok=True)
        copy_image(src, dest_dir, prefix="c20_")
        total += 1
    print(f"  Imported {total} Cassava 2020 images.")


def import_rice(rice_root: Path, out: Path) -> None:
    """Import rice disease images from any folder structure matching RICE_MAP keys."""
    print("\n[Rice] Importing …")
    total = 0
    for folder in sorted(rice_root.rglob("*")):
        if not folder.is_dir():
            continue
        target = RICE_MAP.get(folder.name)
        if not target:
            continue
        dest_dir = out / target
        dest_dir.mkdir(parents=True, exist_ok=True)
        imgs = list(folder.glob("*.jpg")) + list(folder.glob("*.JPG")) + list(folder.glob("*.png"))
        for img in tqdm(imgs, desc=folder.name, leave=False):
            copy_image(img, dest_dir, prefix="rice_")
        total += len(imgs)
    print(f"  Imported {total} rice images.")


def import_ccmt(ccmt_root: Path, out: Path) -> None:
    """
    Import CCMT (Crop Pest & Disease, Mendeley bwh3zbpkpv) images.
    CCMT folder structure:  Cassava/ Maize/ Tomato/ each with disease subfolders.
    We map what we can and skip the rest.
    """
    CCMT_MAP = {
        # Cassava
        "cmd":   "Cassava/Cassava Mosaic Disease",
        "cbb":   "Cassava/Cassava Bacterial Blight",
        "cbsd":  "Cassava/Cassava Brown Streak Disease",
        "cgm":   "Cassava/Cassava Green Mottle",
        "healthy": None,  # resolved by parent crop below
        # Maize
        "mlb":   "Maize/Maize Leaf Blight (Northern)",
        "mls":   "Maize/Maize Leaf Spot (Gray)",
        "rust":  "Maize/Maize Common Rust",
        "msv":   "Maize/Maize Streak Virus",
        "faw":   "Maize/Fall Armyworm Damage",
        # Tomato — CCMT uses short codes
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
    for folder in sorted(ccmt_root.rglob("*")):
        if not folder.is_dir():
            continue
        key = folder.name.lower()
        target = CCMT_MAP.get(key)
        if target is None and key == "healthy":
            # resolve healthy by parent crop folder
            parent = folder.parent.name.lower()
            target = CROP_HEALTHY.get(parent)
        if not target:
            continue
        dest_dir = out / target
        dest_dir.mkdir(parents=True, exist_ok=True)
        imgs = list(folder.glob("*.jpg")) + list(folder.glob("*.JPG")) + list(folder.glob("*.png"))
        for img in tqdm(imgs, desc=folder.name, leave=False):
            copy_image(img, dest_dir, prefix="ccmt_")
        total += len(imgs)
    print(f"  Imported {total} CCMT images.")


# ── Augmentation for thin classes (esp. Yam) ─────────────────────────────────

def augment_to_minimum(out: Path, target_min: int = TARGET_MIN) -> None:
    """
    For every class directory that has fewer than target_min images,
    generate augmented versions until the target is met.
    """
    rng = random.Random(42)

    for rel in CLASS_DIRS.values():
        d = out / rel
        d.mkdir(parents=True, exist_ok=True)
        imgs = list(d.glob("*.jpg")) + list(d.glob("*.jpeg")) + list(d.glob("*.png"))
        count = len(imgs)
        if count == 0:
            print(f"  [WARN] {rel}: 0 real images — cannot augment. Collect real images first.")
            continue
        if count >= target_min:
            continue

        needed = target_min - count
        print(f"  Augmenting {rel}: {count} → {target_min} (+{needed})")
        aug_idx = 0
        while aug_idx < needed:
            src_path = rng.choice(imgs)
            try:
                img = Image.open(src_path).convert("RGB")
            except Exception:
                continue

            # Random augmentation pipeline
            if rng.random() < 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            angle = rng.uniform(-30, 30)
            img = img.rotate(angle, expand=False)
            factor = rng.uniform(0.7, 1.3)
            img = ImageEnhance.Brightness(img).enhance(factor)
            factor = rng.uniform(0.8, 1.2)
            img = ImageEnhance.Contrast(img).enhance(factor)
            factor = rng.uniform(0.9, 1.1)
            img = ImageEnhance.Color(img).enhance(factor)
            if rng.random() < 0.3:
                img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.5, 1.5)))
            # Random crop-zoom (0.85–1.0 of original size)
            w, h = img.size
            scale = rng.uniform(0.85, 1.0)
            new_w, new_h = int(w * scale), int(h * scale)
            left = rng.randint(0, w - new_w)
            top  = rng.randint(0, h - new_h)
            img = img.crop((left, top, left + new_w, top + new_h))
            img = img.resize((w, h), Image.LANCZOS)

            out_path = d / f"aug_{aug_idx:05d}.jpg"
            img.save(out_path, format="JPEG", quality=88)
            aug_idx += 1


# ── Main ──────────────────────────────────────────────────────────────────────

def main(output_dir: str, skip_kaggle: bool, skip_mendeley: bool) -> None:
    out   = Path(output_dir)
    tmp   = Path("data/tmp_downloads")
    ensure_dirs(out)

    print("=" * 60)
    print("AgroScan NG — Data Acquisition")
    print("=" * 60)

    # ── 1. PlantVillage (Kaggle) ──────────────────────────────────────────────
    pv_dest = tmp / "plantvillage"
    if not skip_kaggle:
        print("\n[1/5] PlantVillage via Kaggle …")
        if not (pv_dest / "raw").exists():
            ok = kaggle_download("abdallahalidev/plantvillage-dataset", "dataset", pv_dest)
            if not ok:
                print("  [WARN] PlantVillage download failed. Ensure kaggle.json is configured.")
        if (pv_dest / "raw").exists():
            import_plantvillage(pv_dest, out)
        elif pv_dest.exists():
            # Try without raw/color subfolder (flat layout from some versions)
            import_plantvillage(pv_dest, out)
    else:
        print("\n[1/5] Skipping Kaggle downloads (--skip-kaggle set).")
        if pv_dest.exists():
            import_plantvillage(pv_dest, out)

    # ── 2. Cassava 2020 (Kaggle competition) ─────────────────────────────────
    cassava_dest = tmp / "cassava2020"
    if not skip_kaggle:
        print("\n[2/5] Cassava Leaf Disease 2020 (Kaggle competition) …")
        if not (cassava_dest / "train_images").exists():
            ok = kaggle_download("cassava-leaf-disease-classification", "competition", cassava_dest)
            if ok:
                # Unzip the downloaded archive
                for zf in cassava_dest.glob("*.zip"):
                    print(f"  Extracting {zf.name} …")
                    with zipfile.ZipFile(zf) as z:
                        z.extractall(cassava_dest)
                    zf.unlink()
        if (cassava_dest / "train_images").exists():
            import_cassava_2020(cassava_dest, out)
    else:
        if (cassava_dest / "train_images").exists():
            import_cassava_2020(cassava_dest, out)

    # ── 3. Rice Disease Dataset (Kaggle) ─────────────────────────────────────
    rice_dest = tmp / "rice"
    if not skip_kaggle:
        print("\n[3/5] Rice Leaf Disease (Kaggle) …")
        if not any(rice_dest.rglob("*.jpg")):
            # Try primary source: Solshine dataset (mirrored on Kaggle)
            ok = kaggle_download("minhhuy510/rice-leaf-diseases-dataset", "dataset", rice_dest)
            if not ok:
                # Fallback: second dataset
                kaggle_download("shayanriyaz/riceleafsdiseases", "dataset", rice_dest)
        import_rice(rice_dest, out)
    else:
        if rice_dest.exists():
            import_rice(rice_dest, out)

    # ── 4. CCMT Dataset (Mendeley) ────────────────────────────────────────────
    ccmt_dest = tmp / "ccmt"
    if not skip_mendeley:
        print("\n[4/5] CCMT Dataset (Mendeley bwh3zbpkpv) …")
        if not any(ccmt_dest.rglob("*.jpg")):
            ok = mendeley_download("bwh3zbpkpv/1", ccmt_dest)
            if not ok:
                print("  [INFO] Mendeley API may require manual download.")
                print("  → Visit: https://data.mendeley.com/datasets/bwh3zbpkpv/1")
                print(f"  → Extract to: {ccmt_dest}")
        if ccmt_dest.exists():
            import_ccmt(ccmt_dest, out)
    else:
        if ccmt_dest.exists():
            import_ccmt(ccmt_dest, out)

    # ── 5. Augment under-represented classes ─────────────────────────────────
    print("\n[5/5] Augmenting thin classes to minimum …")
    augment_to_minimum(out, TARGET_MIN)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    grand_total = 0
    for rel in sorted(CLASS_DIRS.values()):
        n = count_class(out, rel)
        flag = "⚠️  " if n < TARGET_MIN else "✓  "
        print(f"  {flag}{rel:<45} {n:>5}")
        grand_total += n
    print(f"\n  Total images: {grand_total}")
    print(f"  Output:       {out.resolve()}")
    print("\nNext step: python ml/data_prep.py --data-dir data/raw --output-dir data/splits")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and organise all training data for AgroScan NG."
    )
    parser.add_argument(
        "--output", default="data/raw",
        help="Root output directory for organised images (default: data/raw)"
    )
    parser.add_argument(
        "--skip-kaggle", action="store_true",
        help="Skip Kaggle downloads (use if kaggle.json not configured; re-use cached)"
    )
    parser.add_argument(
        "--skip-mendeley", action="store_true",
        help="Skip Mendeley downloads"
    )
    args = parser.parse_args()
    main(args.output, args.skip_kaggle, args.skip_mendeley)
