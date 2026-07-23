import csv
from pathlib import Path
from collections import Counter

REPO = Path(__file__).parent.parent

for split in ("train", "val", "test"):
    labels  = Counter()
    missing = []
    rows    = 0
    with open(REPO / f"data/splits/{split}.csv") as f:
        for row in csv.DictReader(f):
            rows += 1
            p = Path(row["path"])
            if not p.exists():
                missing.append(row["path"])
            labels[row["label"]] += 1

    print(f"\n=== {split.upper()} ({rows:,} rows, {len(labels)} classes) ===")
    print(f"Missing files: {len(missing)}")
    for lbl, cnt in sorted(labels.items(), key=lambda x: -x[1]):
        bar = "█" * (cnt // 100)
        print(f"  {lbl:<48} {cnt:>5}  {bar}")
    if labels:
        mn, mx = min(labels.values()), max(labels.values())
        print(f"  ratio: {mx/mn:.1f}x  (min={mn} max={mx})")
