"""
train_colab.py — Self-contained training script for Google Colab / Kaggle GPU.

USAGE ON GOOGLE COLAB
─────────────────────
1. Open https://colab.research.google.com → New notebook
2. Runtime → Change runtime type → T4 GPU
3. In a cell, run:

    # Mount Drive so your data persists between sessions
    from google.colab import drive
    drive.mount('/content/drive')

4. Upload the zip of your repo, or clone it:

    !git clone https://github.com/YOUR_USERNAME/crop-detection.git
    %cd crop-detection

5. Upload your data:

    # Option A — If you already ran download_missing.py locally,
    # zip data/raw and data/splits and upload them:
    from google.colab import files
    files.upload()   # upload data_raw.zip and data_splits.zip
    !unzip -q data_raw.zip    -d data/
    !unzip -q data_splits.zip -d data/

    # Option B — Let Colab re-download from Kaggle:
    !pip install -q kaggle
    # Upload your kaggle.json when prompted:
    from google.colab import files
    files.upload()   # kaggle.json
    !mkdir -p ~/.kaggle && mv kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json
    !python ml/download_missing.py

6. Install deps and run this script:

    !pip install -q tensorflow pillow tqdm
    !python ml/train_colab.py --arch efficientnetb0 --output inference/models/v2

7. Download the trained model:

    import shutil
    shutil.make_archive('models_v2', 'zip', 'inference/models/v2')
    from google.colab import files
    files.download('models_v2.zip')

USAGE ON KAGGLE NOTEBOOK
─────────────────────────
1. New Notebook → Settings → Accelerator: GPU P100
2. Add dataset: your data zip as a Kaggle dataset
3. Same steps as above — Kaggle already has TF installed

NOTE: This script is identical to ml/train.py with no local-path assumptions.
      It reads CSV paths from args so it works wherever you run it.
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

# Suppress TF info logs
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
from tensorflow import keras

print(f"TensorFlow {tf.__version__}")
print(f"GPU devices: {tf.config.list_physical_devices('GPU')}")

IMG_SIZE = (224, 224)
AUTOTUNE = tf.data.AUTOTUNE
SUPPORTED_ARCHS = ("mobilenetv2", "efficientnetb0")


# ── Helpers (identical to train.py) ──────────────────────────────────────────

def build_label_mapping(csv_path: str) -> dict:
    labels = set()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl != "label":
                labels.add(lbl)
    return {label: idx for idx, label in enumerate(sorted(labels))}


def get_preprocess_fn(arch: str):
    if arch == "efficientnetb0":
        return keras.applications.efficientnet.preprocess_input
    return keras.applications.mobilenet_v2.preprocess_input


def _make_decode_fn(n_classes, preprocess_fn):
    h, w = IMG_SIZE
    def _decode(path, label):
        raw = tf.io.read_file(path)
        img = tf.image.decode_jpeg(raw, channels=3,
                                   try_recover_truncated=True,
                                   acceptable_fraction=0.5)
        img = tf.cast(img, tf.float32)
        img = tf.image.resize(img, [h, w])
        img = preprocess_fn(img)
        return img, tf.one_hot(label, n_classes)
    return _decode


def _augment(img, label):
    img = tf.image.random_flip_left_right(img)
    img = tf.image.random_flip_up_down(img)
    k   = tf.random.uniform((), 0, 4, dtype=tf.int32)
    img = tf.image.rot90(img, k)
    img = tf.image.random_brightness(img, max_delta=0.2)
    img = tf.image.random_contrast(img, lower=0.8, upper=1.2)
    img = tf.image.random_saturation(img, lower=0.75, upper=1.25)
    img = tf.image.random_hue(img, max_delta=0.06)
    # Cutout — erase random 32×32 patch
    h, w = IMG_SIZE
    cy = tf.random.uniform((), 0, h, dtype=tf.int32)
    cx = tf.random.uniform((), 0, w, dtype=tf.int32)
    half = 16
    y1, y2 = tf.maximum(0, cy - half), tf.minimum(h, cy + half)
    x1, x2 = tf.maximum(0, cx - half), tf.minimum(w, cx + half)
    mask = tf.concat([
        tf.ones([y1, w, 3]),
        tf.concat([
            tf.ones([y2 - y1, x1, 3]),
            tf.zeros([y2 - y1, x2 - x1, 3]),
            tf.ones([y2 - y1, w - x2, 3]),
        ], axis=1),
        tf.ones([h - y2, w, 3]),
    ], axis=0)
    mask = tf.ensure_shape(mask, [h, w, 3])
    img  = img * mask
    img  = tf.clip_by_value(img, -1.0, 1.0)
    return img, label


def make_dataset(csv_path, label_to_idx, batch_size, preprocess_fn,
                 augment=False, shuffle=True):
    paths, labels = [], []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl in label_to_idx:
                paths.append(row["path"])
                labels.append(label_to_idx[lbl])
    if not paths:
        sys.exit(f"ERROR: No valid rows in {csv_path}")
    n_classes = len(label_to_idx)
    print(f"  {csv_path}: {len(paths):,} samples, {n_classes} classes")
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if shuffle:
        ds = ds.shuffle(len(paths), reshuffle_each_iteration=True, seed=42)
    decode_fn = _make_decode_fn(n_classes, preprocess_fn)
    ds = ds.map(decode_fn, num_parallel_calls=AUTOTUNE)
    if augment:
        ds = ds.map(_augment, num_parallel_calls=AUTOTUNE)
    return ds.batch(batch_size, drop_remainder=False).prefetch(AUTOTUNE)


def compute_class_weights(csv_path, label_to_idx):
    counts = Counter()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl in label_to_idx:
                counts[label_to_idx[lbl]] += 1
    total = sum(counts.values())
    n = len(counts)
    return {idx: total / (n * cnt) for idx, cnt in counts.items()}


def _head(x, n_classes):
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Dense(256, activation="relu")(x)
    x = keras.layers.Dropout(0.4)(x)
    x = keras.layers.Dense(128, activation="relu")(x)
    x = keras.layers.Dropout(0.3)(x)
    return keras.layers.Dense(n_classes, activation="softmax", name="predictions")(x)


def build_model(n_classes, arch):
    if arch == "efficientnetb0":
        base = keras.applications.EfficientNetB0(
            input_shape=(*IMG_SIZE, 3), include_top=False, weights="imagenet"
        )
        name = "agroscan_efficientnetb0"
    else:
        base = keras.applications.MobileNetV2(
            input_shape=(*IMG_SIZE, 3), include_top=False, weights="imagenet"
        )
        name = "agroscan_mobilenetv2"
    base.trainable = False
    inputs  = keras.Input(shape=(*IMG_SIZE, 3), name="image_input")
    outputs = _head(base(inputs, training=False), n_classes)
    return keras.Model(inputs, outputs, name=name)


def unfreeze_top(model, arch, pct=0.30):
    base_name = "efficientnetb0" if arch == "efficientnetb0" else "mobilenetv2_1.00_224"
    base = model.get_layer(base_name)
    base.trainable = True
    n = len(base.layers)
    cutoff = int(n * (1.0 - pct))
    for i, layer in enumerate(base.layers):
        layer.trainable = i >= cutoff
    trainable = sum(1 for l in base.layers if l.trainable)
    print(f"  Unfrozen {trainable}/{n} layers (top {pct*100:.0f}%)")


# ── Main training function ────────────────────────────────────────────────────

def train(train_csv, val_csv, output_dir, arch="efficientnetb0",
          epochs_p1=25, epochs_p2=25, batch_size=32, mixed_precision=True):

    arch = arch.lower()
    if arch not in SUPPORTED_ARCHS:
        sys.exit(f"Unknown arch '{arch}'")

    if mixed_precision:
        keras.mixed_precision.set_global_policy("mixed_float16")
        print("Mixed precision: float16 ON")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    preprocess_fn = get_preprocess_fn(arch)

    print(f"\nArchitecture : {arch.upper()}")
    print(f"Output dir   : {out.resolve()}")

    l2i       = build_label_mapping(train_csv)
    n_classes = len(l2i)
    print(f"Classes      : {n_classes}")
    for lbl, idx in sorted(l2i.items(), key=lambda x: x[1]):
        print(f"  {idx:>3}: {lbl}")

    # Export class_indices.json
    ci = {}
    for label, idx in l2i.items():
        crop, disease = label.split("/", 1)
        ci[str(idx)] = {
            "crop": crop,
            "disease": disease,
            "is_healthy": disease.lower().endswith("healthy"),
        }
    for path in [out / "class_indices.json", out.parent / "class_indices.json"]:
        with open(path, "w") as f:
            json.dump(ci, f, indent=2)
    print(f"class_indices.json saved.")

    print("\nBuilding datasets …")
    train_ds = make_dataset(train_csv, l2i, batch_size, preprocess_fn, augment=True,  shuffle=True)
    val_ds   = make_dataset(val_csv,   l2i, batch_size, preprocess_fn, augment=False, shuffle=False)
    cw       = compute_class_weights(train_csv, l2i)
    print(f"Class weight range: {min(cw.values()):.3f} – {max(cw.values()):.3f}")

    model    = build_model(n_classes, arch)
    loss_fn  = keras.losses.CategoricalCrossentropy(label_smoothing=0.1)

    # Pre-calculate steps per epoch from sample count (avoids iterating dataset)
    with open(train_csv, newline="") as _f:
        _train_n = sum(1 for row in csv.DictReader(_f) if row["label"] in l2i)
    steps_per_epoch = max(1, (_train_n + batch_size - 1) // batch_size)

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("PHASE 1 — frozen backbone")
    print(f"{'='*60}")

    steps_p1 = epochs_p1 * steps_per_epoch
    lr1 = keras.optimizers.schedules.CosineDecay(1e-3, steps_p1, alpha=1e-6)

    model.compile(optimizer=keras.optimizers.Adam(lr1), loss=loss_fn, metrics=["accuracy"])

    cb1 = [
        keras.callbacks.EarlyStopping("val_accuracy", patience=7, restore_best_weights=True, mode="max"),
        keras.callbacks.ModelCheckpoint(str(out / "best_phase1.keras"), "val_accuracy", save_best_only=True, mode="max"),
        keras.callbacks.CSVLogger(str(out / "history_phase1.csv")),
    ]

    h1     = model.fit(train_ds, validation_data=val_ds, epochs=epochs_p1, class_weight=cw, callbacks=cb1, verbose=1)
    best1  = max(h1.history["val_accuracy"])
    print(f"\nPhase 1 best val_accuracy: {best1:.4f}")

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("PHASE 2 — top-30% unfrozen")
    print(f"{'='*60}")

    unfreeze_top(model, arch, pct=0.30)
    steps_p2 = epochs_p2 * steps_per_epoch
    lr2 = keras.optimizers.schedules.CosineDecay(1e-4, steps_p2, alpha=1e-7)

    model.compile(optimizer=keras.optimizers.Adam(lr2), loss=loss_fn, metrics=["accuracy"])

    cb2 = [
        keras.callbacks.EarlyStopping("val_accuracy", patience=7, restore_best_weights=True, mode="max"),
        keras.callbacks.ModelCheckpoint(str(out / "best_phase2.keras"), "val_accuracy", save_best_only=True, mode="max"),
        keras.callbacks.CSVLogger(str(out / "history_phase2.csv")),
    ]

    h2     = model.fit(train_ds, validation_data=val_ds, epochs=epochs_p2, class_weight=cw, callbacks=cb2, verbose=1)
    best2  = max(h2.history["val_accuracy"])
    print(f"\nPhase 2 best val_accuracy: {best2:.4f}")

    # ── Save ──────────────────────────────────────────────────────────────────
    best_path = out / "best_phase2.keras"
    model.save(str(best_path))
    best = max(best1, best2)
    print(f"\nModel saved → {best_path.resolve()}")
    print(f"Best val accuracy : {best:.4f}  (gate: 0.93)")
    print("✓ PASS" if best >= 0.93 else "✗ FAIL — collect more data or more epochs")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--train-csv",       default="data/splits/train.csv")
    p.add_argument("--val-csv",         default="data/splits/val.csv")
    p.add_argument("--output",          default="inference/models/v1")
    p.add_argument("--arch",            default="efficientnetb0", choices=SUPPORTED_ARCHS)
    p.add_argument("--epochs-phase1",   type=int, default=25)
    p.add_argument("--epochs-phase2",   type=int, default=25)
    p.add_argument("--batch-size",      type=int, default=32)
    p.add_argument("--mixed-precision", action="store_true", default=True)
    args = p.parse_args()
    train(
        args.train_csv, args.val_csv, args.output,
        args.arch, args.epochs_phase1, args.epochs_phase2,
        args.batch_size, args.mixed_precision,
    )
