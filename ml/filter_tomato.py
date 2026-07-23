"""
filter_tomato.py — Filter dataset to only Tomato classes for faster training.
"""
import csv
from pathlib import Path

# Tomato classes only
TOMATO_CLASSES = {
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
    """Filter CSV to only include Tomato classes."""
    count = 0
    with open(input_csv) as infile, open(output_csv, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=['path', 'label'])
        writer.writeheader()
        
        for row in reader:
            if row['label'] in TOMATO_CLASSES:
                writer.writerow(row)
                count += 1
    
    return count

def main():
    base_dir = Path("data/splits")
    
    # Filter all three splits
    for split in ['train_balanced', 'val_balanced', 'test_balanced']:
        input_file = base_dir / f"{split}.csv"
        output_file = base_dir / f"{split}_tomato.csv"
        
        if not input_file.exists():
            print(f"⚠️  Input file not found: {input_file}")
            continue
        
        count = filter_csv(input_file, output_file)
        print(f"✓ {split}: {count} samples → {output_file}")
    
    print(f"\nFiltered to {len(TOMATO_CLASSES)} Tomato classes only")

if __name__ == "__main__":
    main()
