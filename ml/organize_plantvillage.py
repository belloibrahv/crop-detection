"""
organize_plantvillage.py — Copy and rename PlantVillage data to AgroScan NG structure.

Maps PlantVillage class names to AgroScan NG class names and copies images to data/raw.
"""
import shutil
from pathlib import Path

# Source: PlantVillage dataset
source_dir = Path("/tmp/plantvillage/plantvillage dataset/color")

# Destination: AgroScan NG structure
dest_dir = Path("data/raw")

# Mapping from PlantVillage class names to AgroScan NG class names
MAPPING = {
    # Maize
    "Corn_(maize)___Common_rust_": "Maize/Maize Common Rust",
    "Corn_(maize)___Northern_Leaf_Blight": "Maize/Maize Leaf Blight (Northern)",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Maize/Maize Leaf Spot (Gray)",
    "Corn_(maize)___healthy": "Maize/Maize Healthy",
    
    # Tomato
    "Tomato___Bacterial_spot": "Tomato/Tomato Bacterial Spot",
    "Tomato___Early_blight": "Tomato/Tomato Early Blight",
    "Tomato___Late_blight": "Tomato/Tomato Late Blight",
    "Tomato___Leaf_Mold": "Tomato/Tomato Leaf Mould",
    "Tomato___Septoria_leaf_spot": "Tomato/Tomato Septoria Leaf Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato/Tomato Yellow Leaf Curl Virus",
    "Tomato___Tomato_mosaic_virus": "Tomato/Tomato Mosaic Virus",
    "Tomato___healthy": "Tomato/Tomato Healthy",
}

def main():
    if not source_dir.exists():
        raise SystemExit(f"Source directory not found: {source_dir}")
    
    total_copied = 0
    
    for pv_class, agro_class in MAPPING.items():
        src_path = source_dir / pv_class
        dest_path = dest_dir / agro_class
        
        if not src_path.exists():
            print(f"⚠️  Source not found: {pv_class}")
            continue
        
        # Create destination directory
        dest_path.mkdir(parents=True, exist_ok=True)
        
        # Count existing images in destination
        existing_images = list(dest_path.glob("*.*")) if dest_path.exists() else []
        existing_count = len(existing_images)
        
        # Copy images (skip if already exists)
        images = list(src_path.glob("*.*"))
        copied = 0
        for img in images:
            if img.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                dest_file = dest_path / img.name
                if not dest_file.exists():
                    shutil.copy2(img, dest_file)
                    copied += 1
        
        total_copied += copied
        total_in_dest = existing_count + copied
        
        print(f"✓ {agro_class}: {copied} new images (total: {total_in_dest})")
    
    print(f"\nTotal images copied: {total_copied}")
    print(f"Destination: {dest_dir.resolve()}")

if __name__ == "__main__":
    main()
