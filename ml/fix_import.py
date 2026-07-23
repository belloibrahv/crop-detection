"""
fix_import.py
Imports the 57k PlantVillage images already in the kagglehub cache
into data/raw/<Crop>/<Disease>/, then rebuilds splits.
Run: ml/.venv/bin/python ml/fix_import.py
"""
import shutil
import sys
from pathlib import Path

REPO     = Path(__file__).parent.parent
PV_COLOR = Path.home() / ".cache/kagglehub/datasets/abdallahalidev/plantvillage-dataset/versions/3/plantvillage dataset/color"

PV_MAP = {
    "Tomato___Early_blight":                              "Tomato/Tomato Early Blight",
    "Tomato___Late_blight":                               "Tomato/Tomato Late Blight",
    "Tomato___Bacterial_spot":                            "Tomato/Tomato Bacterial Spot",
    "Tomato___Leaf_Mold":                                 "Tomato/Tomato Leaf Mould",
    "Tomato___Septoria_leaf_spot":                        "Tomato/Tomato Septoria Leaf Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus":             "Tomato/Tomato Yellow Leaf Curl Virus",
    "Tomato___Tomato_mosaic_virus":                       "Tomato/Tomato Mosaic Virus",
    "Tomato___healthy":                                   "Tomato/Tomato Healthy",
    "Corn_(maize)___Northern_Leaf_Blight":                "Maize/Maize Leaf Blight (Northern)",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Maize/Maize Leaf Spot (Gray)",
    "Corn_(maize)___Common_rust_":                        "Maize/Maize Common Rust",
    "Corn_(maize)___healthy":                             "Maize/Maize Healthy",
}

EXTS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

def import_plantvillage():
    print(f"PlantVillage source: {PV_COLOR}")
    if not PV_COLOR.exists():
        sys.exit(f"ERROR: PlantVillage cache not found at {PV_COLOR}")

    total = 0
    for src_name, dest_class in sorted(PV_MAP.items()):
        src_dir  = PV_COLOR / src_name
        dest_dir = REPO / "data" / "raw" / dest_class
        dest_dir.mkdir(parents=True, exist_ok=True)

        if not src_dir.exists():
            print(f"  MISSING src: {src_name}")
            continue

        imgs  = [f for f in src_dir.iterdir() if f.suffix in EXTS]
        new   = 0
        for f in imgs:
            dest = dest_dir / f"pv_{f.name}"
            if not dest.exists():
                shutil.copy2(f, dest)
                new += 1
        print(f"  {dest_class:<46} total={len(imgs):>5}  new={new:>5}")
        total += len(imgs)

    print(f"\n  PlantVillage import complete: {total:,} images.")
    return total

if __name__ == "__main__":
    import_plantvillage()
    print("\nDone. Now run:  ml/.venv/bin/python ml/rebuild_splits.py")
