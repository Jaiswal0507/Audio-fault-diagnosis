/**
 * ReportGenerator Component for MachineSense
 *
 * Implements a stylized "Download Analysis Report" button that captures
 * the entire Results Panel (Condition Diagnosis, Feature Data, and all Signal Charts)
 * and exports it as a clean, multi-page PDF document named MachineSense_Report_<MachineID>.pdf.
 * 
 */

import React, { useState, useRef, useMemo } from 'react';
import { exportPagesToPDF } from '../utils/pdfExport';
import {
  LineChart, Line,
  AreaChart, Area,
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid,
} from 'recharts';
import { COLORS } from '../charts/SignalCharts';

// Status Themes
const STATUS_CONFIG = {
  normal: {
    label: 'NORMAL OPERATION',
    icon: '✅',
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.1)',
    border: '#4ade80',
    description: 'Machine is operating within baseline acoustic tolerances. No structural anomalies detected.',
  },
  anomaly: {
    label: 'ANOMALY DETECTED',
    icon: '⚠️',
    color: '#facc15',
    bg: 'rgba(250, 204, 21, 0.1)',
    border: '#facc15',
    description: 'Acoustic pattern deviates significantly from baseline. Early indicator of potential degradation.',
  },
  fault: {
    label: 'FAULT DETECTED',
    icon: '🔴',
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.1)',
    border: '#f87171',
    description: 'Characteristic fault signature identified. Immediate inspection and maintenance recommended.',
  },
};

// Feature Groups
const FEATURE_GROUPS = [
  {
    title: 'Time-Domain Features',
    icon: '⏱️',
    color: '#38bdf8',
    features: [
      { key: 'rms', label: 'RMS Amplitude', unit: '' },
      { key: 'peak', label: 'Peak Amplitude', unit: '' },
      { key: 'peak_to_peak', label: 'Peak-to-Peak', unit: '' },
      { key: 'crest_factor', label: 'Crest Factor', unit: '' },
      { key: 'kurtosis', label: 'Kurtosis', unit: '' },
      { key: 'skewness', label: 'Skewness', unit: '' },
    ],
  },
  {
    title: 'Frequency-Domain Features',
    icon: '🔬',
    color: '#a78bfa',
    features: [
      { key: 'dominant_frequency', label: 'Dominant Freq', unit: 'Hz' },
      { key: 'spectral_centroid', label: 'Spectral Centroid', unit: 'Hz' },
      { key: 'spectral_bandwidth', label: 'Bandwidth', unit: 'Hz' },
      { key: 'spectral_rolloff', label: 'Rolloff (85%)', unit: 'Hz' },
      { key: 'spectral_flatness', label: 'Spectral Flatness', unit: '' },
      { key: 'spectral_energy', label: 'Spectral Energy', unit: '' },
    ],
  },
  {
    title: 'Envelope & STFT Features',
    icon: '📈',
    color: '#34d399',
    features: [
      { key: 'envelope_rms', label: 'Envelope RMS', unit: '' },
      { key: 'envelope_kurtosis', label: 'Envelope Kurtosis', unit: '' },
      { key: 'envelope_peak', label: 'Envelope Peak', unit: '' },
      { key: 'envelope_energy', label: 'Envelope Energy', unit: '' },
      { key: 'stft_mean_energy', label: 'Mean STFT Energy', unit: '' },
    ],
  },
];

function formatVal(val) {
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

export function ReportGenerator({
  analysisResult,
  machineId = 'MCH-001',
}) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const page1Ref = useRef(null);
  const page2Ref = useRef(null);

  const features = analysisResult?.features || {};
  const currentMachineId = analysisResult?.machine_id || machineId || 'MCH-001';
  const statusKey = (analysisResult?.status || analysisResult?.condition || 'normal').toLowerCase();
  const theme = STATUS_CONFIG[statusKey] || STATUS_CONFIG.normal;
  const scorePercent = ((analysisResult?.score || 0) * 100).toFixed(1);

  // Real telemetry data from analysis result downsampled for printable PDF
  const waveformData = useMemo(() => {
    const raw = analysisResult?.waveform_data || [];
    if (raw.length <= 300) return raw;
    const step = Math.ceil(raw.length / 300);
    return raw.filter((_, idx) => idx % step === 0);
  }, [analysisResult]);

  const fftData = useMemo(() => {
    const raw = analysisResult?.fft_data || [];
    if (raw.length <= 150) return raw;
    const step = Math.ceil(raw.length / 150);
    return raw.filter((_, idx) => idx % step === 0);
  }, [analysisResult]);

  const envelopeData = useMemo(() => {
    const raw = analysisResult?.envelope_data || [];
    if (raw.length <= 250) return raw;
    const step = Math.ceil(raw.length / 250);
    return raw.filter((_, idx) => idx % step === 0);
  }, [analysisResult]);

  const spectrogramBands = useMemo(() => {
    return analysisResult?.spectrogram_bands || [];
  }, [analysisResult]);

  const handleDownload = async () => {
    if (!analysisResult) return;

    setIsGenerating(true);
    setDownloadSuccess(false);

    try {
      // Brief timeout to ensure DOM & Recharts SVG elements are fully laid out
      await new Promise((resolve) => setTimeout(resolve, 250));

      const safeId = String(currentMachineId).trim().replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `MachineSense_Report_${safeId}.pdf`;

      if (page1Ref.current && page2Ref.current) {
        await exportPagesToPDF([page1Ref.current, page2Ref.current], filename, {
          scale: 2,
          backgroundColor: '#0a0d14',
          windowWidth: 850,
        });
      }

      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 3500);
    } catch (err) {
      console.error('PDF report generation failed:', err);
      alert(`Report export failed: ${err.message || 'Please try again'}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <>
      {/* Stylized Download Report Button */}
      <button
        type="button"
        onClick={handleDownload}
        disabled={isGenerating || !analysisResult}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: downloadSuccess
            ? 'linear-gradient(135deg, #059669 0%, #10b981 100%)'
            : isGenerating
            ? '#1e293b'
            : 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
          color: '#ffffff',
          border: '1px solid rgba(56, 189, 248, 0.4)',
          borderRadius: '8px',
          padding: '8px 16px',
          fontSize: '0.82rem',
          fontWeight: 700,
          letterSpacing: '0.02em',
          cursor: isGenerating || !analysisResult ? 'not-allowed' : 'pointer',
          boxShadow: isGenerating
            ? 'none'
            : '0 4px 14px rgba(37, 99, 235, 0.35)',
          transition: 'all 0.2s ease',
          opacity: !analysisResult ? 0.6 : 1,
        }}
        onMouseOver={(e) => {
          if (!isGenerating && analysisResult && !downloadSuccess) {
            e.currentTarget.style.transform = 'translateY(-1px)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(56, 189, 248, 0.45)';
          }
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          if (!downloadSuccess) {
            e.currentTarget.style.boxShadow = '0 4px 14px rgba(37, 99, 235, 0.35)';
          }
        }}
      >
        <span style={{ fontSize: '1rem' }}>
          {isGenerating ? '⏳' : downloadSuccess ? '✓' : '📄'}
        </span>
        <span>
          {isGenerating
            ? 'Generating PDF...'
            : downloadSuccess
            ? 'Report Downloaded!'
            : 'Download Analysis Report'}
        </span>
      </button>

      {/* Offscreen Printable Report Document (Rendered for html2canvas) */}
      {/* Positioned off-screen with fixed width=800px for exact A4 aspect ratio capture */}
      <div
        style={{
          position: 'fixed',
          left: '-9999px',
          top: 0,
          width: '800px',
          opacity: 1,
          pointerEvents: 'none',
          zIndex: -999,
          fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
          color: '#f0f2f5',
        }}
      >
        {/* PAGE 1: Executive Diagnosis & Feature Data */}
        <div
          ref={page1Ref}
          data-pdf-page="1"
          style={{
            width: '800px',
            minHeight: '1130px',
            boxSizing: 'border-box',
            background: '#0a0d14',
            padding: '36px 36px 30px',
            borderBottom: '2px dashed #334155',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            {/* Report Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                borderBottom: '2px solid #1e293b',
                paddingBottom: '16px',
                marginBottom: '20px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '1.8rem' }}>⚙️</span>
                  <div>
                    <h1
                      style={{
                        margin: 0,
                        fontSize: '1.5rem',
                        fontWeight: 800,
                        color: '#38bdf8',
                        letterSpacing: '0.02em',
                      }}
                    >
                      MachineSense
                    </h1>
                    <p style={{ margin: 0, fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      Acoustic Fault Diagnosis Platform · Telemetry Audit Report
                    </p>
                  </div>
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div
                  style={{
                    display: 'inline-block',
                    background: 'rgba(56, 189, 248, 0.12)',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    color: '#38bdf8',
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    fontFamily: 'monospace',
                  }}
                >
                  REPORT #{analysisResult?.analysis_id || 'ANL-2026-LIVE'}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px' }}>
                  Generated: {new Date().toLocaleString('en-US')}
                </div>
              </div>
            </div>

            {/* Metadata Information Matrix */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '10px',
                background: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 16px',
                marginBottom: '20px',
                fontSize: '0.78rem',
              }}
            >
              <div>
                <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Machine Identifier</div>
                <div style={{ fontWeight: 700, color: '#f8fafc', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {currentMachineId}
                </div>
              </div>
              <div>
                <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Component Type</div>
                <div style={{ fontWeight: 600, color: '#e2e8f0', textTransform: 'capitalize' }}>
                  {analysisResult?.machine_type || 'Industrial Bearing'}
                </div>
              </div>
              <div>
                <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Diagnostic Model</div>
                <div style={{ fontWeight: 600, color: '#e2e8f0' }}>
                  {(analysisResult?.model?.name || 'Diagnostic Model')} (v{analysisResult?.model?.version || '2.0.0'})
                </div>
              </div>
              <div>
                <div style={{ color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase' }}>Capture Sample Rate</div>
                <div style={{ fontWeight: 600, color: '#e2e8f0' }}>
                  16.0 kHz · Mono
                </div>
              </div>
            </div>

            {/* Condition Diagnosis Card */}
            <div
              style={{
                background: theme.bg,
                border: `1.5px solid ${theme.border}`,
                borderRadius: '10px',
                padding: '20px',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span style={{ fontSize: '2.4rem' }}>{theme.icon}</span>
                <div>
                  <div
                    style={{
                      fontSize: '1.25rem',
                      fontWeight: 800,
                      color: theme.color,
                      letterSpacing: '0.04em',
                    }}
                  >
                    {theme.label}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1', marginTop: '2px', maxWidth: '420px' }}>
                    {theme.description}
                  </div>
                  {analysisResult?.fault_type && analysisResult.fault_type !== 'None' && (
                    <div
                      style={{
                        display: 'inline-block',
                        marginTop: '8px',
                        background: 'rgba(248, 113, 113, 0.2)',
                        border: '1px solid rgba(248, 113, 113, 0.4)',
                        color: '#fca5a5',
                        padding: '3px 10px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                      }}
                    >
                      Fault Classification: {analysisResult.fault_type.replace(/_/g, ' ')}
                    </div>
                  )}
                </div>
              </div>

              {/* Confidence Meter Box */}
              <div
                style={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '12px 18px',
                  textAlign: 'center',
                  minWidth: '110px',
                }}
              >
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: theme.color }}>
                  {scorePercent}%
                </div>
                <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Confidence
                </div>
              </div>
            </div>

            {/* DSP Feature Extraction Matrix */}
            <div style={{ marginBottom: '16px' }}>
              <div
                style={{
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: '#94a3b8',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  marginBottom: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>🔢</span>
                <span>Extracted Acoustic Feature Telemetry (DSP Pipeline)</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                {FEATURE_GROUPS.map((group) => (
                  <div
                    key={group.title}
                    style={{
                      background: '#111827',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '12px',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '0.76rem',
                        fontWeight: 700,
                        color: group.color,
                        marginBottom: '8px',
                        borderBottom: '1px solid #1e293b',
                        paddingBottom: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <span>{group.icon}</span>
                      <span>{group.title}</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {group.features.map((feat) => (
                        <div
                          key={feat.key}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: '0.74rem',
                          }}
                        >
                          <span style={{ color: '#94a3b8' }}>{feat.label}</span>
                          <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#f8fafc' }}>
                            {formatVal(features[feat.key])} {feat.unit}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Executive Notes */}
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 16px',
                fontSize: '0.74rem',
                color: '#94a3b8',
                lineHeight: 1.45,
              }}
            >
              <strong style={{ color: '#f8fafc' }}>Analysis Summary: </strong>
              The acoustic signal recorded for machine <strong style={{ color: '#38bdf8' }}>{currentMachineId}</strong> was
              processed through the MachineSense DSP pipeline (pre-filtering, Hilbert envelope extraction, and FFT decomposition).
              Diagnosis status evaluated as <strong style={{ color: theme.color }}>{theme.label}</strong> with {scorePercent}% model confidence.
            </div>
          </div>

                    {/* Experimental Domain Warning Notice */}
          <div
            style={{
              margin: '8px 0',
              padding: '6px 12px',
              borderRadius: '4px',
              background: 'rgba(234, 179, 8, 0.08)',
              border: '1px solid rgba(234, 179, 8, 0.25)',
              color: '#eab308',
              fontSize: '0.68rem',
              fontStyle: 'italic',
              textAlign: 'center',
            }}
          >
            *Experimental: Bearing/Motor results are not validated on microphone audio*
          </div>
          {/* Page 1 Footer */}
          <div
            style={{
              borderTop: '1px solid #1e293b',
              paddingTop: '12px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.68rem',
              color: '#64748b',
            }}
          >
            <span>MachineSense Diagnostic System · Section 54 Compliant Audit Record</span>
            <span>Page 1 of 2</span>
          </div>
        </div>

        {/* PAGE 2: All Signal Charts Visualizations */}
        <div
          ref={page2Ref}
          data-pdf-page="2"
          style={{
            width: '800px',
            minHeight: '1130px',
            boxSizing: 'border-box',
            background: '#0a0d14',
            padding: '36px 36px 30px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            {/* Page 2 Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: '2px solid #1e293b',
                paddingBottom: '12px',
                marginBottom: '18px',
              }}
            >
              <div>
                <h2
                  style={{
                    margin: 0,
                    fontSize: '1.15rem',
                    fontWeight: 700,
                    color: '#f8fafc',
                  }}
                >
                  📊 Signal Visualizations & Spectral Analysis
                </h2>
                <p style={{ margin: 0, fontSize: '0.72rem', color: '#64748b' }}>
                  Acoustic decomposition: Waveform, FFT Spectrum, Energy Bands, and Envelope Modulations
                </p>
              </div>

              <div
                style={{
                  background: '#1e293b',
                  color: '#38bdf8',
                  fontSize: '0.72rem',
                  fontFamily: 'monospace',
                  padding: '3px 8px',
                  borderRadius: '4px',
                }}
              >
                {currentMachineId} · {analysisResult?.analysis_id || 'ANL-2026-LIVE'}
              </div>
            </div>

            {/* Chart 1: Waveform (Amplitude vs Time) */}
            <div
              style={{
                background: '#111827',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '12px',
              }}
            >
              <div
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: COLORS.waveform,
                  marginBottom: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>⚡ Actual Time-Domain Waveform — Amplitude vs Time</span>
                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Sampling: 16 kHz</span>
              </div>
              <LineChart width={730} height={140} data={waveformData}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="time" tick={{ fill: COLORS.axis, fontSize: 9 }} unit="ms" />
                <YAxis tick={{ fill: COLORS.axis, fontSize: 9 }} />
                <Line
                  type="monotone"
                  dataKey="amplitude"
                  stroke={COLORS.waveform}
                  dot={false}
                  strokeWidth={1.2}
                />
              </LineChart>
            </div>

            {/* Chart 2: FFT Spectrum (Magnitude vs Frequency) */}
            <div
              style={{
                background: '#111827',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '12px',
              }}
            >
              <div
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: COLORS.fft,
                  marginBottom: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>🔬 Actual FFT Spectrum — Magnitude vs Frequency</span>
                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                  Dominant: {formatVal(features.dominant_frequency)} Hz
                </span>
              </div>
              <AreaChart width={730} height={140} data={fftData}>
                <defs>
                  <linearGradient id="pdfFftGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.fft} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={COLORS.fft} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="frequency" tick={{ fill: COLORS.axis, fontSize: 9 }} unit="Hz" />
                <YAxis tick={{ fill: COLORS.axis, fontSize: 9 }} />
                <Area
                  type="monotone"
                  dataKey="magnitude"
                  stroke={COLORS.fft}
                  fill="url(#pdfFftGrad)"
                  strokeWidth={1.4}
                />
              </AreaChart>
            </div>

            {/* Chart 3: Spectrogram Frequency Band Energy */}
            <div
              style={{
                background: '#111827',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '12px',
              }}
            >
              <div
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: COLORS.spectrogram,
                  marginBottom: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>🎛️ Spectrogram — Frequency Band Energy</span>
                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Energy Distribution</span>
              </div>
              <BarChart width={730} height={130} data={spectrogramBands} barSize={42}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="band" tick={{ fill: COLORS.axis, fontSize: 9 }} />
                <YAxis tick={{ fill: COLORS.axis, fontSize: 9 }} />
                <Bar dataKey="energy" fill={COLORS.spectrogram} radius={[4, 4, 0, 0]} />
              </BarChart>
            </div>

            {/* Chart 4: Envelope Demodulation */}
            <div
              style={{
                background: '#111827',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '16px',
              }}
            >
              <div
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: COLORS.envelope,
                  marginBottom: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>📈 Envelope — Hilbert Analytic Amplitude</span>
                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Hilbert Transform</span>
              </div>
              <AreaChart width={730} height={130} data={envelopeData}>
                <defs>
                  <linearGradient id="pdfEnvGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.envelope} stopOpacity={0.35} />
                    <stop offset="95%" stopColor={COLORS.envelope} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="time" tick={{ fill: COLORS.axis, fontSize: 9 }} unit="ms" />
                <YAxis tick={{ fill: COLORS.axis, fontSize: 9 }} />
                <Area
                  type="monotone"
                  dataKey="envelope"
                  stroke={COLORS.envelope}
                  fill="url(#pdfEnvGrad)"
                  strokeWidth={1.4}
                />
              </AreaChart>
            </div>

            {/* Engineering Sign-off Box */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '12px',
                background: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px 16px',
                fontSize: '0.72rem',
              }}
            >
              <div>
                <span style={{ color: '#64748b', textTransform: 'uppercase' }}>Maintenance Status Recommendation:</span>
                <div style={{ fontWeight: 700, color: theme.color, marginTop: '2px' }}>
                  {statusKey === 'normal'
                    ? 'Nominal Operation · Continue standard monitoring schedule'
                    : statusKey === 'anomaly'
                    ? 'Inspection Recommended · Re-assess acoustic telemetry within 24h'
                    : 'Maintenance Intervention Required · Inspect bearing assembly immediately'}
                </div>
              </div>
              <div>
                <span style={{ color: '#64748b', textTransform: 'uppercase' }}>Analysis Audit ID:</span>
                <div style={{ fontFamily: 'monospace', color: '#94a3b8', marginTop: '2px' }}>
                  RPT-{analysisResult?.analysis_id || 'ANL-2026-LIVE'}
                </div>
              </div>
            </div>
          </div>

                    {/* Experimental Domain Warning Notice */}
          <div
            style={{
              margin: '8px 0',
              padding: '6px 12px',
              borderRadius: '4px',
              background: 'rgba(234, 179, 8, 0.08)',
              border: '1px solid rgba(234, 179, 8, 0.25)',
              color: '#eab308',
              fontSize: '0.68rem',
              fontStyle: 'italic',
              textAlign: 'center',
            }}
          >
            *Experimental: Bearing/Motor results are not validated on microphone audio*
          </div>
          {/* Page 2 Footer */}
          <div
            style={{
              borderTop: '1px solid #1e293b',
              paddingTop: '12px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.68rem',
              color: '#64748b',
            }}
          >
            <span>MachineSense Diagnostic System · Signal Visualization Audit</span>
            <span>Page 2 of 2 · End of Report</span>
          </div>
        </div>
      </div>
    </>
  );
}

export default ReportGenerator;
