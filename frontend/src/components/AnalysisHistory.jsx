/**
 * AnalysisHistory Component for MachineSense
 *
 * Displays a clean, scrollable table of past machine acoustic analyses
 * with color-coded condition badges, confidence score meters, and timestamps.
 * Fetches records from GET /api/v1/machines/{machine_id}/history via Axios.
 * 
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { apiClient } from '../api/apiClient';

// Base API URL configuration
const API_BASE_URL =
  (typeof import.meta !== 'undefined' &&
    import.meta.env &&
    import.meta.env.VITE_API_URL) ||
  'http://localhost:8000/api/v1';

// Theme configuration for diagnosis conditions
const CONDITION_THEMES = {
  normal: {
    label: 'Normal',
    icon: '✅',
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.12)',
    border: 'rgba(74, 222, 128, 0.35)',
  },
  anomaly: {
    label: 'Anomaly',
    icon: '⚠️',
    color: '#facc15',
    bg: 'rgba(250, 204, 21, 0.12)',
    border: 'rgba(250, 204, 21, 0.35)',
  },
  fault: {
    label: 'Fault',
    icon: '🔴',
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.12)',
    border: 'rgba(248, 113, 113, 0.35)',
  },
};

/**
 * Format ISO datetime string into human-readable Date & Time.
 */
function formatDateTime(isoString) {
  if (!isoString) return { date: '—', time: '—', relative: '' };
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) {
      return { date: String(isoString), time: '', relative: '' };
    }

    const dateStr = d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
    const timeStr = d.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });

    // Compute relative time description
    const diffMs = Date.now() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    let relative = '';
    if (diffMins < 1) relative = 'Just now';
    else if (diffMins < 60) relative = `${diffMins}m ago`;
    else if (diffHours < 24) relative = `${diffHours}h ago`;
    else relative = `${diffDays}d ago`;

    return { date: dateStr, time: timeStr, relative };
  } catch {
    return { date: String(isoString), time: '', relative: '' };
  }
}

export function AnalysisHistory({
  machineId = 'MCH-001',
  onSelectRecord,
  refreshTrigger,
  embedded = false,
}) {
  // Use passed machineId or mock fallback "MCH-001" for initial load
  const [activeMachineId, setActiveMachineId] = useState(
    (machineId && String(machineId).trim()) || 'MCH-001'
  );
  const [machineInput, setMachineInput] = useState(
    (machineId && String(machineId).trim()) || 'MCH-001'
  );
  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterCondition, setFilterCondition] = useState('all');

  // Sync state if external machineId prop changes
  useEffect(() => {
    if (machineId && machineId.trim() && machineId !== activeMachineId) {
      setActiveMachineId(machineId.trim());
      setMachineInput(machineId.trim());
    }
  }, [machineId]);

  // Primary Axios data fetcher from /api/v1/machines/{machine_id}/history
  const fetchHistory = useCallback(async (idToFetch) => {
    const targetId = (idToFetch && String(idToFetch).trim()) || 'MCH-001';
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`/machines/${encodeURIComponent(targetId)}/history`, {
        params: { limit: 100, offset: 0 },
      });

      const data = response.data;
      const analysesList = Array.isArray(data?.analyses) ? data.analyses : [];
      setRecords(analysesList);
      setTotalCount(typeof data?.total === 'number' ? data.total : analysesList.length);

      // If backend responded with 0 records for this machine, keep records empty
      // but inform user that they can load demo data or run an analysis

    } catch (err) {
      console.warn(`History fetch failed for ${targetId}:`, err.message);
      let errMsg = `Unable to fetch history for ${targetId}`;
      if (err.response?.data?.detail) {
        errMsg = typeof err.response.data.detail === 'string'
          ? err.response.data.detail
          : JSON.stringify(err.response.data.detail);
      } else if (err.message) {
        errMsg = err.message;
      }
      setError(errMsg);
      setRecords([]);
      setTotalCount(0);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch when activeMachineId or refreshTrigger changes
  useEffect(() => {
    fetchHistory(activeMachineId);
  }, [activeMachineId, refreshTrigger, fetchHistory]);

  const handleMachineSearch = (e) => {
    e.preventDefault();
    if (machineInput && machineInput.trim()) {
      setActiveMachineId(machineInput.trim());
    }
  };



  // Filter records by condition
  const filteredRecords = useMemo(() => {
    if (filterCondition === 'all') return records;
    return records.filter(
      (r) => (r.condition || '').toLowerCase() === filterCondition.toLowerCase()
    );
  }, [records, filterCondition]);

  // Aggregate statistics for header badges
  const stats = useMemo(() => {
    const total = records.length;
    const normal = records.filter((r) => (r.condition || '').toLowerCase() === 'normal').length;
    const anomaly = records.filter((r) => (r.condition || '').toLowerCase() === 'anomaly').length;
    const fault = records.filter((r) => (r.condition || '').toLowerCase() === 'fault').length;
    const avgScore =
      total > 0
        ? (records.reduce((acc, curr) => acc + (curr.score || 0), 0) / total * 100).toFixed(1)
        : '0.0';
    return { total, normal, anomaly, fault, avgScore };
  }, [records]);

  return (
    <div
      style={{
        background: '#0f172a',
        border: '1px solid #1e293b',
        borderRadius: '12px',
        padding: embedded ? '18px' : '24px',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)',
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        color: '#f0f2f5',
      }}
    >
      {/* Header: Title & Controls */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          paddingBottom: '16px',
          borderBottom: '1px solid #1e293b',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.3rem' }}>📋</span>
            <h2
              style={{
                margin: 0,
                fontSize: '1.2rem',
                fontWeight: 700,
                color: '#f8fafc',
                letterSpacing: '0.01em',
              }}
            >
              Analysis History & Audit Log
            </h2>
            <span
              style={{
                background: '#1e293b',
                color: '#38bdf8',
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '12px',
                border: '1px solid #334155',
                fontFamily: 'monospace',
              }}
            >
              {activeMachineId}
            </span>
          </div>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#64748b' }}>
            Historical diagnosis telemetry for acoustic anomaly detection
          </p>
        </div>

        {/* Machine Selector & Refresh Form */}
        <form
          onSubmit={handleMachineSearch}
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              value={machineInput}
              onChange={(e) => setMachineInput(e.target.value)}
              placeholder="Enter Machine ID..."
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '6px',
                color: '#f8fafc',
                padding: '7px 12px',
                fontSize: '0.82rem',
                width: '130px',
                fontFamily: 'monospace',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#38bdf8')}
              onBlur={(e) => (e.target.style.borderColor = '#334155')}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              background: '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '7px 14px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'background 0.2s',
            }}
            onMouseOver={(e) => !isLoading && (e.currentTarget.style.background = '#1d4ed8')}
            onMouseOut={(e) => (e.currentTarget.style.background = '#2563eb')}
          >
            {isLoading ? 'Loading...' : 'Lookup'}
          </button>

          <button
            type="button"
            onClick={() => fetchHistory(activeMachineId)}
            disabled={isLoading}
            title="Refresh history records"
            style={{
              background: '#1e293b',
              color: '#94a3b8',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '7px 10px',
              fontSize: '0.85rem',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              transition: 'all 0.2s',
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = '#38bdf8')}
            onMouseOut={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            🔄
          </button>
        </form>
      </div>

      {/* Summary Metrics Bar & Filter Controls */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          padding: '12px 0',
          fontSize: '0.78rem',
        }}
      >
        {/* Metric Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              padding: '4px 10px',
              borderRadius: '6px',
              color: '#cbd5e1',
            }}
          >
            Total: <strong style={{ color: '#f8fafc' }}>{stats.total}</strong>
          </span>

          <span
            style={{
              background: 'rgba(74, 222, 128, 0.1)',
              border: '1px solid rgba(74, 222, 128, 0.25)',
              padding: '4px 10px',
              borderRadius: '6px',
              color: '#4ade80',
            }}
          >
            Normal: <strong>{stats.normal}</strong>
          </span>

          <span
            style={{
              background: 'rgba(250, 204, 21, 0.1)',
              border: '1px solid rgba(250, 204, 21, 0.25)',
              padding: '4px 10px',
              borderRadius: '6px',
              color: '#facc15',
            }}
          >
            Anomaly: <strong>{stats.anomaly}</strong>
          </span>

          <span
            style={{
              background: 'rgba(248, 113, 113, 0.1)',
              border: '1px solid rgba(248, 113, 113, 0.25)',
              padding: '4px 10px',
              borderRadius: '6px',
              color: '#f87171',
            }}
          >
            Fault: <strong>{stats.fault}</strong>
          </span>

          {stats.total > 0 && (
            <span
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                padding: '4px 10px',
                borderRadius: '6px',
                color: '#94a3b8',
              }}
            >
              Avg Confidence: <strong style={{ color: '#38bdf8' }}>{stats.avgScore}%</strong>
            </span>
          )}


        </div>

        {/* Condition Filter Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ color: '#64748b', marginRight: '4px' }}>Filter:</span>
          {['all', 'normal', 'anomaly', 'fault'].map((cond) => {
            const isSelected = filterCondition === cond;
            return (
              <button
                key={cond}
                onClick={() => setFilterCondition(cond)}
                style={{
                  background: isSelected ? '#334155' : '#1e293b',
                  color: isSelected ? '#ffffff' : '#94a3b8',
                  border: isSelected ? '1px solid #475569' : '1px solid #1e293b',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: isSelected ? 700 : 500,
                  textTransform: 'capitalize',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {cond}
              </button>
            );
          })}
        </div>
      </div>

      {/* Error Notification Banner (if any) */}
      {error && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            padding: '10px 14px',
            marginBottom: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8rem',
            color: '#fca5a5',
          }}
        >
          <span>⚠️ {error}</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => fetchHistory(activeMachineId)}
              style={{
                background: '#2563eb',
                border: 'none',
                color: '#ffffff',
                borderRadius: '4px',
                padding: '4px 12px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Domain Mismatch Warning conditionally rendered for Bearing / Motor */}
      {records.some((r) => ['bearing', 'motor'].includes((r.machine_type || '').toLowerCase())) && (
        <div
          style={{
            background: 'rgba(234, 179, 8, 0.12)',
            border: '1px solid rgba(234, 179, 8, 0.35)',
            borderRadius: '8px',
            padding: '10px 14px',
            marginBottom: '14px',
            color: '#fde047',
            fontSize: '0.82rem',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span>⚠️ Experimental: Bearing/Motor model is trained on CWRU vibration data and is not validated on microphone audio.</span>
        </div>
      )}

      {/* Scrollable Table Container */}
      <div
        style={{
          border: '1px solid #1e293b',
          borderRadius: '8px',
          overflow: 'hidden',
          background: '#0a0d14',
        }}
      >
        <div
          style={{
            maxHeight: embedded ? '360px' : '440px',
            overflowY: 'auto',
            overflowX: 'auto',
          }}
        >
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              textAlign: 'left',
              fontSize: '0.83rem',
            }}
          >
            {/* Sticky Table Header */}
            <thead>
              <tr
                style={{
                  background: '#0f172a',
                  color: '#94a3b8',
                  fontSize: '0.72rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  position: 'sticky',
                  top: 0,
                  zIndex: 10,
                  borderBottom: '2px solid #1e293b',
                }}
              >
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Date / Time</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Machine ID</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Condition</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Fault Details</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, minWidth: '150px' }}>Score</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Analysis ID</th>
                {onSelectRecord && (
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>
                    Action
                  </th>
                )}
              </tr>
            </thead>

            {/* Table Body */}
            <tbody>
              {/* Loading State */}
              {isLoading && records.length === 0 && (
                <tr>
                  <td
                    colSpan={onSelectRecord ? 7 : 6}
                    style={{
                      padding: '40px 16px',
                      textAlign: 'center',
                      color: '#64748b',
                    }}
                  >
                    <div style={{ display: 'inline-block', marginBottom: '8px', fontSize: '1.4rem' }}>
                      ⏳
                    </div>
                    <div>Fetching analysis telemetry from database...</div>
                  </td>
                </tr>
              )}

              {/* Empty State */}
              {!isLoading && filteredRecords.length === 0 && (
                <tr>
                  <td
                    colSpan={onSelectRecord ? 7 : 6}
                    style={{
                      padding: '40px 20px',
                      textAlign: 'center',
                      color: '#64748b',
                    }}
                  >
                    <div style={{ fontSize: '1.8rem', marginBottom: '6px' }}>🔍</div>
                    <div style={{ fontSize: '0.9rem', color: '#94a3b8', fontWeight: 600 }}>
                      No history records found for {activeMachineId}
                    </div>
                    <p style={{ margin: '6px 0 16px', fontSize: '0.78rem', color: '#64748b' }}>
                      {filterCondition !== 'all'
                        ? `No analyses with condition "${filterCondition}" exist for this machine.`
                        : 'Run a live microphone or file diagnosis above to record the first diagnosis.'}
                    </p>
                    <button
                      type="button"
                      onClick={() => fetchHistory(activeMachineId)}
                      disabled={isLoading}
                      style={{
                        background: '#1e293b',
                        border: '1px solid #334155',
                        color: '#38bdf8',
                        borderRadius: '6px',
                        padding: '6px 14px',
                        fontSize: '0.8rem',
                        cursor: isLoading ? 'not-allowed' : 'pointer',
                        fontWeight: 600,
                      }}
                    >
                      🔄 Refresh History
                    </button>
                  </td>
                </tr>
              )}

              {/* Rows */}
              {filteredRecords.map((item, index) => {
                const conditionKey = (item.condition || 'normal').toLowerCase();
                const theme = CONDITION_THEMES[conditionKey] || CONDITION_THEMES.normal;
                const { date, time, relative } = formatDateTime(item.created_at);
                const scoreValue = typeof item.score === 'number' ? item.score : 0;
                const scorePercent = (scoreValue * 100).toFixed(1);

                return (
                  <tr
                    key={item.id || item.analysis_id || index}
                    style={{
                      borderBottom: '1px solid #1e293b',
                      background: index % 2 === 0 ? 'rgba(15, 23, 42, 0.45)' : 'transparent',
                      transition: 'background 0.15s ease',
                      cursor: onSelectRecord ? 'pointer' : 'default',
                    }}
                    onClick={() => onSelectRecord && onSelectRecord(item)}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(56, 189, 248, 0.08)')}
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background =
                        index % 2 === 0 ? 'rgba(15, 23, 42, 0.45)' : 'transparent')
                    }
                  >
                    {/* 1. Date / Time */}
                    <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                      <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{date}</div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b', display: 'flex', gap: '6px' }}>
                        <span>{time}</span>
                        {relative && <span>· {relative}</span>}
                      </div>
                    </td>

                    {/* 2. Machine ID */}
                    <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                      <span
                        style={{
                          fontFamily: 'monospace',
                          fontWeight: 700,
                          color: '#e2e8f0',
                          background: '#1e293b',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          border: '1px solid #334155',
                          fontSize: '0.78rem',
                        }}
                      >
                        {item.machine_id || item.machine_code || activeMachineId}
                      </span>
                      {item.machine_type && (
                        <div
                          style={{
                            fontSize: '0.68rem',
                            color: '#64748b',
                            marginTop: '3px',
                            textTransform: 'capitalize',
                          }}
                        >
                          {item.machine_type}
                        </div>
                      )}
                    </td>

                    {/* 3. Condition (Color-Coded) */}
                    <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: theme.bg,
                          color: theme.color,
                          border: `1px solid ${theme.border}`,
                          padding: '4px 10px',
                          borderRadius: '20px',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                        }}
                      >
                        <span>{theme.icon}</span>
                        <span>{theme.label}</span>
                      </span>
                    </td>

                    {/* 4. Fault Details */}
                    <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                      {item.fault_type && item.fault_type !== 'None' ? (
                        <span
                          style={{
                            color: '#fca5a5',
                            background: 'rgba(248, 113, 113, 0.1)',
                            border: '1px solid rgba(248, 113, 113, 0.25)',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                          }}
                        >
                          {item.fault_type.replace(/_/g, ' ')}
                        </span>
                      ) : (
                        <span style={{ color: '#475569', fontSize: '0.78rem' }}>— Normal baseline</span>
                      )}
                    </td>

                    {/* 5. Score with confidence bar */}
                    <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          marginBottom: '4px',
                        }}
                      >
                        <span style={{ fontWeight: 700, color: theme.color, fontSize: '0.85rem' }}>
                          {scorePercent}%
                        </span>
                        <span style={{ fontSize: '0.68rem', color: '#64748b' }}>
                          ({scoreValue.toFixed(3)})
                        </span>
                      </div>
                      <div
                        style={{
                          width: '100%',
                          height: '5px',
                          background: '#1e293b',
                          borderRadius: '3px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(100, Math.max(0, scoreValue * 100))}%`,
                            height: '100%',
                            background: theme.color,
                            borderRadius: '3px',
                            transition: 'width 0.4s ease',
                          }}
                        />
                      </div>
                    </td>

                    {/* 6. Analysis ID & Model */}
                    <td style={{ padding: '12px 16px', verticalAlign: 'middle' }}>
                      <div
                        style={{
                          fontFamily: 'monospace',
                          fontSize: '0.75rem',
                          color: '#38bdf8',
                        }}
                      >
                        {item.analysis_id || `ID-${item.id}`}
                      </div>
                      {item.model?.name && (
                        <div style={{ fontSize: '0.68rem', color: '#64748b', marginTop: '2px' }}>
                          {item.model.name}
                        </div>
                      )}
                    </td>

                    {/* 7. Action Button (optional) */}
                    {onSelectRecord && (
                      <td
                        style={{
                          padding: '12px 16px',
                          textAlign: 'center',
                          verticalAlign: 'middle',
                        }}
                      >
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRecord(item);
                          }}
                          style={{
                            background: '#1e293b',
                            border: '1px solid #334155',
                            color: '#38bdf8',
                            borderRadius: '4px',
                            padding: '4px 10px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                          onMouseOver={(e) => {
                            e.currentTarget.style.background = '#2563eb';
                            e.currentTarget.style.color = '#ffffff';
                            e.currentTarget.style.borderColor = '#2563eb';
                          }}
                          onMouseOut={(e) => {
                            e.currentTarget.style.background = '#1e293b';
                            e.currentTarget.style.color = '#38bdf8';
                            e.currentTarget.style.borderColor = '#334155';
                          }}
                        >
                          Inspect
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Table Footer */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '12px',
          fontSize: '0.72rem',
          color: '#64748b',
        }}
      >
        <span>
          Showing {filteredRecords.length} of {totalCount} records
          {filterCondition !== 'all' && ` (filtered by ${filterCondition})`}
        </span>
        <span>
          {activeMachineId}-history
        </span>
      </div>
    </div>
  );
}

export default AnalysisHistory;
