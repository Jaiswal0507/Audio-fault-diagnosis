// Landing page for MachineSense (B.Tech Final Year Project)
// Dark theme inspired by observability tools like Datadog and Grafana

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  AlertCircle,
  AudioWaveform,
  BrainCircuit,
  Building2,
  ChevronRight,
  Gauge,
  Layers,
  Lock,
  LogOut,
  Mail,
  Radio,
  Shield,
  X,
  Zap,
} from 'lucide-react';

// UI theme colors

const palette = {
  bg:        '#060a13',
  bgCard:    '#0c1220',
  bgSurface: '#0f172a',
  bgInput:   '#080d1a',
  border:    '#1a2340',
  borderLt:  '#1e293b',
  text:      '#e2e8f0',
  textMuted: '#64748b',
  textDim:   '#475569',
  accent:    '#38bdf8',
  accentAlt: '#22d3ee',
  green:     '#34d399',
  purple:    '#a78bfa',
  danger:    '#f87171',
  gradA:     'linear-gradient(135deg, #38bdf8 0%, #22d3ee 100%)',
  gradB:     'linear-gradient(135deg, #38bdf8 0%, #a78bfa 100%)',
};

// Main Landing page component

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const [showLogin, setShowLogin] = useState(false);
  const [showSignup, setShowSignup] = useState(false);

  // Close modals on Escape key
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setShowLogin(false);
        setShowSignup(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLaunch = () => {
    if (isAuthenticated) {
      navigate('/dashboard');
    } else {
      setShowLogin(true);
    }
  };

  const switchToSignup = () => {
    setShowLogin(false);
    setShowSignup(true);
  };

  const switchToLogin = () => {
    setShowSignup(false);
    setShowLogin(true);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: palette.bg,
        color: palette.text,
        fontFamily: "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
        overflowX: 'hidden',
      }}
    >
      <Navbar
        isAuthenticated={isAuthenticated}
        user={user}
        onLaunch={handleLaunch}
        onOpenLogin={() => setShowLogin(true)}
        onOpenSignup={() => setShowSignup(true)}
        onLogout={logout}
      />

      <HeroSection
        onLaunch={handleLaunch}
        isAuthenticated={isAuthenticated}
      />

      <MetricsBar />
      <FeaturesGrid />
      <ArchitectureSection />
      <CTABanner
        onLaunch={handleLaunch}
        isAuthenticated={isAuthenticated}
      />
      <Footer />

      {/* Auth Modals */}
      {showLogin && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onSwitchToSignup={switchToSignup}
          onSuccess={() => {
            setShowLogin(false);
            navigate('/dashboard');
          }}
        />
      )}

      {showSignup && (
        <SignupModal
          onClose={() => setShowSignup(false)}
          onSwitchToLogin={switchToLogin}
          onSuccess={() => {
            setShowSignup(false);
            navigate('/dashboard');
          }}
        />
      )}
    </div>
  );
}


// Top navbar

function Navbar({ isAuthenticated, user, onLaunch, onOpenLogin, onOpenSignup, onLogout }) {
  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        background: 'rgba(6, 10, 19, 0.85)',
        backdropFilter: 'blur(16px) saturate(180%)',
        WebkitBackdropFilter: 'blur(16px) saturate(180%)',
        borderBottom: `1px solid ${palette.border}`,
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 24px',
          height: '64px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Left: Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }} onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: palette.gradA,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.3)',
            }}
          >
            <Activity size={18} color="#060a13" strokeWidth={2.5} />
          </div>
          <div>
            <span
              style={{
                fontSize: '1.1rem',
                fontWeight: 700,
                letterSpacing: '-0.01em',
                color: '#f8fafc',
              }}
            >
              MachineSense
            </span>
            <span
              style={{
                display: 'block',
                fontSize: '0.6rem',
                color: palette.textDim,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                marginTop: '-2px',
              }}
            >
              Industrial Diagnostics
            </span>
          </div>
        </div>

        {/* Center / Right: Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <NavLink label="Features" href="#features" />
          <NavLink label="Architecture" href="#architecture" />

          {isAuthenticated ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span
                style={{
                  fontSize: '0.78rem',
                  color: palette.textMuted,
                  background: 'rgba(15, 23, 42, 0.6)',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: `1px solid ${palette.border}`,
                  maxWidth: '160px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
                title={user?.email}
              >
                {user?.organization_name ? `🏢 ${user.organization_name}` : user?.email}
              </span>

              <button
                onClick={onLaunch}
                style={{
                  padding: '8px 18px',
                  border: 'none',
                  borderRadius: '6px',
                  background: palette.gradA,
                  color: '#060a13',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  letterSpacing: '0.01em',
                }}
              >
                Dashboard
              </button>

              <button
                onClick={onLogout}
                title="Log Out"
                style={{
                  padding: '7px',
                  border: `1px solid ${palette.borderLt}`,
                  borderRadius: '6px',
                  background: 'transparent',
                  color: palette.textMuted,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button
                onClick={onOpenLogin}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  background: 'transparent',
                  color: palette.textMuted,
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'color 0.2s ease',
                }}
                onMouseEnter={(e) => (e.target.style.color = palette.text)}
                onMouseLeave={(e) => (e.target.style.color = palette.textMuted)}
              >
                Log In
              </button>

              <button
                onClick={onOpenSignup}
                style={{
                  padding: '8px 18px',
                  border: `1px solid ${palette.accent}`,
                  borderRadius: '6px',
                  background: 'transparent',
                  color: palette.accent,
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  letterSpacing: '0.01em',
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = palette.accent;
                  e.target.style.color = '#060a13';
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = 'transparent';
                  e.target.style.color = palette.accent;
                }}
              >
                Get Started
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

function NavLink({ label, href }) {
  return (
    <a
      href={href}
      style={{
        color: palette.textMuted,
        textDecoration: 'none',
        fontSize: '0.85rem',
        fontWeight: 500,
        transition: 'color 0.2s ease',
        letterSpacing: '0.01em',
      }}
      onMouseEnter={(e) => (e.target.style.color = palette.text)}
      onMouseLeave={(e) => (e.target.style.color = palette.textMuted)}
    >
      {label}
    </a>
  );
}


// Hero section with canvas waveform

function HeroSection({ onLaunch, isAuthenticated }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let time = 0;

    function resize() {
      canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
      canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
      ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    }
    resize();
    window.addEventListener('resize', resize);

    function draw() {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      ctx.clearRect(0, 0, w, h);

      // Draw subtle grid
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.04)';
      ctx.lineWidth = 0.5;
      const gridSize = 40;
      for (let x = 0; x < w; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Draw acoustic waveform lines
      const waveCount = 3;
      const colors = [
        'rgba(56, 189, 248, 0.18)',
        'rgba(34, 211, 238, 0.12)',
        'rgba(167, 139, 250, 0.10)',
      ];

      for (let wave = 0; wave < waveCount; wave++) {
        ctx.beginPath();
        ctx.strokeStyle = colors[wave];
        ctx.lineWidth = 1.5;
        const centerY = h * (0.35 + wave * 0.15);
        const amplitude = 25 + wave * 10;
        const freq = 0.008 - wave * 0.001;
        const phase = time * (0.6 + wave * 0.3);

        for (let x = 0; x <= w; x += 2) {
          const y =
            centerY +
            Math.sin(x * freq + phase) * amplitude +
            Math.sin(x * freq * 2.7 + phase * 1.3) * (amplitude * 0.3) +
            Math.sin(x * freq * 0.5 + phase * 0.7) * (amplitude * 0.5);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // Pulsing grid nodes
      const dotInterval = gridSize * 4;
      for (let x = dotInterval; x < w; x += dotInterval) {
        for (let y = dotInterval; y < h; y += dotInterval) {
          const pulse = 0.3 + 0.7 * Math.abs(Math.sin(time * 0.5 + x * 0.01 + y * 0.01));
          const radius = 1.5 * pulse;
          ctx.beginPath();
          ctx.fillStyle = `rgba(56, 189, 248, ${0.15 * pulse})`;
          ctx.arc(x, y, radius, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      time += 0.016;
      animId = requestAnimationFrame(draw);
    }

    draw();
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <section
      style={{
        position: 'relative',
        minHeight: '92vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: '64px',
      }}
    >
      {/* Animated canvas background */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      />

      {/* Radial gradient background accent */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse 80% 70% at 50% 40%, rgba(56,189,248,0.06) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Content */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          textAlign: 'center',
          padding: '0 24px',
          maxWidth: '820px',
        }}
      >
        {/* Status badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 16px',
            borderRadius: '100px',
            border: `1px solid ${palette.border}`,
            background: 'rgba(15, 23, 42, 0.6)',
            fontSize: '0.75rem',
            color: palette.textMuted,
            marginBottom: '32px',
            letterSpacing: '0.02em',
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: palette.green,
              boxShadow: `0 0 8px ${palette.green}`,
            }}
          />
          <span>Phase 3 — Multi-Tenant JWT Auth & Cascade Diagnostics Active</span>
        </div>

        {/* Main headline */}
        <h1
          style={{
            fontSize: 'clamp(2.2rem, 5vw, 3.6rem)',
            fontWeight: 800,
            lineHeight: 1.1,
            letterSpacing: '-0.03em',
            margin: '0 0 24px',
            color: '#f8fafc',
          }}
        >
          Audio{' '}
          <span
            style={{
              background: palette.gradB,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Fault Diagnosis
          </span>
        </h1>

        {/* Sub-headline */}
        <p
          style={{
            fontSize: 'clamp(1rem, 2vw, 1.15rem)',
            color: palette.textMuted,
            lineHeight: 1.7,
            margin: '0 auto 40px',
            maxWidth: '640px',
          }}
        >
          Isolate bearing flaws, fan imbalances, and motor failures from raw acoustic telemetry.
          Multi-tenant cloud architecture pairing 11-parameter DSP feature pipelines with dual-stage
          CNN cascades.
        </p>

        {/* CTA buttons */}
        <div
          style={{
            display: 'flex',
            gap: '16px',
            justifyContent: 'center',
            flexWrap: 'wrap',
          }}
        >
          <button
            onClick={onLaunch}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '14px 34px',
              border: 'none',
              borderRadius: '8px',
              background: palette.gradA,
              color: '#060a13',
              fontSize: '0.95rem',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.2s ease',
              boxShadow: '0 0 24px rgba(56, 189, 248, 0.25)',
              letterSpacing: '0.01em',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 0 40px rgba(56, 189, 248, 0.45)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 0 24px rgba(56, 189, 248, 0.25)';
            }}
          >
            {isAuthenticated ? 'Go to Dashboard' : 'Launch Dashboard'}
            <ChevronRight size={18} strokeWidth={2.5} />
          </button>

          <a
            href="#architecture"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '14px 28px',
              border: `1px solid ${palette.borderLt}`,
              borderRadius: '8px',
              background: 'transparent',
              color: palette.textMuted,
              fontSize: '0.95rem',
              fontWeight: 600,
              cursor: 'pointer',
              textDecoration: 'none',
              transition: 'all 0.2s ease',
              letterSpacing: '0.01em',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = palette.accent;
              e.currentTarget.style.color = palette.text;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = palette.borderLt;
              e.currentTarget.style.color = palette.textMuted;
            }}
          >
            View Architecture
          </a>
        </div>
      </div>
    </section>
  );
}


// Project key metrics

function MetricsBar() {
  const metrics = [
    { value: 'CNN', label: 'ENSEMBLE LEARNING', icon: <Gauge size={16} color={palette.accent} /> },
    { value: '11', label: 'DSP Features', icon: <Layers size={16} color={palette.accentAlt} /> },
    { value: 'Real-time', label: 'Telemetry Processing', icon: <Zap size={16} color={palette.green} /> },
    { value: 'Multi-Tenant', label: 'Data Isolation', icon: <Shield size={16} color={palette.purple} /> },
  ];

  return (
    <section
      style={{
        borderTop: `1px solid ${palette.border}`,
        borderBottom: `1px solid ${palette.border}`,
        background: palette.bgSurface,
      }}
    >
      <div
        style={{
          maxWidth: '1000px',
          margin: '0 auto',
          padding: '28px 24px',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '24px',
        }}
      >
        {metrics.map((m, i) => (
          <div
            key={i}
            style={{
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {m.icon}
            <span
              style={{
                fontSize: '1.6rem',
                fontWeight: 800,
                color: '#f8fafc',
                letterSpacing: '-0.02em',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {m.value}
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                color: palette.textDim,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              {m.label}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}


// Core features grid

function FeaturesGrid() {
  const features = [
    {
      icon: <AudioWaveform size={24} />,
      iconColor: palette.accent,
      title: 'Acoustic Fingerprinting',
      desc: 'Extract 11 domain-engineered DSP features — crest factor, kurtosis, spectral centroid, envelope analysis — from raw acoustic signals in real time.',
      tags: ['Mel-Spectrogram', 'STFT', 'Envelope Analysis'],
    },
    {
      icon: <BrainCircuit size={24} />,
      iconColor: palette.purple,
      title: 'Multi-Model Inference',
      desc: 'Cascade architecture combining Random Forest classifiers with deep CNNs. Dynamic model registry routes Fan, Motor, and Bearing signals to specialized models.',
      tags: ['CNN Cascade', 'Random Forest', 'Model Registry'],
    },
    {
      icon: <Radio size={24} />,
      iconColor: palette.green,
      title: 'Real-time Telemetry',
      desc: 'Instant diagnosis with persistent multi-tenant SQLite history, interactive waveform charts, PDF report export, and full audit logs per machine.',
      tags: ['Live Waveform', 'PDF Export', 'Tenant Scoped'],
    },
  ];

  return (
    <section id="features" style={{ padding: '96px 24px' }}>
      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '64px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: palette.accent,
              fontWeight: 600,
            }}
          >
            Core Capabilities
          </span>
          <h2
            style={{
              fontSize: 'clamp(1.5rem, 3vw, 2.2rem)',
              fontWeight: 800,
              color: '#f8fafc',
              margin: '12px 0 16px',
              letterSpacing: '-0.02em',
            }}
          >
            Industrial-Grade Signal Intelligence
          </h2>
          <p
            style={{
              color: palette.textMuted,
              fontSize: '1rem',
              maxWidth: '550px',
              margin: '0 auto',
              lineHeight: 1.6,
            }}
          >
            A full-stack diagnostic pipeline from microphone capture to fault classification —
            engineered for predictive maintenance teams.
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '20px',
          }}
        >
          {features.map((feat, i) => (
            <FeatureCard key={i} {...feat} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ icon, iconColor, title, desc, tags }) {
  return (
    <div
      style={{
        padding: '32px 28px',
        borderRadius: '12px',
        border: `1px solid ${palette.border}`,
        background: palette.bgCard,
        transition: 'border-color 0.25s ease, box-shadow 0.25s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.25)';
        e.currentTarget.style.boxShadow = '0 4px 32px rgba(56, 189, 248, 0.06)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = palette.border;
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '10px',
          background: `${iconColor}12`,
          border: `1px solid ${iconColor}25`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: iconColor,
          marginBottom: '20px',
        }}
      >
        {icon}
      </div>

      <h3
        style={{
          fontSize: '1.05rem',
          fontWeight: 700,
          color: '#f1f5f9',
          margin: '0 0 10px',
          letterSpacing: '-0.01em',
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: '0.85rem',
          color: palette.textMuted,
          lineHeight: 1.65,
          margin: '0 0 18px',
        }}
      >
        {desc}
      </p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {tags.map((tag) => (
          <span
            key={tag}
            style={{
              padding: '3px 10px',
              borderRadius: '4px',
              background: 'rgba(56, 189, 248, 0.06)',
              border: '1px solid rgba(56, 189, 248, 0.1)',
              fontSize: '0.68rem',
              color: palette.accent,
              fontWeight: 500,
              letterSpacing: '0.02em',
            }}
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}


// System architecture section

function ArchitectureSection() {
  const layers = [
    {
      label: 'Signal Acquisition',
      detail: 'Browser mic / WAV upload → 16 kHz mono PCM telemetry',
      color: palette.accent,
    },
    {
      label: 'DSP Feature Extraction',
      detail: '11 engineered features: spectral statistics, envelope spectrum peak & kurtosis',
      color: palette.accentAlt,
    },
    {
      label: 'Mel-Spectrogram Generation',
      detail: '128-bin log-power spectrogram with dynamic 128×128 image scaling',
      color: palette.purple,
    },
    {
      label: 'Stage 1 — Random Forest',
      detail: 'Physics-based baseline classification on statistical DSP vectors',
      color: palette.green,
    },
    {
      label: 'Stage 2 — CNN Cascade',
      detail: 'Acoustic visual feature maps with weighted consensus ensemble',
      color: '#f59e0b',
    },
    {
      label: 'Tenant Scoped History & Reports',
      detail: 'Multi-tenant database storage, PDF generation, and telemetry audits',
      color: '#f87171',
    },
  ];

  return (
    <section
      id="architecture"
      style={{
        padding: '96px 24px',
        background: palette.bgSurface,
        borderTop: `1px solid ${palette.border}`,
        borderBottom: `1px solid ${palette.border}`,
      }}
    >
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '56px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: palette.accent,
              fontWeight: 600,
            }}
          >
            System Design
          </span>
          <h2
            style={{
              fontSize: 'clamp(1.5rem, 3vw, 2.2rem)',
              fontWeight: 800,
              color: '#f8fafc',
              margin: '12px 0 16px',
              letterSpacing: '-0.02em',
            }}
          >
            Cascade Inference Pipeline
          </h2>
          <p
            style={{
              color: palette.textMuted,
              fontSize: '0.95rem',
              maxWidth: '500px',
              margin: '0 auto',
              lineHeight: 1.6,
            }}
          >
            Six-stage pipeline from raw acoustic telemetry to verified fault classification —
            each stage independently verifiable.
          </p>
        </div>

        <div>
          {layers.map((layer, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '20px',
                marginBottom: i < layers.length - 1 ? '8px' : 0,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  width: '24px',
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: layer.color,
                    boxShadow: `0 0 10px ${layer.color}50`,
                    flexShrink: 0,
                    marginTop: '4px',
                  }}
                />
                {i < layers.length - 1 && (
                  <div
                    style={{
                      width: '2px',
                      flex: 1,
                      minHeight: '36px',
                      background: `linear-gradient(to bottom, ${layer.color}40, ${layers[i + 1].color}40)`,
                    }}
                  />
                )}
              </div>

              <div
                style={{
                  padding: '12px 20px 20px',
                  borderRadius: '8px',
                  border: `1px solid ${palette.border}`,
                  background: palette.bgCard,
                  flex: 1,
                }}
              >
                <div
                  style={{
                    fontSize: '0.65rem',
                    color: layer.color,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    marginBottom: '4px',
                  }}
                >
                  Stage {i + 1}
                </div>
                <div
                  style={{
                    fontSize: '0.95rem',
                    fontWeight: 700,
                    color: '#f1f5f9',
                    marginBottom: '4px',
                  }}
                >
                  {layer.label}
                </div>
                <div
                  style={{
                    fontSize: '0.8rem',
                    color: palette.textMuted,
                    lineHeight: 1.5,
                  }}
                >
                  {layer.detail}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}


// Bottom CTA banner

function CTABanner({ onLaunch, isAuthenticated }) {
  return (
    <section style={{ padding: '80px 24px', textAlign: 'center' }}>
      <div
        style={{
          maxWidth: '640px',
          margin: '0 auto',
          padding: '56px 40px',
          borderRadius: '16px',
          border: `1px solid ${palette.border}`,
          background: `linear-gradient(135deg, ${palette.bgCard} 0%, ${palette.bgSurface} 100%)`,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: '-60px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '300px',
            height: '200px',
            background: 'radial-gradient(circle, rgba(56,189,248,0.08) 0%, transparent 70%)',
            pointerEvents: 'none',
          }}
        />

        <h2
          style={{
            fontSize: '1.8rem',
            fontWeight: 800,
            color: '#f8fafc',
            margin: '0 0 12px',
            letterSpacing: '-0.02em',
            position: 'relative',
          }}
        >
          Start Diagnosing Machine Faults
        </h2>
        <p
          style={{
            color: palette.textMuted,
            fontSize: '0.95rem',
            margin: '0 0 32px',
            lineHeight: 1.6,
            position: 'relative',
          }}
        >
          Upload audio telemetry or record directly from machine sensors in your browser.
          Get verified condition reports with confidence scoring.
        </p>
        <button
          onClick={onLaunch}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '14px 36px',
            border: 'none',
            borderRadius: '8px',
            background: palette.gradA,
            color: '#060a13',
            fontSize: '0.95rem',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'transform 0.15s ease, box-shadow 0.2s ease',
            boxShadow: '0 0 24px rgba(56, 189, 248, 0.25)',
            position: 'relative',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 0 40px rgba(56, 189, 248, 0.45)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 0 24px rgba(56, 189, 248, 0.25)';
          }}
        >
          {isAuthenticated ? 'Open Dashboard' : 'Sign In & Launch'}
          <ChevronRight size={18} strokeWidth={2.5} />
        </button>
      </div>
    </section>
  );
}


// Footer

function Footer() {
  return (
    <footer
      style={{
        borderTop: `1px solid ${palette.border}`,
        padding: '32px 24px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          maxWidth: '1000px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <span style={{ fontSize: '0.78rem', color: palette.textDim }}>
          MachineSense · Enterprise Acoustic Fault Diagnosis
        </span>
        <span
          style={{
            fontSize: '0.72rem',
            color: palette.textDim,
            fontFamily: 'monospace',
          }}
        >
          FastAPI + JWT Multi-Tenant Auth · DSP + CNN Cascade · v1.0
        </span>
      </div>
    </footer>
  );
}


// Login modal

function LoginModal({ onClose, onSwitchToSignup, onSuccess }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Please provide both email and password.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      await login(email, password);
      onSuccess();
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalBackdrop onClose={onClose}>
      <div style={modalCardStyle} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc' }}>
              Welcome Back
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: palette.textMuted }}>
              Sign in to access your organization's telemetry dashboard
            </p>
          </div>
          <button onClick={onClose} style={closeButtonStyle}>
            <X size={18} />
          </button>
        </div>

        {error && <ErrorBanner message={error} />}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Work Email</label>
            <div style={inputContainerStyle}>
              <Mail size={16} color={palette.textMuted} />
              <input
                type="email"
                required
                placeholder="admin@gmail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
                autoFocus
              />
            </div>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={labelStyle}>Password</label>
            <div style={inputContainerStyle}>
              <Lock size={16} color={palette.textMuted} />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              ...primarySubmitButtonStyle,
              opacity: loading ? 0.7 : 1,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Authenticating...' : 'Sign In to Dashboard'}
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.82rem', color: palette.textMuted }}>
          Don't have an organization account?{' '}
          <button
            onClick={onSwitchToSignup}
            style={inlineLinkButtonStyle}
          >
            Create Organization
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}


// Registration modal

function SignupModal({ onClose, onSwitchToLogin, onSuccess }) {
  const { register } = useAuth();
  const [organizationName, setOrganizationName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!organizationName.trim()) {
      setError('Organization name is required.');
      return;
    }
    if (!email.trim()) {
      setError('Email address is required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      await register(email, password, organizationName);
      onSuccess();
    } catch (err) {
      setError(err.message || 'Registration failed. Please check the details and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalBackdrop onClose={onClose}>
      <div style={modalCardStyle} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc' }}>
              Register Organization
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: palette.textMuted }}>
              Set up multi-tenant acoustic telemetry for your facility
            </p>
          </div>
          <button onClick={onClose} style={closeButtonStyle}>
            <X size={18} />
          </button>
        </div>

        {error && <ErrorBanner message={error} />}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Organization / Facility Name</label>
            <div style={inputContainerStyle}>
              <Building2 size={16} color={palette.textMuted} />
              <input
                type="text"
                required
                placeholder="e.g. Apex Manufacturing Ltd."
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                style={inputStyle}
                autoFocus
              />
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Administrator Work Email</label>
            <div style={inputContainerStyle}>
              <Mail size={16} color={palette.textMuted} />
              <input
                type="email"
                required
                placeholder="admin@gmail.in"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
              />
            </div>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={labelStyle}>Password (min 6 characters)</label>
            <div style={inputContainerStyle}>
              <Lock size={16} color={palette.textMuted} />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              ...primarySubmitButtonStyle,
              opacity: loading ? 0.7 : 1,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Creating Organization...' : 'Create Account & Launch'}
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.82rem', color: palette.textMuted }}>
          Already have an account?{' '}
          <button
            onClick={onSwitchToLogin}
            style={inlineLinkButtonStyle}
          >
            Sign In
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}


// Modal backdrop and styles

function ModalBackdrop({ children, onClose }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        background: 'rgba(3, 7, 18, 0.78)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        animation: 'fadeIn 0.2s ease',
      }}
    >
      {children}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

function ErrorBanner({ message }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '10px 14px',
        background: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.25)',
        borderRadius: '8px',
        color: palette.danger,
        fontSize: '0.82rem',
        marginBottom: '18px',
      }}
    >
      <AlertCircle size={16} style={{ flexShrink: 0 }} />
      <span>{message}</span>
    </div>
  );
}

const modalCardStyle = {
  width: '100%',
  maxWidth: '440px',
  background: '#0c1220',
  border: '1px solid #1a2340',
  borderRadius: '16px',
  padding: '32px',
  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.65), 0 0 20px rgba(56, 189, 248, 0.1)',
  position: 'relative',
};

const closeButtonStyle = {
  background: 'transparent',
  border: 'none',
  color: palette.textMuted,
  cursor: 'pointer',
  padding: '4px',
  borderRadius: '6px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'color 0.15s ease',
};

const labelStyle = {
  display: 'block',
  fontSize: '0.78rem',
  fontWeight: 600,
  color: '#cbd5e1',
  marginBottom: '6px',
  letterSpacing: '0.01em',
};

const inputContainerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  background: palette.bgInput,
  border: `1px solid ${palette.borderLt}`,
  borderRadius: '8px',
  padding: '10px 14px',
  transition: 'border-color 0.2s ease',
};

const inputStyle = {
  flex: 1,
  background: 'transparent',
  border: 'none',
  outline: 'none',
  color: '#f8fafc',
  fontSize: '0.88rem',
  fontFamily: 'inherit',
};

const primarySubmitButtonStyle = {
  width: '100%',
  padding: '12px 20px',
  border: 'none',
  borderRadius: '8px',
  background: palette.gradA,
  color: '#060a13',
  fontSize: '0.9rem',
  fontWeight: 700,
  cursor: 'pointer',
  transition: 'transform 0.15s ease, box-shadow 0.2s ease',
  boxShadow: '0 0 20px rgba(56, 189, 248, 0.2)',
};

const inlineLinkButtonStyle = {
  background: 'transparent',
  border: 'none',
  color: palette.accent,
  fontWeight: 600,
  cursor: 'pointer',
  padding: 0,
  fontSize: 'inherit',
  textDecoration: 'underline',
};
