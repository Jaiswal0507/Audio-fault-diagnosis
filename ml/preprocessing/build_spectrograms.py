"""Mel-Spectrogram Generation and Preprocessing Pipeline for MachineSense.

This module provides parallel extraction of Mel-Spectrograms from acoustic dataset
recordings, converting them into decibel-scaled representations and saving them as
borderless PNG images for Convolutional Neural Network (CNN) acoustic classifiers.
"""

import multiprocessing as mp
import os
from pathlib import Path
import sys
from typing import Any, List, Optional, Sequence, Tuple, Union

import librosa
import numpy as np

# Configure non-interactive backend for headless and multiprocess-safe image generation
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure project root is available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datasets.dataset_loader import DatasetManager


def save_spectrogram_image(
    mel_spec_db: np.ndarray,
    output_path: Union[str, Path],
    cmap: str = "magma",
    figsize: Tuple[float, float] = (4.0, 4.0),
    dpi: int = 100,
) -> Path:
    """Save decibel Mel-Spectrogram as a PNG image strictly without axes, margins, or whitespace.

    Args:
        mel_spec_db (np.ndarray): Decibel-scaled Mel-Spectrogram matrix.
        output_path (Union[str, Path]): Destination PNG file path.
        cmap (str): Matplotlib colormap (default: 'magma').
        figsize (Tuple[float, float]): Figure dimensions in inches (default: (4.0, 4.0)).
        dpi (int): Image resolution dots per inch (default: 100).

    Returns:
        Path: Destination path of the saved PNG image.
    """
    dest = Path(output_path).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=figsize, dpi=dpi)
    # Position axes to fill 100% of the figure canvas with zero margin
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_axis_off()
    ax.imshow(mel_spec_db, aspect="auto", origin="lower", cmap=cmap)

    # Save strictly without padding or bounding box borders
    fig.savefig(str(dest), bbox_inches="tight", pad_inches=0.0, format="png")
    plt.close(fig)

    return dest


def process_single_audio(
    task: Sequence[Any],
) -> Tuple[bool, str]:
    """Process a single audio sample: load, compute log-mel spectrogram, and save PNG image.

    This top-level function is designed for pickling across worker processes in
    Python's multiprocessing pool.

    Args:
        task: Task parameters tuple or sequence:
            (filepath, machine_type, condition, filename, machine_id, output_root, target_sr, n_mels, fmax, cmap)

    Returns:
        Tuple[bool, str]: Success status and output image path (or error message on failure).
    """
    filepath = str(task[0])
    machine_type = str(task[1])
    condition = str(task[2])
    filename = str(task[3])

    if len(task) >= 10:
        machine_id = str(task[4])
        output_root = str(task[5])
        target_sr = int(task[6])
        n_mels = int(task[7])
        fmax = int(task[8])
        cmap = str(task[9])
    else:
        # Fallback for 9-element legacy tasks without machine_id
        output_root = str(task[4])
        target_sr = int(task[5])
        n_mels = int(task[6])
        fmax = int(task[7])
        cmap = str(task[8])

        # Infer machine_id from filepath if omitted
        machine_id = "default"
        for part in reversed(Path(filepath).parts):
            if part.lower().startswith("id_") or part.lower().startswith("section_"):
                machine_id = part
                break

    try:
        # Include machine_id in destination directory structure to strictly prevent cross-machine overwrites
        dest_dir = Path(output_root) / machine_type / condition / machine_id
        dest_path = dest_dir / f"{Path(filename).stem}.png"

        # 1. Load audio signal
        y, sr = librosa.load(filepath, sr=target_sr)

        # Guard against Nyquist violations if sample rate is lower than 2 * fmax
        effective_fmax = fmax if (sr is None or sr >= 2 * fmax) else (sr // 2)

        # 2. Compute Mel-Spectrogram (n_mels=128, fmax=8000)
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_mels=n_mels,
            fmax=effective_fmax,
        )

        # 3. Convert power spectrogram to decibels (dB)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        # 4. Save spectrogram strictly removing axes, margins, and whitespace
        save_spectrogram_image(mel_spec_db, dest_path, cmap=cmap)

        return True, str(dest_path)
    except Exception as exc:
        return False, f"Failed processing '{filename}': {exc}"


def generate_spectrograms(
    raw_data_path: Union[str, Path],
    output_dir: Union[str, Path],
    target_sr: int = 16000,
    n_mels: int = 128,
    fmax: int = 8000,
    cmap: str = "magma",
    num_workers: Optional[int] = None,
    verbose: bool = True,
) -> List[str]:
    """Scan audio dataset directory and generate Mel-Spectrogram images in parallel.

    Saves images under the structured hierarchy:
        <output_dir>/<machine_type>/<condition>/<machine_id>/<original_filename>.png

    Args:
        raw_data_path (Union[str, Path]): Root path containing raw audio folder structure.
        output_dir (Union[str, Path]): Destination directory for generated spectrograms.
        target_sr (int): Target sampling rate for librosa (default: 16000 Hz).
        n_mels (int): Number of Mel frequency bands (default: 128).
        fmax (int): Maximum frequency cutoff in Hz (default: 8000).
        cmap (str): Matplotlib colormap (default: 'magma').
        num_workers (Optional[int]): Number of parallel worker processes (default: cpu_count).
        verbose (bool): Whether to log progress statements (default: True).

    Returns:
        List[str]: List of paths to successfully generated spectrogram PNG files.

    Raises:
        FileNotFoundError: If raw_data_path does not exist.
        ValueError: If no audio files are discovered in raw_data_path.
    """
    raw_path = Path(raw_data_path).resolve()
    out_root = Path(output_dir).resolve()

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw audio data path not found: '{raw_path}'")

    # 1. Discover all audio samples using DatasetManager
    dataset_mgr = DatasetManager()
    samples = dataset_mgr.scan_directory(raw_path)

    if not samples:
        raise ValueError(f"No audio recordings discovered in: '{raw_path}'")

    total_samples = len(samples)
    if verbose:
        print(
            f"[build_spectrograms] Discovered {total_samples} audio recordings in '{raw_path.name}'."
        )

    # 2. Prepare task parameter tuples for multiprocessing (includes machine_id)
    tasks = [
        (
            sample["filepath"],
            sample["machine_type"],
            sample["condition"],
            sample["filename"],
            sample.get("machine_id", "default") or "default",
            str(out_root),
            target_sr,
            n_mels,
            fmax,
            cmap,
        )
        for sample in samples
    ]

    workers = num_workers if num_workers and num_workers > 0 else max(1, os.cpu_count() or 1)
    if verbose:
        print(
            f"[build_spectrograms] Processing {total_samples} spectrograms across "
            f"{workers} worker process(es)..."
        )

    generated_paths: List[str] = []
    failed_items: List[str] = []

    # 3. Parallel extraction and rendering via multiprocessing.Pool
    with mp.Pool(processes=workers) as pool:
        for idx, (success, result) in enumerate(
            pool.imap_unordered(process_single_audio, tasks), 1
        ):
            if success:
                generated_paths.append(result)
            else:
                failed_items.append(result)
                if verbose:
                    print(f"[build_spectrograms] Warning: {result}")

            if verbose and (idx % 10 == 0 or idx == total_samples):
                pct = (idx / total_samples) * 100
                print(
                    f"[build_spectrograms] Progress: {idx}/{total_samples} "
                    f"spectrograms generated ({pct:.1f}%)..."
                )

    if verbose:
        print(
            f"[build_spectrograms] Successfully completed: {len(generated_paths)} "
            f"spectrograms created in '{out_root}'."
        )
        if failed_items:
            print(f"[build_spectrograms] Note: {len(failed_items)} files failed to process.")

    return generated_paths


if __name__ == "__main__":
    raw_path = PROJECT_ROOT / "datasets"
    output_dir = PROJECT_ROOT / "data" / "spectrograms"

    if not raw_path.exists():
        print(f"[build_spectrograms] Error: Raw datasets folder not found at '{raw_path}'.")
        sys.exit(1)

    try:
        generate_spectrograms(
            raw_data_path=raw_path,
            output_dir=output_dir,
            target_sr=16000,
            n_mels=128,
            fmax=8000,
            verbose=True,
        )
    except Exception as exc:
        print(f"[build_spectrograms] Execution failed: {exc}")
        sys.exit(1)

