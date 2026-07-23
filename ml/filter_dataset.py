"""
filter_dataset.py — Filter dataset to only include well-represented classes.

Creates a reduced scope dataset with only Tomato and Maize classes (12 classes)
to address severe class imbalance issues.
"""
import csv
from pathlib import Path

# Classes to include (Tomato + Maize only)
TARGET_CLASSES = {
    "Maize/Maize Common Rust",
    "Maize/Maize Healthy", 
    "Maize/Maize Leaf Blight (Northern)",
    "Maize/Maize Leaf Spot (Gray)",
    "Tomato/Tomato Bacterial Spot",
    "Tomato/Tomato Early Blight",
    "Tomato/Tomato Healthy",
    "Tomato/Tomato Late Blight",
    "Tomato/Tomato Leaf Mould",
    "Tomato/Tomato Mosaic Virus",
    "Tomato/Tomato Septoria Leaf Spot",
    "Tomato/Tomato Yellow Leaf Curl Virus",
}

def filter_csv(input_csv: Path, output_csv: Path) -> int:
    """Filter CSV to only include target classes."""
    count = 0
    with open(input_csv) as infile, open(output_csv, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=['path', 'label'])
        writer.writeheader()
        
        for row in reader:
            if row['label'] in TARGET_CLASSES:
                writer.writerow(row)
                count += 1
    
    return count

def main():
    base_dir = Path("data/splits")
    
    # Filter all three splits
    for split in ['train', 'val', 'test']:
        input_file = base_dir / f"{split}.csv"
        output_file = base_dir / f"{split}_filtered.csv"
        
        if not input_file.exists():
            print(f"⚠️  Input file not found: {input_file}")
            continue
        
        count = filter_csv(input_file, output_file)
        print(f"✓ {split}: {count} samples → {output_file}")
    
    print(f"\nFiltered to {len(TARGET_CLASSES)} classes (Tomato + Maize only)")
    print(f"Excluded: Cassava (1 class), Rice (1 class)")

if __name__ == "__main__":
    main()
