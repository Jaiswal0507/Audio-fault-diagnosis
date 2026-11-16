/**
 * FeatureSummary Component for MachineSense
 *
 * Displays extracted DSP features in an organized, tabular grid with
 * domain labels, formatted values, and units.
 * 
 */

import React from 'react';

// Feature Definitions
const FEATURE_GROUPS = [
  {
    title: 'Time-Domain',
    icon: '⏱️',
    color: '#38bdf8',
    features: [
      { key: 'rms', label: 'RMS', unit: '' },
      { key: 'peak', label: 'Peak Amplitude', unit: '' },
      { key: 'peak_to_peak', label: 'Peak-to-Peak', unit: '' },
      { key: 'crest_factor', label: 'Crest Factor', unit: '' },
      { key: 'kurtosis', label: 'Kurtosis', unit: '' },
      { key: 'skewness', label: 'Skewness', unit: '' },
    ],
  },
  {
    title: 'Frequency-Domain',
    icon: '🔬',
    color: '#a78bfa',
    features: [
      { key: 'dominant_frequency', label: 'Dominant Frequency', unit: 'Hz' },
      { key: 'spectral_centroid', label: 'Spectral Centroid', unit: 'Hz' },
      { key: 'spectral_bandwidth', label: 'Spectral Bandwidth', unit: 'Hz' },
      { key: 'spectral_rolloff', label: 'Spectral Rolloff', unit: 'Hz' },
      { key: 'spectral_flatness', label: 'Spectral Flatness', unit: '' },
      { key: 'spectral_energy', label: 'Spectral Energy', unit: '' },
    ],
  },
  {
    title: 'Envelope',
    icon: '📈',
    color: '#34d399',
    features: [
      { key: 'envelope_rms', label: 'Envelope RMS', unit: '' },
      { key: 'envelope_kurtosis', label: 'Envelope Kurtosis', unit: '' },
      { key: 'envelope_peak', label: 'Envelope Peak', unit: '' },
      { key: 'envelope_energy', label: 'Envelope Energy', unit: '' },
    ],
  },
  {
    title: 'STFT',
    icon: '🎛️',
    color: '#f59e0b',
    features: [
      { key: 'stft_mean_energy', label: 'Mean STFT Energy', unit: '' },
    ],
  },
];

/**
 * Format a numeric feature value for display.
 */
function formatValue(val) {
  if (val === undefined || val === null) return '—';
  if (typeof val !== 'number') return String(val);
  const abs = Math.abs(val);
  if (abs >= 1e6) return val.toExponential(2);
  if (abs >= 100) return val.toFixed(1);
  if (abs >= 1) return val.toFixed(3);
  if (abs >= 0.001) return val.toFixed(4);
  if (abs === 0) return '0';
  return val.toExponential(2);
}

export function FeatureSummary({ features }) {
  if (!features || typeof features !== 'object' || Object.keys(features).length === 0) {
    return (
      <div
        style={{
          background: '#111827',
          borderRadius: '10px',
          border: '1px solid #1e293b',
          padding: '40px 20px',
          textAlign: 'center',
          color: '#6b7280',
        }}
      >
        <p style={{ fontSize: '1.1rem' }}>🔢 Feature data will appear here after analysis.</p>
      </div>
    );
  }

  return (
    <div>
      {FEATURE_GROUPS.map((group) => {
        // Only render group if at least one feature key exists
        const availableFeatures = group.features.filter((f) => features[f.key] !== undefined);
        if (availableFeatures.length === 0) return null;

        return (
          <div
            key={group.title}
            style={{
              background: '#111827',
              borderRadius: '10px',
              border: '1px solid #1e293b',
              padding: '18px 20px',
              marginBottom: '14px',
            }}
          >
            <h4
              style={{
                margin: '0 0 12px 0',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: group.color,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              {group.icon} {group.title} Features
            </h4>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                gap: '8px',
              }}
            >
              {availableFeatures.map((feat) => (
                <div
                  key={feat.key}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#0f172a',
                    borderRadius: '6px',
                    padding: '10px 12px',
                    border: '1px solid #1e293b',
                  }}
                >
                  <span style={{ fontSize: '0.78rem', color: '#9ca3af' }}>
                    {feat.label}
                  </span>
                  <span
                    style={{
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      color: '#f0f2f5',
                      fontFamily: 'monospace',
                    }}
                  >
                    {formatValue(features[feat.key])}
                    {feat.unit && (
                      <span
                        style={{
                          fontSize: '0.7rem',
                          color: '#6b7280',
                          marginLeft: '3px',
                          fontWeight: 400,
                        }}
                      >
                        {feat.unit}
                      </span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default FeatureSummary;
