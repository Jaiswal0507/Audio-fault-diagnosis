"""Fast Fourier Transform (FFT) Analyzer.

Computes the 1D Discrete Fourier Transform for real-valued acoustic signals,
applying a Hann window to reduce spectral leakage and returning single-sided
positive frequencies and magnitudes.
"""

from typing import Tuple, Union
import numpy as np
from scipy.signal.windows import hann


class FFTAnalyzer:
    """Analyzer for computing windowed Fast Fourier Transform on acoustic signals."""

    def __init__(self, normalize: bool = False):
        """Initialize FFTAnalyzer.

        Args:
            normalize (bool): If True, normalize magnitudes by signal length (2/N). Default is False.
        """
        self.normalize = normalize

    def compute_fft(
        self,
        signal: np.ndarray,
        sample_rate: Union[int, float],
        normalize: Union[bool, None] = None,
        apply_window: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute the 1D Discrete Fourier Transform for real-valued signals.

        Returns positive frequencies and corresponding spectral magnitudes.

        Args:
            signal (np.ndarray): 1D numpy array representing the time-domain audio signal.
            sample_rate (Union[int, float]): Sampling rate in Hz (must be positive).
            normalize (Union[bool, None]): Whether to scale magnitudes by 2/N. If None, uses self.normalize.
            apply_window (bool): Whether to apply a Hann window prior to FFT (default: True).

        Returns:
            Tuple[np.ndarray, np.ndarray]:
                - frequencies: 1D numpy array of positive frequencies in Hz (0 to Nyquist).
                - magnitudes: 1D numpy array of absolute spectral magnitudes.
        """
        if not isinstance(sample_rate, (int, float)) or sample_rate <= 0:
            raise ValueError(f"sample_rate must be a positive number, got: {sample_rate}")

        if signal is None:
            raise ValueError("Input signal cannot be None.")

        if not isinstance(signal, np.ndarray):
            try:
                signal = np.asarray(signal)
            except Exception as exc:
                raise TypeError(f"Could not convert input to numpy array: {exc}") from exc

        if signal.ndim != 1:
            if signal.ndim == 2 and 1 in signal.shape:
                signal = signal.squeeze()
            else:
                raise ValueError(
                    f"Input signal must be a 1D array. Received shape: {signal.shape}"
                )

        if signal.size == 0:
            raise ValueError("Input signal is empty.")

        if not np.issubdtype(signal.dtype, np.number):
            raise TypeError(f"Signal must contain numeric data, got dtype: {signal.dtype}")

        if not np.all(np.isfinite(signal)):
            raise ValueError("Input signal contains non-finite values (NaN or Inf).")

        n = len(signal)
        frequencies = np.fft.rfftfreq(n, d=1.0 / float(sample_rate))

        windowed_sig = signal
        if apply_window and n > 1:
            w = hann(n)
            windowed_sig = signal * w

        fft_complex = np.fft.rfft(windowed_sig)
        magnitudes = np.abs(fft_complex)

        should_normalize = self.normalize if normalize is None else normalize
        if should_normalize and n > 0:
            magnitudes = (magnitudes * 2.0) / n
            magnitudes[0] /= 2.0
            if n % 2 == 0 and len(magnitudes) > 1:
                magnitudes[-1] /= 2.0

        return frequencies, magnitudes


if __name__ == "__main__":
    print("=" * 60)
    print("FFTAnalyzer Self-Verification Test")
    print("=" * 60)

    analyzer = FFTAnalyzer()

    # 1. Generate a 1-second sine wave at 400 Hz sampled at 16000 Hz
    sample_rate = 16000
    duration = 1.0
    target_freq = 400.0
    num_samples = int(sample_rate * duration)

    time_axis = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
    mock_sine = np.sin(2 * np.pi * target_freq * time_axis)

    # 2. Compute FFT
    frequencies, magnitudes = analyzer.compute_fft(mock_sine, sample_rate, normalize=True)

    # Ignore DC bin (bin 0)
    peak_idx = int(np.argmax(magnitudes[1:])) + 1
    peak_freq = frequencies[peak_idx]
    print(f"Detected dominant peak: {peak_freq:.2f} Hz (Target: {target_freq:.2f} Hz)")
    assert np.isclose(peak_freq, target_freq, atol=1.0), "Peak frequency mismatch"
    print("[PASS] FFT computation with Hann window successfully verified!")
    print("=" * 60)
