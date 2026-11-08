"""Resonance Demodulation and Envelope Analysis Module.

Extracts the analytic signal and instantaneous amplitude envelope using
Butterworth bandpass filtering and the Hilbert transform for bearing defect detection.
"""

from typing import Any, Optional, Tuple, Union
import numpy as np
from scipy.signal import butter, filtfilt, hilbert
from scipy.signal.windows import hann


def calculate_envelope(
    sig: np.ndarray,
    sr: Optional[int] = None,
    sample_rate: Optional[int] = None,
    band: Tuple[float, float] = (2000.0, 6000.0),
    filter_order: int = 4,
) -> np.ndarray:
    """Compute amplitude envelope using Butterworth bandpass pre-filtering and Hilbert transform.

    Applies a zero-phase bandpass filter around high-frequency structural resonances
    (typically 2 kHz - 6 kHz) to isolate impact ring-downs from low-frequency rotational
    unbalance, followed by the Hilbert transform modulus.

    Args:
        sig (np.ndarray): 1D time-domain audio signal.
        sr (Optional[int]): Sampling rate in Hz (default: 16000).
        sample_rate (Optional[int]): Alias for sr.
        band (Tuple[float, float]): Lower and upper cutoff frequencies in Hz (default: (2000, 6000)).
        filter_order (int): Order of the Butterworth filter (default: 4).

    Returns:
        np.ndarray: 1D non-negative instantaneous amplitude envelope.
    """
    effective_sr = sr if sr is not None else (sample_rate if sample_rate is not None else 16000)

    if sig is None:
        raise ValueError("Input signal cannot be None.")

    if not isinstance(sig, np.ndarray):
        try:
            sig = np.asarray(sig)
        except Exception as exc:
            raise TypeError(f"Could not convert input to numpy array: {exc}") from exc

    if sig.ndim != 1:
        if sig.ndim == 2 and 1 in sig.shape:
            sig = sig.squeeze()
        else:
            raise ValueError(f"Input signal must be a 1D array. Received shape: {sig.shape}")

    if sig.size == 0:
        raise ValueError("Input signal is empty.")

    if not np.issubdtype(sig.dtype, np.number):
        raise TypeError(f"Signal must contain numeric data, got dtype: {sig.dtype}")

    if not np.all(np.isfinite(sig)):
        raise ValueError("Input signal contains non-finite values (NaN or Inf).")

    if not np.issubdtype(sig.dtype, np.floating):
        sig = sig.astype(np.float64)

    filtered_sig = sig
    if band is not None and effective_sr > 0:
        f_nyq = 0.5 * effective_sr
        low, high = float(band[0]), float(band[1])

        # Guard against Nyquist limits
        if high >= f_nyq:
            high = 0.95 * f_nyq
        if low <= 0:
            low = 100.0

        if low < high and low < f_nyq:
            wn = [low / f_nyq, high / f_nyq]
            # Need sufficient length for zero-phase filtfilt padding
            min_len = 3 * (2 * filter_order + 1)
            if len(sig) > min_len:
                try:
                    ba_filter: Any = butter(filter_order, wn, btype="bandpass", output="ba")
                    b, a = ba_filter[0], ba_filter[1]
                    filtered_sig = filtfilt(b, a, sig)
                except Exception:
                    filtered_sig = sig

    # Analytic signal via Hilbert transform
    analytic = hilbert(filtered_sig)
    envelope = np.abs(analytic)
    return envelope


def compute_envelope_spectrum(
    envelope: np.ndarray,
    sr: Optional[int] = None,
    sample_rate: Optional[int] = None,
) -> Tuple[float, float]:
    """Compute the envelope spectrum and extract dominant defect frequency and amplitude.

    Subtracts the DC mean, applies a Hann window, computes single-sided FFT,
    and identifies the maximum spectral peak ignoring the DC bin (bin 0).

    Args:
        envelope (np.ndarray): 1D amplitude envelope array.
        sr (Optional[int]): Sampling rate in Hz (default: 16000).
        sample_rate (Optional[int]): Alias for sr.

    Returns:
        Tuple[float, float]:
            - envelope_spectrum_peak_hz: Frequency of highest peak in Hz (excluding DC).
            - envelope_spectrum_peak_amp: Magnitude of that peak.
    """
    effective_sr = sr if sr is not None else (sample_rate if sample_rate is not None else 16000)

    if envelope is None or len(envelope) == 0:
        return 0.0, 0.0

    # Demean envelope to eliminate large DC component
    env_demeaned = envelope - np.mean(envelope)
    n = len(env_demeaned)

    # Apply Hann window to minimize spectral leakage
    w = hann(n)
    windowed = env_demeaned * w

    fft_vals = np.fft.rfft(windowed)
    freqs = np.fft.rfftfreq(n, d=1.0 / float(effective_sr))
    mags = np.abs(fft_vals)

    # Normalize single-sided magnitude
    mags = (mags * 2.0) / n

    if len(mags) > 1:
        # Strictly ignore DC bin 0
        peak_idx = int(np.argmax(mags[1:])) + 1
        peak_hz = float(freqs[peak_idx])
        raw_peak_amp = float(mags[peak_idx])
        peak_amp = float(raw_peak_amp / (envelope.mean() + 1e-12))
    else:
        peak_hz = 0.0
        peak_amp = 0.0

    return peak_hz, peak_amp


class EnvelopeAnalyzer:
    """Class wrapper for resonance envelope extraction and envelope spectrum analysis."""

    def __init__(self, default_band: Tuple[float, float] = (2000.0, 6000.0), default_sr: int = 16000):
        self.default_band = default_band
        self.default_sr = default_sr

    def calculate_envelope(
        self,
        signal: np.ndarray,
        sr: Optional[int] = None,
        sample_rate: Optional[int] = None,
        band: Optional[Tuple[float, float]] = None,
        filter_order: int = 4,
    ) -> np.ndarray:
        """Compute the instantaneous amplitude envelope using bandpass filtering + Hilbert transform."""
        effective_sr = sr if sr is not None else (sample_rate if sample_rate is not None else self.default_sr)
        b = band if band is not None else self.default_band
        return calculate_envelope(signal, sr=effective_sr, band=b, filter_order=filter_order)

    def compute_envelope_spectrum(
        self,
        envelope: np.ndarray,
        sr: Optional[int] = None,
        sample_rate: Optional[int] = None,
    ) -> Tuple[float, float]:
        """Compute the envelope spectrum and return peak frequency and peak amplitude."""
        effective_sr = sr if sr is not None else (sample_rate if sample_rate is not None else self.default_sr)
        return compute_envelope_spectrum(envelope, sr=effective_sr)


if __name__ == "__main__":
    print("=" * 60)
    print("EnvelopeAnalyzer Self-Verification Test")
    print("=" * 60)

    analyzer = EnvelopeAnalyzer()

    # 1. Synthesize bearing defect pulse signal:
    # 3500 Hz resonance carrier modulated by 60 Hz defect impact frequency
    test_sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(test_sr * duration), endpoint=False)
    impact_rate = 60.0  # Hz
    carrier = np.sin(2 * np.pi * 3500.0 * t)
    modulator = (np.sin(2 * np.pi * impact_rate * t) > 0.8).astype(np.float32)
    test_sig = (modulator * carrier).astype(np.float32)

    # 2. Extract envelope with bandpass (2000, 6000)
    env = analyzer.calculate_envelope(test_sig, sr=test_sr, band=(2000.0, 6000.0))
    assert env.shape == test_sig.shape, "Envelope shape mismatch"
    assert np.all(env >= 0), "Envelope values must be non-negative"

    # 3. Compute envelope spectrum
    peak_hz, peak_amp = analyzer.compute_envelope_spectrum(env, sr=test_sr)
    print(f"Detected envelope spectrum peak: {peak_hz:.2f} Hz, amplitude: {peak_amp:.4f}")
    assert abs(peak_hz - impact_rate) <= 3.0, f"Expected ~60 Hz, got {peak_hz:.2f} Hz"

    print("[PASS] True Envelope Spectrum Analysis successfully verified!")
    print("=" * 60)
