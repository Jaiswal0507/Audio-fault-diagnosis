"""
Diagnosis service for MachineSense.
Coordinates DSP feature extraction and routes audio through Fan CNN or CWRU Bearing CNN.
"""

import io
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
import joblib
import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.cm as cm
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import pandas as pd
from PIL import Image
import tensorflow as tf

# Support root directory resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logger = logging.getLogger(__name__)

try:
    from dsp.features.feature_pipeline import FEATURE_NAMES, FEATURE_VERSION, FeatureExtractor
except ImportError:
    # Try importing from PROJECT_ROOT directly
    import importlib.util
    dsp_pipeline_path = PROJECT_ROOT / "dsp" / "features" / "feature_pipeline.py"
    if dsp_pipeline_path.exists():
        spec = importlib.util.spec_from_file_location("feature_pipeline", str(dsp_pipeline_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create an import spec for {dsp_pipeline_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        FeatureExtractor = mod.FeatureExtractor
        FEATURE_NAMES = getattr(mod, "FEATURE_NAMES", [])
        FEATURE_VERSION = getattr(mod, "FEATURE_VERSION", 2)
    else:
        raise ImportError(f"Could not load FeatureExtractor from {dsp_pipeline_path}")
 

class DiagnosisService:
    """Service that orchestrates DSP feature extraction and machine learning inference."""

    DEFAULT_FEATURE_KEYS = list(FEATURE_NAMES)

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        model_name: str = "baseline_rf_fan",
        model_version: str = "2.0",
    ):
        """Initialize DiagnosisService with dynamic metadata loading from baseline_rf_fan.pkl.

        Args:
            model_path (Optional[Union[str, Path]]): Path to saved .pkl model artifact.
            model_name (str): Label for the active model.
            model_version (str): Version tag of the model.
        """
        self.model_name = model_name
        self.model_version = model_version
        self.feature_extractor = FeatureExtractor(target_sr=16000)

        # Default model search path if none provided
        resolved_path = (
            Path(model_path)
            if model_path
            else PROJECT_ROOT / "models" / "baseline_rf_fan.pkl"
        )

        self.model = self._load_rf_model(resolved_path)

        # Load and compile CNN models for Fan and Motor/Bearing
        self._load_models()

    def _load_models(self) -> None:
        """Load and explicitly compile CNN models for Fan and Motor/Bearing inference.

        Since models were saved with include_optimizer=False, keras.models.load_model
        leaves them uncompiled. We explicitly call .compile(loss='sparse_categorical_crossentropy',
        metrics=['accuracy']) after loading so they are fully initialized for inference.
        """
        # 1. Load Fan CNN model
        self.fan_cnn_model = None
        for candidate_filename in ["advanced_cnn_fan.h5", "advanced_cnn.h5"]:
            fan_model_path = PROJECT_ROOT / "models" / candidate_filename
            if fan_model_path.exists():
                try:
                    self.fan_cnn_model = tf.keras.models.load_model(str(fan_model_path), compile=False)
                    self.fan_cnn_model.compile(loss="sparse_categorical_crossentropy", metrics=["accuracy"])
                    logger.info("[DiagnosisService] Successfully loaded and compiled Fan CNN model from '%s'.", fan_model_path)
                    break
                except Exception as exc:
                    logger.warning("[DiagnosisService] Warning: Failed to load/compile fan model from '%s': %s", fan_model_path, exc)

        # 2. Load Motor/Bearing CWRU CNN model
        self.cnn_model = None
        motor_model_path = PROJECT_ROOT / "models" / "cwru_cnn.h5"
        if motor_model_path.exists():
            try:
                self.cnn_model = tf.keras.models.load_model(str(motor_model_path), compile=False)
                self.cnn_model.compile(loss="sparse_categorical_crossentropy", metrics=["accuracy"])
                logger.info("[DiagnosisService] Successfully loaded and compiled Motor/Bearing CNN model from '%s'.", motor_model_path)
            except Exception as exc:
                logger.warning("[DiagnosisService] Warning: Failed to load/compile motor model from '%s': %s", motor_model_path, exc)

        # Compatibility aliases
        self.fan_model = self.fan_cnn_model
        self.motor_model = self.cnn_model

        # Dynamic Model Registry mapping machine types to their active compiled CNN models
        self.model_registry: Dict[str, Any] = {
            "fan": self.fan_cnn_model,
            "motor": self.cnn_model,
            "bearing": self.cnn_model,
        }

    def _generate_fan_input(self, filepath: Union[str, Path]) -> np.ndarray:
        """Generate normalized 128x128 RGB Mel-Spectrogram input for Fan CNN inference.

        Matches MIMII Fan training pipeline with magma colormap and proper orientation.

        Args:
            filepath (Union[str, Path]): Path to target audio file.

        Returns:
            np.ndarray: Input array of shape (1, 128, 128, 3) with pixel values 0-255.
        """
        path = Path(filepath)

        # 1. Load audio with target sr=16000
        y, sr = librosa.load(str(path), sr=16000)

        # 2. Compute Mel-spectrogram and convert to dB
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_mels=128,
            fmax=8000,
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        # Took 2 days to fix this bug! Do NOT change magma to viridis here, it breaks the CNN predictions.
        vmin, vmax = float(np.min(mel_spec_db)), float(np.max(mel_spec_db))
        norm = (mel_spec_db - vmin) / (vmax - vmin) if vmax > vmin else np.zeros_like(mel_spec_db)
        flipped = np.flipud(norm)
        rgba = cm.magma(flipped)
        rgb = (rgba[:, :, :3] * 255).astype(np.uint8)

        # 4. Load and dynamically resize to 128x128
        img = Image.fromarray(rgb).resize((128, 128))

        # 5. Return as numpy array with batch dimension (1, 128, 128, 3)
        return np.expand_dims(np.array(img, dtype=np.uint8), axis=0)

    def _generate_motor_input(self, filepath: Union[str, Path]) -> np.ndarray:
        """Generate normalized 128x128 RGB Mel-Spectrogram input for CWRU Motor/Bearing CNN inference.

        Matches CWRU training pipeline with librosa.display.specshow and magma colormap.

        Args:
            filepath (Union[str, Path]): Path to target audio file.

        Returns:
            np.ndarray: Input array of shape (1, 128, 128, 3) with pixel values 0-255.
        """
        path = Path(filepath)

        # 1. Load audio explicitly with sr=16000 to match CWRU model training
        y, sr = librosa.load(str(path), sr=16000)

        # 2. Compute Mel-spectrogram
        fmax_val = 8000
        S = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_mels=128,
            fmax=fmax_val,
        )
        S_dB = librosa.power_to_db(S, ref=np.max)

        # 3. Render plot identically to librosa's specshow using thread-safe Object-Oriented Matplotlib
        fig = Figure(figsize=(3, 3))
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        ax.axis("off")
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        librosa.display.specshow(
            S_dB,
            sr=sr,
            x_axis="time",
            y_axis="mel",
            fmax=fmax_val,
            ax=ax,
            cmap="magma",
        )

        # 4. Save to in-memory buffer and explicitly free figure resources
        buf = io.BytesIO()
        canvas.print_png(buf)
        fig.clear()
        del ax
        del canvas
        del fig

        # 5. Load buffer with PIL, convert to RGB, and resize to 128x128
        buf.seek(0)
        img = Image.open(buf).convert("RGB").resize((128, 128))

        # 6. Return as numpy array with batch dimension (1, 128, 128, 3)
        return np.expand_dims(np.array(img), axis=0)

    def _generate_cnn_input(self, filepath: Union[str, Path], machine_key: str = "bearing") -> np.ndarray:
        """Backward-compatible helper redirecting to dedicated preprocessor."""
        if str(machine_key).lower() == "fan":
            return self._generate_fan_input(filepath)
        return self._generate_motor_input(filepath)

    def _load_rf_model(self, path: Path) -> Any:
        """Dynamically load Fan Stage 1 Random Forest model and extract metadata."""
        if not path.exists():
            raise RuntimeError(
                f"Required Fan Random Forest model artifact not found at '{path.resolve()}'. "
                f"Run ml/classifiers/train_rf.py to train and export baseline_rf_fan.pkl."
            )

        try:
            model = joblib.load(path)
        except Exception as exc:
            raise RuntimeError(f"Failed to load Fan model artifact from '{path.resolve()}': {exc}") from exc

        # Validate feature_version strictly against FEATURE_VERSION = 2
        self.feature_version = getattr(model, "feature_version_", None)
        if self.feature_version != FEATURE_VERSION:
            raise RuntimeError(
                f"Model at '{path.resolve()}' has feature_version {self.feature_version}, "
                f"but system strictly requires FEATURE_VERSION = {FEATURE_VERSION}."
            )

        # Extract feature names dynamically from model metadata
        raw_features = getattr(model, "feature_names_list_", None) or getattr(model, "feature_names_in_", None)
        if not raw_features:
            raise RuntimeError(f"Model at '{path.resolve()}' is missing feature names metadata.")
        self.feature_names = [str(f) for f in raw_features]

        # Extract class names dynamically from model metadata
        raw_classes = getattr(model, "classes_list_", None) or getattr(model, "classes_", None)
        if raw_classes is None:
            raise RuntimeError(f"Model at '{path.resolve()}' is missing class names metadata.")
        self.class_names = [str(c) for c in raw_classes]

        logger.info(
            "[DiagnosisService] Successfully loaded Fan Stage 1 RF model from '%s' "
            "(v%s, %d features, classes=%s).",
            path.name,
            self.feature_version,
            len(self.feature_names),
            self.class_names,
        )
        return model

    def analyze_audio(
        self,
        filepath: Union[str, Path],
        machine_type: str,
        machine_id: str = "MCH-001",
    ) -> Dict[str, Any]:
        """Execute end-to-end DSP analysis and model inference on an audio file.

        Args:
            filepath (Union[str, Path]): Path to target audio file.
            machine_type (str): Strictly required machine category (e.g. 'fan', 'motor', 'bearing').
            machine_id (str): Identifier of the monitored machine (default 'MCH-001').

        Returns:
            Dict[str, Any]: Standardized JSON Analysis Object with diagnosis and telemetry data.

        Raises:
            FileNotFoundError: If audio file does not exist.
            ValueError: If machine_type is missing or its diagnostic model is unavailable.
            RuntimeError: If DSP processing fails.
        """
        if not machine_type or not isinstance(machine_type, str) or not machine_type.strip():
            raise ValueError("A valid machine_type string is strictly required for audio diagnosis.")

        # 3. Unavailable Model Check via Dynamic Model Registry
        machine_key = machine_type.strip().lower()
        if machine_key not in self.model_registry or self.model_registry.get(machine_key) is None:
            raise ValueError(f"Diagnostic model for '{machine_type}' is currently unavailable or in development.")

        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: '{path.resolve()}'")

        # 1. DSP Feature Extraction and Real Signal Processing
        cleaned_signal, sample_rate = self.feature_extractor.preprocessor.preprocess(path)
        features = self.feature_extractor.extract_features_from_signal(cleaned_signal, sample_rate)

        # Max-Pooling decimation of real time-domain waveform to ~1200 points to prevent aliasing
        # and preserve narrow impulsive defect peaks (e.g., bearing impact transients)
        total_samples = len(cleaned_signal)
        target_wave_points = min(1200, total_samples)
        wave_step = max(1, total_samples // target_wave_points)
        waveform_data = []
        for i in range(0, total_samples, wave_step):
            window = cleaned_signal[i : min(i + wave_step, total_samples)]
            if len(window) == 0:
                continue
            max_v = float(np.max(window))
            min_v = float(np.min(window))
            peak_amp = max_v if abs(max_v) >= abs(min_v) else min_v
            waveform_data.append({
                "time": round(float((i / sample_rate) * 1000.0), 2),
                "amplitude": round(peak_amp, 4),
            })
            if len(waveform_data) >= target_wave_points:
                break

        # Calculate actual FFT frequency spectrum with peak magnitude preservation
        freqs, mags = self.feature_extractor.fft_analyzer.compute_fft(
            cleaned_signal, sample_rate, normalize=True
        )
        total_bins = len(freqs)
        target_fft_bins = min(600, total_bins)
        fft_step = max(1, total_bins // target_fft_bins)
        fft_data = []
        for i in range(0, total_bins, fft_step):
            bin_window = mags[i : min(i + fft_step, total_bins)]
            if len(bin_window) == 0:
                continue
            peak_offset = int(np.argmax(bin_window))
            peak_idx = i + peak_offset
            fft_data.append({
                "frequency": round(float(freqs[peak_idx]), 1),
                "magnitude": round(float(mags[peak_idx]), 4),
            })
            if len(fft_data) >= target_fft_bins:
                break

        # Real analytic envelope from Butterworth band-pass pre-filtered Hilbert transform
        env_signal = self.feature_extractor.envelope_analyzer.calculate_envelope(
            cleaned_signal, sr=sample_rate, band=(2000.0, 6000.0)
        )
        target_env_points = min(600, len(env_signal))
        env_step = max(1, len(env_signal) // target_env_points)
        envelope_data = []
        for i in range(0, len(env_signal), env_step):
            env_window = env_signal[i : min(i + env_step, len(env_signal))]
            if len(env_window) == 0:
                continue
            peak_env = float(np.max(env_window))
            envelope_data.append({
                "time": round(float((i / sample_rate) * 1000.0), 2),
                "envelope": round(peak_env, 4),
            })
            if len(envelope_data) >= target_env_points:
                break

        # Real frequency band energy distribution from FFT magnitudes
        band_ranges = [
            ("0-500 Hz", 0, 500, "Low"),
            ("500-1k Hz", 500, 1000, "Low-Mid"),
            ("1k-2k Hz", 1000, 2000, "Mid"),
            ("2k-4k Hz", 2000, 4000, "High-Mid"),
            ("4k-8k Hz", 4000, 8000, "High"),
        ]
        spectrogram_bands = []
        for band_name, f_min, f_max, label in band_ranges:
            mask = (freqs >= f_min) & (freqs < f_max)
            band_energy = float(np.sum(mags[mask] ** 2)) if np.any(mask) else 0.0
            spectrogram_bands.append({
                "band": band_name,
                "label": label,
                "energy": round(band_energy * 1000.0, 2),
            })

        # 2. Stage 1: Random Forest Feature Inference
        feature_vector = [features[k] for k in self.feature_names]
        X = np.array([feature_vector], dtype=np.float32)

        rf_probs = self.model.predict_proba(X)[0]
        norm_idx = self.class_names.index("normal") if "normal" in self.class_names else 0
        anom_idx = self.class_names.index("anomaly") if "anomaly" in self.class_names else 1

        rf_prob_normal = float(rf_probs[norm_idx])
        rf_prob_anomaly = float(rf_probs[anom_idx])

        # Mathematical normalization of Stage 1 RF probabilities: rf_n = rf_probs[idx_n] / sum
        rf_sum = rf_prob_normal + rf_prob_anomaly
        if rf_sum > 0.0:
            rf_prob_normal = rf_prob_normal / rf_sum
            rf_prob_anomaly = rf_prob_anomaly / rf_sum
        else:
            rf_prob_normal, rf_prob_anomaly = 0.5, 0.5

        if rf_prob_normal >= rf_prob_anomaly:
            status = "normal"
            confidence = round(rf_prob_normal, 4)
        else:
            status = "anomaly"
            confidence = round(rf_prob_anomaly, 4)

        fault_type = None
        active_model_name = self.model_name

        # 3. Stage 2: Dynamic Routing for CNN Cascade Predictions
        selected_model = self.model_registry.get(machine_key)
        if selected_model is not None:
            try:
                if machine_key == "fan":
                    cnn_input = self._generate_fan_input(path)
                    cnn_pred = selected_model.predict(cnn_input, verbose=0)
                    preds = cnn_pred[0]

                    # 2-class softmax output [anomaly_prob, normal_prob]
                    cnn_prob_anomaly = float(preds[0])
                    cnn_prob_normal = float(preds[1])

                    # Mathematical normalization of CNN probabilities
                    cnn_sum = cnn_prob_normal + cnn_prob_anomaly
                    if cnn_sum > 0.0:
                        cnn_prob_normal = cnn_prob_normal / cnn_sum
                        cnn_prob_anomaly = cnn_prob_anomaly / cnn_sum
                    else:
                        cnn_prob_normal, cnn_prob_anomaly = 0.5, 0.5

                    # The RF model failed LOGO CV (32.8% accuracy) due to dominant_frequency memorization.
                    # It is retained purely as an experimental baseline; final inference bypasses RF (weight 0.0)
                    # and relies exclusively on the Fan CNN (weight 1.0).
                    rf_weight = 0.0
                    cnn_weight = 1.0
                    cascade_prob_normal = rf_weight * rf_prob_normal + cnn_weight * cnn_prob_normal
                    cascade_prob_anomaly = rf_weight * rf_prob_anomaly + cnn_weight * cnn_prob_anomaly

                    # Mathematical re-normalization ensuring probabilities sum to exactly 1.0
                    cascade_total = cascade_prob_normal + cascade_prob_anomaly
                    if cascade_total > 0.0:
                        cascade_prob_normal /= cascade_total
                        cascade_prob_anomaly /= cascade_total
                    else:
                        cascade_prob_normal, cascade_prob_anomaly = 0.5, 0.5

                    if cascade_prob_normal >= cascade_prob_anomaly:
                        status = "normal"
                        confidence = round(float(cascade_prob_normal), 4)
                    else:
                        status = "anomaly"
                        confidence = round(float(cascade_prob_anomaly), 4)

                    fault_type = None
                    active_model_name = "Advanced_CNN_Cascade"

                elif machine_key in ["motor", "bearing"]:
                    cnn_input = self._generate_motor_input(path)
                    cnn_pred = selected_model.predict(cnn_input, verbose=0)
                    preds = cnn_pred[0]

                    # Multi-class classification logic (CWRU bearing/motor model)
                    pred_index = int(np.argmax(preds))
                    confidence = round(float(np.max(preds)), 4)
                    class_names = ["ball_defect", "inner_race", "normal", "outer_race"]
                    detected_class = class_names[pred_index]

                    if detected_class == "normal":
                        status = "normal"
                        fault_type = None
                    else:
                        status = "anomaly"
                        fault_type = detected_class.replace("_", " ").title()

                    active_model_name = "CWRU_MultiClass_CNN"

            except Exception as exc:
                logger.warning("[DiagnosisService] Warning: CNN prediction for '%s' failed (%s). Retaining Stage 1 Random Forest output.", machine_key, exc)

        # 6. Assemble final analysis response dictionary
        analysis_id = f"AN-{uuid.uuid4().hex[:6].upper()}"

        response: Dict[str, Any] = {
            "analysis_id": analysis_id,
            "machine_id": machine_id,
            "machine_type": machine_key,
            "status": status,
            "condition": status,  # Compatibility alias
            "fault_type": fault_type,
            "score": round(confidence, 2),
            "model": {
                "name": active_model_name,
                "version": self.model_version,
            },
            "features": features,
            "waveform_data": waveform_data,
            "fft_data": fft_data,
            "envelope_data": envelope_data,
            "spectrogram_bands": spectrogram_bands,
        }

        return response

    # Service alias for background thread executors
    process_audio = analyze_audio
