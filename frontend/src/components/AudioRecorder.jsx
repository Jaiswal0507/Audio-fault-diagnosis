/**
 * AudioRecorder Component for MachineSense
 * 
 * Provides a user interface for browser-based microphone recording
 * as well as manual audio file upload (.wav, .mp3, .flac, .ogg, .webm)
 * connected to the FastAPI analysis service.
 * 
 */ 

import React, { useState, useRef, useEffect } from 'react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { analyzeMachineAudio } from '../services/api';

export function AudioRecorder({
  defaultMachineId = 'MCH-001',
  defaultMachineType = 'bearing',
  onAnalysisSuccess,
  onAnalysisError,
}) {
  const [machineId, setMachineId] = useState(defaultMachineId);
  const [machineType, setMachineType] = useState(defaultMachineType);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [apiError, setApiError] = useState(null);

  // Local state for manual audio file upload
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadedAudioUrl, setUploadedAudioUrl] = useState(null);
  const fileInputRef = useRef(null);

  const {
    isRecording,
    audioBlob,
    audioUrl,
    recordingDuration,
    error: recorderError,
    isSupported,
    startRecording,
    stopRecording,
    resetRecording,
  } = useAudioRecorder();

  // Format seconds to MM:SS
  const formatTime = (totalSeconds) => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  // Format bytes to KB or MB
  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    if (bytes < k * k) {
      return `${(bytes / k).toFixed(1)} KB`;
    }
    return `${(bytes / (k * k)).toFixed(2)} MB`;
  };

  // Clean up object URL on unmount or URL change
  useEffect(() => {
    return () => {
      if (uploadedAudioUrl) {
        URL.revokeObjectURL(uploadedAudioUrl);
      }
    };
  }, [uploadedAudioUrl]);

  // Handle live microphone recording start
  const handleStart = async () => {
    setApiError(null);
    setAnalysisResult(null);

    // If a file was previously uploaded, clear it to focus on new live recording
    if (uploadedFile) {
      handleRemoveUploadedFile();
    }

    try {
      await startRecording();
    } catch (err) {
      console.error('Failed to start recording:', err);
    }
  };

  // Handle manual audio file upload
  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Clean up previous object URL if any
    if (uploadedAudioUrl) {
      URL.revokeObjectURL(uploadedAudioUrl);
    }

    // Reset live microphone recording state
    if (audioBlob) {
      resetRecording();
    }

    setUploadedFile(file);
    const url = URL.createObjectURL(file);
    setUploadedAudioUrl(url);

    setApiError(null);
    setAnalysisResult(null);
  };

  // Remove/Clear uploaded audio file
  const handleRemoveUploadedFile = () => {
    if (uploadedAudioUrl) {
      URL.revokeObjectURL(uploadedAudioUrl);
    }
    setUploadedFile(null);
    setUploadedAudioUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setApiError(null);
  };

  // Submit audio for DSP feature extraction and ML diagnosis
  const handleAnalyze = async () => {
    // Prefer uploaded file if present, otherwise use recorded audio blob
    const targetAudio = uploadedFile || audioBlob;
    if (!targetAudio) return;

    setIsAnalyzing(true);
    setApiError(null);

    try {
      const result = await analyzeMachineAudio(targetAudio, machineId, machineType);
      setAnalysisResult(result);
      if (onAnalysisSuccess) {
        onAnalysisSuccess(result);
      }
    } catch (err) {
      setApiError(err.message || 'Analysis request failed');
      if (onAnalysisError) {
        onAnalysisError(err);
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Active audio URL and payload detection
  const activeAudioUrl = uploadedAudioUrl || audioUrl;
  const hasAudioPayload = Boolean(uploadedFile || audioBlob);

  return (
    <div
      style={{
        maxWidth: '560px',
        margin: '20px auto',
        padding: '24px',
        borderRadius: '12px',
        background: '#1a1d24',
        color: '#f0f2f5',
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🎙️</span>
          <span>Machine Acoustic Recorder</span>
        </h2>
        <span
          style={{
            fontSize: '0.72rem',
            color: '#38bdf8',
            background: 'rgba(56, 189, 248, 0.1)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            padding: '2px 8px',
            borderRadius: '10px',
            fontWeight: 600,
          }}
        >
          Mic / File Upload
        </span>
      </div>

      {!isSupported && (
        <div style={{ background: '#7f1d1d', padding: '10px', borderRadius: '6px', marginBottom: '16px', fontSize: '0.85rem' }}>
          Browser microphone API is not supported in this browser. You can still use the <strong>Upload Audio File</strong> feature below.
        </div>
      )}

      {/* Machine Context Inputs */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', color: '#9ca3af' }}>
            Machine ID
          </label>
          <input
            type="text"
            value={machineId}
            disabled={isRecording || isAnalyzing}
            onChange={(e) => setMachineId(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #374151',
              background: '#111827',
              color: '#f9fafb',
              boxSizing: 'border-box',
              fontFamily: 'monospace',
              fontSize: '0.9rem',
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', color: '#9ca3af' }}>
            Machine Type
          </label>
          <select
            value={machineType}
            disabled={isRecording || isAnalyzing}
            onChange={(e) => setMachineType(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #374151',
              background: '#111827',
              color: '#f9fafb',
              boxSizing: 'border-box',
              fontSize: '0.9rem',
            }}
          >
            <option value="bearing">Bearing</option>
            <option value="pump">Pump</option>
            <option value="fan">Fan</option>
            <option value="motor">Motor</option>
            <option value="valve">Valve</option>
          </select>
        </div>
      </div>

      {/* Timer and Status Indicator */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#0f172a',
          padding: '16px 20px',
          borderRadius: '8px',
          marginBottom: '20px',
          border: '1px solid #1e293b',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span
            style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: isRecording
                ? '#ef4444'
                : uploadedFile
                ? '#38bdf8'
                : audioBlob
                ? '#10b981'
                : '#6b7280',
              boxShadow: isRecording
                ? '0 0 10px #ef4444'
                : uploadedFile
                ? '0 0 8px #38bdf8'
                : audioBlob
                ? '0 0 8px #10b981'
                : 'none',
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: '0.9rem', color: '#d1d5db' }}>
            {isRecording
              ? 'Recording Acoustic Signal...'
              : uploadedFile
              ? 'Audio File Ready'
              : audioBlob
              ? 'Recording Ready'
              : 'Standby'}
          </span>
        </div>
        <div style={{ fontSize: '1.4rem', fontFamily: 'monospace', fontWeight: 700, color: '#38bdf8' }}>
          {uploadedFile ? 'FILE' : formatTime(recordingDuration)}
        </div>
      </div>

      {/* Audio Source Action Controls */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*,.wav,.mp3,.flac,.ogg,.m4a,.webm"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
        />

        {/* 1. Live Record Button */}
        {!isRecording ? (
          <button
            type="button"
            onClick={handleStart}
            disabled={isAnalyzing || !isSupported}
            style={{
              flex: 1,
              minWidth: '140px',
              padding: '12px',
              borderRadius: '6px',
              border: 'none',
              background: '#2563eb',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.88rem',
              cursor: isAnalyzing || !isSupported ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'background 0.2s',
            }}
            onMouseOver={(e) => !isAnalyzing && (e.currentTarget.style.background = '#1d4ed8')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#2563eb')}
          >
            <span>▶</span>
            <span>Start Recording</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={stopRecording}
            style={{
              flex: 1,
              minWidth: '140px',
              padding: '12px',
              borderRadius: '6px',
              border: 'none',
              background: '#dc2626',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.88rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <span>⏹</span>
            <span>Stop Recording</span>
          </button>
        )}

        {/* 2. Upload Audio File Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isRecording || isAnalyzing}
          style={{
            flex: 1,
            minWidth: '140px',
            padding: '12px',
            borderRadius: '6px',
            border: '1px solid #334155',
            background: '#1e293b',
            color: '#f8fafc',
            fontWeight: 600,
            fontSize: '0.88rem',
            cursor: isRecording || isAnalyzing ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            transition: 'all 0.2s ease',
          }}
          onMouseOver={(e) => {
            if (!isRecording && !isAnalyzing) {
              e.currentTarget.style.background = '#334155';
              e.currentTarget.style.borderColor = '#38bdf8';
            }
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = '#1e293b';
            e.currentTarget.style.borderColor = '#334155';
          }}
        >
          <span>📁</span>
          <span>Upload Audio File</span>
        </button>

        {/* Reset Microphone Recording Button (if recorded) */}
        {audioBlob && !isRecording && !uploadedFile && (
          <button
            type="button"
            onClick={resetRecording}
            disabled={isAnalyzing}
            style={{
              padding: '12px 16px',
              borderRadius: '6px',
              border: '1px solid #4b5563',
              background: 'transparent',
              color: '#9ca3af',
              cursor: isAnalyzing ? 'not-allowed' : 'pointer',
              fontSize: '0.85rem',
            }}
          >
            Reset
          </button>
        )}
      </div>

      {/* Uploaded File Detail Banner */}
      {uploadedFile && (
        <div
          style={{
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '8px',
            padding: '12px 16px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
            <span style={{ fontSize: '1.4rem' }}>🎧</span>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  color: '#f8fafc',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={uploadedFile.name}
              >
                {uploadedFile.name}
              </div>
              <div style={{ fontSize: '0.74rem', color: '#94a3b8', display: 'flex', gap: '8px' }}>
                <span>{formatFileSize(uploadedFile.size)}</span>
                <span>·</span>
                <span style={{ textTransform: 'uppercase' }}>
                  {uploadedFile.name.split('.').pop() || 'audio'}
                </span>
              </div>
            </div>
          </div>

          {/* Remove File Button */}
          <button
            type="button"
            onClick={handleRemoveUploadedFile}
            disabled={isAnalyzing}
            title="Remove uploaded file"
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              color: '#f87171',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: isAnalyzing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease',
            }}
            onMouseOver={(e) => {
              if (!isAnalyzing) {
                e.currentTarget.style.background = 'rgba(248, 113, 113, 0.15)';
                e.currentTarget.style.borderColor = '#f87171';
              }
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = '#1e293b';
              e.currentTarget.style.borderColor = '#334155';
            }}
          >
            <span>✕</span>
            <span>Remove</span>
          </button>
        </div>
      )}

      {/* Audio Playback Preview */}
      {activeAudioUrl && (
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '0.82rem', marginBottom: '6px', color: '#9ca3af' }}>
            {uploadedFile ? 'Audio Playback Preview (Uploaded File)' : 'Audio Playback Preview (Microphone Recording)'}
          </label>
          <audio controls src={activeAudioUrl} style={{ width: '100%', height: '40px' }} />
        </div>
      )}

      {/* Analyze Button */}
      {hasAudioPayload && !isRecording && (
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '8px',
            border: 'none',
            background: isAnalyzing
              ? 'linear-gradient(135deg, #059669 0%, #047857 100%)'
              : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            color: '#fff',
            fontWeight: 700,
            fontSize: '1rem',
            letterSpacing: '0.02em',
            cursor: isAnalyzing ? 'wait' : 'pointer',
            marginBottom: '16px',
            boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            transition: 'all 0.2s ease',
          }}
          onMouseOver={(e) => !isAnalyzing && (e.currentTarget.style.transform = 'translateY(-1px)')}
          onMouseOut={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
        >
          <span>{isAnalyzing ? '⚡' : '🔍'}</span>
          <span>
            {isAnalyzing
              ? 'Processing DSP & ML Diagnosis...'
              : uploadedFile
              ? 'Analyze Uploaded Audio'
              : 'Analyze Machine Audio'}
          </span>
        </button>
      )}

      {/* Errors */}
      {(recorderError || apiError) && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            marginTop: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span>⚠️</span>
          <span>{recorderError || apiError}</span>
        </div>
      )}

      {/* Analysis Result Summary Preview */}
      {analysisResult && (
        <div
          style={{
            marginTop: '20px',
            padding: '16px',
            borderRadius: '8px',
            background: '#0f172a',
            border: '1px solid #1e293b',
          }}
        >
          <h4 style={{ margin: '0 0 10px 0', color: '#38bdf8' }}>Diagnosis Result</h4>
          <p style={{ margin: '4px 0', fontSize: '0.9rem' }}>
            <strong>Analysis ID:</strong> {analysisResult.analysis_id}
          </p>
          <p style={{ margin: '4px 0', fontSize: '0.9rem' }}>
            <strong>Condition Status:</strong>{' '}
            <span
              style={{
                color:
                  (analysisResult.status || analysisResult.condition) === 'normal'
                    ? '#4ade80'
                    : (analysisResult.status || analysisResult.condition) === 'anomaly'
                    ? '#facc15'
                    : '#f87171',
                textTransform: 'uppercase',
                fontWeight: 'bold',
              }}
            >
              {analysisResult.status || analysisResult.condition}
            </span>
          </p>
          {analysisResult.fault_type && (
            <p style={{ margin: '4px 0', fontSize: '0.9rem' }}>
              <strong>Fault Classification:</strong> {analysisResult.fault_type}
            </p>
          )}
          <p style={{ margin: '4px 0', fontSize: '0.9rem' }}>
            <strong>Confidence Score:</strong> {((analysisResult.score || 0) * 100).toFixed(1)}%
          </p>
        </div>
      )}
    </div>
  );
}

export default AudioRecorder;
