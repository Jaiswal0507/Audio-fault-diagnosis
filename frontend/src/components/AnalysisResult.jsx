/**
 * AnalysisResult Component for MachineSense
 *
 * Displays a visually prominent condition diagnosis card with color-coded
 * status (Normal / Anomaly / Fault), confidence score, and model metadata.
 * 
 */

import React from 'react';

// Status Theming
const STATUS_CONFIG = {
  normal: {
    icon: '✅',
    label: 'NORMAL',
    subtitle: 'Machine operating within learned normal pattern.',
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.08)',
    border: 'rgba(74, 222, 128, 0.25)',
    glow: '0 0 30px rgba(74, 222, 128, 0.12)',
  },
  anomaly: {
    icon: '⚠️',
    label: 'ANOMALY DETECTED',
    subtitle: 'Acoustic pattern differs from learned normal behaviour.',
    color: '#facc15',
    bg: 'rgba(250, 204, 21, 0.08)',
    border: 'rgba(250, 204, 21, 0.25)',
    glow: '0 0 30px rgba(250, 204, 21, 0.12)',
  },
  fault: {
    icon: '🔴',
    label: 'FAULT DETECTED',
    subtitle: 'A specific labelled fault has been identified.',
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.08)',
    border: 'rgba(248, 113, 113, 0.25)',
    glow: '0 0 30px rgba(248, 113, 113, 0.12)',
  },
};

export function AnalysisResult({ result }) {
  if (!result) return null;

  const statusKey = (result.status || 'normal').toLowerCase();
  const theme = STATUS_CONFIG[statusKey] || STATUS_CONFIG.normal;
  const scorePercent = ((result.score || 0) * 100).toFixed(1);

  return (
    <div
      style={{
        background: theme.bg,
        border: `1.5px solid ${theme.border}`,
        borderRadius: '12px',
        padding: '28px 24px',
        marginBottom: '20px',
        boxShadow: theme.glow,
        transition: 'all 0.3s ease',
      }}
    >
      {/* Condition Header */}
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        <span style={{ fontSize: '2.2rem' }}>{theme.icon}</span>
        <h2
          style={{
            margin: '8px 0 4px',
            fontSize: '1.6rem',
            fontWeight: 800,
            color: theme.color,
            letterSpacing: '0.06em',
          }}
        >
          {theme.label}
        </h2>
        <p style={{ margin: 0, color: '#9ca3af', fontSize: '0.9rem' }}>
          {theme.subtitle}
        </p>
      </div>

      {/* Fault Type Badge */}
      {result.fault_type && (
        <div
          style={{
            textAlign: 'center',
            marginBottom: '18px',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              background: 'rgba(248, 113, 113, 0.15)',
              border: '1px solid rgba(248, 113, 113, 0.3)',
              color: '#fca5a5',
              padding: '6px 18px',
              borderRadius: '20px',
              fontSize: '0.85rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Fault Type: {result.fault_type.replace(/_/g, ' ')}
          </span>
        </div>
      )}

      {/* Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: '12px',
          textAlign: 'center',
        }}
      >
        {/* Confidence Score */}
        <div
          style={{
            background: '#0f172a',
            borderRadius: '8px',
            padding: '14px 10px',
            border: '1px solid #1e293b',
          }}
        >
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: theme.color }}>
            {scorePercent}%
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Confidence
          </div>
        </div>

        {/* Model Name */}
        <div
          style={{
            background: '#0f172a',
            borderRadius: '8px',
            padding: '14px 10px',
            border: '1px solid #1e293b',
          }}
        >
          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#e2e8f0' }}>
            {result.model?.name || 'N/A'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Model
          </div>
        </div>

        {/* Analysis ID */}
        <div
          style={{
            background: '#0f172a',
            borderRadius: '8px',
            padding: '14px 10px',
            border: '1px solid #1e293b',
          }}
        >
          <div
            style={{
              fontSize: '0.85rem',
              fontWeight: 600,
              color: '#38bdf8',
              fontFamily: 'monospace',
            }}
          >
            {result.analysis_id || '—'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Analysis ID
          </div>
        </div>
      </div>

      {/* Machine Metadata */}
      <div
        style={{
          marginTop: '16px',
          display: 'flex',
          justifyContent: 'center',
          gap: '20px',
          fontSize: '0.82rem',
          color: '#6b7280',
        }}
      >
        <span>
          Machine: <strong style={{ color: '#d1d5db' }}>{result.machine_id}</strong>
        </span>
        <span>
          Type: <strong style={{ color: '#d1d5db', textTransform: 'capitalize' }}>{result.machine_type}</strong>
        </span>
        {result.model?.version && (
          <span>
            Version: <strong style={{ color: '#d1d5db' }}>v{result.model.version}</strong>
          </span>
        )}
      </div>
    </div>
  );
}

export default AnalysisResult;
