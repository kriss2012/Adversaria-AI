import React, { useState } from 'react';
import {
  ShieldCheck, TrendingUp, Zap, Scale,
  ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, XCircle,
} from 'lucide-react';
import type { DebateRound, CriticVote } from '../types';

interface DebatePanelProps {
  round: DebateRound | null;
}

const criticMeta = {
  purist: {
    label:       'Brand-Purist Critic',
    color:       '#f59e0b',
    bgColor:     'rgba(245, 158, 11, 0.06)',
    borderColor: 'rgba(245, 158, 11, 0.2)',
    icon:        ShieldCheck,
    tagline:     'Style guide enforcement & brand coherence',
  },
  marketer: {
    label:       'Performance-Marketer Critic',
    color:       '#a78bfa',
    bgColor:     'rgba(167, 139, 250, 0.06)',
    borderColor: 'rgba(167, 139, 250, 0.2)',
    icon:        TrendingUp,
    tagline:     'CTR, conversion & call-to-action optimization',
  },
  novelty: {
    label:       'Novelty Critic',
    color:       '#06b6d4',
    bgColor:     'rgba(6, 182, 212, 0.06)',
    borderColor: 'rgba(6, 182, 212, 0.2)',
    icon:        Zap,
    tagline:     'Distance from prior outputs & genericness penalty',
  },
} as const;

const VerdictBadge: React.FC<{ verdict: CriticVote['verdict'] }> = ({ verdict }) => {
  const cfg = {
    approve: { icon: CheckCircle2, color: '#10b981', label: 'Approve' },
    reject:  { icon: XCircle,     color: '#ef4444', label: 'Reject' },
    amend:   { icon: AlertTriangle, color: '#f59e0b', label: 'Amend' },
  }[verdict];
  const Icon = cfg.icon;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: cfg.color, fontSize: '12px', fontWeight: 600 }}>
      <Icon size={13} /> {cfg.label}
    </div>
  );
};

const ScoreRing: React.FC<{ score: number; color: string }> = ({ score, color }) => {
  const r = 22;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;
  return (
    <div style={{ position: 'relative', width: '56px', height: '56px', flexShrink: 0 }}>
      <svg width="56" height="56" viewBox="0 0 56 56" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="28" cy="28" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
        <circle
          cx="28" cy="28" r={r}
          fill="none" stroke={color}
          strokeWidth="5"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '13px', fontWeight: 800, color,
      }}>
        {score}
      </div>
    </div>
  );
};

export const DebatePanel: React.FC<DebatePanelProps> = ({ round }) => {
  const [showLog, setShowLog]            = useState(false);
  const [expandedCritic, setExpanded]    = useState<string | null>('purist');

  if (!round) {
    return (
      <div className="empty-state">
        <Scale size={36} />
        <p style={{ fontSize: '13.5px' }}>
          Run the pipeline to see the adversarial critique panel debate a generated concept.
        </p>
      </div>
    );
  }

  const finalConfig = {
    approved: { color: '#10b981', label: 'Panel Approved',      bg: 'rgba(16, 185, 129, 0.1)' },
    rejected: { color: '#ef4444', label: 'Panel Rejected',      bg: 'rgba(239, 68, 68, 0.1)'  },
    iterated: { color: '#f59e0b', label: 'Sent for Iteration',  bg: 'rgba(245, 158, 11, 0.1)' },
  }[round.finalVerdict];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
            <Scale size={16} style={{ color: 'var(--color-primary-light)' }} />
            Adversarial Critique Panel
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '12.5px', marginTop: '3px' }}>
            Concept: <em style={{ color: 'var(--text-sub)' }}>"{round.concept}"</em>
          </p>
        </div>
        <div style={{
          background:   finalConfig.bg,
          color:        finalConfig.color,
          padding:      '4px 12px',
          borderRadius: '9999px',
          fontSize:     '11.5px',
          fontWeight:   700,
          whiteSpace:   'nowrap',
          flexShrink:   0,
        }}>
          {finalConfig.label}
        </div>
      </div>

      {/* Critic Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {round.votes.map((vote) => {
          const meta     = criticMeta[vote.critic];
          const Icon     = meta.icon;
          const isExpanded = expandedCritic === vote.critic;
          return (
            <div
              key={vote.critic}
              style={{
                background:   isExpanded ? meta.bgColor : 'var(--bg-elevated)',
                border:       `1px solid ${isExpanded ? meta.borderColor : 'var(--border-light)'}`,
                borderRadius: 'var(--radius-md)',
                overflow:     'hidden',
                transition:   'all 0.25s ease',
              }}
            >
              {/* Critic Header Button */}
              <button
                onClick={() => setExpanded(isExpanded ? null : vote.critic)}
                style={{
                  background:     'none',
                  border:         'none',
                  cursor:         'pointer',
                  width:          '100%',
                  padding:        '10px 14px',
                  display:        'flex',
                  alignItems:     'center',
                  justifyContent: 'space-between',
                  gap:            '12px',
                  color:          'var(--text-main)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                  <Icon size={15} style={{ color: meta.color, flexShrink: 0 }} />
                  <div style={{ textAlign: 'left', minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: meta.color }}>{meta.label}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{meta.tagline}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
                  <ScoreRing score={vote.score} color={meta.color} />
                  <VerdictBadge verdict={vote.verdict} />
                  {isExpanded
                    ? <ChevronUp size={15} style={{ color: 'var(--text-muted)' }} />
                    : <ChevronDown size={15} style={{ color: 'var(--text-muted)' }} />
                  }
                </div>
              </button>

              {/* Expanded Body */}
              {isExpanded && (
                <div style={{
                  padding:     '0 14px 14px',
                  borderTop:   `1px solid ${meta.borderColor}`,
                  paddingTop:  '12px',
                  display:     'flex',
                  flexDirection: 'column',
                  gap:         '10px',
                }}>
                  <p style={{ fontSize: '13px', color: 'var(--text-sub)', lineHeight: 1.6 }}>{vote.reasoning}</p>
                  {vote.keyIssues.length > 0 && (
                    <div>
                      <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Key Issues</p>
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '4px', listStyle: 'none' }}>
                        {vote.keyIssues.map((issue, i) => (
                          <li key={i} style={{ fontSize: '12.5px', color: 'var(--text-sub)', display: 'flex', gap: '6px' }}>
                            <span style={{ color: meta.color, flexShrink: 0, marginTop: '2px' }}>▸</span>
                            {issue}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div style={{
                    background:   'var(--bg-input)',
                    border:       `1px solid ${meta.borderColor}`,
                    borderRadius: 'var(--radius-sm)',
                    padding:      '8px 10px',
                    fontSize:     '12.5px',
                    color:        meta.color,
                    fontStyle:    'italic',
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
        background:   'rgba(124, 58, 237, 0.06)',
        border:       '1px solid rgba(124, 58, 237, 0.2)',
        borderRadius: 'var(--radius-md)',
        padding:      '14px',
      }}>
        <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-primary-light)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
          🧠 Creative Director Synthesis
        </p>
        <p style={{ fontSize: '13px', lineHeight: 1.65, color: 'var(--text-sub)' }}>{round.directorSynthesis}</p>
        <div style={{ display: 'flex', gap: '24px', marginTop: '14px' }}>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Consensus Score</span>
            <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--color-primary-light)' }}>
              {round.consensusScore}
              <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-muted)' }}>/100</span>
            </div>
          </div>
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Verdict Distribution</span>
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
              {round.votes.map(v => (
                <div
                  key={v.critic}
                  title={`${criticMeta[v.critic].label}: ${v.verdict}`}
                  style={{
                    width:        '10px',
                    height:       '10px',
                    borderRadius: '50%',
                    background:   v.verdict === 'approve' ? '#10b981' : v.verdict === 'amend' ? '#f59e0b' : '#ef4444',
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Debate Log Toggle */}
      <button
        onClick={() => setShowLog(!showLog)}
        style={{
          background:     'var(--bg-elevated)',
          border:         '1px solid var(--border-light)',
          color:          'var(--text-muted)',
          borderRadius:   'var(--radius-sm)',
          padding:        '8px 12px',
          fontSize:       '12.5px',
          cursor:         'pointer',
          display:        'flex',
          alignItems:     'center',
          gap:            '6px',
          width:          '100%',
          justifyContent: 'center',
          transition:     'all 0.2s',
          fontFamily:     'var(--font-sans)',
        }}
      >
        {showLog ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        {showLog ? 'Hide' : 'Show'} Raw Debate Transcript
      </button>

      {showLog && (
        <div
          className="animate-fade-in"
          style={{
            background:    '#070810',
            borderRadius:  'var(--radius-md)',
            padding:       '12px',
            border:        '1px solid var(--border-light)',
            fontFamily:    'var(--font-mono)',
            fontSize:      '12px',
            maxHeight:     '200px',
            overflowY:     'auto',
            display:       'flex',
            flexDirection: 'column',
            gap:           '6px',
            lineHeight:    1.5,
          }}
        >
          {round.debateLog.map((entry, i) => {
            const c = Object.entries(criticMeta).find(([, v]) => v.label.includes(entry.speaker));
            const col = c ? c[1].color : 'var(--color-primary-light)';
            return (
              <div key={i}>
                <span style={{ color: col, fontWeight: 700 }}>[{entry.speaker}]</span>{' '}
                <span style={{ color: 'var(--text-sub)' }}>{entry.line}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
