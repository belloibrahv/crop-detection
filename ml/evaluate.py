"""
evaluate.py — Model evaluation gate for AgroScan NG (SRS Section 11.5).

Loads the SavedModel at --model-dir, runs it against --test-csv, and prints
per-class + weighted accuracy / precision / recall / F1.

Exit codes:
  0  Model passes the release gate (weighted accuracy ≥ ACCURACY_GATE)
  1  Model fails the gate — do NOT promote to production

Usage:
  python ml/evaluate.py \
    --model-dir  models/v1 \
    --test-csv   data/splits/test.csv \
    --class-indices  models/v1/class_indices.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf

ACCURACY_GATE = 0.93    # NFR-2: ≥ 93% weighted test accuracy before promotion
IMG_SIZE = (224, 224)


def load_class_indices(path: str) -> dict[int, dict]:
    with open(path) as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw.items()}


def load_test_data(
    csv_path: str,
    label_to_idx: dict[str, int],
    arch: str = 'mobilenetv2',
    batch_size: int = 32,
) -> tuple[tf.data.Dataset, list[int]]:
    import csv
    if arch == 'efficientnetb0':
        preprocess_fn = tf.keras.applications.efficientnet.preprocess_input
    else:
        preprocess_fn = tf.keras.applications.mobilenet_v2.preprocess_input
    rows = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['label'] in label_to_idx:
                rows.append((row['path'], label_to_idx[row['label']]))

    paths  = [r[0] for r in rows]
    labels = [r[1] for r in rows]

    path_ds  = tf.data.Dataset.from_tensor_slices(paths)
    label_ds = tf.data.Dataset.from_tensor_slices(labels)
    ds = tf.data.Dataset.zip((path_ds, label_ds))

    def load_image(path, label):
        img = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img, channels=3, try_recover_truncated=True)
        img = tf.cast(img, tf.float32)
        img = tf.image.resize(img, IMG_SIZE)
        img = preprocess_fn(img)
        return img, label

    ds = ds.map(load_image, num_parallel_calls=tf.data.AUTOTUNE).batch(batch_size)
    return ds, labels


def weighted_metrics(
    y_true: list[int],
    y_pred: list[int],
    n_classes: int,
) -> dict:
    counts = np.zeros(n_classes, dtype=int)
    tp     = np.zeros(n_classes, dtype=int)
    fp     = np.zeros(n_classes, dtype=int)
    fn     = np.zeros(n_classes, dtype=int)

    for t, p in zip(y_true, y_pred):
        counts[t] += 1
        if t == p:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1

    precision = np.where(tp + fp > 0, tp / (tp + fp), 0.0)
    recall    = np.where(tp + fn > 0, tp / (tp + fn), 0.0)
    f1        = np.where(precision + recall > 0,
                         2 * precision * recall / (precision + recall), 0.0)

    total  = sum(counts)
    w_prec = float(np.sum(precision * counts) / total) if total else 0.0
    w_rec  = float(np.sum(recall   * counts) / total) if total else 0.0
    w_f1   = float(np.sum(f1       * counts) / total) if total else 0.0
    w_acc  = float(sum(t == p for t, p in zip(y_true, y_pred)) / total) if total else 0.0

    return {
        'weighted_accuracy':  w_acc,
        'weighted_precision': w_prec,
        'weighted_recall':    w_rec,
        'weighted_f1':        w_f1,
        'per_class_precision': precision.tolist(),
        'per_class_recall':    recall.tolist(),
        'per_class_f1':        f1.tolist(),
        'per_class_support':   counts.tolist(),
    }


def evaluate(model_dir: str, test_csv: str, class_indices_path: str) -> None:
    print(f"Loading model from {model_dir} …")
    model = tf.keras.models.load_model(model_dir)

    class_map = load_class_indices(class_indices_path)
    n_classes  = len(class_map)
    # Build label string → index mapping from class_indices.json
    label_to_idx = {
        f"{v['crop']}/{v['disease']}": k
        for k, v in class_map.items()
    }

    print(f"Running inference on {test_csv} …")
    test_ds, y_true = load_test_data(test_csv, label_to_idx, arch=args.arch)

    y_pred_probs = model.predict(test_ds, verbose=1)
    y_pred = np.argmax(y_pred_probs, axis=1).tolist()

    metrics = weighted_metrics(y_true, y_pred, n_classes)

    # ── Report ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Weighted Accuracy  : {metrics['weighted_accuracy']:.4f}")
    print(f"  Weighted Precision : {metrics['weighted_precision']:.4f}")
    print(f"  Weighted Recall    : {metrics['weighted_recall']:.4f}")
    print(f"  Weighted F1        : {metrics['weighted_f1']:.4f}")
    print()
    print(f"{'Class':<45} {'Prec':>6} {'Rec':>6} {'F1':>6} {'N':>5}")
    print("-" * 70)
    for idx, info in sorted(class_map.items()):
        label  = f"{info['crop']} / {info['disease']}"
        p = metrics['per_class_precision'][idx]
        r = metrics['per_class_recall'][idx]
        f = metrics['per_class_f1'][idx]
        n = metrics['per_class_support'][idx]
        print(f"  {label:<43} {p:6.3f} {r:6.3f} {f:6.3f} {n:5d}")

    print("=" * 60)

    # ── Save JSON results for fill_chapter4_tables.py ────────────────────────
    out_dir = Path(model_dir).parent if Path(model_dir).is_file() else Path(model_dir)
    json_out = out_dir / 'eval_results.json'
    save_data = dict(metrics)
    save_data['class_map'] = {str(k): v for k, v in class_map.items()}
    with open(json_out, 'w') as _jf:
        json.dump(save_data, _jf, indent=2)
    print(f"\n  Results saved → {json_out}")

    # ── Gate check ──────────────────────────────────────────────────────────
    acc = metrics['weighted_accuracy']
    if acc >= ACCURACY_GATE:
        print(f"\n✅ PASS — accuracy {acc:.4f} ≥ gate {ACCURACY_GATE:.2f}. Model may be promoted.")
        sys.exit(0)
    else:
        print(f"\n❌ FAIL — accuracy {acc:.4f} < gate {ACCURACY_GATE:.2f}. Do NOT promote this model.")
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate AgroScan NG model against the release gate.')
    parser.add_argument('--model-dir',       default='models/v1')
    parser.add_argument('--test-csv',        default='data/splits/test.csv')
    parser.add_argument('--class-indices',   default='models/v1/class_indices.json')
    parser.add_argument('--arch',            default='mobilenetv2',
                        choices=['mobilenetv2', 'efficientnetb0'])
    args = parser.parse_args()
    evaluate(args.model_dir, args.test_csv, args.class_indices)
