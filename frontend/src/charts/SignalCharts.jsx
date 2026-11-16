/**
 * Signal Visualization Charts for MachineSense
 *
 * Renders actual raw time-domain Waveform, FFT Magnitude Spectrum,
 * Hilbert Envelope, and Spectrogram Energy Bands extracted directly
 * from audio recordings via the backend DSP pipeline.
 *
 * Uses recharts for responsive, interactive scientific visualizations.
 */

import React from 'react';
import {
  AreaChart, Area,
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

// Style Tokens
const CARD = {
  background: '#111827',
  borderRadius: '10px',
  border: '1px solid #1e293b',
  padding: '20px',
  marginBottom: '16px',
};

const TITLE = {
  margin: '0 0 14px 0',
  fontSize: '0.95rem',
  fontWeight: 600,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

export const COLORS = {
  waveform: '#38bdf8',
  fft: '#a78bfa',
  envelope: '#34d399',
  spectrogram: '#f59e0b',
  grid: '#1e293b',
  axis: '#6b7280',
};

// Tooltip Formatter
const ChartTooltip = ({ active, payload, label, unit = '' }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '6px',
        padding: '8px 12px',
        fontSize: '0.8rem',
      }}
    >
      <p style={{ margin: 0, color: '#94a3b8' }}>
        {label} {unit}
      </p>
      {payload.map((p, i) => (
        <p key={i} style={{ margin: '2px 0 0', color: p.color, fontWeight: 600 }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
        </p>
      ))}
    </div>
  );
};

export function SignalCharts({
  features,
  waveformData = [],
  fftData = [],
  envelopeData = [],
  spectrogramBands = [],
  result,
}) {
  const wave = (waveformData && waveformData.length > 0)
    ? waveformData
    : (result?.waveform_data || features?.waveform_data || []);

  const fft = (fftData && fftData.length > 0)
    ? fftData
    : (result?.fft_data || features?.fft_data || []);

  const env = (envelopeData && envelopeData.length > 0)
    ? envelopeData
    : (result?.envelope_data || features?.envelope_data || []);

  const spec = (spectrogramBands && spectrogramBands.length > 0)
    ? spectrogramBands
    : (result?.spectrogram_bands || features?.spectrogram_bands || []);

  if ((!features || typeof features !== 'object') && wave.length === 0) {
    return (
      <div style={{ ...CARD, textAlign: 'center', color: '#6b7280', padding: '40px' }}>
        <p style={{ fontSize: '1.1rem' }}>📊 Signal visualizations will appear here after analysis.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Waveform */}
      <div style={CARD}>
        <div style={{ ...TITLE, color: COLORS.waveform }}>
          <span>⚡ Actual Time-Domain Waveform — Amplitude vs Time</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 500, textTransform: 'none' }}>
            {wave.length > 0 ? `${wave.length} Telemetry Samples` : 'No Signal Captured'}
          </span>
        </div>
        {wave.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={wave}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis
                dataKey="time"
                tick={{ fill: COLORS.axis, fontSize: 11 }}
                label={{ value: 'Time (ms)', position: 'insideBottom', offset: -4, fill: COLORS.axis, fontSize: 11 }}
              />
              <YAxis
                tick={{ fill: COLORS.axis, fontSize: 11 }}
                label={{ value: 'Amplitude', angle: -90, position: 'insideLeft', fill: COLORS.axis, fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip unit="ms" />} />
              <Line
                type="monotone"
                dataKey="amplitude"
                stroke={COLORS.waveform}
                dot={false}
                strokeWidth={1.2}
                name="Amplitude"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
            Waveform telemetry unavailable for this historical entry. Run a fresh recording or file upload to view raw signal.
          </div>
        )}
      </div>

      {/* FFT Spectrum */}
      <div style={CARD}>
        <div style={{ ...TITLE, color: COLORS.fft }}>
          <span>🔬 Actual FFT Spectrum — Magnitude vs Frequency</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 500, textTransform: 'none' }}>
            {fft.length > 0 ? `0 – ${(fft[fft.length - 1]?.frequency || 8000).toFixed(0)} Hz` : 'No FFT Data'}
          </span>
        </div>
        {fft.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={fft}>
              <defs>
                <linearGradient id="fftGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.fft} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={COLORS.fft} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis
                dataKey="frequency"
                tick={{ fill: COLORS.axis, fontSize: 11 }}
                label={{ value: 'Frequency (Hz)', position: 'insideBottom', offset: -4, fill: COLORS.axis, fontSize: 11 }}
              />
              <YAxis
                tick={{ fill: COLORS.axis, fontSize: 11 }}
                label={{ value: 'Magnitude', angle: -90, position: 'insideLeft', fill: COLORS.axis, fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip unit="Hz" />} />
              <Area
                type="monotone"
                dataKey="magnitude"
                stroke={COLORS.fft}
                fill="url(#fftGradient)"
                strokeWidth={1.5}
                name="Magnitude"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
            FFT frequency spectrum not stored in historical summary.
          </div>
        )}
      </div>

      {/* Spectrogram Energy Bands */}
      <div style={CARD}>
        <div style={{ ...TITLE, color: COLORS.spectrogram }}>
          <span>🎛️ Spectrogram — Frequency Band Energy</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 500, textTransform: 'none' }}>
            Filterbank Energy Distribution
          </span>
        </div>
        {spec.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={spec} barSize={36}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="band" tick={{ fill: COLORS.axis, fontSize: 11 }} />
              <YAxis
                tick={{ fill: COLORS.axis, fontSize: 11 }}
                label={{ value: 'Energy', angle: -90, position: 'insideLeft', fill: COLORS.axis, fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="energy" fill={COLORS.spectrogram} radius={[4, 4, 0, 0]} name="Energy" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
            Spectrogram bands unavailable for this entry.
          </div>
        )}
      </div>

      {/* Envelope */}
      <div style={CARD}>
        <div style={{ ...TITLE, color: COLORS.envelope }}>
          <span>📈 Envelope — Hilbert Analytic Amplitude</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 500, textTransform: 'none' }}>
            Demodulated Acoustic Wave
          </span>
        </div>
        {env.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={env}>
              <defs>
                <linearGradient id="envGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.envelope} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={COLORS.envelope} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis
                dataKey="time"
                tick={{ fill: COLORS.axis, fontSize: 11 }}
                label={{ value: 'Time (ms)', position: 'insideBottom', offset: -4, fill: COLORS.axis, fontSize: 11 }}
              />
              <YAxis
                tick={{ fill: COLORS.axis, fontSize: 11 }}
                label={{ value: 'Envelope', angle: -90, position: 'insideLeft', fill: COLORS.axis, fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip unit="ms" />} />
              <Area
                type="monotone"
                dataKey="envelope"
                stroke={COLORS.envelope}
                fill="url(#envGradient)"
                strokeWidth={1.5}
                name="Envelope"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
            Hilbert envelope unavailable for this entry.
          </div>
        )}
      </div>
    </div>
  );
}

export default SignalCharts;
