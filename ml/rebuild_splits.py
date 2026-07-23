"""
rebuild_splits.py
=================
Builds clean, stratified 70/15/15 splits from only classes that have real
images.  Applies a per-class ceiling (CAP) to the majority classes so that
no single class can dominate more than CAP * minority_size samples in training
— this controls the imbalance without throwing away val/test data.

Run:
  ml/.venv/bin/python ml/rebuild_splits.py
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

REPO   = Path(__file__).parent.parent
RAW    = REPO / "data" / "raw"
SPLITS = REPO / "data" / "splits"
EXTS   = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

# Maximum imbalance ratio in the training split.
# Majority class is capped at CAP × smallest-class count.
IMBALANCE_CAP = 8

SEED = 42


def collect_images() -> dict:
    """Walk data/raw and return {class_label: [Path, ...]} for non-empty classes only."""
    samples = defaultdict(list)
    for crop_dir in sorted(RAW.iterdir()):
        if not crop_dir.is_dir():
            continue
        for disease_dir in sorted(crop_dir.iterdir()):
            if not disease_dir.is_dir():
                continue
            label = f"{crop_dir.name}/{disease_dir.name}"
            imgs = [p for p in disease_dir.iterdir() if p.suffix in EXTS]
            if imgs:
                samples[label] = imgs
    return dict(samples)


def build_splits(samples: dict, seed: int = SEED, cap_ratio: int = IMBALANCE_CAP):
    rng = random.Random(seed)

    # Shuffle within each class first
    for label in samples:
        rng.shuffle(samples[label])

    # 70/15/15 per-class split
    per_class = {}
    for label, imgs in samples.items():
        n     = len(imgs)
        n_tr  = int(n * 0.70)
        n_val = int(n * 0.15)
        per_class[label] = {
            "train": imgs[:n_tr],
            "val":   imgs[n_tr : n_tr + n_val],
            "test":  imgs[n_tr + n_val :],
        }

    # Cap majority classes in the training split only
    # (val and test keep all samples for unbiased evaluation)
    train_sizes = {lbl: len(v["train"]) for lbl, v in per_class.items()}
    min_train   = min(train_sizes.values())
    max_allowed = min_train * cap_ratio

    print(f"\nClass counts (train split before capping):")
    for lbl, sz in sorted(train_sizes.items(), key=lambda x: -x[1]):
        capped = min(sz, max_allowed)
        flag   = f"  → capped to {capped}" if sz > max_allowed else ""
        print(f"  {lbl:<48} {sz:>5}{flag}")

    # Apply cap
    for label in per_class:
        tr = per_class[label]["train"]
        if len(tr) > max_allowed:
            per_class[label]["train"] = tr[:max_allowed]

    return per_class


def write_splits(per_class: dict) -> dict:
    SPLITS.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    rows = {"train": [], "val": [], "test": []}
    for label, splits in per_class.items():
        for split_name, imgs in splits.items():
            rows[split_name] += [(str(p), label) for p in imgs]

    # Shuffle each split
    for split_name in rows:
        rng.shuffle(rows[split_name])

    counts = {}
    for split_name, data in rows.items():
        out = SPLITS / f"{split_name}.csv"
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "label"])
            w.writerows(data)
        counts[split_name] = len(data)
        print(f"  {split_name:5s}: {len(data):>6,} rows  →  {out}")

    return counts


def save_class_stats(samples: dict):
    stats = {lbl: len(imgs) for lbl, imgs in sorted(samples.items())}
    out   = SPLITS / "class_stats.json"
    with open(out, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  class_stats.json saved → {out}")
    return stats


def main():
    print("=" * 62)
    print("AgroScan NG — Rebuild Splits")
    print("=" * 62)

    samples = collect_images()

    if not samples:
        raise SystemExit("No images found in data/raw. Run fix_import.py first.")

    total = sum(len(v) for v in samples.values())
    print(f"\nFound {len(samples)} non-empty classes, {total:,} total images:")
    for lbl, imgs in sorted(samples.items()):
        print(f"  {lbl:<48} {len(imgs):>6,}")

    per_class = build_splits(samples)

    print("\nWriting splits …")
    counts = write_splits(per_class)
    save_class_stats(samples)

    print(f"""
Summary
  Classes:     {len(samples)}
  Total imgs:  {total:,}
  Train rows:  {counts['train']:,}
  Val rows:    {counts['val']:,}
  Test rows:   {counts['test']:,}
  Imbalance cap: {IMBALANCE_CAP}× minority class
  (majority classes capped in training; val/test uncapped for fair eval)

Next step:
  ml/.venv/bin/python ml/train.py \\
    --train-csv data/splits/train.csv \\
    --val-csv   data/splits/val.csv \\
    --output    inference/models/v1
""")


if __name__ == "__main__":
    main()
