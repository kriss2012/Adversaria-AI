import React, { useState } from 'react';
import { BarChart3, TrendingUp, Star, Cpu, History, Info } from 'lucide-react';
import type { EvalScores, HistoricalEntry } from '../types';

interface EvalDashboardProps {
  currentScores: EvalScores | null;
  history:       HistoricalEntry[];
}

/* ─── Axis Bar ─────────────────────────────────────────────────────────────── */
const AxisBar: React.FC<{
  label:  string;
  score:  number;
  color:  string;
  reason?: string;
  icon:   React.ReactNode;
}> = ({ label, score, color, reason, icon }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 500, color: 'var(--text-sub)' }}>
          {icon}
          {label}
          {reason && (
            <div
              style={{ position: 'relative', display: 'inline-flex', cursor: 'help' }}
              onMouseEnter={() => setHovered(true)}
              onMouseLeave={() => setHovered(false)}
            >
              <Info size={12} style={{ color: 'var(--text-dark)' }} />
              {hovered && (
                <div style={{
                  position:     'absolute',
                  bottom:       '18px',
                  left:         '-60px',
                  width:        '220px',
                  background:   'var(--bg-elevated)',
                  border:       '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-md)',
                  padding:      '8px 10px',
                  fontSize:     '11.5px',
                  color:        'var(--text-sub)',
                  zIndex:       99,
                  boxShadow:    'var(--shadow-lg)',
                  lineHeight:   1.45,
                  pointerEvents: 'none',
                }}>
                  {reason}
                </div>
              )}
            </div>
          )}
        </div>
        <span style={{ fontSize: '16px', fontWeight: 800, color }}>
          {score}
          <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--text-muted)' }}>/100</span>
        </span>
      </div>
      <div style={{ height: '7px', background: 'var(--bg-input)', borderRadius: '9999px', overflow: 'hidden' }}>
        <div style={{
          height:       '100%',
          width:        `${score}%`,
          background:   `linear-gradient(to right, ${color}88, ${color})`,
          borderRadius: '9999px',
          transition:   'width 1.2s cubic-bezier(0.16, 1, 0.3, 1)',
        }} />
      </div>
    </div>
  );
};

/* ─── Gauge ────────────────────────────────────────────────────────────────── */
const OverallGauge: React.FC<{ score: number }> = ({ score }) => {
  const r = 48;
  const circumference = Math.PI * r;
  const dashoffset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? '#10b981' : score >= 45 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px', flexShrink: 0 }}>
      <svg width="110" height="65" viewBox="0 0 120 70">
        <path d="M 12 62 A 48 48 0 0 1 108 62" fill="none" stroke="var(--bg-input)" strokeWidth="10" strokeLinecap="round" />
        <path
          d="M 12 62 A 48 48 0 0 1 108 62"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashoffset}
          style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: 'stroke-dashoffset 1.5s ease, stroke 0.5s ease' }}
        />
        <text x="60" y="58" textAnchor="middle" fill={color} fontSize="20" fontWeight="800" fontFamily="Outfit, sans-serif">{score}</text>
      </svg>
      <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>Overall Score</span>
    </div>
  );
};

/* ─── Main ─────────────────────────────────────────────────────────────────── */
export const EvalDashboard: React.FC<EvalDashboardProps> = ({ currentScores, history }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Current Scores */}
      <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
              <BarChart3 size={16} style={{ color: 'var(--color-primary-light)' }} />
              Evaluation Harness
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '12.5px', marginTop: '3px' }}>
              Auto-scored on three measurable axes per generated concept.
            </p>
          </div>
          {currentScores && <OverallGauge score={currentScores.overallScore} />}
        </div>

        {!currentScores ? (
          <div className="empty-state" style={{ minHeight: '140px' }}>
            <BarChart3 size={32} />
            <p style={{ fontSize: '13.5px' }}>No scores yet — generate a concept to run the eval harness.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <AxisBar
              label="Brand Fit"
              score={currentScores.brandFit}
              color="#a78bfa"
              reason={currentScores.breakdown.brandFitReason}
              icon={<Star size={13} style={{ color: '#a78bfa' }} />}
            />
            <AxisBar
              label="Novelty"
              score={currentScores.novelty}
              color="#06b6d4"
              reason={currentScores.breakdown.noveltyReason}
              icon={<Cpu size={13} style={{ color: '#06b6d4' }} />}
            />
            <AxisBar
              label="Predicted Performance"
              score={currentScores.predictedPerformance}
              color="#10b981"
              reason={currentScores.breakdown.predictedPerfReason}
              icon={<TrendingUp size={13} style={{ color: '#10b981' }} />}
            />

            {/* Axis legend */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
              {[
                { label: 'Brand Fit',   desc: 'Embedding similarity to brand corpus & style guide compliance', color: '#a78bfa' },
                { label: 'Novelty',     desc: 'Cosine distance from prior outputs in concept embedding space', color: '#06b6d4' },
                { label: 'Pred. Perf.', desc: 'Regression model trained on historical ad CTR data',            color: '#10b981' },
              ].map(axis => (
                <div key={axis.label} style={{
                  background:   'var(--bg-elevated)',
                  border:       '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-sm)',
                  padding:      '8px 10px',
                  fontSize:     '11px',
                }}>
                  <div style={{ color: axis.color, fontWeight: 700, marginBottom: '4px' }}>{axis.label}</div>
                  <div style={{ color: 'var(--text-muted)', lineHeight: 1.4 }}>{axis.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Run History */}
      {history.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)' }}>
            <History size={15} style={{ color: 'var(--color-secondary)' }} />
            Concept History
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '240px', overflowY: 'auto' }}>
            {history.map((entry) => {
              const statusColor = entry.status === 'approved' ? '#10b981' : entry.status === 'rejected' ? '#ef4444' : '#f59e0b';
              return (
                <div key={entry.id} style={{
                  background:     'var(--bg-elevated)',
                  border:         '1px solid var(--border-light)',
                  borderRadius:   'var(--radius-md)',
                  padding:        '10px 12px',
                  display:        'flex',
                  alignItems:     'center',
                  justifyContent: 'space-between',
                  gap:            '12px',
                  transition:     'border-color 0.2s',
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-main)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {entry.conceptName}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{entry.timestamp}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                    <div style={{ display: 'flex', gap: '5px' }}>
                      {[
                        { score: entry.scores.brandFit,              color: '#a78bfa' },
                        { score: entry.scores.novelty,               color: '#06b6d4' },
                        { score: entry.scores.predictedPerformance,  color: '#10b981' },
                      ].map((s, i) => (
                        <div key={i} style={{
                          background:   'var(--bg-input)',
                          borderRadius: '4px',
                          padding:      '2px 6px',
                          fontSize:     '11px',
                          fontWeight:   700,
                          color:        s.color,
                        }}>
                          {s.score}
                        </div>
                      ))}
                    </div>
                    <div style={{ fontSize: '11.5px', fontWeight: 600, color: statusColor }}>
                      {entry.status.charAt(0).toUpperCase() + entry.status.slice(1)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
