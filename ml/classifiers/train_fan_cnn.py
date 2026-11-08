"""MIMII Industrial Fan Spectrogram CNN Classifier Training Pipeline.

Trains a Convolutional Neural Network on Log-Mel Spectrogram images from the MIMII
industrial fan dataset (Hitachi/DCASE 2020 Challenge). Evaluates binary condition
classification ('anomaly' vs 'normal') using Leave-One-Group-Out (LOGO) cross-validation
across physical machine IDs (id_00, id_02, id_04, id_06) to strictly eliminate
cross-machine audio data leakage.

Saves the production model as models/advanced_cnn_fan.h5 with include_optimizer=False
and dumps honest evaluation metrics to ml/evaluation/fan_cnn_metrics.json.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys
import time
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
from sklearn.utils.class_weight import compute_class_weight
from sklearn.model_selection import LeaveOneGroupOut
import tensorflow as tf

# Ensure project root is available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Strict class mapping: index 0 = anomaly, index 1 = normal
FAN_CLASSES: List[str] = ["anomaly", "normal"]


def build_fan_cnn_model(
    input_shape: Tuple[int, int, int] = (128, 128, 3),
    num_classes: int = 2,
    dropout_rate: float = 0.3,
) -> tf.keras.Model:
    """Build standardized 2D CNN architecture for Fan Log-Mel Spectrogram classification.

    Architecture:
        Rescaling -> 3x[Conv2D + MaxPool] -> Flatten -> Dense(128) -> Dropout -> Softmax(2)

    Args:
        input_shape: Dimensions of spectrogram image (height, width, channels).
        num_classes: Number of binary condition categories (2: anomaly, normal).
        dropout_rate: Dropout fraction for regularization.

    Returns:
        tf.keras.Model: Sequential Keras model ready for compilation.
    """
    model = tf.keras.Sequential([
        # 1. Normalize raw pixel intensities from [0, 255] to [0.0, 1.0]
        tf.keras.layers.Rescaling(1.0 / 255.0, input_shape=input_shape),

        # 2. Block 1: Low-level acoustic texture
        tf.keras.layers.Conv2D(32, (3, 3), activation="relu", padding="same", name="conv1"),
        tf.keras.layers.MaxPooling2D((2, 2), name="pool1"),

        # 3. Block 2: Intermediate frequency patterns
        tf.keras.layers.Conv2D(64, (3, 3), activation="relu", padding="same", name="conv2"),
        tf.keras.layers.MaxPooling2D((2, 2), name="pool2"),

        # 4. Block 3: High-level harmonic resonances
        tf.keras.layers.Conv2D(128, (3, 3), activation="relu", padding="same", name="conv3"),
        tf.keras.layers.MaxPooling2D((2, 2), name="pool3"),

        # 5. Classifier Head
        tf.keras.layers.Flatten(name="flatten"),
        tf.keras.layers.Dense(128, activation="relu", name="dense_features"),
        tf.keras.layers.Dropout(dropout_rate, name="dropout"),
        tf.keras.layers.Dense(num_classes, activation="softmax", name="predictions"),
    ], name="mimii_fan_cnn")

    return model


def _load_single_image(args: Tuple[Path, int, str, Tuple[int, int]]) -> Optional[Tuple[np.ndarray, int, str]]:
    """Helper for concurrent image loading and resizing."""
    img_path, label_idx, machine_id, target_size = args
    try:
        with Image.open(img_path) as img:
            rgb_img = img.convert("RGB").resize(target_size)
            arr = np.array(rgb_img, dtype=np.uint8)
        return arr, label_idx, machine_id
    except Exception as exc:
        print(f"[train_fan_cnn] Error reading image '{img_path}': {exc}")
        return None


def load_fan_spectrogram_dataset(
    data_dir: Union[str, Path],
    target_size: Tuple[int, int] = (128, 128),
    subsample_ratio: Optional[float] = None,
    max_workers: int = 8,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Load all Fan Mel-spectrogram images concurrently from disk with machine IDs.

    Args:
        data_dir: Root directory of fan spectrograms (e.g. data/spectrograms/fan).
        target_size: Target image dimensions (128, 128).
        subsample_ratio: Optional fraction to subsample for accelerated testing.
        max_workers: Thread worker count for parallel image disk reads.

    Returns:
        Tuple of (X_images, y_labels, groups_machine_ids, class_names).
    """
    root_path = Path(data_dir).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Fan spectrogram directory not found: '{root_path}'")

    class_names = list(FAN_CLASSES)
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}

    tasks: List[Tuple[Path, int, str, Tuple[int, int]]] = []

    print(f"[train_fan_cnn] Indexing Fan spectrogram images in '{root_path}'...")
    for class_name in class_names:
        class_dir = root_path / class_name
        if not class_dir.exists():
            print(f"[train_fan_cnn] Warning: Condition directory missing: '{class_dir.name}'. Skipping.")
            continue

        label_idx = class_to_idx[class_name]

        # Machine subdirectories: id_00, id_02, id_04, id_06
        for machine_dir in sorted(class_dir.glob("id_*")):
            if not machine_dir.is_dir():
                continue
            m_id = machine_dir.name.lower().strip()
            png_files = sorted(list(machine_dir.glob("*.png")))
            for p in png_files:
                tasks.append((p, label_idx, m_id, target_size))

    if not tasks:
        raise ValueError(f"No spectrogram images found in '{root_path}'.")

    if subsample_ratio and 0.0 < subsample_ratio < 1.0:
        rng = np.random.default_rng(42)
        idx_sample = rng.choice(len(tasks), size=int(len(tasks) * subsample_ratio), replace=False)
        tasks = [tasks[i] for i in idx_sample]
        print(f"[train_fan_cnn] Subsampled dataset to {len(tasks)} images (ratio={subsample_ratio:.2f}).")

    print(f"[train_fan_cnn] Loading {len(tasks)} images concurrently (workers={max_workers})...")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_load_single_image, tasks))

    valid_results = [r for r in results if r is not None]
    if not valid_results:
        raise ValueError("Failed to load any valid images.")

    images_list, labels_list, groups_list = zip(*valid_results)
    X = np.stack(images_list, axis=0)  # Shape (N, 128, 128, 3) in uint8
    y = np.array(labels_list, dtype=np.int32)
    groups = np.array(groups_list, dtype=object)

    elapsed = time.time() - t0
    unique_groups = sorted(list(np.unique(groups)))
    print(f"[train_fan_cnn] Successfully loaded {len(X)} images across {len(unique_groups)} machine IDs in {elapsed:.2f}s.")
    print(f"[train_fan_cnn] Machine IDs: {unique_groups}")

    return X, y, groups, class_names


def train_fan_cnn(
    data_dir: Optional[Union[str, Path]] = None,
    output_model_path: Optional[Union[str, Path]] = None,
    metrics_output_path: Optional[Union[str, Path]] = None,
    epochs: int = 3,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    subsample_ratio: Optional[float] = None,
    verbose: int = 1,
) -> Tuple[tf.keras.Model, Dict[str, Any]]:
    """Execute LeaveOneGroupOut evaluation across machine IDs and retrain production Fan CNN.

    Args:
        data_dir: Root directory of fan spectrograms.
        output_model_path: Target path for advanced_cnn_fan.h5.
        metrics_output_path: Target path for fan_cnn_metrics.json.
        epochs: Training epochs per fold and final retrain.
        batch_size: Mini-batch size.
        learning_rate: Adam optimizer learning rate.
        subsample_ratio: Optional fraction for rapid dry-runs.
        verbose: Verbosity level for training logs.

    Returns:
        Tuple of (trained_production_model, metrics_dict).
    """
    resolved_data_dir = (
        Path(data_dir).resolve()
        if data_dir
        else PROJECT_ROOT / "data" / "spectrograms" / "fan"
    )
    resolved_output_path = (
        Path(output_model_path).resolve()
        if output_model_path
        else PROJECT_ROOT / "models" / "advanced_cnn_fan.h5"
    )
    resolved_metrics_path = (
        Path(metrics_output_path).resolve()
        if metrics_output_path
        else PROJECT_ROOT / "ml" / "evaluation" / "fan_cnn_metrics.json"
    )

    # 1. Load full spectrogram dataset
    X, y, groups, class_names = load_fan_spectrogram_dataset(
        data_dir=resolved_data_dir,
        target_size=(128, 128),
        subsample_ratio=subsample_ratio,
    )

    # 2. LeaveOneGroupOut Cross-Validation Loop across machine IDs
    logo = LeaveOneGroupOut()
    num_folds = logo.get_n_splits(groups=groups)
    unique_groups = sorted(list(np.unique(groups)))

    print("\n" + "=" * 65)
    print(f" Starting Fan CNN LeaveOneGroupOut Cross-Validation ({num_folds} Folds)")
    print(f" Machine IDs Evaluated: {unique_groups}")
    print(f" Total Fan Samples    : {len(X)}")
    print("=" * 65)

    fold_metrics: List[Dict[str, Any]] = []
    all_y_true: List[int] = []
    all_y_pred: List[int] = []

    for fold_idx, (train_idx, val_idx) in enumerate(logo.split(X, y, groups=groups), 1):
        test_group = str(groups[val_idx[0]])
        X_train_f, X_val_f = X[train_idx], X[val_idx]
        y_train_f, y_val_f = y[train_idx], y[val_idx]

        print(f"\n[Fold {fold_idx}/{num_folds}] Holdout Test Machine: '{test_group}' "
              f"(Train: {len(X_train_f)}, Val: {len(X_val_f)} samples)")

        fold_model = build_fan_cnn_model(
            input_shape=(128, 128, 3),
            num_classes=len(class_names),
            dropout_rate=0.3,
        )
        fold_model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )

        # Compute balanced class weights for fold training
        classes_f = np.unique(y_train_f)
        weights_f = compute_class_weight(class_weight="balanced", classes=classes_f, y=y_train_f)
        class_weight_dict_f = {cls: float(w) for cls, w in zip(classes_f, weights_f)}

        fold_model.fit(
            X_train_f,
            y_train_f,
            validation_data=(X_val_f, y_val_f),
            epochs=epochs,
            batch_size=batch_size,
            class_weight=class_weight_dict_f,
            verbose=verbose,
        )

        # Predict on holdout validation fold
        val_probs = fold_model.predict(X_val_f, verbose=0)
        val_pred = np.argmax(val_probs, axis=-1)

        acc = float(accuracy_score(y_val_f, val_pred))
        prec = float(precision_score(y_val_f, val_pred, average="weighted", zero_division=0))
        rec = float(recall_score(y_val_f, val_pred, average="weighted", zero_division=0))
        f1 = float(f1_score(y_val_f, val_pred, average="weighted", zero_division=0))
        cm = confusion_matrix(y_val_f, val_pred, labels=list(range(len(class_names)))).tolist()

        all_y_true.extend(y_val_f.tolist())
        all_y_pred.extend(val_pred.tolist())

        fold_metrics.append({
            "fold": fold_idx,
            "test_group": test_group,
            "train_samples": int(len(train_idx)),
            "val_samples": int(len(val_idx)),
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "confusion_matrix": cm,
        })

        print(f"  Fold {fold_idx} [{test_group}] -> "
              f"Accuracy: {acc * 100:.2f}% | Precision: {prec * 100:.2f}% | "
              f"Recall: {rec * 100:.2f}% | F1: {f1 * 100:.2f}%")

    # 3. Summary statistics across all folds
    acc_list = [f["accuracy"] for f in fold_metrics]
    prec_list = [f["precision"] for f in fold_metrics]
    rec_list = [f["recall"] for f in fold_metrics]
    f1_list = [f["f1_score"] for f in fold_metrics]

    mean_acc = float(np.mean(acc_list))
    std_acc = float(np.std(acc_list))
    mean_prec = float(np.mean(prec_list))
    std_prec = float(np.std(prec_list))
    mean_rec = float(np.mean(rec_list))
    std_rec = float(np.std(rec_list))
    mean_f1 = float(np.mean(f1_list))
    std_f1 = float(np.std(f1_list))

    overall_cm = confusion_matrix(all_y_true, all_y_pred, labels=list(range(len(class_names)))).tolist()
    overall_report = classification_report(
        all_y_true,
        all_y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    overall_report_text = classification_report(
        all_y_true,
        all_y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        zero_division=0,
    )

    print("\n" + "=" * 65)
    print(f" MachineSense - Fan CNN LeaveOneGroupOut Summary ({num_folds} Folds)")
    print("=" * 65)
    print(f" Mean Accuracy : {mean_acc * 100:.2f}% ± {std_acc * 100:.2f}%")
    print(f" Mean Precision: {mean_prec * 100:.2f}% ± {std_prec * 100:.2f}%")
    print(f" Mean Recall   : {mean_rec * 100:.2f}% ± {std_rec * 100:.2f}%")
    print(f" Mean F1 Score : {mean_f1 * 100:.2f}% ± {std_f1 * 100:.2f}%")
    print("=" * 65)
    print("\nPooled Classification Report across all holdout folds:")
    print(overall_report_text)
    print("=" * 65)

    # 4. Retrain production model on ALL data combined
    print("\n[train_fan_cnn] Retraining final production Fan CNN on ALL combined machine IDs...")
    production_model = build_fan_cnn_model(
        input_shape=(128, 128, 3),
        num_classes=len(class_names),
        dropout_rate=0.3,
    )
    production_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    # Compute balanced class weights for full dataset
    classes_all = np.unique(y)
    weights_all = compute_class_weight(class_weight="balanced", classes=classes_all, y=y)
    class_weight_dict_all = {cls: float(w) for cls, w in zip(classes_all, weights_all)}

    production_model.fit(
        X,
        y,
        epochs=epochs,
        batch_size=batch_size,
        class_weight=class_weight_dict_all,
        verbose=verbose,
    )

    # 5. Save production model without optimizer
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    cast(Any, production_model).save(str(resolved_output_path), include_optimizer=False)
    print(f"[train_fan_cnn] Production model saved to '{resolved_output_path}' (include_optimizer=False)")

    # Save class names JSON
    class_names_path = resolved_output_path.parent / f"{resolved_output_path.stem}_class_names.json"
    with open(class_names_path, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)

    # 6. Dump honest evaluation metrics JSON
    resolved_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    honest_metrics_payload: Dict[str, Any] = {
        "model_name": "advanced_cnn_fan",
        "model_artifact": str(resolved_output_path.name),
        "dataset": "MIMII Industrial Fan Dataset (Hitachi / DCASE 2020 Challenge)",
        "task": "Stage 2 Fan Binary Anomaly Detection (Spectrogram CNN)",
        "classes": class_names,
        "input_shape": list(production_model.input_shape[1:] if production_model.input_shape else (128, 128, 3)),
        "evaluation_strategy": "LeaveOneGroupOut cross-validation across all machine IDs",
        "groups": unique_groups,
        "num_folds": len(fold_metrics),
        "total_samples": int(len(X)),
        "folds": fold_metrics,
        "mean_metrics": {
            "mean_accuracy": mean_acc,
            "std_accuracy": std_acc,
            "mean_precision": mean_prec,
            "std_precision": std_prec,
            "mean_recall": mean_rec,
            "std_recall": std_rec,
            "mean_f1": mean_f1,
            "std_f1": std_f1,
        },
        "accuracy_summary": f"{mean_acc * 100:.2f}% ± {std_acc * 100:.2f}%",
        "confusion_matrix": overall_cm,
        "overall_classification_report": overall_report,
        "epochs_trained": epochs,
    }

    with open(resolved_metrics_path, "w", encoding="utf-8") as f:
        json.dump(honest_metrics_payload, f, indent=2)

    print(f"[train_fan_cnn] Evaluation metrics automatically dumped to '{resolved_metrics_path}'.\n")
    return production_model, honest_metrics_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train MIMII Fan Spectrogram CNN Classifier")
    parser.add_argument("--data-dir", type=str, default=None, help="Path to spectrograms directory")
    parser.add_argument("--output-model", type=str, default=None, help="Output .h5 model path")
    parser.add_argument("--metrics-path", type=str, default=None, help="Output metrics JSON path")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Mini-batch size")
    parser.add_argument("--subsample", type=float, default=None, help="Optional subsample ratio")
    args = parser.parse_args()

    train_fan_cnn(
        data_dir=args.data_dir,
        output_model_path=args.output_model,
        metrics_output_path=args.metrics_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        subsample_ratio=args.subsample,
    )

