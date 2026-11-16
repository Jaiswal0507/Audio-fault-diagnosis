// Dashboard.jsx - Main workspace for audio recording, telemetry charts and diagnosis results

import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Building2, User as UserIcon, LogOut, ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import AudioRecorder from '../components/AudioRecorder';
import AnalysisResult from '../components/AnalysisResult';
import FeatureSummary from '../components/FeatureSummary';
import AnalysisHistory from '../components/AnalysisHistory';
import ReportGenerator from '../components/ReportGenerator';
import SignalCharts from '../charts/SignalCharts';
import { checkHealth } from '../services/api';

export function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };
  const [selectedMachineId, setSelectedMachineId] = useState('MCH-001');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isBackendOnline, setIsBackendOnline] = useState(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  // Check backend connectivity on mount
  useEffect(() => {
    // console.log("checking backend health...");
    checkHealth()
      .then(() => setIsBackendOnline(true))
      .catch(() => setIsBackendOnline(false));
  }, []);

  const handleAnalysisSuccess = (result) => {
    // console.log("got analysis result:", result);
    setAnalysisResult(result);
    if (result?.machine_id) {
      setSelectedMachineId(result.machine_id);
    }
    // Automatically trigger history re-fetch to reflect new record
    // TODO: fix this re-render later if history lags
    setHistoryRefreshKey((prev) => prev + 1);
  };

  // Inspect a past analysis from the history table
  const handleSelectHistoryRecord = (record) => {
    if (!record) return;
    const formattedResult = {
      analysis_id: record.analysis_id,
      machine_id: record.machine_id,
      machine_type: record.machine_type || 'bearing',
      status: record.condition,
      fault_type: record.fault_type,
      score: record.score,
      model: record.model || { name: 'CNN + RF Cascade', version: '2.0.0' },
      features: record.features || {},
      waveform_data: record.waveform_data || [],
      fft_data: record.fft_data || [],
      envelope_data: record.envelope_data || [],
      spectrogram_bands: record.spectrogram_bands || [],
      created_at: record.created_at,
    };
    setAnalysisResult(formattedResult);
    if (record.machine_id) {
      setSelectedMachineId(record.machine_id);
    }
    // Smooth scroll to top to view inspected diagnosis
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const features = analysisResult?.features || null;

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0a0d14',
        color: '#f0f2f5',
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <header
        style={{
          background: 'linear-gradient(135deg, #0f172a 0%, #111827 100%)',
          borderBottom: '1px solid #1e293b',
          padding: '16px 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.5rem' }}>⚙️</span>
          <div>
            <h1
              style={{
                margin: 0,
                fontSize: '1.35rem',
                fontWeight: 800,
                background: 'linear-gradient(90deg, #38bdf8, #a78bfa)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '0.02em',
              }}
            >
              MachineSense
            </h1>
            <p
              style={{
                margin: 0,
                fontSize: '0.7rem',
                color: '#6b7280',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              Acoustic Fault Diagnosis Platform
            </p>
          </div>
        </div>

        {/* Header Right Actions: Multi-Tenant Context & Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          {/* Back to Home Link */}
          <Link
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              color: '#94a3b8',
              textDecoration: 'none',
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid #1e293b',
              background: 'rgba(15, 23, 42, 0.4)',
              transition: 'all 0.2s ease',
            }}
          >
            <ArrowLeft size={14} />
            <span>Home</span>
          </Link>

          {/* Backend Status Indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor:
                  isBackendOnline === null
                    ? '#6b7280'
                    : isBackendOnline
                    ? '#4ade80'
                    : '#f87171',
                display: 'inline-block',
                boxShadow: isBackendOnline ? '0 0 6px #4ade80' : 'none',
              }}
            />
            <span style={{ color: '#9ca3af' }}>
              {isBackendOnline === null
                ? 'Connecting...'
                : isBackendOnline
                ? 'API Online'
                : 'API Offline'}
            </span>
          </div>

          {/* User & Organization Multi-Tenant Profile Badge */}
          {user && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '5px 12px',
                borderRadius: '8px',
                border: '1px solid #1e293b',
                background: 'rgba(15, 23, 42, 0.6)',
                fontSize: '0.8rem',
              }}
            >
              {user.organization_name && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontWeight: 600 }}>
                  <Building2 size={14} />
                  <span>{user.organization_name}</span>
                </div>
              )}
              {user.organization_name && <span style={{ color: '#334155' }}>|</span>}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#cbd5e1' }}>
                <UserIcon size={14} color="#94a3b8" />
                <span>{user.email}</span>
                <span
                  style={{
                    fontSize: '0.65rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    background: 'rgba(56, 189, 248, 0.12)',
                    color: '#38bdf8',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontWeight: 700,
                  }}
                >
                  {user.role || 'Admin'}
                </span>
              </div>
            </div>
          )}

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            title="Log Out of MachineSense"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid rgba(248, 113, 113, 0.3)',
              background: 'rgba(239, 68, 68, 0.08)',
              color: '#f87171',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
              e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.5)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)';
              e.currentTarget.style.borderColor = 'rgba(248, 113, 113, 0.3)';
            }}
          >
            <LogOut size={14} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px 24px 48px' }}>
        {/* Top Section: Audio Recorder & Active Diagnosis */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: analysisResult ? '420px 1fr' : '1fr',
            gap: '24px',
            alignItems: 'start',
          }}
        >
          {/* Left Column: Audio Input */}
          <div>
            <AudioRecorder
              defaultMachineId={selectedMachineId}
              defaultMachineType="bearing"
              onAnalysisSuccess={handleAnalysisSuccess}
            />

            {/* Upload / Getting Started Hint */}
            {!analysisResult && (
              <div
                style={{
                  marginTop: '16px',
                  padding: '32px 20px',
                  border: '2px dashed #1e293b',
                  borderRadius: '12px',
                  textAlign: 'center',
                  color: '#4b5563',
                  background: 'rgba(15, 23, 42, 0.3)',
                }}
              >
                <p style={{ margin: 0, fontSize: '2rem' }}>🎧</p>
                <p style={{ margin: '12px 0 4px', fontSize: '1rem', color: '#94a3b8', fontWeight: 600 }}>
                  Record Machine Acoustic Telemetry
                </p>
                <p style={{ margin: 0, fontSize: '0.82rem', color: '#64748b', maxWidth: '480px', marginInline: 'auto' }}>
                  Capture acoustic vibration signals via browser microphone. The DSP engine will extract features,
                  run ML diagnosis, and persist the record to SQLite history.
                </p>
              </div>
            )}
          </div>

          {/* Right Column: Live Analysis Result (conditional) */}
          {analysisResult && (
            <div style={{ minWidth: 0 }}>
              {/* Top Action Bar for Results Panel with Prominent PDF Export */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '18px',
                  paddingBottom: '14px',
                  borderBottom: '1px solid #1e293b',
                  gap: '12px',
                  flexWrap: 'wrap',
                }}
              >
                <div>
                  <h2
                    style={{
                      margin: 0,
                      fontSize: '1.25rem',
                      fontWeight: 700,
                      color: '#f8fafc',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <span>🎯</span>
                    <span>Diagnosis & Telemetry Results</span>
                  </h2>
                  <p style={{ margin: '3px 0 0', fontSize: '0.78rem', color: '#64748b' }}>
                    Machine{' '}
                    <span style={{ color: '#38bdf8', fontFamily: 'monospace', fontWeight: 600 }}>
                      {analysisResult.machine_id || selectedMachineId}
                    </span>{' '}
                    · Analysis ID:{' '}
                    <span style={{ color: '#94a3b8', fontFamily: 'monospace' }}>
                      {analysisResult.analysis_id || '—'}
                    </span>
                  </p>
                </div>

                {/* Prominent PDF Report Generator Button at Top Right */}
                <ReportGenerator
                  analysisResult={analysisResult}
                  machineId={analysisResult.machine_id || selectedMachineId}
                />
              </div>

              {/* Domain Mismatch Warning conditionally rendered for Bearing / Motor */}
              {['bearing', 'motor'].includes((analysisResult?.machine_type || '').toLowerCase()) && (
                <div
                  style={{
                    background: 'rgba(234, 179, 8, 0.12)',
                    border: '1px solid rgba(234, 179, 8, 0.4)',
                    borderRadius: '8px',
                    padding: '12px 16px',
                    marginBottom: '16px',
                    color: '#fde047',
                    fontSize: '0.85rem',
                    fontWeight: 500,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    boxShadow: '0 2px 8px rgba(234, 179, 8, 0.1)',
                  }}
                >
                  <span>⚠️ Experimental: Bearing/Motor model is trained on CWRU vibration data and is not validated on microphone audio.</span>
                </div>
              )}

              {/* Diagnosis Condition Card */}
              <AnalysisResult result={analysisResult} />

              {/* Tabbed Result Inspection Sections */}
              <SectionTabs
                features={features}
                analysisResult={analysisResult}
                machineId={selectedMachineId}
                historyRefreshKey={historyRefreshKey}
                onSelectRecord={handleSelectHistoryRecord}
              />
            </div>
          )}
        </div>

        {/* Past Analysis History Table */}
        <section style={{ marginTop: '36px' }}>
          <AnalysisHistory
            machineId={selectedMachineId}
            refreshTrigger={historyRefreshKey}
            onSelectRecord={handleSelectHistoryRecord}
            embedded={false}
          />
        </section>
      </main>

      {/* Footer */}
      <footer
        style={{
          textAlign: 'center',
          padding: '20px',
          borderTop: '1px solid #1e293b',
          fontSize: '0.75rem',
          color: '#4b5563',
        }}
      >
        MachineSense Platform · Audio-Based Machine Fault Diagnosis · DSP + ML Pipeline
      </footer>
    </div>
  );
}

// Tab switcher for charts, raw features and history
function SectionTabs({ features, analysisResult, machineId, historyRefreshKey, onSelectRecord }) {
  const [activeTab, setActiveTab] = useState('signals');

  const tabs = [
    { id: 'signals', label: '📊 Signal Analysis', icon: '📊' },
    { id: 'features', label: '🔢 Feature Data', icon: '🔢' },
    { id: 'history', label: '📋 History Log', icon: '📋' },
  ];

  return (
    <div>
      {/* Tab Navigation */}
      <div
        style={{
          display: 'flex',
          gap: '4px',
          background: '#0f172a',
          borderRadius: '8px',
          padding: '4px',
          marginBottom: '16px',
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1,
              padding: '10px 16px',
              border: 'none',
              borderRadius: '6px',
              background: activeTab === tab.id ? '#1e293b' : 'transparent',
              color: activeTab === tab.id ? '#f0f2f5' : '#6b7280',
              fontWeight: activeTab === tab.id ? 700 : 500,
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active Panel */}
      {activeTab === 'signals' && <SignalCharts features={features} waveformData={analysisResult?.waveform_data} fftData={analysisResult?.fft_data} envelopeData={analysisResult?.envelope_data} spectrogramBands={analysisResult?.spectrogram_bands} result={analysisResult} />}
      {activeTab === 'features' && <FeatureSummary features={features} />}
      {activeTab === 'history' && (
        <AnalysisHistory
          machineId={machineId}
          refreshTrigger={historyRefreshKey}
          onSelectRecord={onSelectRecord}
          embedded={true}
        />
      )}
    </div>
  );
}

export default Dashboard;