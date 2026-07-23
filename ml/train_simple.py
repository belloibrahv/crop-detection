"""
train_simple.py — Simplified training script for faster iteration.

Uses smaller epochs and simpler configuration for quick testing.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow import keras

IMG_SIZE = (224, 224)
AUTOTUNE = tf.data.AUTOTUNE


def build_label_mapping(csv_path: str) -> dict[str, int]:
    labels = set()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            labels.add(row["label"])
    return {label: idx for idx, label in enumerate(sorted(labels))}


def make_dataset(
    csv_path: str,
    label_to_idx: dict[str, int],
    batch_size: int,
    augment: bool = False,
    shuffle: bool = True,
) -> tf.data.Dataset:

    paths, labels = [], []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["label"] in label_to_idx:
                paths.append(row["path"])
                labels.append(label_to_idx[row["label"]])

    n_classes = len(label_to_idx)

    def load(path, label):
        img = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, IMG_SIZE)
        img = tf.keras.applications.mobilenet_v2.preprocess_input(img)
        return img, tf.one_hot(label, n_classes)

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if shuffle:
        ds = ds.shuffle(min(1000, len(paths)), reshuffle_each_iteration=True)
    ds = ds.map(load, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size).cache().prefetch(tf.data.AUTOTUNE)
    return ds


def build_model(n_classes: int) -> keras.Model:
    base = keras.applications.MobileNetV2(
        input_shape=(*IMG_SIZE, 3), include_top=False, weights="imagenet"
    )
    base.trainable = False

    inputs = keras.Input(shape=(*IMG_SIZE, 3))
    x = base(inputs, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.5)(x)
    outputs = keras.layers.Dense(n_classes, activation="softmax")(x)
    return keras.Model(inputs, outputs)


def train(
    train_csv: str,
    val_csv: str,
    output_dir: str,
    epochs: int = 10,
    batch_size: int = 32,
):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print("Building label mapping …")
    l2i = build_label_mapping(train_csv)
    n_classes = len(l2i)
    print(f"  {n_classes} classes")
    
    # Save class indices
    class_indices = {str(idx): {"crop": label.split("/")[0], "disease": label.split("/")[1]} 
                     for label, idx in l2i.items()}
    with open(out / "class_indices.json", "w") as f:
        json.dump(class_indices, f, indent=2)

    print("Building tf.data pipelines …")
    train_ds = make_dataset(train_csv, l2i, batch_size, augment=False, shuffle=True)
    val_ds = make_dataset(val_csv, l2i, batch_size, augment=False, shuffle=False)

    print("Building model …")
    model = build_model(n_classes)

    print("\n=== Training ===")
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    
    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        keras.callbacks.ModelCheckpoint(str(out / "best.keras"), monitor="val_accuracy", save_best_only=True),
    ]
    
    model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=callbacks)

    # Save final model
    model.save(str(out))
    print(f"\nModel saved → {out.resolve()}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--train-csv", default="data/splits/train_balanced.csv")
    p.add_argument("--val-csv", default="data/splits/val_balanced.csv")
    p.add_argument("--output", default="inference/models/v5")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=32)
    args = p.parse_args()

    train(args.train_csv, args.val_csv, args.output, args.epochs, args.batch_size)
