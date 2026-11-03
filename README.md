# MachineSense - Acoustic Fault Diagnosis (B.Tech 7th Sem Project)

A machine condition monitoring and acoustic fault diagnosis system developed as our 7th-semester B.Tech final year project. 

The goal of this project is to detect mechanical defects in industrial machinery (industrial cooling fans and motor bearings) using audio recordings and vibration acoustics instead of relying on expensive contact accelerometers or halting production lines for manual inspections.

---

## Project Overview

Traditional vibration monitoring requires drilling into machine chassis to mount piezoelectric sensors. MachineSense provides a non-invasive alternative:
1. An audio recording is captured via a directional microphone or uploaded as a standard audio file (`.wav`, `.mp3`, etc.).
2. The acoustic signal passes through a dual-stage pipeline combining classical Digital Signal Processing (DSP) and Deep Learning (Convolutional Neural Networks).
3. The web dashboard displays real-time health telemetry, frequency spectra, envelope analysis, and precise fault classification (e.g., normal, inner race defect, outer race defect, ball defect).

---

## System Architecture

The diagnostic engine uses a two-stage cascade architecture combining physical acoustic features with visual Mel-Spectrogram image classification:

```
                  +---------------------------+
                  | Raw Audio File (16kHz WAV)|
                  +-------------+-------------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
    [ Stage 1: DSP Features ]       [ Stage 2: Mel-Spectrogram ]
    - 11 domain-engineered metrics   - Log-Mel Power Spectrogram (dB)
    - Time: Crest Factor,           - 128 Mel bands, 0-8000 Hz
      Kurtosis, Skewness            - Rendered in 128x128 RGB
    - Freq: Centroid, Bandwidth,    - Magma colormap mapping
      Rolloff, Flatness, Peak Hz                 |
    - Envelope: Demodulation & FFT               v
               |                    [ Deep CNN Classifier ]
               v                    - Fan: 2-class Anomaly CNN
    [ Random Forest Classifier ]    - Motor/Bearing: 4-class CWRU CNN
               |                                 |
               +----------------+----------------+
                                |
                                v
               [ Weighted Cascade Ensemble ]
               - Combines DSP physical statistics + CNN pattern recognition
               - Outputs final condition status, fault category & confidence score
```

### 1. Stage 1: DSP Feature Extraction
We extract 11 physical acoustic features directly from the raw audio waveform:
- **Time Domain:** Crest Factor, Kurtosis, Skewness.
- **Frequency Domain:** Dominant Frequency, Spectral Centroid, Spectral Bandwidth, Spectral Rolloff, Spectral Flatness.
- **Envelope Analysis:** 2 kHz - 6 kHz bandpass demodulation + Hilbert envelope spectrum: Envelope Kurtosis, Envelope Spectrum Peak Frequency (Hz), and Envelope Spectrum Peak Amplitude.

### 2. Stage 2: CNN Spectrogram Classifier
The acoustic signal is transformed into a 128x128 Log-Mel Spectrogram:
- **Fan Diagnostic Model (`advanced_cnn.h5`):** Trained on the MIMII industrial fan dataset. Predicts binary machine health (`normal` vs `anomaly`). Outputs are ensembled with Stage 1 RF probabilities for stable noise rejection.
- **Motor / Bearing Model (`cwru_cnn.h5`):** Trained on Case Western Reserve University (CWRU) vibration benchmark recordings. Performs multi-class exact fault classification:
  - `normal` (Healthy bearing)
  - `inner_race` (Inner raceway fault)
  - `outer_race` (Outer raceway fault)
  - `ball_defect` (Rolling element ball defect)

---

## Challenges & Learnings

Developing this system taught us practical lessons that never showed up in textbook tutorials:

### 1. The Dataset Overwrite Bug
During our initial data preprocessing pipeline (`build_spectrograms.py`), we ran batch extraction on the MIMII fan dataset across four machine IDs (`id_00`, `id_02`, `id_04`, `id_06`). 

The output directory logic saved images as `data/spectrograms/fan/<condition>/<filename>.png`. Because all four machine folders contained identically numbered files (`00000000.wav`, `00000001.wav`, etc.), each subsequent folder silently overwrote the files from the earlier ones in the destination folder. When the script finished, `id_06` had completely wiped out the spectrograms from `id_00`, `id_02`, and `id_04`.

The model trained with 99% accuracy on the extracted dataset, but when we tested live audios from `id_00` in the lab, it gave garbage results. We spent hours inspecting model weights before checking the file creation timestamps in `data/spectrograms/fan/` and realizing only a fraction of the total images existed. We fixed the pipeline in `build_spectrograms.py` to preserve the machine ID namespace in the destination directory (`data/spectrograms/<machine_type>/<condition>/<machine_id>/<filename>.png`), completely eliminating cross-machine file collisions and ensuring full data integrity.

### 2. The Spectrogram Colormap Collision (Viridis vs Magma)
This was the most frustrating bug in the project and took two full days to diagnose. When testing known normal audio files (like `00000013.wav`) through the web interface, the system consistently outputted **"ANOMALY DETECTED (100.0% CONFIDENCE)"**.

We initially suspected that the Random Forest model was biased or that the audio normalization was clipping. But after logging intermediate tensor predictions, we discovered the issue was in the spectrogram preprocessing:
- The CNN model (`advanced_cnn.h5`) was trained on spectrogram images rendered using matplotlib's `magma` colormap with unnormalized raw byte intensities (`0 to 255`).
- During inference in `diagnosis_service.py`, our preprocessing helper was using `librosa.display.specshow` with a `viridis` colormap and normalizing values between `0.0 and 1.0`.

Because the RGB channel weights and color spectrum between `viridis` (yellow-green-purple) and `magma` (black-red-white) are completely different, the CNN received an input distribution that looked nothing like its training domain, triggering false-positive anomalies on 100% of normal inputs. Once we separated the preprocessing into dedicated `_generate_fan_input` (matching the exact magma RGB distribution) and restarted the backend server, normal files immediately began detecting as `normal` with 90-99% confidence.

---

## Known Limitations & Domain Gap

### 1. The CWRU Vibration vs. Microphone Domain Gap
The Case Western Reserve University (CWRU) bearing benchmark dataset was acquired under controlled laboratory conditions using high-frequency **contact piezoelectric accelerometers** attached directly with magnetic bases to the motor housing. 

In real-world non-invasive deployments, MachineSense captures acoustic sound pressure waves through an air microphone. This introduces significant physical domain differences:
- **Acoustic Transfer Function & Dispersion:** Structural vibration passes through machine casing, air-medium acoustic boundaries, and room reverberation before reaching the microphone sensor.
- **Ambient Acoustic Noise:** Background industrial noise (compressors, HVAC, speech, echoes) can mask low-amplitude bearing click transients in the acoustic spectrum compared to direct accelerometer contact.
- **Operational Guidance:** Due to this domain difference, the Bearing and Motor models are flagged with a prominent yellow banner (`⚠️ Experimental: Bearing/Motor model is trained on CWRU vibration data and is not validated on microphone audio.`) in the user interface. For production bearing defect diagnosis, contact vibration sensors or acoustic isolation shields are strongly recommended.

### 2. Operational Ingestion Limits
To ensure reliable server throughput and prevent server memory exhaustion:
- Maximum audio recording duration is strictly limited to **30.0 seconds** (`HTTP 400`).
- File upload payload size is strictly capped at **10 MB** (`HTTP 413`).

---

## Tech Stack

- **Backend:** Python 3.13, FastAPI, Uvicorn, TensorFlow / Keras, Librosa, Scikit-learn, SciPy, NumPy, Matplotlib, SQLAlchemy (SQLite), JWT Authentication (passlib, python-jose).
- **Frontend:** React 18, Vite, React Router v6, Lucide React icons, Recharts, HTML5 Canvas API (real-time waveform animation).
- **Datasets:** MIMII Industrial Dataset (Hitachi / DCASE) & Case Western Reserve University (CWRU) Bearing Data Center.

---

## How to Run Locally

### Prerequisites
- Python 3.11 - 3.13
- Node.js (v18+) and npm

### 1. Backend Setup

```bash
# Navigate to project backend folder
cd machine-sense

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\activate
# Linux / macOS:
# source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Start the FastAPI server with auto-reload
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend API will be live at `http://127.0.0.1:8000`.
You can view interactive Swagger documentation at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

In a new terminal window:

```bash
# Navigate to the frontend directory
cd machine-sense/frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

Open your browser and navigate to `http://localhost:3000`.

### 3. User Registration & Multi-Tenant Access
MachineSense enforces strict multi-tenant isolation. There are no default hardcoded credentials:
- Open http://localhost:3000 (or http://localhost:5173).
- Switch to the **Register** tab.
- Enter your organization name, administrator email, and a secure password (minimum 6 characters) to register your isolated tenant account.

---

## Running Automated Tests

To verify backend endpoints and machine learning routing:

```bash
# From the machine-sense directory with venv activated:
python backend/tests/test_api.py
python backend/tests/test_auth.py
```

---

