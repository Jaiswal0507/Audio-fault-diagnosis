"""Short-Time Fourier Transform (STFT) Analyzer for MachineSense.

This module provides the STFTAnalyzer class to compute the Short-Time
Fourier Transform on acoustic signals, returning time frames, frequency bins,
and the magnitude spectrogram.
"""

from typing import Tuple, Union
import numpy as np
import librosa


class STFTAnalyzer:
    """Analyzer for computing Short-Time Fourier Transform (STFT) on acoustic signals."""

    def __init__(
        self,
        n_fft: int = 1024,
        hop_length: int = 256,
        win_length: Union[int, None] = None,
        window: str = "hann",
    ):
        """Initialize STFTAnalyzer with default parameters.

        Args:
            n_fft (int): Length of the FFT window (default: 1024).
            hop_length (int): Number of audio samples between adjacent STFT columns (default: 256).
            win_length (Union[int, None]): Window size in samples (default: None, which uses n_fft).
            window (str): Window specification for librosa (default: "hann").
        """
        if not isinstance(n_fft, int) or n_fft <= 0:
            raise ValueError(f"n_fft must be a positive integer, got: {n_fft}")
        if not isinstance(hop_length, int) or hop_length <= 0:
            raise ValueError(f"hop_length must be a positive integer, got: {hop_length}")

        self.n_fft = n_fft
        self.hop_length = hop_length
        self.win_length = win_length
        self.window = window

    def compute_stft(
        self,
        signal: np.ndarray,
        sample_rate: Union[int, float],
        n_fft: Union[int, None] = None,
        hop_length: Union[int, None] = None,
        win_length: Union[int, None] = None,
        window: Union[str, None] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute the Short-Time Fourier Transform (STFT) of an acoustic signal.

        Args:
            signal (np.ndarray): 1D numpy array representing the time-domain signal.
            sample_rate (Union[int, float]): Sampling rate of the audio in Hz.
            n_fft (Union[int, None]): Number of FFT points (overrides default if provided).
            hop_length (Union[int, None]): Hop length in samples (overrides default if provided).
            win_length (Union[int, None]): Window length (overrides default if provided).
            window (Union[str, None]): Window function name (overrides default if provided).

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]:
                - times: 1D numpy array of time coordinates corresponding to each STFT column (in seconds).
                - frequencies: 1D numpy array of frequency bin centers (in Hz).
                - magnitude_spectrogram: 2D numpy array of shape (n_freqs, n_times) containing STFT absolute magnitudes.

        Raises:
            TypeError: If input signal is not an ndarray or not numeric.
            ValueError: If signal is empty, not 1D, contains NaN/Inf, or sample_rate <= 0.
        """
        # Validate sample rate
        if not isinstance(sample_rate, (int, float)) or sample_rate <= 0:
            raise ValueError(f"sample_rate must be a positive number, got: {sample_rate}")

        # Validate signal presence
        if signal is None:
            raise ValueError("Input signal cannot be None.")

        # Ensure ndarray type
        if not isinstance(signal, np.ndarray):
            try:
                signal = np.asarray(signal)
            except Exception as exc:
                raise TypeError(f"Could not convert input to numpy array: {exc}") from exc

        # Ensure 1D signal
        if signal.ndim != 1:
            if signal.ndim == 2 and 1 in signal.shape:
                signal = signal.squeeze()
            else:
                raise ValueError(
                    f"Input signal must be a 1D array. Received shape: {signal.shape}"
                )

        if signal.size == 0:
            raise ValueError("Input signal is empty.")

        # Ensure numeric type and finite values
        if not np.issubdtype(signal.dtype, np.number):
            raise TypeError(f"Signal must contain numeric data, got dtype: {signal.dtype}")

        if not np.all(np.isfinite(signal)):
            raise ValueError("Input signal contains non-finite values (NaN or Inf).")

        # Resolve parameters
        effective_n_fft = n_fft if n_fft is not None else self.n_fft
        effective_hop_length = hop_length if hop_length is not None else self.hop_length
        effective_win_length = win_length if win_length is not None else self.win_length
        effective_window = window if window is not None else self.window

        if effective_n_fft <= 0 or effective_hop_length <= 0:
            raise ValueError("n_fft and hop_length must be strictly positive integers.")

        # Ensure float array for librosa
        if not np.issubdtype(signal.dtype, np.floating):
            signal = signal.astype(np.float32)

        # Compute complex STFT using librosa
        stft_matrix = librosa.stft(
            y=signal,
            n_fft=effective_n_fft,
            hop_length=effective_hop_length,
            win_length=effective_win_length,
            window=effective_window,
            center=True,
        )

        # Compute magnitude spectrogram (absolute values)
        magnitude_spectrogram = np.abs(stft_matrix)

        # Compute frequency values for each bin
        frequencies = librosa.fft_frequencies(sr=float(sample_rate), n_fft=effective_n_fft)

        # Compute time coordinates for each frame
        times = librosa.frames_to_time(
            np.arange(stft_matrix.shape[1]),
            sr=float(sample_rate),
            hop_length=effective_hop_length,
            n_fft=effective_n_fft,
        )

        return times, frequencies, magnitude_spectrogram


if __name__ == "__main__":
    print("=" * 60)
    print("MachineSense - STFTAnalyzer Self-Verification Test")
    print("=" * 60)

    analyzer = STFTAnalyzer(n_fft=1024, hop_length=256)

    # 1. Generate a mock 1-second sine wave at 400 Hz sampled at 16000 Hz
    sample_rate = 16000
    duration = 1.0
    target_freq = 400.0
    num_samples = int(sample_rate * duration)

    time_axis = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
    mock_sine = np.sin(2 * np.pi * target_freq * time_axis)

    # 2. Compute STFT
    times, frequencies, magnitude_spectrogram = analyzer.compute_stft(mock_sine, sample_rate)

    print(f"Signal Length: {len(mock_sine)} samples ({duration}s at {sample_rate} Hz)")
    print(f"Times shape:                 {times.shape} (from {times[0]:.3f}s to {times[-1]:.3f}s)")
    print(f"Frequencies shape:           {frequencies.shape} (0 Hz to {frequencies[-1]:.1f} Hz)")
    print(f"Magnitude spectrogram shape: {magnitude_spectrogram.shape}")

    # Expected shapes:
    # Frequencies: 1 + n_fft // 2 = 1 + 1024 // 2 = 513
    expected_freq_bins = 1 + analyzer.n_fft // 2
    assert frequencies.shape == (expected_freq_bins,), (
        f"Expected frequency bins {expected_freq_bins}, got {frequencies.shape[0]}"
    )
    assert magnitude_spectrogram.shape[0] == expected_freq_bins, (
        f"Spectrogram frequency dimension mismatch"
    )
    assert magnitude_spectrogram.shape[1] == len(times), (
        f"Spectrogram time frames mismatch: {magnitude_spectrogram.shape[1]} vs {len(times)}"
    )

    # 3. Verify dominant frequency along time axis corresponds to ~400 Hz
    mean_spectrum = np.mean(magnitude_spectrogram, axis=1)
    peak_bin = int(np.argmax(mean_spectrum))
    detected_freq = frequencies[peak_bin]
    print(f"Dominant detected frequency in spectrogram: {detected_freq:.2f} Hz (Expected: ~{target_freq} Hz)")
    assert abs(detected_freq - target_freq) <= (frequencies[1] - frequencies[0]), (
        f"Dominant frequency {detected_freq} is not within bin resolution of {target_freq} Hz"
    )
    print("[PASS] STFT spectrogram successfully captured 400 Hz energy ridge!")

    # 4. Error handling tests
    try:
        analyzer.compute_stft(np.zeros((3, 100)), sample_rate)
        assert False, "Should have raised ValueError for 2D multichannel array"
    except ValueError as e:
        print(f"[PASS] Correctly rejected 2D signal ({e})")

    try:
        analyzer.compute_stft(np.array([]), sample_rate)
        assert False, "Should have raised ValueError for empty array"
    except ValueError as e:
        print(f"[PASS] Correctly rejected empty signal ({e})")

    try:
        analyzer.compute_stft(mock_sine, 0)
        assert False, "Should have raised ValueError for non-positive sample rate"
    except ValueError as e:
        print(f"[PASS] Correctly rejected non-positive sample rate ({e})")

    print("=" * 60)
    print("All STFTAnalyzer tests PASSED successfully!")
    print("=" * 60)
