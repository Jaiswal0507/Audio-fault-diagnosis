"""CWRU Bearing Dataset Mel-Spectrogram Preprocessing.

This module processes CWRU bearing vibration WAV recordings into Mel-Spectrogram
images using librosa and matplotlib, strictly matching the production backend
feature representation and styling.
"""

from pathlib import Path
import sys
import time
from typing import List, Optional, Union

import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Resolve PROJECT_ROOT (machine-sense repository root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Target defect subdirectories in CWRU dataset
CWRU_CATEGORIES = ["normal", "inner_race", "outer_race", "ball_defect"]


def build_cwru_spectrograms(
    raw_dir: Optional[Union[str, Path]] = None,
    out_dir: Optional[Union[str, Path]] = None,
    target_sr: int = 16000,
    n_mels: int = 128,
    fmax: int = 8000,
    cmap: str = "magma",
) -> List[Path]:
    """Scan CWRU dataset and generate matching Mel-Spectrogram PNG images.

    Args:
        raw_dir: Root directory containing raw CWRU audio subdirectories.
                 Defaults to PROJECT_ROOT / "datasets" / "cwru".
        out_dir: Root directory to save generated spectrogram images.
                 Defaults to PROJECT_ROOT / "data" / "spectrograms" / "cwru".
        target_sr: Target audio sampling rate (default 16000 Hz).
        n_mels: Number of Mel frequency bands (default 128).
        fmax: Highest frequency for Mel filter bank (default 8000 Hz).
        cmap: Matplotlib colormap (default 'magma').

    Returns:
        List of generated PNG image Paths.
    """
    raw_path = Path(raw_dir) if raw_dir else PROJECT_ROOT / "datasets" / "cwru"
    output_path = Path(out_dir) if out_dir else PROJECT_ROOT / "data" / "spectrograms" / "cwru"

    if not raw_path.exists():
        raise FileNotFoundError(f"CWRU dataset directory not found at: '{raw_path.resolve()}'")

    print(f"============================================================")
    print(f"MachineSense - CWRU Spectrogram Generation Pipeline")
    print(f"============================================================")
    print(f"Source Directory: {raw_path.resolve()}")
    print(f"Output Directory: {output_path.resolve()}")
    print(f"Parameters: sr={target_sr}, n_mels={n_mels}, fmax={fmax}, cmap='{cmap}'")
    print(f"============================================================\n")

    # 1. Discover all .wav files across the 4 subdirectories
    all_tasks = []
    for category in CWRU_CATEGORIES:
        cat_dir = raw_path / category
        out_cat_dir = output_path / category
        # Ensure matching output directory exists
        out_cat_dir.mkdir(parents=True, exist_ok=True)

        if not cat_dir.exists():
            print(f"[WARNING] Directory not found: '{cat_dir.resolve()}'. Skipping...")
            continue

        wav_files = sorted(list(cat_dir.glob("*.wav")))
        for wav_file in wav_files:
            dest_file = out_cat_dir / f"{wav_file.stem}.png"
            all_tasks.append((category, wav_file, dest_file))

    total_files = len(all_tasks)
    print(f"Found {total_files} WAV files across CWRU subdirectories.\n")
    if total_files == 0:
        print("No WAV files found to process.")
        return []

    generated_paths: List[Path] = []
    start_time = time.time()

    for idx, (category, wav_path, dest_path) in enumerate(all_tasks, start=1):
        try:
            # 3. Load audio with librosa at target_sr
            y, sr = librosa.load(str(wav_path), sr=target_sr)

            # 4. Compute Mel-spectrogram and convert to dB
            S = librosa.feature.melspectrogram(
                y=y,
                sr=target_sr,
                n_mels=n_mels,
                fmax=fmax,
            )
            S_dB = librosa.power_to_db(S, ref=np.max)

            # 5. Render image EXACTLY like the production backend fix
            fig, ax = plt.subplots(figsize=(3, 3))
            ax.axis("off")
            plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
            librosa.display.specshow(
                S_dB,
                sr=target_sr,
                x_axis="time",
                y_axis="mel",
                fmax=fmax,
                ax=ax,
                cmap=cmap,
            )

            # Save figure directly to target folder
            fig.savefig(str(dest_path), bbox_inches="tight", pad_inches=0)

            # 6. Close figure to free memory
            plt.close(fig)

            generated_paths.append(dest_path)

            # Progress tracking
            if idx % 25 == 0 or idx == total_files:
                pct = (idx / total_files) * 100.0
                elapsed = time.time() - start_time
                print(f"[{idx}/{total_files} - {pct:5.1f}%] Processed: {category}/{wav_path.name} ({elapsed:.1f}s)")

        except Exception as exc:
            print(f"[ERROR] Failed processing '{wav_path.name}': {exc}")

    total_elapsed = time.time() - start_time
    print(f"\n============================================================")
    print(f"[SUCCESS] Spectrogram Generation Complete!")
    print(f"Successfully generated: {len(generated_paths)}/{total_files} spectrograms")
    print(f"Elapsed Time: {total_elapsed:.2f} seconds")
    print(f"Output saved to: {output_path.resolve()}")
    print(f"============================================================")

    return generated_paths


if __name__ == "__main__":
    build_cwru_spectrograms()

