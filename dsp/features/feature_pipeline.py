"""Feature Extraction Pipeline for MachineSense.

Coordinates audio preprocessing, windowed FFT analysis, and bandpass envelope
demodulation to produce domain-engineered acoustic features for condition monitoring.
"""

from pathlib import Path
import sys
from typing import Dict, List, Optional, Union
import numpy as np
from scipy import stats
import librosa

# Support execution both as direct script and as package module
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dsp.preprocessing.audio_loader import AudioPreprocessor
from dsp.fft.fft_analyzer import FFTAnalyzer
from dsp.envelope.envelope_analyzer import EnvelopeAnalyzer, calculate_envelope

FEATURE_VERSION: int = 2

FEATURE_NAMES: List[str] = [
    "crest_factor",
    "kurtosis",
    "skewness",
    "dominant_frequency",
    "spectral_centroid",
    "spectral_bandwidth",
    "spectral_rolloff",
    "spectral_flatness",
    "envelope_kurtosis",
    "envelope_spectrum_peak_hz",
    "envelope_spectrum_peak_amp",
]


class FeatureExtractor:
    """Extracts scale-invariant and demodulated spectral features from machine audio signals."""

    def __init__(
        self,
        target_sr: int = 16000,
        resonance_band: tuple = (2000.0, 6000.0),
    ):
        """Initialize feature extractor with preprocessing, FFT, and envelope analyzers.

        Args:
            target_sr (int): Target sampling rate in Hz (default: 16000).
            resonance_band (tuple): Bandpass cutoff range for envelope demodulation in Hz.
        """
        self.target_sr = target_sr
        self.resonance_band = resonance_band
        self.preprocessor = AudioPreprocessor(target_sr=target_sr)
        self.fft_analyzer = FFTAnalyzer(normalize=True)
        self.envelope_analyzer = EnvelopeAnalyzer(default_band=resonance_band, default_sr=target_sr)

    def extract_features_from_signal(
        self, signal: np.ndarray, sample_rate: int
    ) -> Dict[str, float]:
        """Compute the frozen 11 domain features from a 1D preprocessed signal array.

        Args:
            signal (np.ndarray): 1D preprocessed signal array.
            sample_rate (int): Sampling rate in Hz.

        Returns:
            Dict[str, float]: Strict dictionary with keys matching FEATURE_NAMES.
        """
        if signal is None:
            raise ValueError("Input signal cannot be None.")

        if not isinstance(signal, np.ndarray):
            signal = np.asarray(signal)

        if signal.ndim != 1:
            if signal.ndim == 2 and 1 in signal.shape:
                signal = signal.squeeze()
            else:
                raise ValueError(f"Signal must be 1D, got shape {signal.shape}")

        if signal.size == 0:
            raise ValueError("Signal cannot be empty.")

        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be positive, got {sample_rate}")

        # 1. Time-Domain Shape Metrics (Scale-invariant)
        rms = float(np.sqrt(np.mean(signal ** 2)))
        peak = float(np.max(np.abs(signal)))
        crest_factor = float(peak / (rms + 1e-12))
        kurtosis = float(stats.kurtosis(signal, fisher=True))
        skewness = float(stats.skew(signal))

        # 2. Frequency-Domain Features (Windowed FFT, ignoring DC bin 0)
        frequencies, magnitudes = self.fft_analyzer.compute_fft(
            signal, sample_rate, normalize=True, apply_window=True
        )
        if len(magnitudes) > 1:
            dominant_idx = int(np.argmax(magnitudes[1:])) + 1
            dominant_frequency = float(frequencies[dominant_idx])
        else:
            dominant_frequency = 0.0

        # Spectral distribution metrics via librosa
        spec_centroid_arr = librosa.feature.spectral_centroid(y=signal, sr=sample_rate)
        spectral_centroid = float(np.mean(spec_centroid_arr))

        spec_bandwidth_arr = librosa.feature.spectral_bandwidth(y=signal, sr=sample_rate)
        spectral_bandwidth = float(np.mean(spec_bandwidth_arr))

        spec_rolloff_arr = librosa.feature.spectral_rolloff(
            y=signal, sr=sample_rate, roll_percent=0.85
        )
        spectral_rolloff = float(np.mean(spec_rolloff_arr))

        spec_flatness_arr = librosa.feature.spectral_flatness(y=signal)
        spectral_flatness = float(np.mean(spec_flatness_arr))

        # 3. True Envelope Analysis (2 kHz - 6 kHz Bandpass Demodulation + Envelope Spectrum)
        envelope = self.envelope_analyzer.calculate_envelope(
            signal, sr=sample_rate, band=self.resonance_band
        )
        envelope_kurtosis = float(stats.kurtosis(envelope, fisher=True))

        env_peak_hz, env_peak_amp = self.envelope_analyzer.compute_envelope_spectrum(
            envelope, sr=sample_rate
        )
        envelope_spectrum_peak_hz = float(env_peak_hz)
        envelope_spectrum_peak_amp = float(env_peak_amp)

        # Strictly return only the frozen FEATURE_NAMES
        return {
            "crest_factor": crest_factor,
            "kurtosis": kurtosis,
            "skewness": skewness,
            "dominant_frequency": dominant_frequency,
            "spectral_centroid": spectral_centroid,
            "spectral_bandwidth": spectral_bandwidth,
            "spectral_rolloff": spectral_rolloff,
            "spectral_flatness": spectral_flatness,
            "envelope_kurtosis": envelope_kurtosis,
            "envelope_spectrum_peak_hz": envelope_spectrum_peak_hz,
            "envelope_spectrum_peak_amp": envelope_spectrum_peak_amp,
        }

    def extract_features(self, filepath: Union[str, Path]) -> Dict[str, float]:
        """Execute end-to-end DSP feature extraction pipeline on an audio file.

        Args:
            filepath (Union[str, Path]): Path to target audio file.

        Returns:
            Dict[str, float]: Strict dictionary with keys matching FEATURE_NAMES.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Audio file does not exist: '{path.resolve()}'")

        try:
            cleaned_signal, sample_rate = self.preprocessor.preprocess(path)
            return self.extract_features_from_signal(cleaned_signal, sample_rate)
        except (FileNotFoundError, ValueError):
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Feature extraction pipeline failed on file '{path.name}': {exc}"
            ) from exc


if __name__ == "__main__":
    import json
    import tempfile
    import soundfile as sf

    print("=" * 60)
    print(f"FeatureExtractor Self-Verification Test (FEATURE_VERSION = {FEATURE_VERSION})")
    print("=" * 60)

    extractor = FeatureExtractor(target_sr=16000)

    # 1. Synthesize 1-second audio: 400 Hz tone + 3500 Hz carrier modulated at 75 Hz
    sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    synthetic_signal = (
        0.5 * np.sin(2 * np.pi * 400.0 * t)
        + 0.3 * (1.0 + np.sin(2 * np.pi * 75.0 * t)) * np.sin(2 * np.pi * 3500.0 * t)
    ).astype(np.float32)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        dummy_wav_path = Path(tmp_file.name)

    try:
        sf.write(str(dummy_wav_path), synthetic_signal, sr)
        feature_dict = extractor.extract_features(dummy_wav_path)

        print("\nExtracted Feature Dictionary:")
        print(json.dumps(feature_dict, indent=2))

        # Verify strict key match
        assert list(feature_dict.keys()) == FEATURE_NAMES, "Extracted keys do not strictly match FEATURE_NAMES"
        for name in FEATURE_NAMES:
            assert np.isfinite(feature_dict[name]), f"Feature {name} is not finite: {feature_dict[name]}"

        # Verify dominant frequency is 400 Hz (not DC 0 Hz)
        print(f"\nDominant frequency: {feature_dict['dominant_frequency']:.2f} Hz (Expected: ~400 Hz)")
        assert abs(feature_dict["dominant_frequency"] - 400.0) <= 5.0, "Dominant frequency deviated"

        # Verify envelope spectrum peak is ~75 Hz
        print(f"Envelope spectrum peak: {feature_dict['envelope_spectrum_peak_hz']:.2f} Hz (Expected: ~75 Hz)")
        assert abs(feature_dict["envelope_spectrum_peak_hz"] - 75.0) <= 5.0, "Envelope peak deviated"

        print("\n[PASS] All 11 frozen features verified successfully!")
    finally:
        if dummy_wav_path.exists():
            dummy_wav_path.unlink()

    print("=" * 60)
