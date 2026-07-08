import React, { useState } from 'react';
import { ChevronDown, ChevronUp, GitBranch, FileText, Layers } from 'lucide-react';
import type { RationaleTrace } from '../types';

interface RationalePanelProps {
  rationale: RationaleTrace | null;
}

/* ─── Confidence Pips ─────────────────────────────────────────────────────── */
const ConfidencePip: React.FC<{ confidence: number }> = ({ confidence }) => {
  const filled = Math.round((confidence / 100) * 5);
  return (
    <div style={{ display: 'flex', gap: '3px', alignItems: 'center', flexShrink: 0 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} style={{
          width:        '5px',
          height:       '5px',
          borderRadius: '50%',
          background:   i < filled ? 'var(--color-primary-light)' : 'var(--bg-input)',
          border:       i < filled ? 'none' : '1px solid var(--border-light)',
        }} />
      ))}
      <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '4px' }}>{confidence}%</span>
    </div>
  );
};

/* ─── Main ─────────────────────────────────────────────────────────────────── */
export const RationalePanel: React.FC<RationalePanelProps> = ({ rationale }) => {
  const [showDecisions, setShowDecisions] = useState(true);

  if (!rationale) {
    return (
      <div className="empty-state">
        <FileText size={32} />
        <p style={{ fontSize: '13.5px' }}>
          Explainable Design Rationale (XDR) trace will appear here after generation.
        </p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div>
        <h3 style={{ fontSize: '15px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
          <GitBranch size={16} style={{ color: '#a78bfa' }} />
          Explainable Design Rationale (XDR)
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '12.5px', marginTop: '3px', lineHeight: 1.5 }}>
          Full audit trail: which rule drove which decision. Enterprise-ready for legal & compliance review.
        </p>
      </div>

      {/* Concept Preview Card */}
      <div style={{
        background:    'linear-gradient(135deg, rgba(124,58,237,0.1), rgba(6,182,212,0.05))',
        border:        '1px solid rgba(124,58,237,0.2)',
        borderRadius:  'var(--radius-lg)',
        padding:       '16px',
        display:       'flex',
        flexDirection: 'column',
        gap:           '10px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: '10.5px', color: 'var(--color-primary-light)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              {rationale.platform}
            </div>
            <h4 style={{
              fontSize:           '20px',
              fontWeight:         800,
              letterSpacing:      '-0.025em',
              marginTop:          '4px',
              background:         'linear-gradient(135deg, white, #c4b5fd)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              lineHeight:         1.2,
            }}>
              {rationale.headline}
            </h4>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>{rationale.tagline}</p>
          </div>
          {/* Color Palette */}
          <div style={{ display: 'flex', gap: '5px', flexShrink: 0, alignItems: 'flex-start', marginTop: '4px' }}>
            {rationale.colorPalette.map((color, i) => (
              <div key={i} title={color} style={{
                width:        '18px',
                height:       '18px',
                borderRadius: '50%',
                background:   color,
                border:       '2px solid rgba(255,255,255,0.12)',
                flexShrink:   0,
              }} />
            ))}
          </div>
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px', lineHeight: 1.5 }}>
          <strong style={{ color: 'var(--text-sub)', fontWeight: 600 }}>Layout: </strong>
          {rationale.layoutDescription}
        </div>
      </div>

      {/* Decision Trace */}
      <div>
        <button
          onClick={() => setShowDecisions(!showDecisions)}
          style={{
            background:     'none',
            border:         'none',
            cursor:         'pointer',
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'space-between',
            width:          '100%',
            padding:        '8px 0',
            color:          'var(--text-main)',
            fontFamily:     'var(--font-sans)',
          }}
        >
          <span style={{ fontSize: '13.5px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '7px', color: 'var(--text-sub)' }}>
            <Layers size={14} style={{ color: 'var(--color-primary-light)' }} />
            Decision Trace ({rationale.decisions.length} rules fired)
          </span>
          {showDecisions ? <ChevronUp size={15} style={{ color: 'var(--text-muted)' }} /> : <ChevronDown size={15} style={{ color: 'var(--text-muted)' }} />}
        </button>

        {showDecisions && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '7px', marginTop: '8px' }}>
            {rationale.decisions.map((dec, i) => (
              <div key={i} style={{
                background:   'var(--bg-elevated)',
                border:       '1px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
                padding:      '10px 12px',
                display:      'grid',
                gridTemplateColumns: '1fr auto',
                gap:          '10px',
                alignItems:   'start',
              }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-main)', marginBottom: '5px' }}>{dec.decision}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    <span style={{
                      fontSize:     '10px',
                      background:   'var(--color-primary-dim)',
                      color:        'var(--color-primary-light)',
                      border:       '1px solid rgba(124,58,237,0.2)',
                      padding:      '1px 7px',
                      borderRadius: '9999px',
                      fontWeight:   700,
                    }}>
                      {dec.ruleSource}
                    </span>
                    <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>{dec.rule}</span>
                  </div>
                </div>
                <ConfidencePip confidence={dec.confidence} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Hanlon's Razor */}
      {rationale.hanlonReframe && (
        <div style={{
          background:   'rgba(245, 158, 11, 0.05)',
          border:       '1px solid rgba(245, 158, 11, 0.18)',
          borderRadius: 'var(--radius-md)',
          padding:      '12px 14px',
          display:      'flex',
          gap:          '10px',
          alignItems:   'flex-start',
        }}>
          <span style={{ fontSize: '18px', flexShrink: 0, lineHeight: 1.2 }}>🪒</span>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#f59e0b', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Hanlon's Razor Reframe Fired
            </div>
            <p style={{ fontSize: '12.5px', color: 'var(--text-sub)', lineHeight: 1.55 }}>{rationale.hanlonReframe}</p>
          </div>
        </div>
      )}

      {/* Competitor Gap */}
      <div style={{
        background:   'var(--color-secondary-dim)',
        border:       '1px solid rgba(6, 182, 212, 0.18)',
        borderRadius: 'var(--radius-md)',
        padding:      '12px 14px',
      }}>
        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-secondary)', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Market Signal / Competitor Gap Exploited
        </div>
        <p style={{ fontSize: '12.5px', color: 'var(--text-sub)', lineHeight: 1.55 }}>{rationale.competitorGap}</p>
      </div>

      {/* Suggested Iterations */}
      <div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-sub)', marginBottom: '10px' }}>
          Suggested Next Iterations
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
          {rationale.suggestedIterations.map((iter, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '9px', fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              <span style={{
                width:          '18px',
                height:         '18px',
                borderRadius:   '50%',
                background:     'var(--color-primary-dim)',
                color:          'var(--color-primary-light)',
                display:        'flex',
                alignItems:     'center',
                justifyContent: 'center',
                fontSize:       '10px',
                fontWeight:     800,
                flexShrink:     0,
                marginTop:      '1px',
              }}>
                {i + 1}
              </span>
              {iter}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
