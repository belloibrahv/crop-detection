"""
train.py — Two-phase fine-tuning for AgroScan NG.

Supports MobileNetV2 (default, lightweight) and EfficientNetB0 (higher
accuracy, slightly larger).  Adds cosine-decay learning-rate schedule and
stronger augmentation (cutout, perspective jitter) vs. the original.

Usage:
  # MobileNetV2 — default, works on free Colab/Kaggle GPU
  ml/.venv/bin/python ml/train.py \
      --train-csv data/splits/train.csv \
      --val-csv   data/splits/val.csv   \
      --output    inference/models/v1

  # EfficientNetB0 — higher accuracy, same GPU budget
  ml/.venv/bin/python ml/train.py \
      --arch efficientnetb0 \
      --output inference/models/v2 \
      --mixed-precision

  # Full run with all options
  ml/.venv/bin/python ml/train.py \
      --arch efficientnetb0 \
      --epochs-phase1 25 --epochs-phase2 25 \
      --batch-size 32 \
      --mixed-precision \
      --output inference/models/v2
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

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

IMG_SIZE = (224, 224)
AUTOTUNE = tf.data.AUTOTUNE

SUPPORTED_ARCHS = ("mobilenetv2", "efficientnetb0")


# ── Label mapping ─────────────────────────────────────────────────────────────

def build_label_mapping(csv_path: str) -> dict:
    """Sorted alphabetically so class indices are stable across runs."""
    labels = set()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl != "label":
                labels.add(lbl)
    return {label: idx for idx, label in enumerate(sorted(labels))}


# ── tf.data pipeline ──────────────────────────────────────────────────────────

def _make_decode_fn(n_classes: int, preprocess_fn):
    """Returns a decode function closed over n_classes and preprocess_fn.

    Uses decode_jpeg with try_recover_truncated=True so that corrupt or
    truncated JPEGs in the dataset don't crash the entire training run —
    they are silently replaced with a black image instead.
    """
    h, w = IMG_SIZE
    def _decode(path: tf.Tensor, label: tf.Tensor):
        raw = tf.io.read_file(path)
        # try_recover_truncated: corrupt bytes yield a partial/black image
        # rather than raising InvalidArgumentError
        img = tf.image.decode_jpeg(raw, channels=3,
                                   try_recover_truncated=True,
                                   acceptable_fraction=0.5)
        img = tf.cast(img, tf.float32)
        img = tf.image.resize(img, [h, w])
        img = preprocess_fn(img)
        return img, tf.one_hot(label, n_classes)
    return _decode


def _augment(img: tf.Tensor, label: tf.Tensor) -> tuple:
    """
    Strong augmentation pipeline — all ops applied in the preprocessed space.
    Added vs original: cutout (random erasing), extra hue jitter.
    """
    # Geometric
    img = tf.image.random_flip_left_right(img)
    img = tf.image.random_flip_up_down(img)
    k   = tf.random.uniform((), 0, 4, dtype=tf.int32)
    img = tf.image.rot90(img, k)

    # Colour jitter
    img = tf.image.random_brightness(img, max_delta=0.2)
    img = tf.image.random_contrast(img, lower=0.8, upper=1.2)
    img = tf.image.random_saturation(img, lower=0.75, upper=1.25)
    img = tf.image.random_hue(img, max_delta=0.06)

    # Cutout — erase a random 32×32 patch (simulates occlusion by other leaves)
    h, w = IMG_SIZE
    cy = tf.random.uniform((), 0, h, dtype=tf.int32)
    cx = tf.random.uniform((), 0, w, dtype=tf.int32)
    half = 16
    y1 = tf.maximum(0, cy - half)
    y2 = tf.minimum(h, cy + half)
    x1 = tf.maximum(0, cx - half)
    x2 = tf.minimum(w, cx + half)
    # Build a mask with zeros in the erased region
    mask_top    = tf.ones([y1, w, 3])
    mask_mid    = tf.concat([
        tf.ones([y2 - y1, x1, 3]),
        tf.zeros([y2 - y1, x2 - x1, 3]),
        tf.ones([y2 - y1, w - x2, 3]),
    ], axis=1)
    mask_bottom = tf.ones([h - y2, w, 3])
    mask = tf.concat([mask_top, mask_mid, mask_bottom], axis=0)
    mask = tf.ensure_shape(mask, [h, w, 3])
    img  = img * mask

    # Clip to valid preprocessed range
    img = tf.clip_by_value(img, -1.0, 1.0)
    return img, label


def make_dataset(
    csv_path: str,
    label_to_idx: dict,
    batch_size: int,
    preprocess_fn,
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
        ds = ds.shuffle(len(paths), reshuffle_each_iteration=True, seed=42)

    decode_fn = _make_decode_fn(n_classes, preprocess_fn)
    ds = ds.map(decode_fn, num_parallel_calls=AUTOTUNE)

    if augment:
        ds = ds.map(_augment, num_parallel_calls=AUTOTUNE)

    # No .cache() — too large for RAM. prefetch keeps GPU saturated.
    ds = ds.batch(batch_size, drop_remainder=False).prefetch(AUTOTUNE)
    return ds


# ── Class weights ─────────────────────────────────────────────────────────────

def compute_class_weights(csv_path: str, label_to_idx: dict) -> dict:
    counts: Counter = Counter()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            lbl = row["label"]
            if lbl in label_to_idx:
                counts[label_to_idx[lbl]] += 1
    total     = sum(counts.values())
    n_present = len(counts)
    return {idx: total / (n_present * cnt) for idx, cnt in counts.items()}


# ── Model builders ────────────────────────────────────────────────────────────

def _head(x, n_classes: int) -> tf.Tensor:
    """Shared classification head used by both architectures."""
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Dense(256, activation="relu")(x)
    x = keras.layers.Dropout(0.4)(x)
    x = keras.layers.Dense(128, activation="relu")(x)
    x = keras.layers.Dropout(0.3)(x)
    return keras.layers.Dense(n_classes, activation="softmax", name="predictions")(x)


def build_mobilenetv2(n_classes: int) -> keras.Model:
    base = keras.applications.MobileNetV2(
        input_shape=(*IMG_SIZE, 3), include_top=False, weights="imagenet"
    )
    base.trainable = False
    inputs  = keras.Input(shape=(*IMG_SIZE, 3), name="image_input")
    x       = base(inputs, training=False)
    outputs = _head(x, n_classes)
    return keras.Model(inputs, outputs, name="agroscan_mobilenetv2")


def build_efficientnetb0(n_classes: int) -> keras.Model:
    base = keras.applications.EfficientNetB0(
        input_shape=(*IMG_SIZE, 3), include_top=False, weights="imagenet"
    )
    base.trainable = False
    inputs  = keras.Input(shape=(*IMG_SIZE, 3), name="image_input")
    x       = base(inputs, training=False)
    outputs = _head(x, n_classes)
    return keras.Model(inputs, outputs, name="agroscan_efficientnetb0")


def build_model(n_classes: int, arch: str) -> keras.Model:
    if arch == "efficientnetb0":
        return build_efficientnetb0(n_classes)
    return build_mobilenetv2(n_classes)


def get_preprocess_fn(arch: str):
    if arch == "efficientnetb0":
        # EfficientNet uses its own preprocessing (scales to [0,1] internally)
        return keras.applications.efficientnet.preprocess_input
    return keras.applications.mobilenet_v2.preprocess_input


def unfreeze_top(model: keras.Model, arch: str, pct: float = 0.30) -> None:
    """Unfreeze the top pct fraction of the backbone for fine-tuning."""
    base_name = "efficientnetb0" if arch == "efficientnetb0" else "mobilenetv2_1.00_224"
    base = model.get_layer(base_name)
    base.trainable = True
    n = len(base.layers)
    cutoff = int(n * (1.0 - pct))
    for i, layer in enumerate(base.layers):
        layer.trainable = i >= cutoff
    trainable = sum(1 for l in base.layers if l.trainable)
    print(f"  Unfrozen {trainable}/{n} layers of {base_name} (top {pct*100:.0f}%)")


# ── Training ──────────────────────────────────────────────────────────────────

def train(
    train_csv: str,
    val_csv: str,
    output_dir: str,
    arch: str = "mobilenetv2",
    epochs_p1: int = 25,
    epochs_p2: int = 25,
    batch_size: int = 32,
    mixed_precision: bool = False,
) -> None:

    arch = arch.lower()
    if arch not in SUPPORTED_ARCHS:
        sys.exit(f"Unknown arch '{arch}'. Choose from: {SUPPORTED_ARCHS}")

    if mixed_precision:
        keras.mixed_precision.set_global_policy("mixed_float16")
        print("Mixed precision: float16 enabled")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    preprocess_fn = get_preprocess_fn(arch)

    # ── Label mapping ─────────────────────────────────────────────────────────
    print(f"\nArchitecture: {arch.upper()}")
    print("Building label mapping …")
    l2i       = build_label_mapping(train_csv)
    n_classes = len(l2i)
    print(f"  {n_classes} classes")
    for lbl, idx in sorted(l2i.items(), key=lambda x: x[1]):
        print(f"    {idx:>3}: {lbl}")

    # Export class_indices.json
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
    # Keep root models/ in sync
    root_ci = Path(output_dir).parent / "class_indices.json"
    with root_ci.open("w") as f:
        json.dump(ci, f, indent=2)
    print(f"  class_indices.json → {ci_path} + {root_ci}")

    # ── Data pipelines ────────────────────────────────────────────────────────
    print("\nBuilding tf.data pipelines …")
    train_ds = make_dataset(train_csv, l2i, batch_size, preprocess_fn, augment=True,  shuffle=True)
    val_ds   = make_dataset(val_csv,   l2i, batch_size, preprocess_fn, augment=False, shuffle=False)

    cw = compute_class_weights(train_csv, l2i)
    print(f"  Class weights range: {min(cw.values()):.3f} – {max(cw.values()):.3f}")

    # ── Build model ───────────────────────────────────────────────────────────
    print("\nBuilding model …")
    model = build_model(n_classes, arch)
    trainable_p1 = sum(tf.size(w).numpy() for w in model.trainable_weights)
    print(f"  Trainable params (phase 1): {trainable_p1:,}")

    # Loss: label smoothing reduces overconfidence on noisy field images
    loss_fn = keras.losses.CategoricalCrossentropy(label_smoothing=0.1)

    # Count train samples for LR schedule (avoid iterating entire dataset)
    with open(train_csv, newline="") as _f:
        _train_n = sum(1 for row in csv.DictReader(_f) if row["label"] in l2i)

    # ── Phase 1: frozen backbone, train head ──────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 1 — frozen backbone, head training")
    print("=" * 60)

    steps_per_epoch_p1 = max(1, (_train_n + batch_size - 1) // batch_size)
    total_steps_p1     = epochs_p1 * steps_per_epoch_p1
    lr_schedule_p1     = keras.optimizers.schedules.CosineDecay(
        initial_learning_rate=1e-3,
        decay_steps=total_steps_p1,
        alpha=1e-6,    # floor — never fully zero
    )
    print(f"  LR schedule: CosineDecay 1e-3 → 1e-6 over {total_steps_p1:,} steps")

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr_schedule_p1),
        loss=loss_fn,
        metrics=["accuracy"],
    )

    cb_p1 = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=7,
            restore_best_weights=True, mode="max",
        ),
        keras.callbacks.ModelCheckpoint(
            str(out / "best_phase1.keras"),
            monitor="val_accuracy", save_best_only=True, mode="max",
        ),
        keras.callbacks.CSVLogger(str(out / "history_phase1.csv")),
    ]

    hist1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_p1,
        class_weight=cw,
        callbacks=cb_p1,
        verbose=1,
    )

    best_p1 = max(hist1.history["val_accuracy"])
    print(f"\n  Phase 1 best val_accuracy: {best_p1:.4f}")

    # ── Phase 2: unfreeze top 30%, fine-tune ─────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2 — top-30% unfrozen, fine-tuning")
    print("=" * 60)

    unfreeze_top(model, arch, pct=0.30)
    trainable_p2 = sum(tf.size(w).numpy() for w in model.trainable_weights)
    print(f"  Trainable params (phase 2): {trainable_p2:,}")

    steps_per_epoch_p2 = steps_per_epoch_p1   # same data, same batch size
    total_steps_p2     = epochs_p2 * steps_per_epoch_p2
    lr_schedule_p2     = keras.optimizers.schedules.CosineDecay(
        initial_learning_rate=1e-4,   # 10× lower than phase 1
        decay_steps=total_steps_p2,
        alpha=1e-7,
    )
    print(f"  LR schedule: CosineDecay 1e-4 → 1e-7 over {total_steps_p2:,} steps")

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr_schedule_p2),
        loss=loss_fn,
        metrics=["accuracy"],
    )

    cb_p2 = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=7,
            restore_best_weights=True, mode="max",
        ),
        keras.callbacks.ModelCheckpoint(
            str(out / "best_phase2.keras"),
            monitor="val_accuracy", save_best_only=True, mode="max",
        ),
        keras.callbacks.CSVLogger(str(out / "history_phase2.csv")),
    ]

    hist2 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_p2,
        class_weight=cw,
        callbacks=cb_p2,
        verbose=1,
    )

    best_p2 = max(hist2.history["val_accuracy"])
    print(f"\n  Phase 2 best val_accuracy: {best_p2:.4f}")

    # ── Save ──────────────────────────────────────────────────────────────────
    model.save(str(out / "best_phase2.keras"))
    print(f"\n  Model saved → {(out / 'best_phase2.keras').resolve()}")

    best = max(best_p1, best_p2)
    print(f"  Final best val accuracy : {best:.4f}")
    print(f"  Release gate (NFR-2)    : 0.9300")
    if best >= 0.93:
        print("  STATUS: ✓ PASS — run evaluate.py then promote to production")
    else:
        print("  STATUS: ✗ Below gate — collect more data or increase epochs")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Train AgroScan NG crop disease model")
    p.add_argument("--train-csv",       default="data/splits/train.csv")
    p.add_argument("--val-csv",         default="data/splits/val.csv")
    p.add_argument("--output",          default="inference/models/v1")
    p.add_argument("--arch",            default="mobilenetv2",
                   choices=SUPPORTED_ARCHS,
                   help="Model architecture (default: mobilenetv2)")
    p.add_argument("--epochs-phase1",   type=int, default=25)
    p.add_argument("--epochs-phase2",   type=int, default=25)
    p.add_argument("--batch-size",      type=int, default=32)
    p.add_argument("--mixed-precision", action="store_true",
                   help="Enable float16 mixed precision (faster on NVIDIA/Apple GPU)")
    args = p.parse_args()
    train(
        args.train_csv, args.val_csv, args.output,
        args.arch,
        args.epochs_phase1, args.epochs_phase2,
        args.batch_size, args.mixed_precision,
    )
