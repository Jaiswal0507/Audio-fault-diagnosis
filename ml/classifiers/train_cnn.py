"""CWRU Bearing Spectrogram CNN Classifier Training Pipeline.

Trains a Convolutional Neural Network on Mel-spectrogram images representing
CWRU bearing vibration states. Features leak-free group splitting across source
recordings, compact model serialization without optimizer states, class
mapping metadata persistence, and automated classification report dumping to JSON.
"""

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy as np
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupShuffleSplit
import tensorflow as tf

# Support project root and package imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Standard CWRU bearing multi-class categories
DEFAULT_CWRU_CLASSES: List[str] = ["ball_defect", "inner_race", "normal", "outer_race"]


def build_cnn_model(
    input_shape: Tuple[int, int, int] = (128, 128, 3),
    num_classes: int = 4,
    dropout_rate: float = 0.3,
) -> tf.keras.Model:
    """Build standardized TF/Keras CNN architecture for spectrogram classification.

    Architecture:
        Rescaling -> 3x[Conv2D + MaxPool] -> Flatten -> Dense(128) -> Dropout -> Softmax

    Args:
        input_shape: Dimensions of input spectrogram (height, width, channels).
        num_classes: Total target classification categories.
        dropout_rate: Dropout probability for regularization.

    Returns:
        tf.keras.Model: Uncompiled Keras Sequential model.
    """
    model = tf.keras.Sequential([
        # 1. Rescaling layer: normalize pixel intensities [0, 255] -> [0.0, 1.0]
        tf.keras.layers.Rescaling(1.0 / 255.0, input_shape=input_shape),

        # 2. Convolutional Block 1
        tf.keras.layers.Conv2D(32, (3, 3), activation="relu", padding="same", name="conv1"),
        tf.keras.layers.MaxPooling2D((2, 2), name="pool1"),

        # 3. Convolutional Block 2
        tf.keras.layers.Conv2D(64, (3, 3), activation="relu", padding="same", name="conv2"),
        tf.keras.layers.MaxPooling2D((2, 2), name="pool2"),

        # 4. Convolutional Block 3
        tf.keras.layers.Conv2D(128, (3, 3), activation="relu", padding="same", name="conv3"),
        tf.keras.layers.MaxPooling2D((2, 2), name="pool3"),

        # 5. Classifier Head
        tf.keras.layers.Flatten(name="flatten"),
        tf.keras.layers.Dense(128, activation="relu", name="dense_features"),
        tf.keras.layers.Dropout(dropout_rate, name="dropout"),
        tf.keras.layers.Dense(num_classes, activation="softmax", name="predictions"),
    ], name="cwru_bearing_cnn")

    return model


def load_spectrogram_dataset(
    data_dir: Union[str, Path],
    categories: Optional[List[str]] = None,
    target_size: Tuple[int, int] = (128, 128),
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Load Mel-spectrogram images from disk, map class labels, and extract recording groups.

    Args:
        data_dir: Path to directory containing class subdirectories.
        categories: Explicit ordered class names (defaults to DEFAULT_CWRU_CLASSES).
        target_size: Spatial dimensions to resize spectrograms to (128, 128).

    Returns:
        Tuple of (images_array, labels_array, groups_array, class_names).
    """
    root_path = Path(data_dir).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Spectrogram directory not found: '{root_path}'")

    class_names = list(categories) if categories else list(DEFAULT_CWRU_CLASSES)
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}

    images_list: List[np.ndarray] = []
    labels_list: List[int] = []
    groups_list: List[str] = []

    print(f"[train_cnn] Scanning spectrograms in '{root_path}'...")
    for class_name in class_names:
        class_dir = root_path / class_name
        if not class_dir.exists():
            print(f"[train_cnn] Warning: Category directory missing: '{class_dir.name}'. Skipping.")
            continue

        label_idx = class_to_idx[class_name]
        image_files = sorted(list(class_dir.rglob("*.png")))

        for img_path in image_files:
            try:
                # Load with PIL, guarantee RGB channels, and resize to (128, 128)
                with Image.open(img_path) as img:
                    rgb_img = img.convert("RGB").resize(target_size)
                    arr = np.array(rgb_img, dtype=np.float32)

                # Extract source recording stem (group) to prevent chunk data leakage
                # e.g., 'B007_1_123_chunk_0.png' -> 'B007_1_123'
                stem = img_path.stem
                match = re.search(r"^(.*?)(?:_chunk_\d+.*)?$", stem)
                group_id = match.group(1) if match and match.group(1) else stem

                images_list.append(arr)
                labels_list.append(label_idx)
                groups_list.append(group_id)
            except Exception as exc:
                print(f"[train_cnn] Error reading image '{img_path}': {exc}")

    if not images_list:
        raise ValueError(f"No valid spectrogram images found in '{root_path}'.")

    X = np.stack(images_list, axis=0)
    y = np.array(labels_list, dtype=np.int32)
    groups = np.array(groups_list, dtype=object)

    print(f"[train_cnn] Loaded {len(X)} images across {len(np.unique(groups))} recording groups.")
    return X, y, groups, class_names


def split_dataset_leak_free(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, set, set]:
    """Split dataset ensuring all chunks from the same source recording stay strictly grouped.

    Args:
        X: Feature image array of shape (N, H, W, C).
        y: Categorical integer label array of shape (N,).
        groups: Group identifier array corresponding to source recordings.
        test_size: Proportion of recording groups allocated to validation.
        random_state: Random state seed for reproducibility.

    Returns:
        Tuple of (X_train, X_val, y_train, y_val, train_groups, val_groups).
    """
    unique_groups = np.unique(groups)
    if len(unique_groups) > 1:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, val_idx = next(splitter.split(X, y, groups=groups))
    else:
        # Fallback if only single group exists in tiny test set
        indices = np.arange(len(X))
        np.random.seed(random_state)
        np.random.shuffle(indices)
        split_point = int(len(X) * (1.0 - test_size))
        train_idx, val_idx = indices[:split_point], indices[split_point:]

    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    train_groups = set(groups[train_idx])
    val_groups = set(groups[val_idx])
    overlap = train_groups.intersection(val_groups)

    print(f"[train_cnn] Train set: {len(X_train)} samples ({len(train_groups)} groups)")
    print(f"[train_cnn] Val set  : {len(X_val)} samples ({len(val_groups)} groups)")
    print(f"[train_cnn] Group overlap count: {len(overlap)} (Strict 0 = Zero Leakage)")

    return X_train, X_val, y_train, y_val, train_groups, val_groups


def train_cwru_cnn(
    data_dir: Optional[Union[str, Path]] = None,
    output_model_path: Optional[Union[str, Path]] = None,
    metrics_output_path: Optional[Union[str, Path]] = None,
    epochs: int = 20,
    batch_size: int = 16,
    learning_rate: float = 0.001,
    random_state: int = 42,
    verbose: int = 1,
) -> Tuple[tf.keras.Model, Dict[str, Any]]:
    """Execute end-to-end CNN training on CWRU bearing spectrograms.

    Args:
        data_dir: Root directory of CWRU spectrogram dataset.
        output_model_path: Path where trained .h5 model should be saved.
        metrics_output_path: Path where evaluation metrics JSON should be dumped.
        epochs: Maximum training epochs.
        batch_size: Mini-batch size.
        learning_rate: Adam optimizer learning rate.
        random_state: Seed for reproducibility.
        verbose: Verbosity level for model fitting.

    Returns:
        Tuple of (trained_model, cnn_metrics_payload).
    """
    resolved_data_dir = (
        Path(data_dir).resolve()
        if data_dir
        else PROJECT_ROOT / "data" / "spectrograms" / "cwru"
    )
    resolved_output_path = (
        Path(output_model_path).resolve()
        if output_model_path
        else PROJECT_ROOT / "models" / "cwru_cnn.h5"
    )
    resolved_metrics_path = (
        Path(metrics_output_path).resolve()
        if metrics_output_path
        else PROJECT_ROOT / "ml" / "evaluation" / "cnn_metrics.json"
    )

    # 1. Load data and split with zero data leakage
    X, y, groups, class_names = load_spectrogram_dataset(
        data_dir=resolved_data_dir,
        categories=DEFAULT_CWRU_CLASSES,
        target_size=(128, 128),
    )
    X_train, X_val, y_train, y_val, train_groups, val_groups = split_dataset_leak_free(
        X, y, groups, test_size=0.2, random_state=random_state
    )

    # 2. Build and compile CNN model
    model = build_cnn_model(
        input_shape=(128, 128, 3),
        num_classes=len(class_names),
        dropout_rate=0.3,
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    # 3. Callbacks: Early stopping to prevent overfitting
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
            verbose=1,
        )
    ]

    # 4. Train model
    print(f"\n[train_cnn] Training CNN model for {epochs} epochs (batch_size={batch_size})...")
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=verbose,
    )

    # 5. Evaluate on validation set
    val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"\n[train_cnn] Validation Loss: {val_loss:.4f} | Validation Accuracy: {val_acc * 100:.2f}%")

    # Generate model predictions for classification report and metrics
    y_pred_probs = model.predict(X_val, verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=-1)

    acc = float(accuracy_score(y_val, y_pred))
    prec = float(precision_score(y_val, y_pred, average="weighted", zero_division=0))
    rec = float(recall_score(y_val, y_pred, average="weighted", zero_division=0))
    f1 = float(f1_score(y_val, y_pred, average="weighted", zero_division=0))
    cm = confusion_matrix(y_val, y_pred, labels=list(range(len(class_names)))).tolist()

    report_dict = classification_report(
        y_val,
        y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    report_text = classification_report(
        y_val,
        y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        zero_division=0,
    )

    print("\n" + "=" * 65)
    print(" MachineSense - CWRU Spectrogram CNN Classification Report")
    print("=" * 65)
    print(report_text)
    print("=" * 65)

    # Explicit acknowledgment of preliminary nature of CWRU evaluation
    preliminary_note = (
        f"Evaluation notice: The CWRU bearing dataset evaluation is currently preliminary "
        f"due to a limited number of source recording groups ({len(np.unique(groups))} total recording stems). "
        "The holdout validation set represents a small subset of independent motor runs under laboratory conditions. "
        "Acoustic generalization in factory environments with non-contact microphones requires extensive in-situ validation."
    )
    print("\n" + "=" * 75)
    print(f"[train_cnn] [NOTICE] {preliminary_note}")
    print("=" * 75 + "\n")

    # 6. Save model without optimizer to reduce disk footprint
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    cast(Any, model).save(str(resolved_output_path), include_optimizer=False)
    print(f"[train_cnn] Model saved to '{resolved_output_path}' (include_optimizer=False)")

    # 7. Explicitly save class_names.json alongside the model artifact
    class_names_path = resolved_output_path.parent / "class_names.json"
    with open(class_names_path, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)
    print(f"[train_cnn] Class mappings saved to '{class_names_path}'")

    specific_class_names_path = resolved_output_path.parent / f"{resolved_output_path.stem}_class_names.json"
    with open(specific_class_names_path, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)

    # 8. Dump honest evaluation artifacts to ml/evaluation/cnn_metrics.json
    resolved_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    cnn_metrics_payload: Dict[str, Any] = {
        "model_name": "cwru_cnn",
        "model_artifact": str(resolved_output_path.name),
        "task": "Bearing & Motor Multi-Class Mechanical Defect Classification",
        "dataset": "Case Western Reserve University (CWRU) Bearing Data Center",
        "classes": class_names,
        "input_shape": list(model.input_shape[1:] if model.input_shape else (128, 128, 3)),
        "validation_strategy": "GroupShuffleSplit (source recording grouped, zero leakage)",
        "total_samples": int(len(X)),
        "train_samples": int(len(X_train)),
        "val_samples": int(len(X_val)),
        "total_recording_groups": int(len(np.unique(groups))),
        "train_recording_groups": int(len(train_groups)),
        "val_recording_groups": int(len(val_groups)),
        "val_loss": float(val_loss),
        "val_accuracy": float(val_acc),
        "test_accuracy": float(acc),
        "test_precision_weighted": float(prec),
        "test_recall_weighted": float(rec),
        "test_f1_weighted": float(f1),
        "confusion_matrix": cm,
        "classification_report": report_dict,
        "preliminary_evaluation_notice": preliminary_note,
        "epochs_trained": len(history.history.get("loss", [])),
    }

    with open(resolved_metrics_path, "w", encoding="utf-8") as f:
        json.dump(cnn_metrics_payload, f, indent=2)
    print(f"[train_cnn] Honest CNN evaluation metrics written to '{resolved_metrics_path}'.\n")

    return model, cnn_metrics_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CWRU Spectrogram CNN Classifier")
    parser.add_argument("--data-dir", type=str, default=None, help="Path to spectrograms directory")
    parser.add_argument("--output-model", type=str, default=None, help="Output .h5 model path")
    parser.add_argument("--metrics-path", type=str, default=None, help="Output metrics JSON path")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Mini-batch size")
    args = parser.parse_args()

    train_cwru_cnn(
        data_dir=args.data_dir,
        output_model_path=args.output_model,
        metrics_output_path=args.metrics_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
