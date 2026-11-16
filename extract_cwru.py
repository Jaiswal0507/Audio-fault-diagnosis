"""CWRU Bearing Dataset Extraction and Audio Conversion Pipeline.

Converts Case Western Reserve University (CWRU) vibration MAT files
to standardized 16 kHz mono WAV audio segments for machine fault diagnosis models.
Explicitly resamples raw sensor signals to 16000 Hz to prevent pitch shifting.
"""

import os
from pathlib import Path
import librosa
import numpy as np
import scipy.io
import soundfile as sf

# Dataset directories configured via relative paths or environment variables
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = Path(os.getenv("CWRU_RAW_DIR", BASE_DIR / "datasets" / "raw"))
OUT_DIR = Path(os.getenv("CWRU_OUT_DIR", BASE_DIR / "datasets" / "cwru"))
TARGET_SR = 16000

# Mapping prefixes to bearing fault condition classes
CLASSES = {
    "B": "ball_defect",
    "IR": "inner_race",
    "OR": "outer_race",
    "Time_Normal": "normal",
}


def extract_cwru_dataset(raw_dir: Path = RAW_DIR, out_dir: Path = OUT_DIR, target_sr: int = TARGET_SR) -> int:
    """Extract and resample CWRU vibration signals into 1.0-second WAV files."""
    # Ensure destination subdirectories exist
    for c in CLASSES.values():
        (out_dir / c).mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print(f"Notice: Raw directory '{raw_dir}' not found. Please provide valid CWRU raw MAT files.")
        return 0

    print(f"Scanning '{raw_dir}' for MAT recordings...")
    total_wavs = 0

    for file in sorted(os.listdir(raw_dir)):
        if not file.endswith(".mat"):
            continue

        # Match class label from file prefix
        label = None
        for key, value in CLASSES.items():
            if file.startswith(key):
                label = value
                break

        if not label:
            continue

        # Load MATLAB structured file
        mat_path = raw_dir / file
        try:
            mat_data = scipy.io.loadmat(str(mat_path))
        except Exception as exc:
            print(f"Skipping corrupt or unreadable file '{file}': {exc}")
            continue

        # Extract drive end acceleration time series (_DE_time)
        data_array = None
        for k, v in mat_data.items():
            if "_DE_time" in k or (isinstance(v, np.ndarray) and v.size > 10000):
                data_array = v.flatten().astype(np.float32)
                break

        if data_array is None or len(data_array) == 0:
            continue

        # Identify native sample rate (12 kHz drive-end or 48 kHz normal/high-speed)
        orig_sr = 48000 if ("48" in file or "normal" in file.lower()) else 12000

        # Resample to 16000 Hz to prevent playback pitch distortion
        if orig_sr != target_sr:
            resampled = librosa.resample(y=data_array, orig_sr=orig_sr, target_sr=target_sr)
        else:
            resampled = data_array

        # Scale amplitude to [-1.0, 1.0] range
        max_val = float(np.max(np.abs(resampled)))
        if max_val > 0:
            resampled = resampled / max_val

        # Segment signal into 1.0-second chunks (16000 samples)
        chunk_size = target_sr
        num_chunks = len(resampled) // chunk_size

        for i in range(num_chunks):
            chunk = resampled[i * chunk_size : (i + 1) * chunk_size]
            out_name = f"{Path(file).stem}_chunk_{i}.wav"
            out_path = out_dir / label / out_name

            sf.write(str(out_path), chunk, target_sr)
            total_wavs += 1

    print(f"Extraction complete: Generated {total_wavs} standardized WAV files in '{out_dir}'.")
    return total_wavs


if __name__ == "__main__":
    extract_cwru_dataset()
