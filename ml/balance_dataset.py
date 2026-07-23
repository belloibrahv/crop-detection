"""
balance_dataset.py — Create a balanced dataset by undersampling large classes.

Target: 1,000 images per class maximum to reduce class imbalance.
"""
import csv
import random
from pathlib import Path
from collections import defaultdict

# Target maximum images per class
TARGET_MAX = 1000

def balance_csv(input_csv: Path, output_csv: Path, target_max: int = TARGET_MAX) -> int:
    """Balance CSV by undersampling classes above target_max."""
    # Group images by class
    class_images = defaultdict(list)
    with open(input_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            class_images[row['label']].append(row)
    
    # Sample from each class
    balanced_rows = []
    for label, images in class_images.items():
        if len(images) > target_max:
            sampled = random.sample(images, target_max)
            print(f"  {label}: {len(images)} → {target_max} (undersampled)")
        else:
            sampled = images
            print(f"  {label}: {len(images)} (kept)")
        balanced_rows.extend(sampled)
    
    # Shuffle and write
    random.shuffle(balanced_rows)
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'label'])
        writer.writeheader()
        writer.writerows(balanced_rows)
    
    return len(balanced_rows)

def main():
    random.seed(42)  # For reproducibility
    base_dir = Path("data/splits")
    
    print("Balancing dataset (target: 1000 images per class max)")
    print("=" * 60)
    
    for split in ['train', 'val', 'test']:
        input_file = base_dir / f"{split}.csv"
        output_file = base_dir / f"{split}_balanced.csv"
        
        if not input_file.exists():
            print(f"⚠️  Input file not found: {input_file}")
            continue
        
        count = balance_csv(input_file, output_file)
        print(f"✓ {split}: {count} samples → {output_file}")
        print()

if __name__ == "__main__":
    main()
