"""
fill_chapter4_tables.py
Reads the training history CSVs and evaluate.py output, then prints the
populated versions of Tables 4.4, 4.5, and 4.6/4.7 for pasting into Chapter 4.

Usage (run after training and evaluation are complete):
  ml/.venv/bin/python3 ml/fill_chapter4_tables.py \
      --phase1-csv  inference/models/v2/history_phase1.csv \
      --phase2-csv  inference/models/v2/history_phase2.csv \
      --eval-output inference/models/v2/eval_results.json
"""
import argparse, csv, json
from pathlib import Path


def print_history_table(csv_path: str, title: str) -> None:
    path = Path(csv_path)
    if not path.exists():
        print(f"  {title}: file not found at {csv_path}")
        return
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    if not rows:
        print(f"  {title}: empty file")
        return
    print(f"\n{title}")
    print(f"{'Epoch':>5} | {'Train Acc':>9} | {'Val Acc':>8} | {'Train Loss':>10} | {'Val Loss':>9}")
    print("-" * 55)
    best_val = 0.0
    best_epoch = 0
    for r in rows:
        ep  = int(r['epoch']) + 1
        ta  = float(r['accuracy'])
        va  = float(r['val_accuracy'])
        tl  = float(r['loss'])
        vl  = float(r['val_loss'])
        if va > best_val:
            best_val = va
            best_epoch = ep
        marker = " ◀ best" if ep == best_epoch else ""
        print(f"{ep:>5} | {ta:>9.4f} | {va:>8.4f} | {tl:>10.4f} | {vl:>9.4f}{marker}")
    print(f"\n  Best val_accuracy: {best_val:.4f} at epoch {best_epoch}")


def print_eval_table(eval_path: str) -> None:
    path = Path(eval_path)
    if not path.exists():
        print(f"\nEvaluation results file not found at {eval_path}")
        print("Run: ml/.venv/bin/python3 ml/evaluate.py --model-dir inference/models/v2/best_phase2.keras "
              "--test-csv data/splits/test.csv --class-indices inference/models/v2/class_indices.json "
              "--arch mobilenetv2")
        return
    with open(path) as f:
        data = json.load(f)
    print("\nTable 4.6 — Weighted Aggregate Metrics")
    print(f"  Weighted Accuracy  : {data['weighted_accuracy']:.4f}")
    print(f"  Weighted Precision : {data['weighted_precision']:.4f}")
    print(f"  Weighted Recall    : {data['weighted_recall']:.4f}")
    print(f"  Weighted F1        : {data['weighted_f1']:.4f}")
    gate = 0.93
    acc = data['weighted_accuracy']
    print(f"  Gate (NFR-2 ≥{gate}): {'✅ PASS' if acc >= gate else '❌ FAIL'}")

    if 'class_map' in data and 'per_class_precision' in data:
        print("\nTable 4.7 — Per-Class Results")
        print(f"{'Class':<45} {'Prec':>6} {'Rec':>6} {'F1':>6} {'N':>5}")
        print("-" * 70)
        for idx_str, info in sorted(data['class_map'].items(), key=lambda x: int(x[0])):
            idx = int(idx_str)
            label = f"{info['crop']} / {info['disease']}"
            p = data['per_class_precision'][idx]
            r = data['per_class_recall'][idx]
            f = data['per_class_f1'][idx]
            n = data['per_class_support'][idx]
            print(f"  {label:<43} {p:6.3f} {r:6.3f} {f:6.3f} {n:5d}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase1-csv',  default='inference/models/v2/history_phase1.csv')
    parser.add_argument('--phase2-csv',  default='inference/models/v2/history_phase2.csv')
    parser.add_argument('--eval-output', default='inference/models/v2/eval_results.json')
    args = parser.parse_args()

    print("=" * 60)
    print("CHAPTER 4 TABLE FILLER — AgroScan NG")
    print("=" * 60)
    print_history_table(args.phase1_csv, "Table 4.4 — Phase 1 Training History")
    print_history_table(args.phase2_csv, "Table 4.5 — Phase 2 Training History")
    print_eval_table(args.eval_output)
