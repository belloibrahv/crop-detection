"""
fetch_plantvillage.py
Fetches only the 12 PlantVillage folders we need using the GitHub Contents API
(no git clone, no auth, downloads only the images we want).

Run: ml/.venv/bin/python ml/fetch_plantvillage.py
"""
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

# Folders to download → our canonical class name
FOLDERS = {
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

REPO       = Path(__file__).parent.parent
RAW        = REPO / "data" / "raw"
API_BASE   = "https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color"
RAW_BASE   = "https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/raw/color"


def api_get(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "agroscan-downloader/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def download_file(url: str, dest: Path, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agroscan-downloader/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)
            return True
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"      FAILED: {e}")
    return False


def fetch_folder(pv_folder: str, class_path: str):
    dest_dir = RAW / class_path
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in dest_dir.iterdir() if p.suffix in {".jpg", ".JPG", ".png"}}

    encoded = urllib.parse.quote(pv_folder)
    url = f"{API_BASE}/{encoded}"

    try:
        files = api_get(url)
    except Exception as e:
        print(f"  [WARN] GitHub API error for {pv_folder}: {e}")
        # Fallback: try paginated listing
        return 0

    imgs = [f for f in files if isinstance(f, dict) and
            f.get("name", "").lower().endswith((".jpg", ".png"))]

    print(f"  {class_path}: {len(imgs)} images (have {len(existing)})")

    downloaded = 0
    for i, finfo in enumerate(imgs):
        name = finfo["name"]
        if name in existing:
            downloaded += 1
            continue
        raw_url = finfo.get("download_url") or f"{RAW_BASE}/{encoded}/{urllib.parse.quote(name)}"
        dest    = dest_dir / f"pv_{name}"
        if dest.exists():
            downloaded += 1
            continue
        if download_file(raw_url, dest):
            downloaded += 1
        if (i + 1) % 100 == 0:
            print(f"    {i + 1}/{len(imgs)} …")
        # be polite to GitHub API — avoid rate limiting
        time.sleep(0.02)

    return downloaded


def main():
    import urllib.parse  # ensure available inside fetch_folder
    print("=" * 60)
    print("Downloading PlantVillage images via GitHub Contents API")
    print("=" * 60)
    total = 0
    for pv_folder, class_path in FOLDERS.items():
        total += fetch_folder(pv_folder, class_path)
    print(f"\nTotal downloaded: {total:,} images → {RAW}")


if __name__ == "__main__":
    import urllib.parse
    main()
