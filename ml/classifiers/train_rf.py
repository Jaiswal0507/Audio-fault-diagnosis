"""Fan Acoustic Classifier Training Pipeline for MachineSense.

Trains, evaluates, and serializes a Random Forest Stage 1 filter dedicated purely
to MIMII Fan normal/anomaly acoustic classification using domain-engineered DSP features.
Evaluates domain generalization using a full Leave-One-Group-Out (LOGO) cross-validation
loop across all 4 MIMII machine IDs (id_00, id_02, id_04, id_06), calculates mean +/- std
performance metrics, retrains on all IDs combined, and dumps honest evaluation artifacts.
"""

import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union, cast
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import LeaveOneGroupOut, train_test_split

# Ensure project root is available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dsp.features.feature_pipeline import FEATURE_NAMES, FEATURE_VERSION

# Default metadata columns to exclude from feature matrix
METADATA_COLUMNS = {
    "filepath", "filename", "machine_type", "condition",
    "dataset_name", "machine_id", "split", "group_id"
}


class RandomForestTrainer:
    """Trainer for the MachineSense Fan Stage 1 Random Forest acoustic classifier."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 10,
        min_samples_leaf: int = 5,
        random_state: int = 42,
        class_weight: Any = "balanced",
    ):
        """Initialize trainer with regularized Random Forest hyper-parameters.

        Args:
            n_estimators (int): Number of trees in forest (default: 100).
            max_depth (Optional[int]): Maximum tree depth (default: 10, prevents overfitting).
            min_samples_leaf (int): Minimum samples required at leaf node (default: 5).
            random_state (int): Seed for reproducibility (default: 42).
            class_weight: Balancing strategy or class-weight mapping (default: 'balanced').
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.class_weight: Any = class_weight
        self.model: Optional[RandomForestClassifier] = None
        self.feature_columns: List[str] = list(FEATURE_NAMES)
        self.class_names: List[str] = ["normal", "anomaly"]

    def prepare_dataset(
        self,
        data: Union[str, Path, pd.DataFrame],
        target_column: str = "condition",
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Load data, filter strictly to Fan recordings, map binary labels, and extract groups.

        Args:
            data (Union[str, Path, pd.DataFrame]): Path to CSV or existing DataFrame.
            target_column (str): Name of the label column (default: 'condition').

        Returns:
            Tuple[pd.DataFrame, pd.Series, pd.Series]:
                X (feature matrix), y (binary labels), groups (machine ID series)
        """
        if isinstance(data, (str, Path)):
            csv_path = Path(data).resolve()
            if not csv_path.exists():
                raise FileNotFoundError(f"Feature dataset not found at '{csv_path}'")
            df = pd.read_csv(csv_path)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise TypeError(f"Expected file path or DataFrame, got {type(data)}")

        if df.empty:
            raise ValueError("Input dataset is empty.")

        # 1. Filter explicitly to use ONLY Fan data
        if "machine_type" in df.columns:
            df = df[df["machine_type"].astype(str).str.lower().str.strip() == "fan"].copy()

        if df.empty:
            raise ValueError("No Fan records found in dataset after filtering machine_type == 'fan'.")

        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found in dataset columns: {list(df.columns)}")

        # 2. Map classes strictly to ['normal', 'anomaly']
        def _map_condition(val: Any) -> str:
            s = str(val).lower().strip()
            if s in {"normal", "healthy", "ok", "0"}:
                return "normal"
            return "anomaly"

        df[target_column] = df[target_column].apply(_map_condition)
        df = df[df[target_column].notna()]
        y = df[target_column].reset_index(drop=True)

        # 3. Select feature columns strictly matching FEATURE_NAMES
        matching = [col for col in FEATURE_NAMES if col in df.columns]
        if matching:
            self.feature_columns = matching
        else:
            self.feature_columns = [
                str(col)
                for col in df.columns
                if str(col) not in METADATA_COLUMNS and pd.api.types.is_numeric_dtype(df[col])
            ]

        if not self.feature_columns:
            raise ValueError("No numerical feature columns found for training.")

        X = df[self.feature_columns].reset_index(drop=True)

        # 4. Extract Machine ID as group for LeaveOneGroupOut split
        def _extract_machine_group(row: pd.Series) -> str:
            if "machine_id" in row and pd.notna(row["machine_id"]):
                m_id = str(row["machine_id"]).strip().lower()
                if m_id and m_id not in {"unknown", "generic", "none", ""}:
                    return m_id

            filepath_str = str(row.get("filepath", "")).strip()
            filename_str = str(row.get("filename", "")).strip()
            for candidate in [filepath_str, filename_str]:
                match = re.search(r"id_\d+", candidate, re.IGNORECASE)
                if match:
                    return match.group(0).lower()

            if "group_id" in row and pd.notna(row["group_id"]):
                return str(row["group_id"]).strip().lower()

            return "id_00"

        groups = df.apply(_extract_machine_group, axis=1).reset_index(drop=True)
        return X, y, groups

    def prepare_data(
        self,
        data: Union[str, Path, pd.DataFrame],
        target_column: str = "condition",
        test_size: float = 0.2,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Backward-compatible train/test split helper."""
        X, y, groups = self.prepare_dataset(data, target_column=target_column)

        if groups.nunique() > 1:
            logo = LeaveOneGroupOut()
            train_idx, test_idx = next(logo.split(X, y, groups=groups))
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        else:
            splits = train_test_split(
                X,
                y,
                test_size=test_size,
                random_state=self.random_state,
                stratify=y if len(y.unique()) > 1 else None,
            )
            X_train, X_test, y_train, y_test = splits

        return cast(
            Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series],
            (X_train, X_test, y_train, y_test),
        )

    def evaluate_leave_one_group_out(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """Execute full LeaveOneGroupOut loop across all machine IDs and accumulate metrics.

        Args:
            X (pd.DataFrame): Full feature matrix.
            y (pd.Series): Binary labels.
            groups (pd.Series): Machine ID per sample.
            verbose (bool): Whether to log progress.

        Returns:
            Dict[str, Any]: Detailed evaluation dictionary across all folds.
        """
        logo = LeaveOneGroupOut()
        unique_groups = sorted(list(groups.unique()))
        num_splits = logo.get_n_splits(groups=groups)

        if verbose:
            print("\n" + "=" * 65)
            print(f" Starting Full LeaveOneGroupOut Cross-Validation ({num_splits} Folds)")
            print(f" Machine IDs Evaluated: {unique_groups}")
            print(f" Total Fan Samples    : {len(X)}")
            print("=" * 65)

        fold_metrics: List[Dict[str, Any]] = []
        all_y_true: List[str] = []
        all_y_pred: List[str] = []

        for fold_idx, (train_idx, val_idx) in enumerate(logo.split(X, y, groups=groups), 1):
            test_group = str(groups.iloc[val_idx].iloc[0])

            X_train_fold, X_val_fold = X.iloc[train_idx], X.iloc[val_idx]
            y_train_fold, y_val_fold = y.iloc[train_idx], y.iloc[val_idx]

            # Train regularized fold model
            fold_model = RandomForestClassifier(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                class_weight=self.class_weight,
                random_state=self.random_state,
                n_jobs=-1,
            )
            fold_model.fit(X_train_fold, y_train_fold)

            # Predict on unseen machine ID holdout fold
            y_pred_fold = fold_model.predict(X_val_fold)

            acc = float(accuracy_score(y_val_fold, y_pred_fold))
            prec = float(precision_score(y_val_fold, y_pred_fold, average="weighted", zero_division=0))
            rec = float(recall_score(y_val_fold, y_pred_fold, average="weighted", zero_division=0))
            f1 = float(f1_score(y_val_fold, y_pred_fold, average="weighted", zero_division=0))
            cm = confusion_matrix(y_val_fold, y_pred_fold, labels=self.class_names).tolist()

            all_y_true.extend(y_val_fold)
            all_y_pred.extend(y_pred_fold)

            fold_result = {
                "fold": fold_idx,
                "test_group": test_group,
                "train_samples": int(len(train_idx)),
                "val_samples": int(len(val_idx)),
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "confusion_matrix": cm,
            }
            fold_metrics.append(fold_result)

            if verbose:
                print(
                    f"  Fold {fold_idx}/{num_splits} [Test Group: {test_group:<6}] -> "
                    f"Accuracy: {acc * 100:6.2f}% | Precision: {prec * 100:6.2f}% | "
                    f"Recall: {rec * 100:6.2f}% | F1: {f1 * 100:6.2f}% (N={len(val_idx)})"
                )

        # Calculate mean and standard deviation across all folds
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

        overall_cm = confusion_matrix(all_y_true, all_y_pred, labels=self.class_names).tolist()
        overall_report = classification_report(
            all_y_true, all_y_pred, target_names=self.class_names, output_dict=True, zero_division=0
        )

        if verbose:
            print("\n" + "=" * 65)
            print(" MachineSense - LeaveOneGroupOut Summary Across All 4 Folds")
            print("=" * 65)
            print(f" Mean Accuracy : {mean_acc * 100:.2f}% ± {std_acc * 100:.2f}%")
            print(f" Mean Precision: {mean_prec * 100:.2f}% ± {std_prec * 100:.2f}%")
            print(f" Mean Recall   : {mean_rec * 100:.2f}% ± {std_rec * 100:.2f}%")
            print(f" Mean F1 Score : {mean_f1 * 100:.2f}% ± {std_f1 * 100:.2f}%")
            print("=" * 65)

        return {
            "folds": fold_metrics,
            "mean_accuracy": mean_acc,
            "std_accuracy": std_acc,
            "mean_precision": mean_prec,
            "std_precision": std_prec,
            "mean_recall": mean_rec,
            "std_recall": std_rec,
            "mean_f1": mean_f1,
            "std_f1": std_f1,
            "overall_confusion_matrix": overall_cm,
            "overall_classification_report": overall_report,
        }

    def train_final_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> RandomForestClassifier:
        """Retrain final Random Forest classifier on all available groups combined.

        Args:
            X (pd.DataFrame): Complete feature matrix across all IDs.
            y (pd.Series): Complete label set.

        Returns:
            RandomForestClassifier: Fitted final production model.
        """
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            class_weight=self.class_weight,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(X, y)
        return self.model

    def save_model(self, output_path: Union[str, Path] = "models/baseline_rf_fan.pkl") -> Path:
        """Serialize trained model to disk with embedded metadata for dynamic loading.

        Args:
            output_path (Union[str, Path]): Target path for .pkl file.

        Returns:
            Path: Absolute path of saved model artifact.
        """
        if self.model is None:
            raise RuntimeError("Cannot save model: no model has been trained.")

        dest = Path(output_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)

        classes_arr = getattr(self.model, "classes_", np.array(["normal", "anomaly"]))
        classes = classes_arr.tolist() if hasattr(classes_arr, "tolist") else list(classes_arr)

        # Attach metadata attributes for dynamic backend loading
        setattr(self.model, "feature_version_", FEATURE_VERSION)
        setattr(self.model, "feature_names_list_", self.feature_columns)
        setattr(self.model, "classes_list_", classes)

        joblib.dump(self.model, dest)
        return dest


def train_and_save_fan_pipeline(
    data: Union[str, Path, pd.DataFrame],
    model_output_path: Union[str, Path] = "models/baseline_rf_fan.pkl",
    metrics_output_path: Optional[Union[str, Path]] = None,
    target_column: str = "condition",
    verbose: bool = True,
) -> Tuple[RandomForestClassifier, Dict[str, Any]]:
    """Complete pipeline to evaluate via LOGO across all IDs, retrain on all data, and save artifacts."""
    trainer = RandomForestTrainer(
        n_estimators=100,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
    )

    # 1. Load data and extract machine IDs
    X, y, groups = trainer.prepare_dataset(data, target_column=target_column)

    if verbose:
        print(f"[train_rf] Loaded {len(X)} Fan samples across {groups.nunique()} machine IDs: {sorted(list(groups.unique()))}")
        print(f"[train_rf] Features ({len(trainer.feature_columns)}): {trainer.feature_columns}")

    # 2. Execute full LeaveOneGroupOut loop across all machine IDs
    logo_results = trainer.evaluate_leave_one_group_out(X, y, groups, verbose=verbose)

    # 3. Retrain final Random Forest on ALL 4 IDs combined
    if verbose:
        print("\n[train_rf] Retraining final production Random Forest on ALL combined machine IDs...")
    final_model = trainer.train_final_model(X, y)

    # 4. Save final model artifact
    saved_model_path = trainer.save_model(model_output_path)
    if verbose:
        print(f"[train_rf] Production model saved to '{saved_model_path}'.")

    # 5. Extract feature importances
    feature_importances = {
        col: float(imp)
        for col, imp in zip(trainer.feature_columns, final_model.feature_importances_)
    }
    # Sort feature importances descending
    feature_importances = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True))

    # 6. Assemble honest evaluation metrics dictionary
    resolved_metrics_path = (
        Path(metrics_output_path).resolve()
        if metrics_output_path
        else PROJECT_ROOT / "ml" / "evaluation" / "rf_fan_metrics.json"
    )
    resolved_metrics_path.parent.mkdir(parents=True, exist_ok=True)

    honest_metrics_payload: Dict[str, Any] = {
        "model_name": "baseline_rf_fan",
        "model_artifact": str(Path(model_output_path).name),
        "dataset": "MIMII Dataset (Hitachi/DCASE 2020 Challenge)",
        "task": "Stage 1 Fan Binary Acoustic Filtering (normal vs anomaly)",
        "feature_version": FEATURE_VERSION,
        "features": trainer.feature_columns,
        "num_features": len(trainer.feature_columns),
        "classes": list(final_model.classes_),
        "num_samples": int(len(X)),
        "evaluation_strategy": "LeaveOneGroupOut cross-validation across all machine IDs",
        "groups": sorted(list(groups.unique())),
        "num_folds": len(logo_results["folds"]),
        "folds": logo_results["folds"],
        "mean_metrics": {
            "mean_accuracy": logo_results["mean_accuracy"],
            "std_accuracy": logo_results["std_accuracy"],
            "mean_precision": logo_results["mean_precision"],
            "std_precision": logo_results["std_precision"],
            "mean_recall": logo_results["mean_recall"],
            "std_recall": logo_results["std_recall"],
            "mean_f1": logo_results["mean_f1"],
            "std_f1": logo_results["std_f1"],
        },
        "accuracy_summary": f"{logo_results['mean_accuracy'] * 100:.2f}% ± {logo_results['std_accuracy'] * 100:.2f}%",
        "confusion_matrix": logo_results["overall_confusion_matrix"],
        "feature_importances": feature_importances,
        "overall_classification_report": logo_results["overall_classification_report"],
    }

    # 7. Write strictly using python's json module (no hand-typed numbers)
    with open(resolved_metrics_path, "w", encoding="utf-8") as f:
        json.dump(honest_metrics_payload, f, indent=2)

    if verbose:
        print(f"[train_rf] Honest evaluation metrics dumped to '{resolved_metrics_path}'.\n")

    return final_model, honest_metrics_payload


# Backward-compatible pipeline alias
train_and_save_pipeline = train_and_save_fan_pipeline


if __name__ == "__main__":
    default_csv = PROJECT_ROOT / "data" / "processed" / "training_features.csv"
    default_out = PROJECT_ROOT / "models" / "baseline_rf_fan.pkl"
    default_metrics = PROJECT_ROOT / "ml" / "evaluation" / "rf_fan_metrics.json"

    if default_csv.exists():
        print(f"[train_rf] Training Fan Random Forest model on '{default_csv}'...")
        train_and_save_fan_pipeline(
            data=default_csv,
            model_output_path=default_out,
            metrics_output_path=default_metrics,
            verbose=True,
        )
    else:
        print(f"[train_rf] Default dataset not found at '{default_csv}'.")
