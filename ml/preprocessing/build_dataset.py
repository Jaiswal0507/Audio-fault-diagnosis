"""Dataset Preprocessing and Feature Extraction Bridge for MachineSense.

This module provides the batch feature extraction pipeline that scans audio datasets,
computes DSP features via FeatureExtractor, and compiles labeled datasets into CSV format.
"""

from pathlib import Path
import sys
from typing import Optional, Union
import pandas as pd

# Ensure project root is available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datasets.dataset_loader import DatasetManager
from dsp.features.feature_pipeline import FeatureExtractor


def process_all_audio(
    raw_data_path: Union[str, Path],
    output_csv_path: Union[str, Path],
    target_sr: int = 16000,
    verbose: bool = True,
) -> pd.DataFrame:
    """Scan audio dataset directory, extract DSP features, and save combined dataset to CSV.

    Args:
        raw_data_path (Union[str, Path]): Root path containing the raw audio folder structure.
        output_csv_path (Union[str, Path]): Destination file path for the exported CSV dataset.
        target_sr (int): Target sampling rate for feature extraction (default: 16000 Hz).
        verbose (bool): Whether to log progress information (default: True).

    Returns:
        pd.DataFrame: Compiled DataFrame containing metadata, labels, and extracted DSP features.

    Raises:
        FileNotFoundError: If raw_data_path does not exist.
        ValueError: If no audio files are found in the directory.
    """
    raw_path = Path(raw_data_path).resolve()
    out_path = Path(output_csv_path).resolve()

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data path not found: '{raw_path}'")

    # 1. Discover all audio samples using DatasetManager
    dataset_mgr = DatasetManager()
    samples = dataset_mgr.scan_directory(raw_path)

    if not samples:
        raise ValueError(f"No audio files discovered in: '{raw_path}'")

    if verbose:
        print(f"[build_dataset] Discovered {len(samples)} audio recordings in '{raw_path.name}'.")

    # 2. Initialize master feature extractor
    extractor = FeatureExtractor(target_sr=target_sr)
    records = []
    failed_count = 0

    # 3. Process each audio sample
    for idx, sample in enumerate(samples, 1):
        fp = sample["filepath"]
        try:
            features = extractor.extract_features(fp)
            # Combine metadata, label, and numerical features
            row = {
                "filepath": fp,
                "machine_type": sample["machine_type"],
                "machine_id": sample.get("machine_id", "unknown"),
                "condition": sample["condition"],
                **features,
            }
            records.append(row)

            if verbose and (idx % 10 == 0 or idx == len(samples)):
                print(f"[build_dataset] Processed {idx}/{len(samples)} samples...")
        except Exception as exc:
            failed_count += 1
            if verbose:
                print(f"[build_dataset] Warning: failed to extract features for '{Path(fp).name}': {exc}")

    if not records:
        raise RuntimeError("Failed to extract features from any of the discovered audio files.")

    # 4. Compile into pandas DataFrame
    df = pd.DataFrame(records)

    # 5. Save DataFrame to CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    if verbose:
        print(f"[build_dataset] Successfully compiled {len(df)} samples into '{out_path}'.")
        if failed_count > 0:
            print(f"[build_dataset] Note: {failed_count} files could not be processed.")

    return df


if __name__ == "__main__":
    raw_path = PROJECT_ROOT / "datasets"
    out_csv = PROJECT_ROOT / "data" / "processed" / "training_features.csv"
    process_all_audio(raw_path, out_csv, verbose=True)
