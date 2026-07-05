import React, { useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, GitBranch, FileText, Layers } from 'lucide-react';

export interface RationaleTrace {
  conceptName: string;
  platform: string;
  headline: string;
  tagline: string;
  colorPalette: string[];
  layoutDescription: string;
  decisions: {
    decision: string;
    rule: string;
    ruleSource: string;
    confidence: number;
  }[];
  hanlonReframe: string | null;
  competitorGap: string;
  suggestedIterations: string[];
}

interface RationalePanelProps {
  rationale: RationaleTrace | null;
}

const ConfidencePip: React.FC<{ confidence: number }> = ({ confidence }) => {
  const filled = Math.round((confidence / 100) * 5);
  return (
    <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: i < filled ? 'var(--color-primary-light)' : 'rgba(255,255,255,0.1)'
        }} />
      ))}
      <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '4px' }}>{confidence}%</span>
    </div>
  );
};

export const RationalePanel: React.FC<RationalePanelProps> = ({ rationale }) => {
  const [showDecisions, setShowDecisions] = useState(true);

  if (!rationale) {
    return (
      <div className="glass-panel p-6" style={{ minHeight: '200px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '10px' }}>
        <FileText size={32} style={{ color: 'var(--text-dark)', opacity: 0.3 }} />
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', textAlign: 'center' }}>
          Explainable Design Rationale (XDR) trace will appear here after generation.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel p-6 animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitBranch style={{ color: '#a78bfa', width: '20px', height: '20px' }} />
          Explainable Design Rationale (XDR)
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
          Full audit trail: which rule drove which decision. Enterprise-ready for legal & compliance review.
        </p>
      </div>

      {/* Concept Preview Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(139,92,246,0.12), rgba(6,182,212,0.06))',
        border: '1px solid rgba(139,92,246,0.2)',
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-primary-light)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{rationale.platform}</div>
            <h4 style={{ fontSize: '22px', fontWeight: 800, letterSpacing: '-0.02em', marginTop: '4px', background: 'linear-gradient(135deg, white, #c4b5fd)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              {rationale.headline}
            </h4>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>{rationale.tagline}</p>
          </div>
          <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
            {rationale.colorPalette.map((color, i) => (
              <div key={i} title={color} style={{ width: '20px', height: '20px', borderRadius: '50%', background: color, border: '2px solid rgba(255,255,255,0.1)' }} />
            ))}
          </div>
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px' }}>
          <strong style={{ color: 'var(--text-main)' }}>Layout:</strong> {rationale.layoutDescription}
        </div>
      </div>

      {/* Decision Trace */}
      <div>
        <button
          onClick={() => setShowDecisions(!showDecisions)}
          style={{
            background: 'none', border: 'none', cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'space-between', width: '100%',
            padding: '8px 0', color: 'var(--text-main)'
          }}
        >
          <span style={{ fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Layers size={15} style={{ color: 'var(--color-primary-light)' }} />
            Decision Trace ({rationale.decisions.length} rules fired)
          </span>
          {showDecisions ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showDecisions && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }} className="animate-fade-in">
            {rationale.decisions.map((dec, i) => (
              <div key={i} style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border-light)',
                borderRadius: '8px',
                padding: '10px 12px',
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                gap: '8px',
                alignItems: 'start'
              }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>{dec.decision}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{
                      fontSize: '10px',
                      background: 'rgba(139,92,246,0.12)',
                      color: 'var(--color-primary-light)',
                      border: '1px solid rgba(139,92,246,0.2)',
                      padding: '1px 6px',
                      borderRadius: '9999px',
                      fontWeight: 600
                    }}>
                      {dec.ruleSource}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{dec.rule}</span>
                  </div>
                </div>
                <ConfidencePip confidence={dec.confidence} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Hanlon's Razor Reframe */}
      {rationale.hanlonReframe && (
        <div style={{
          background: 'rgba(245, 158, 11, 0.06)',
          border: '1px solid rgba(245, 158, 11, 0.2)',
          borderRadius: '10px',
          padding: '12px 14px',
          display: 'flex',
          gap: '10px',
          alignItems: 'flex-start'
        }}>
          <span style={{ fontSize: '20px', flexShrink: 0 }}>🪒</span>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#f59e0b', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Hanlon's Razor Reframe Fired</div>
            <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5 }}>{rationale.hanlonReframe}</p>
          </div>
        </div>
      )}

      {/* Competitor Gap */}
      <div style={{
        background: 'rgba(6, 182, 212, 0.06)',
        border: '1px solid rgba(6, 182, 212, 0.2)',
        borderRadius: '10px',
        padding: '12px 14px'
      }}>
        <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-secondary)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Market Signal / Competitor Gap Exploited</div>
        <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5 }}>{rationale.competitorGap}</p>
      </div>

      {/* Suggested Iterations */}
      <div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>Suggested Next Iterations</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {rationale.suggestedIterations.map((iter, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4
            }}>
              <span style={{
                width: '18px', height: '18px', borderRadius: '50%',
                background: 'rgba(139,92,246,0.15)', color: 'var(--color-primary-light)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '10px', fontWeight: 700, flexShrink: 0
              }}>{i + 1}</span>
              {iter}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
