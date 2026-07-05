import React, { useState } from 'react';
import { ShieldCheck, TrendingUp, Zap, Scale, ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

export interface CriticVote {
  critic: 'purist' | 'marketer' | 'novelty';
  verdict: 'approve' | 'reject' | 'amend';
  score: number; // 0–100
  reasoning: string;
  keyIssues: string[];
  recommendation: string;
}

export interface DebateRound {
  id: string;
  concept: string;
  votes: CriticVote[];
  directorSynthesis: string;
  finalVerdict: 'approved' | 'rejected' | 'iterated';
  consensusScore: number;
  debateLog: { speaker: string; line: string }[];
}

interface DebatePanelProps {
  round: DebateRound | null;
}

const criticMeta = {
  purist: {
    label: 'Brand-Purist Critic',
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.08)',
    borderColor: 'rgba(245, 158, 11, 0.25)',
    icon: ShieldCheck,
    tagline: 'Style guide enforcement & brand coherence'
  },
  marketer: {
    label: 'Performance-Marketer Critic',
    color: '#a78bfa',
    bgColor: 'rgba(167, 139, 250, 0.08)',
    borderColor: 'rgba(167, 139, 250, 0.25)',
    icon: TrendingUp,
    tagline: 'CTR, conversion & call-to-action optimization'
  },
  novelty: {
    label: 'Novelty Critic',
    color: '#06b6d4',
    bgColor: 'rgba(6, 182, 212, 0.08)',
    borderColor: 'rgba(6, 182, 212, 0.25)',
    icon: Zap,
    tagline: 'Distance from prior outputs & genericness penalty'
  },
};

const VerdictBadge: React.FC<{ verdict: CriticVote['verdict'] }> = ({ verdict }) => {
  const config = {
    approve: { icon: CheckCircle2, color: '#10b981', label: 'Approve' },
    reject: { icon: XCircle, color: '#ef4444', label: 'Reject' },
    amend: { icon: AlertTriangle, color: '#f59e0b', label: 'Amend' },
  }[verdict];
  const Icon = config.icon;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: config.color, fontSize: '12px', fontWeight: 600 }}>
      <Icon size={14} />
      {config.label}
    </div>
  );
};

const ScoreRing: React.FC<{ score: number; color: string }> = ({ score, color }) => {
  const radius = 22;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  return (
    <div style={{ position: 'relative', width: '60px', height: '60px', flexShrink: 0 }}>
      <svg width="60" height="60" viewBox="0 0 60 60" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="30" cy="30" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="5" />
        <circle
          cx="30" cy="30" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '14px', fontWeight: 700, color
      }}>
        {score}
      </div>
    </div>
  );
};

export const DebatePanel: React.FC<DebatePanelProps> = ({ round }) => {
  const [showDebateLog, setShowDebateLog] = useState(false);
  const [expandedCritic, setExpandedCritic] = useState<string | null>('purist');

  if (!round) {
    return (
      <div className="glass-panel p-6 flex flex-col" style={{ gap: '12px', minHeight: '320px', justifyContent: 'center', alignItems: 'center' }}>
        <Scale size={36} style={{ color: 'var(--text-dark)', opacity: 0.4 }} />
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', fontSize: '14px' }}>
          Run the pipeline to see the adversarial critique panel debate a generated concept.
        </p>
      </div>
    );
  }

  const finalConfig = {
    approved: { color: '#10b981', label: 'Panel Approved', bg: 'rgba(16, 185, 129, 0.1)' },
    rejected: { color: '#ef4444', label: 'Panel Rejected', bg: 'rgba(239, 68, 68, 0.1)' },
    iterated: { color: '#f59e0b', label: 'Sent for Iteration', bg: 'rgba(245, 158, 11, 0.1)' },
  }[round.finalVerdict];

  return (
    <div className="glass-panel p-6 flex flex-col animate-fade-in" style={{ gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Scale style={{ color: 'var(--color-primary-light)', width: '20px', height: '20px' }} />
            Adversarial Critique Panel
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
            Concept: <span style={{ color: 'var(--text-main)', fontStyle: 'italic' }}>&ldquo;{round.concept}&rdquo;</span>
          </p>
        </div>
        <div style={{
          background: finalConfig.bg,
          color: finalConfig.color,
          padding: '4px 12px',
          borderRadius: '9999px',
          fontSize: '12px',
          fontWeight: 700,
          whiteSpace: 'nowrap'
        }}>
          {finalConfig.label}
        </div>
      </div>

      {/* Critic Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {round.votes.map((vote) => {
          const meta = criticMeta[vote.critic];
          const Icon = meta.icon;
          const isExpanded = expandedCritic === vote.critic;
          return (
            <div
              key={vote.critic}
              style={{
                background: isExpanded ? meta.bgColor : 'rgba(255,255,255,0.01)',
                border: `1px solid ${isExpanded ? meta.borderColor : 'var(--border-light)'}`,
                borderRadius: '10px',
                overflow: 'hidden',
                transition: 'all 0.3s ease'
              }}
            >
              {/* Critic Header */}
              <button
                onClick={() => setExpandedCritic(isExpanded ? null : vote.critic)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  width: '100%', padding: '12px 14px',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  color: 'var(--text-main)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Icon size={16} style={{ color: meta.color, flexShrink: 0 }} />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: meta.color }}>{meta.label}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{meta.tagline}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <ScoreRing score={vote.score} color={meta.color} />
                  <VerdictBadge verdict={vote.verdict} />
                  {isExpanded
                    ? <ChevronUp size={16} style={{ color: 'var(--text-muted)' }} />
                    : <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} />
                  }
                </div>
              </button>

              {/* Critic Body */}
              {isExpanded && (
                <div style={{ padding: '0 14px 14px 14px', borderTop: `1px solid ${meta.borderColor}`, paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5 }}>{vote.reasoning}</p>
                  {vote.keyIssues.length > 0 && (
                    <div>
                      <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Key Issues</p>
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '4px', listStyle: 'none' }}>
                        {vote.keyIssues.map((issue, i) => (
                          <li key={i} style={{ fontSize: '12px', color: 'var(--text-main)', display: 'flex', gap: '6px' }}>
                            <span style={{ color: meta.color, marginTop: '2px' }}>▸</span>
                            {issue}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    fontSize: '12px',
                    color: meta.color,
                    fontStyle: 'italic'
                  }}>
                    💡 {vote.recommendation}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Director Synthesis */}
      <div style={{
        background: 'rgba(139, 92, 246, 0.07)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: '10px',
        padding: '14px'
      }}>
        <p style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-primary-light)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          🧠 Creative Director Synthesis
        </p>
        <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-main)' }}>
          {round.directorSynthesis}
        </p>
        <div style={{ display: 'flex', gap: '20px', marginTop: '12px' }}>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Consensus Score</span>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-light)' }}>{round.consensusScore}<span style={{ fontSize: '13px', fontWeight: 400 }}>/100</span></div>
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Verdict Distribution</span>
            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
              {round.votes.map(v => (
                <div key={v.critic} style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: v.verdict === 'approve' ? '#10b981' : v.verdict === 'amend' ? '#f59e0b' : '#ef4444'
                }} title={`${criticMeta[v.critic].label}: ${v.verdict}`} />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Debate Log Toggle */}
      <button
        onClick={() => setShowDebateLog(!showDebateLog)}
        style={{
          background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-muted)',
          borderRadius: '8px', padding: '8px 12px', fontSize: '12px', cursor: 'pointer', display: 'flex',
          alignItems: 'center', gap: '6px', width: '100%', justifyContent: 'center', transition: 'all 0.2s'
        }}
      >
        {showDebateLog ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {showDebateLog ? 'Hide' : 'Show'} Raw Debate Transcript
      </button>

      {showDebateLog && (
        <div
          style={{
            background: '#06070a',
            borderRadius: '8px',
            padding: '12px',
            border: '1px solid var(--border-light)',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            maxHeight: '200px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px'
          }}
          className="animate-fade-in"
        >
          {round.debateLog.map((entry, i) => {
            const c = Object.entries(criticMeta).find(([, v]) => v.label.includes(entry.speaker));
            const color = c ? c[1].color : 'var(--color-primary-light)';
            return (
              <div key={i}>
                <span style={{ color, fontWeight: 600 }}>[{entry.speaker}]</span>{' '}
                <span style={{ color: 'var(--text-main)' }}>{entry.line}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
