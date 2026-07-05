import React, { useState } from 'react';
import { BarChart3, TrendingUp, Star, Cpu, RefreshCw, History, Info } from 'lucide-react';

export interface EvalScores {
  brandFit: number;
  novelty: number;
  predictedPerformance: number;
  overallScore: number;
  breakdown: {
    brandFitReason: string;
    noveltyReason: string;
    predictedPerfReason: string;
  };
}

export interface HistoricalEntry {
  id: string;
  conceptName: string;
  timestamp: string;
  scores: EvalScores;
  status: 'approved' | 'rejected' | 'iterated';
}

interface EvalDashboardProps {
  currentScores: EvalScores | null;
  history: HistoricalEntry[];
}

const AxisBar: React.FC<{ label: string; score: number; color: string; reason?: string; icon: React.ReactNode }> = ({
  label, score, color, reason, icon
}) => {
  const [hovered, setHovered] = useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 500 }}>
          {icon}
          {label}
          {reason && (
            <div style={{ position: 'relative', display: 'inline-flex' }}
              onMouseEnter={() => setHovered(true)}
              onMouseLeave={() => setHovered(false)}>
              <Info size={12} style={{ color: 'var(--text-dark)', cursor: 'help' }} />
              {hovered && (
                <div style={{
                  position: 'absolute',
                  bottom: '16px',
                  left: '-60px',
                  width: '220px',
                  background: '#1e2130',
                  border: '1px solid var(--border-light)',
                  borderRadius: '8px',
                  padding: '8px 10px',
                  fontSize: '11px',
                  color: 'var(--text-main)',
                  zIndex: 99,
                  boxShadow: 'var(--shadow-lg)',
                  lineHeight: 1.4
                }}>
                  {reason}
                </div>
              )}
            </div>
          )}
        </div>
        <span style={{ fontSize: '15px', fontWeight: 700, color }}>{score}<span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 400 }}>/100</span></span>
      </div>
      <div style={{ height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '9999px', overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${score}%`,
            background: `linear-gradient(to right, ${color}88, ${color})`,
            borderRadius: '9999px',
            transition: 'width 1.2s cubic-bezier(0.16, 1, 0.3, 1)'
          }}
        />
      </div>
    </div>
  );
};

const OverallGauge: React.FC<{ score: number }> = ({ score }) => {
  const r = 48;
  const circumference = Math.PI * r; // semicircle
  const dashoffset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? '#10b981' : score >= 45 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
      <svg width="120" height="70" viewBox="0 0 120 70">
        <path d="M 12 62 A 48 48 0 0 1 108 62" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" strokeLinecap="round" />
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
      <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '-4px' }}>Overall Eval Score</span>
    </div>
  );
};

export const EvalDashboard: React.FC<EvalDashboardProps> = ({ currentScores, history }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Current Concept Scores */}
      <div className="glass-panel p-6 animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BarChart3 style={{ color: 'var(--color-primary)', width: '20px', height: '20px' }} />
              Evaluation Harness
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
              Auto-scored on three measurable axes per generated concept.
            </p>
          </div>
          {currentScores && <OverallGauge score={currentScores.overallScore} />}
        </div>

        {!currentScores ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '14px' }}>
            <BarChart3 size={32} style={{ opacity: 0.2, margin: '0 auto 8px' }} />
            No scores yet — generate a concept to see the eval harness run.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <AxisBar
              label="Brand Fit"
              score={currentScores.brandFit}
              color="#a78bfa"
              reason={currentScores.breakdown.brandFitReason}
              icon={<Star size={14} style={{ color: '#a78bfa' }} />}
            />
            <AxisBar
              label="Novelty"
              score={currentScores.novelty}
              color="#06b6d4"
              reason={currentScores.breakdown.noveltyReason}
              icon={<Cpu size={14} style={{ color: '#06b6d4' }} />}
            />
            <AxisBar
              label="Predicted Performance"
              score={currentScores.predictedPerformance}
              color="#10b981"
              reason={currentScores.breakdown.predictedPerfReason}
              icon={<TrendingUp size={14} style={{ color: '#10b981' }} />}
            />

            {/* Axis Explanations */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginTop: '4px' }}>
              {[
                { label: 'Brand Fit', desc: 'Embedding similarity to brand corpus & style guide compliance', color: '#a78bfa' },
                { label: 'Novelty', desc: 'Cosine distance from prior outputs in concept embedding space', color: '#06b6d4' },
                { label: 'Pred. Perf.', desc: 'A lightweight regression model trained on historical ad CTR data', color: '#10b981' },
              ].map(axis => (
                <div key={axis.label} style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-light)',
                  borderRadius: '8px',
                  padding: '8px',
                  fontSize: '11px'
                }}>
                  <div style={{ color: axis.color, fontWeight: 600, marginBottom: '4px' }}>{axis.label}</div>
                  <div style={{ color: 'var(--text-muted)', lineHeight: 1.4 }}>{axis.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Run History */}
      {history.length > 0 && (
        <div className="glass-panel p-6" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <History style={{ color: 'var(--color-secondary)', width: '18px', height: '18px' }} />
            Concept History
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '240px', overflowY: 'auto' }}>
            {history.map((entry) => {
              const statusColor = entry.status === 'approved' ? '#10b981' : entry.status === 'rejected' ? '#ef4444' : '#f59e0b';
              return (
                <div key={entry.id} style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-light)',
                  borderRadius: '8px',
                  padding: '10px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px'
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 500, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{entry.conceptName}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{entry.timestamp}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {[
                        { score: entry.scores.brandFit, color: '#a78bfa' },
                        { score: entry.scores.novelty, color: '#06b6d4' },
                        { score: entry.scores.predictedPerformance, color: '#10b981' },
                      ].map((s, i) => (
                        <div key={i} style={{
                          background: 'rgba(255,255,255,0.04)',
                          borderRadius: '4px',
                          padding: '2px 6px',
                          fontSize: '11px',
                          fontWeight: 700,
                          color: s.color
                        }}>{s.score}</div>
                      ))}
                    </div>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: statusColor }}>
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
