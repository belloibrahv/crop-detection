"""
data_prep.py — Dataset preparation for AgroScan NG.

Responsibilities:
  1. Validate that the local dataset directory matches the expected class list.
  2. Compute per-class sample counts and flag under-represented classes.
  3. Produce stratified train / validation / test splits (70 / 15 / 15).
  4. Optionally copy the split files into separate output directories or
     write CSV manifests for use in train.py.

Expected source layout:
  data/raw/
    Cassava/
      Cassava Mosaic Disease/
        img001.jpg
        ...
      Cassava Healthy/
        ...
    Maize/
      ...

Usage:
  python ml/data_prep.py --data-dir data/raw --output-dir data/splits
"""
import argparse
import csv
import json
import os
import random
from collections import defaultdict
from pathlib import Path

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
SPLIT_RATIOS = (0.70, 0.15, 0.15)   # train / val / test
MIN_SAMPLES_WARNING = 100            # warn if a class has fewer than this


def collect_samples(data_dir: Path) -> dict[str, list[Path]]:
    """Walk data_dir and return {class_label: [image_path, ...]}."""
    samples: dict[str, list[Path]] = defaultdict(list)
    for crop_dir in sorted(data_dir.iterdir()):
        if not crop_dir.is_dir():
            continue
        for disease_dir in sorted(crop_dir.iterdir()):
            if not disease_dir.is_dir():
                continue
            label = f"{crop_dir.name}/{disease_dir.name}"
            for img in disease_dir.iterdir():
                if img.suffix.lower() in VALID_EXTENSIONS:
                    samples[label].append(img)
    return dict(samples)


def stratified_split(
    samples: dict[str, list[Path]],
    ratios: tuple[float, float, float] = SPLIT_RATIOS,
    seed: int = 42,
) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]], list[tuple[Path, str]]]:
    """Return (train, val, test) lists of (path, label) tuples."""
    rng = random.Random(seed)
    train, val, test = [], [], []
    for label, paths in samples.items():
        shuffled = paths.copy()
        rng.shuffle(shuffled)
        n = len(shuffled)
        n_train = int(n * ratios[0])
        n_val   = int(n * ratios[1])
        train += [(p, label) for p in shuffled[:n_train]]
        val   += [(p, label) for p in shuffled[n_train:n_train + n_val]]
        test  += [(p, label) for p in shuffled[n_train + n_val:]]
    return train, val, test


def write_manifest(rows: list[tuple[Path, str]], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['path', 'label'])
        for path, label in rows:
            writer.writerow([str(path), label])


def main(data_dir: str, output_dir: str) -> None:
    src = Path(data_dir)
    out = Path(output_dir)

    if not src.exists():
        raise SystemExit(f"Data directory not found: {src}")

    print(f"Scanning {src} …")
    samples = collect_samples(src)

    if not samples:
        raise SystemExit("No images found. Check your directory structure.")

    print(f"\nFound {sum(len(v) for v in samples.values())} images across {len(samples)} classes:\n")
    class_counts: dict[str, int] = {}
    for label, paths in sorted(samples.items()):
        count = len(paths)
        class_counts[label] = count
        warn = " ⚠️  (< recommended minimum)" if count < MIN_SAMPLES_WARNING else ""
        print(f"  {label}: {count}{warn}")

    # Save class stats
    stats_path = out / 'class_stats.json'
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with stats_path.open('w') as f:
        json.dump(class_counts, f, indent=2)
    print(f"\nClass stats saved → {stats_path}")

    # Stratified split
    train, val, test = stratified_split(samples)
    print(f"\nSplit sizes: train={len(train)}, val={len(val)}, test={len(test)}")

    write_manifest(train, out / 'train.csv')
    write_manifest(val,   out / 'val.csv')
    write_manifest(test,  out / 'test.csv')
    print(f"Manifests saved → {out}/{{train,val,test}}.csv")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare AgroScan NG dataset splits.')
    parser.add_argument('--data-dir',    default='data/raw',    help='Root of raw image data')
    parser.add_argument('--output-dir',  default='data/splits', help='Where to write CSV manifests')
    args = parser.parse_args()
    main(args.data_dir, args.output_dir)
