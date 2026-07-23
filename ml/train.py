"""
train.py — Fixed MobileNetV2 two-phase fine-tuning for AgroScan NG.

Bugs fixed vs previous version:
  1. Removed Keras preprocessing layers from the model graph — augmentation
     was being applied twice (once in the model, once in the data pipeline).
  2. Removed .cache() from the tf.data pipeline — it caused OOM with 40k imgs.
  3. Fixed class weight formula — was using n_classes but should use
     len(counts) to handle classes absent from training set gracefully.
  4. Fixed unfreeze_top — was searching by isinstance(keras.Model) which
     matches all submodels; now finds the base by name.
  5. Added label smoothing (0.1) — reduces overconfidence on noisy labels.
  6. Augmentation pipeline is now only in tf.data (correct place), not graph.
  7. Increased shuffle buffer to cover full dataset for proper randomisation.
  8. Added per-epoch val accuracy print so training progress is visible.

Usage:
  ml/.venv/bin/python ml/train.py \
    --train-csv  data/splits/train.csv \
    --val-csv    data/splits/val.csv \
    --output     inference/models/v1
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow import keras

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")   # suppress info/warning spam

IMG_SIZE = (224, 224)
AUTOTUNE = tf.data.AUTOTUNE


# ── Label mapping ─────────────────────────────────────────────────────────────

def build_label_mapping(csv_path: str) -> dict:
    """Sorted alphabetically so indices are stable across runs."""
    labels = set()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl != "label":          # skip header rows
                labels.add(lbl)
    return {label: idx for idx, label in enumerate(sorted(labels))}


# ── tf.data pipeline ──────────────────────────────────────────────────────────

def _decode(path: tf.Tensor, label: tf.Tensor, n_classes: int) -> tuple:
    raw  = tf.io.read_file(path)
    # decode_image handles jpg/png/gif/bmp; expand_animations=False for safety
    img  = tf.image.decode_image(raw, channels=3, expand_animations=False)
    img  = tf.cast(img, tf.float32)
    img  = tf.image.resize(img, IMG_SIZE)
    img  = tf.keras.applications.mobilenet_v2.preprocess_input(img)
    return img, tf.one_hot(label, n_classes)


def _augment(img: tf.Tensor, label: tf.Tensor) -> tuple:
    """Standard augmentation applied ONLY in the data pipeline, not in model."""
    img = tf.image.random_flip_left_right(img)
    img = tf.image.random_flip_up_down(img)
    # brightness/contrast jitter — applied in [-1,1] preprocess space
    img = tf.image.random_brightness(img, max_delta=0.15)
    img = tf.image.random_contrast(img, lower=0.85, upper=1.15)
    img = tf.image.random_saturation(img, lower=0.8, upper=1.2)
    img = tf.image.random_hue(img, max_delta=0.04)
    # Random 90° rotation via transpose trick
    k   = tf.random.uniform((), minval=0, maxval=4, dtype=tf.int32)
    img = tf.image.rot90(img, k)
    # Clip back to valid preprocess range [-1, 1]
    img = tf.clip_by_value(img, -1.0, 1.0)
    return img, label


def make_dataset(
    csv_path: str,
    label_to_idx: dict,
    batch_size: int,
    augment: bool = False,
    shuffle: bool = True,
) -> tf.data.Dataset:
    paths, labels = [], []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl in label_to_idx:
                paths.append(row["path"])
                labels.append(label_to_idx[lbl])

    if not paths:
        sys.exit(f"ERROR: No valid rows found in {csv_path}")

    n_classes = len(label_to_idx)
    print(f"  {csv_path}: {len(paths):,} samples, {n_classes} classes")

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))

    if shuffle:
        # Buffer = full dataset for proper shuffling
        ds = ds.shuffle(len(paths), reshuffle_each_iteration=True, seed=42)

    ds = ds.map(
        lambda p, l: _decode(p, l, n_classes),
        num_parallel_calls=AUTOTUNE,
    )

    if augment:
        ds = ds.map(_augment, num_parallel_calls=AUTOTUNE)

    # NOTE: No .cache() — with 40k+ images it exhausts RAM.
    # prefetch(AUTOTUNE) is sufficient to keep GPU fed.
    ds = ds.batch(batch_size, drop_remainder=False).prefetch(AUTOTUNE)
    return ds


# ── Class weights (balanced) ──────────────────────────────────────────────────

def compute_class_weights(csv_path: str, label_to_idx: dict) -> dict:
    """
    Inverse-frequency weights.  Uses only classes that actually appear in the
    CSV (not the full label_to_idx) to avoid divide-by-zero on empty classes.
    """
    counts: Counter = Counter()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl in label_to_idx:
                counts[label_to_idx[lbl]] += 1

    total       = sum(counts.values())
    n_present   = len(counts)                   # only classes with samples
    weights     = {}
    for idx, cnt in counts.items():
        # sklearn-style balanced weight: total / (n_present * count)
        weights[idx] = total / (n_present * cnt)
    return weights


# ── Model ─────────────────────────────────────────────────────────────────────

def build_model(n_classes: int) -> keras.Model:
    """
    Clean model — NO augmentation layers inside the graph.
    Augmentation lives in the data pipeline (see _augment above).
    """
    base = keras.applications.MobileNetV2(
        input_shape=(*IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    inputs = keras.Input(shape=(*IMG_SIZE, 3), name="image_input")
    x = base(inputs, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Dense(256, activation="relu")(x)
    x = keras.layers.Dropout(0.4)(x)
    x = keras.layers.Dense(128, activation="relu")(x)
    x = keras.layers.Dropout(0.3)(x)
    outputs = keras.layers.Dense(n_classes, activation="softmax", name="predictions")(x)

    model = keras.Model(inputs, outputs, name="agroscan_mobilenetv2")
    return model


def unfreeze_top(model: keras.Model, pct: float = 0.30) -> None:
    """Unfreeze the top `pct` fraction of MobileNetV2 layers for fine-tuning."""
    # Find base model by name, not isinstance — avoids matching every sub-model
    base = model.get_layer("mobilenetv2_1.00_224")
    base.trainable = True
    n = len(base.layers)
    cutoff = int(n * (1.0 - pct))
    for i, layer in enumerate(base.layers):
        layer.trainable = i >= cutoff
    trainable = sum(1 for l in base.layers if l.trainable)
    print(f"  Unfrozen {trainable}/{n} base layers (top {pct*100:.0f}%)")


# ── Training entry point ──────────────────────────────────────────────────────

def train(
    train_csv: str,
    val_csv: str,
    output_dir: str,
    epochs_p1: int = 20,
    epochs_p2: int = 20,
    batch_size: int = 32,
    mixed_precision: bool = False,
) -> None:

    if mixed_precision:
        keras.mixed_precision.set_global_policy("mixed_float16")
        print("Mixed precision: float16 enabled")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── Label mapping ─────────────────────────────────────────────────────────
    print("\nBuilding label mapping from train CSV …")
    l2i       = build_label_mapping(train_csv)
    n_classes = len(l2i)
    print(f"  {n_classes} classes found")
    for lbl, idx in sorted(l2i.items(), key=lambda x: x[1]):
        print(f"    {idx:>3}: {lbl}")

    # Export class_indices.json (must stay in sync with inference/models/)
    ci = {}
    for label, idx in l2i.items():
        crop, disease = label.split("/", 1)
        ci[str(idx)] = {
            "crop": crop,
            "disease": disease,
            "is_healthy": disease.lower().endswith("healthy"),
        }
    ci_path = out / "class_indices.json"
    with ci_path.open("w") as f:
        json.dump(ci, f, indent=2)
    print(f"  Saved {ci_path}")

    # ── Data pipelines ────────────────────────────────────────────────────────
    print("\nBuilding tf.data pipelines …")
    train_ds = make_dataset(train_csv, l2i, batch_size, augment=True,  shuffle=True)
    val_ds   = make_dataset(val_csv,   l2i, batch_size, augment=False, shuffle=False)

    cw = compute_class_weights(train_csv, l2i)
    print(f"  Class weights range: {min(cw.values()):.3f} – {max(cw.values()):.3f}")

    # ── Build model ───────────────────────────────────────────────────────────
    print("\nBuilding model …")
    model = build_model(n_classes)
    model.summary(line_length=90, print_fn=lambda s: None)  # suppress for clean output

    trainable_params = sum(
        tf.size(w).numpy() for w in model.trainable_weights
    )
    print(f"  Trainable params (phase 1): {trainable_params:,}")

    # ── Phase 1: Frozen base, train head only ─────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 1 — frozen base, head training")
    print("=" * 60)

    # Label smoothing 0.1 — reduces overconfident predictions on noisy labels
    loss_fn = keras.losses.CategoricalCrossentropy(label_smoothing=0.1)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss=loss_fn,
        metrics=["accuracy"],
    )

    callbacks_p1 = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=6,
            restore_best_weights=True, mode="max",
        ),
        keras.callbacks.ModelCheckpoint(
            str(out / "best_phase1.keras"),
            monitor="val_accuracy", save_best_only=True, mode="max",
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3,
            min_lr=1e-6, verbose=1,
        ),
        keras.callbacks.CSVLogger(str(out / "history_phase1.csv")),
    ]

    hist1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_p1,
        class_weight=cw,
        callbacks=callbacks_p1,
        verbose=1,
    )

    best_p1 = max(hist1.history["val_accuracy"])
    print(f"\n  Phase 1 best val_accuracy: {best_p1:.4f}")

    # ── Phase 2: Unfreeze top 30% of base, fine-tune ──────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2 — top-30% unfrozen, fine-tuning")
    print("=" * 60)

    unfreeze_top(model, pct=0.30)

    trainable_params_p2 = sum(
        tf.size(w).numpy() for w in model.trainable_weights
    )
    print(f"  Trainable params (phase 2): {trainable_params_p2:,}")

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-5),
        loss=loss_fn,
        metrics=["accuracy"],
    )

    callbacks_p2 = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=6,
            restore_best_weights=True, mode="max",
        ),
        keras.callbacks.ModelCheckpoint(
            str(out / "best_phase2.keras"),
            monitor="val_accuracy", save_best_only=True, mode="max",
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3,
            min_lr=1e-7, verbose=1,
        ),
        keras.callbacks.CSVLogger(str(out / "history_phase2.csv")),
    ]

    hist2 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_p2,
        class_weight=cw,
        callbacks=callbacks_p2,
        verbose=1,
    )

    best_p2 = max(hist2.history["val_accuracy"])
    print(f"\n  Phase 2 best val_accuracy: {best_p2:.4f}")

    # ── Save final SavedModel ─────────────────────────────────────────────────
    model.save(str(out))
    print(f"\n  Model saved → {out.resolve()}")
    print(f"  Final best val accuracy:  {max(best_p1, best_p2):.4f}")
    print(f"  Target (93% gate):        0.9300")
    if max(best_p1, best_p2) >= 0.93:
        print("  STATUS: ✓ PASS — ready for evaluate.py and deployment")
    else:
        print("  STATUS: ✗ Below gate — consider more data or more epochs")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Train AgroScan NG MobileNetV2 model")
    p.add_argument("--train-csv",       default="data/splits/train.csv")
    p.add_argument("--val-csv",         default="data/splits/val.csv")
    p.add_argument("--output",          default="inference/models/v1")
    p.add_argument("--epochs-phase1",   type=int, default=20)
    p.add_argument("--epochs-phase2",   type=int, default=20)
    p.add_argument("--batch-size",      type=int, default=32)
    p.add_argument("--mixed-precision", action="store_true",
                   help="float16 mixed precision — faster on NVIDIA/Apple GPU")
    args = p.parse_args()
    train(
        args.train_csv, args.val_csv, args.output,
        args.epochs_phase1, args.epochs_phase2,
        args.batch_size, args.mixed_precision,
    )
