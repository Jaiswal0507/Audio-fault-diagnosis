"""Audio Preprocessing Module for MachineSense.

This module provides the AudioPreprocessor class to validate, load,
convert to mono, and resample acoustic machine signals.
Raw amplitude variance is preserved (peak normalization removed) so that
domain-engineered DSP features retain natural physical scaling without artificial distortion.
"""

from pathlib import Path
from typing import Tuple, Union
import numpy as np
import librosa


class AudioPreprocessor:
    """Preprocessor for acoustic signals in the MachineSense pipeline.

    Handles audio loading with standardized sampling rate (16 kHz),
    channel conversion to mono, and resampling.
    """

    SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"}

    def __init__(self, target_sr: int = 16000):
        """Initialize AudioPreprocessor.

        Args:
            target_sr (int): Target sampling rate in Hz (default: 16000 Hz).
        """
        if not isinstance(target_sr, int) or target_sr <= 0:
            raise ValueError(f"Target sample rate must be a positive integer, got: {target_sr}")
        self.target_sr = target_sr

    def load_audio(
        self, filepath: Union[str, Path], sr: Union[int, None] = 16000
    ) -> Tuple[np.ndarray, int]:
        """Validate existence and format, then load audio file.

        Args:
            filepath (Union[str, Path]): Path to the target audio file.
            sr (Union[int, None]): Target sampling rate during load (defaults to 16000 Hz).

        Returns:
            Tuple[np.ndarray, int]: Audio signal array and sampling rate.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file format is unsupported, file is empty, or corrupted.
            RuntimeError: If librosa fails to decode the audio file.
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: '{path.resolve()}'")

        if not path.is_file():
            raise ValueError(f"Path is not a file: '{path.resolve()}'")

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format '{path.suffix}'. "
                f"Supported formats: {sorted(self.SUPPORTED_EXTENSIONS)}"
            )

        if path.stat().st_size == 0:
            raise ValueError(f"Audio file is empty (0 bytes): '{path.resolve()}'")

        target_load_sr = sr if sr is not None else self.target_sr

        try:
            # Load with explicit sampling rate (16000 Hz) to avoid sensor domain mismatches
            signal, sample_rate = librosa.load(str(path), sr=target_load_sr, mono=False)
        except Exception as exc:
            raise RuntimeError(f"Failed to load/decode audio file '{path.name}': {exc}") from exc

        if signal is None or signal.size == 0:
            raise ValueError(f"Loaded audio signal from '{path.name}' is empty.")

        return signal, int(sample_rate)

    def convert_to_mono(self, signal: np.ndarray) -> np.ndarray:
        """Ensure the audio signal is single-channel (mono).

        Args:
            signal (np.ndarray): Audio signal (1D array or 2D multichannel array).

        Returns:
            np.ndarray: Single-channel 1D audio signal.

        Raises:
            TypeError: If input is not a numpy array.
            ValueError: If signal array dimensions are invalid (> 2 dimensions).
        """
        if not isinstance(signal, np.ndarray):
            signal = np.asarray(signal)

        if signal.ndim == 1:
            return signal
        elif signal.ndim == 2:
            # Check shape: librosa expects (channels, samples)
            if signal.shape[0] > signal.shape[1] and signal.shape[1] <= 8:
                signal = signal.T
            return librosa.to_mono(signal)
        else:
            raise ValueError(
                f"Invalid signal shape {signal.shape}. Expected 1D (mono) or 2D (multichannel) array."
            )

    def resample_audio(
        self, signal: np.ndarray, orig_sr: int, target_sr: Union[int, None] = None
    ) -> np.ndarray:
        """Resample the audio signal to the target sampling rate (default 16 kHz).

        Args:
            signal (np.ndarray): Single-channel or multichannel audio array.
            orig_sr (int): Original sampling rate of the signal in Hz.
            target_sr (Union[int, None]): Desired sampling rate in Hz (defaults to self.target_sr).

        Returns:
            np.ndarray: Resampled audio signal.

        Raises:
            ValueError: If sample rates are invalid or signal is empty.
        """
        if target_sr is None:
            target_sr = self.target_sr

        if orig_sr <= 0 or target_sr <= 0:
            raise ValueError(
                f"Sampling rates must be positive. Received orig_sr={orig_sr}, target_sr={target_sr}"
            )

        if signal.size == 0:
            raise ValueError("Cannot resample empty signal.")

        if orig_sr == target_sr:
            return signal

        return librosa.resample(
            y=signal,
            orig_sr=orig_sr,
            target_sr=target_sr,
        )

    def normalize_amplitude(self, signal: np.ndarray) -> np.ndarray:
        """Passthrough signal preserving genuine physical amplitude variance.

        Note: Peak normalization (forcing max absolute amplitude to 1.0) has been intentionally
        removed so that DSP features (RMS, spectral energy, envelope energy) retain true physical
        vibration scale and avoid collinearity.
        """
        if not isinstance(signal, np.ndarray):
            signal = np.asarray(signal)
        return signal

    def preprocess(
        self, filepath: Union[str, Path], target_sr: Union[int, None] = None
    ) -> Tuple[np.ndarray, int]:
        """Execute the full preprocessing pipeline on an audio file.

        Chains: load (sr=16000) -> convert_to_mono -> resample (if needed).
        Peak normalization is bypassed so downstream feature extraction preserves genuine acoustic variance.

        Args:
            filepath (Union[str, Path]): Path to raw audio file.
            target_sr (Union[int, None]): Target sampling rate (defaults to self.target_sr).

        Returns:
            Tuple[np.ndarray, int]: Cleaned 1D audio signal and final sample rate.
        """
        if target_sr is None:
            target_sr = self.target_sr

        # 1. Load audio file with standardized 16000 Hz sample rate
        raw_signal, native_sr = self.load_audio(filepath, sr=target_sr)

        # 2. Convert to mono
        mono_signal = self.convert_to_mono(raw_signal)

        # 3. Resample to target sample rate if native_sr differs
        resampled_signal = self.resample_audio(
            mono_signal, orig_sr=native_sr, target_sr=target_sr
        )

        return resampled_signal, target_sr


if __name__ == "__main__":
    print("=" * 60)
    print("MachineSense - AudioPreprocessor Self-Verification Test")
    print("=" * 60)

    preprocessor = AudioPreprocessor(target_sr=16000)

    # 1. Test convert_to_mono with mock stereo array
    np.random.seed(42)
    mock_stereo = np.random.uniform(-0.6, 0.6, size=(2, 44100)).astype(np.float32)
    mono = preprocessor.convert_to_mono(mock_stereo)
    assert mono.ndim == 1, f"Expected 1D mono signal, got ndim={mono.ndim}"
    assert len(mono) == 44100, f"Expected 44100 samples, got {len(mono)}"
    print("[PASS] convert_to_mono: stereo (2, 44100) -> mono (44100,)")

    # 2. Test resample_audio: 44.1 kHz -> 16 kHz
    orig_sr = 44100
    target_sr = 16000
    resampled = preprocessor.resample_audio(mono, orig_sr=orig_sr, target_sr=target_sr)
    expected_len = int(round(len(mono) * target_sr / orig_sr))
    assert abs(len(resampled) - expected_len) <= 2, (
        f"Resampled length mismatch: expected ~{expected_len}, got {len(resampled)}"
    )
    print(f"[PASS] resample_audio: {orig_sr} Hz ({len(mono)} samples) -> {target_sr} Hz ({len(resampled)} samples)")

    # 3. Test raw amplitude variance preservation (no peak normalization)
    test_sig = np.array([0.1, -0.4, 0.25, -0.05], dtype=np.float32)
    processed_sig = preprocessor.normalize_amplitude(test_sig)
    assert np.allclose(test_sig, processed_sig), "Signal amplitude must be preserved without peak normalization"
    print("[PASS] normalize_amplitude: raw amplitude variance preserved without artificial peak scaling")

    # 4. Test error handling for non-existent file
    try:
        preprocessor.load_audio("non_existent_audio_file.wav")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        print("[PASS] load_audio: correctly raised FileNotFoundError for missing file")

    # 5. Test error handling for invalid format
    try:
        dummy_txt = Path("test_dummy.txt")
        dummy_txt.write_text("not an audio file")
        try:
            preprocessor.load_audio(dummy_txt)
            assert False, "Should have raised ValueError"
        finally:
            if dummy_txt.exists():
                dummy_txt.unlink()
    except ValueError as e:
        print(f"[PASS] load_audio: correctly rejected invalid extension ({e})")

    # 6. Test with a synthetic audio file on disk
    import tempfile
    import scipy.io.wavfile as wavfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_path = Path(tmp_wav.name)

    try:
        t = np.linspace(0, 1.0, 44100, endpoint=False, dtype=np.float32)
        sine_wave = 0.5 * np.sin(2 * np.pi * 440.0 * t)
        wavfile.write(str(tmp_path), 44100, (sine_wave * 32767).astype(np.int16))

        cleaned_signal, final_sr = preprocessor.preprocess(tmp_path)
        assert final_sr == 16000, f"Expected 16000 Hz, got {final_sr}"
        assert cleaned_signal.ndim == 1, "Cleaned signal must be 1D"
        # Since peak normalization is removed, peak amplitude should reflect the genuine ~0.5 scale
        peak_amp = float(np.max(np.abs(cleaned_signal)))
        assert 0.4 <= peak_amp <= 0.6, f"Expected genuine peak ~0.5, got {peak_amp}"
        print(f"[PASS] preprocess: 16kHz mono signal loaded with preserved amplitude scale (peak: {peak_amp:.4f})")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    print("=" * 60)
    print("All AudioPreprocessor tests PASSED successfully!")
    print("=" * 60)
