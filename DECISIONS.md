# MachineSense - Technical Architectural Decisions (ADR)

This document records the architectural and engineering decisions behind the MachineSense acoustic fault diagnosis platform, highlighting trade-offs and rationale.

---

### 1. Composite Foreign Keys for Strict Tenant Isolation
- **Decision:** Composite Foreign Keys (`machine_code`, `organization_id`) were implemented to enforce strict tenant isolation. In both `Machine` and `Analysis` models, `organization_id` is strictly non-nullable (`nullable=False`), and `Analysis` references `machines(machine_code, organization_id)` coupled with a composite unique constraint `UniqueConstraint("machine_code", "organization_id", name="uix_org_machine")`.
- **Rationale:** Enforcing composite foreign keys guarantees atomic referential integrity at the database engine level (via guarded `PRAGMA foreign_keys=ON`). It prevents cross-tenant data leaks and enables distinct organizations to safely register and analyze identical human-friendly machine identifiers (such as `MCH-001`) without namespace collisions or cross-tenant query contamination.

---

### 2. GroupShuffleSplit & LeaveOneGroupOut to Prevent Audio Chunk Leakage
- **Decision:** Split datasets using `GroupShuffleSplit` (grouped by the base source recording stem for CWRU) and `LeaveOneGroupOut` (grouped by physical machine ID for MIMII fans).
- **Rationale:** Audio files are divided into sliding or consecutive time-domain chunks during preprocessing. Random sample-level splitting causes chunks originating from the exact same recording or machine run to land simultaneously in both training and test sets. This creates severe data leakage, artificial performance metrics, and failure when encountering unseen machinery in production. Group-based splitting ensures that test folds evaluate genuine cross-machine generalization.

---

### 3. Compact Serialization via `include_optimizer=False`
- **Decision:** Using `include_optimizer=False` reduced the CWRU CNN model size by 33% (from ~25.5 MB to ~17.2 MB).
- **Rationale:** Deep learning optimizers (such as Adam) maintain first and second momentum gradient tensors for all trainable parameters. Stripping optimizer states substantially reduces disk footprint, accelerates container deployment and download times, and minimizes resident memory overhead during inference where gradients are never calculated.

---

### 4. Butterworth Bandpass Pre-Filtering & Gain-Invariant Demodulation
- **Decision:** Envelope analysis applies a 4th-order zero-phase Butterworth bandpass filter (2000 Hz to 6000 Hz via `scipy.signal.butter` and `filtfilt`) prior to taking the Hilbert transform and envelope spectrum FFT. The Envelope Spectrum Peak amplitude was normalized by the mean envelope to ensure mic-gain invariance.
- **Rationale:** Microscopic rolling element bearing defects produce high-frequency impact shocks that excite structural resonance frequencies (typically 2–6 kHz). Bandpass demodulation isolates impulsive impacts from rotational harmonics, and normalizing the spectral peak amplitude by `(envelope.mean() + 1e-12)` ensures the extracted feature remains dimensionless and invariant to microphone volume and analog recording gain.

---

### 5. Max-Pooling Decimation for Aliasing-Free Frontend Waveforms
- **Decision:** Real audio arrays are downsampled from 16,000–48,000 samples to ~1200 frontend visualization points using windowed Max-Pooling (extracting maximum absolute peak amplitudes) instead of naive stride slicing (`waveform[::step]`).
- **Rationale:** Stride subsampling acts as an impulse decimation filter that completely misses narrow transient spikes lasting only a few milliseconds—the hallmark signature of mechanical bearing faults. Max-pooling window decimation guarantees that peak transient energies and defect shocks remain prominently visible on the UI canvas without crashing frontend charting renderers with tens of thousands of SVG nodes.
