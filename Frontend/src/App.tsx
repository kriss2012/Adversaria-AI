import React, { useState, useCallback, useRef, useEffect } from 'react';
import './index.css';
import './App.css';

import { BriefForm, BriefData } from './components/BriefForm';
import { AgentVisualizer, AgentLog } from './components/AgentVisualizer';
import { DebatePanel, DebateRound } from './components/DebatePanel';
import { EvalDashboard, EvalScores, HistoricalEntry } from './components/EvalDashboard';
import { RationalePanel, RationaleTrace } from './components/RationalePanel';
import { runAgentSimulation } from './agentEngine';
import { Sparkles, Bot, Scale, BarChart3, GitBranch, ChevronRight, Github, Zap } from 'lucide-react';
import logoImg from './assets/logo.png';

// ─── TAB CONFIG ───────────────────────────────────────────────────────────────
type Tab = 'pipeline' | 'debate' | 'eval' | 'rationale';
const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'pipeline', label: 'Agent Pipeline', icon: <Bot size={15} /> },
  { id: 'debate', label: 'Critique Panel', icon: <Scale size={15} /> },
  { id: 'eval', label: 'Eval Harness', icon: <BarChart3 size={15} /> },
  { id: 'rationale', label: 'XDR Trace', icon: <GitBranch size={15} /> },
];

// ─── APP ──────────────────────────────────────────────────────────────────────
function App() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('pipeline');
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [spawnedAgents, setSpawnedAgents] = useState<string[]>([]);
  const [debateRound, setDebateRound] = useState<DebateRound | null>(null);
  const [evalScores, setEvalScores] = useState<EvalScores | null>(null);
  const [rationale, setRationale] = useState<RationaleTrace | null>(null);
  const [history, setHistory] = useState<HistoricalEntry[]>([]);
  const abortRef = useRef(false);

  const handleSubmit = useCallback(async (data: BriefData) => {
    abortRef.current = false;
    setIsGenerating(true);
    setLogs([]);
    setActiveAgentId(null);
    setSpawnedAgents([]);
    setDebateRound(null);
    setEvalScores(null);
    setRationale(null);
    setActiveTab('pipeline');

    try {
      await runAgentSimulation(data, (step) => {
        if (abortRef.current) return;
        if (step.logEntry) {
          setLogs(prev => [...prev, step.logEntry!]);
        }
        if (step.activeAgent !== undefined) {
          setActiveAgentId(step.activeAgent);
        }
        if (step.spawnedAgents) {
          setSpawnedAgents(step.spawnedAgents);
        }
        if (step.debateRound) {
          setDebateRound(step.debateRound);
        }
        if (step.evalScores) {
          setEvalScores(step.evalScores);
        }
        if (step.rationale) {
          setRationale(step.rationale);
        }
        if (step.historyEntry) {
          setHistory(prev => [step.historyEntry!, ...prev]);
        }
      });
    } finally {
      if (!abortRef.current) {
        setIsGenerating(false);
        setActiveAgentId(null);
      }
    }
  }, []);

  return (
    <div className="app-container">
      {/* ─── TOPBAR ─────────────────────────────────────────────────── */}
      <header style={{
        borderBottom: '1px solid var(--border-light)',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '56px',
        background: 'rgba(7, 8, 12, 0.9)',
        backdropFilter: 'blur(12px)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Logo mark */}
          <img
            src={logoImg}
            alt="Adversaria logo"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              objectFit: 'contain',
              filter: 'drop-shadow(0 0 6px rgba(139,92,246,0.4))'
            }}
          />
          <div>
            <span style={{ fontSize: '16px', fontWeight: 800, letterSpacing: '-0.03em' }}>Adversaria</span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '8px' }}>Adversarial Multi-Agent Creative Engine</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Status Indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <div style={{
              width: '7px', height: '7px', borderRadius: '50%',
              background: isGenerating ? 'var(--color-primary)' : '#10b981',
              boxShadow: isGenerating ? '0 0 8px var(--color-primary)' : '0 0 8px #10b981',
              animation: isGenerating ? 'none' : undefined
            }} />
            {isGenerating ? 'Pipeline Running' : 'Idle — Ready'}
          </div>
          
          {/* Pipeline legend */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', borderLeft: '1px solid var(--border-light)', paddingLeft: '12px' }}>
            {[
              { label: 'Director', color: 'var(--color-primary)' },
              { label: 'Designer', color: 'var(--color-secondary)' },
              { label: 'Critics', color: 'var(--color-accent)' },
            ].map(item => (
              <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: item.color }} />
                {item.label}
              </div>
            ))}
          </div>

          <a
            href="https://github.com"
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border-light)',
              color: 'var(--text-muted)',
              borderRadius: '8px',
              padding: '5px 10px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              textDecoration: 'none',
              transition: 'all 0.2s'
            }}
          >
            <Github size={14} />
            GitHub
          </a>
        </div>
      </header>

      {/* ─── HERO BANNER ────────────────────────────────────────────── */}
      <div style={{
        padding: '32px 24px 24px',
        maxWidth: '1600px',
        width: '100%',
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '11px',
            background: 'rgba(139, 92, 246, 0.12)',
            color: 'var(--color-primary-light)',
            border: '1px solid rgba(139, 92, 246, 0.25)',
            padding: '2px 10px',
            borderRadius: '9999px',
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase'
          }}>
            v1.0 — Research Preview
          </span>
          <span style={{
            fontSize: '11px',
            background: 'rgba(16, 185, 129, 0.1)',
            color: '#10b981',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            padding: '2px 10px',
            borderRadius: '9999px',
            fontWeight: 600,
          }}>
            <Zap size={10} style={{ display: 'inline', marginRight: '4px' }} />
            Multi-Agent Debate Panel Active
          </span>
        </div>
        <h1 style={{ fontSize: '28px', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.2, marginTop: '4px' }}>
          Adversarial Creative Intelligence Platform
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '720px', lineHeight: 1.6 }}>
          Not just another wrapper. An agentic pipeline with a <strong style={{ color: 'var(--text-main)' }}>debate-then-synthesize</strong> critic architecture, 
          dynamic agent spawning, explainable design rationale (XDR), and a built-in eval harness that scores every concept on{' '}
          <span style={{ color: '#a78bfa' }}>brand fit</span>, <span style={{ color: '#06b6d4' }}>novelty</span>, and{' '}
          <span style={{ color: '#10b981' }}>predicted performance</span>.
        </p>
      </div>

      {/* ─── MAIN LAYOUT ────────────────────────────────────────────── */}
      <div className="dashboard-grid" style={{ paddingTop: 0 }}>
        {/* LEFT: Brief Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <BriefForm onSubmit={handleSubmit} isGenerating={isGenerating} />

          {/* Architecture notes card */}
          <div className="glass-panel p-4" style={{ fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontWeight: 700, fontSize: '13px', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sparkles size={14} style={{ color: 'var(--color-primary-light)' }} />
              What's Novel Here
            </div>
            {[
              { label: 'Adversarial Debate', desc: '3 critics argue before a verdict — not a single guard', color: 'var(--color-accent)' },
              { label: 'Dynamic Spawning', desc: 'Director spawns Market Signal + Persona Simulation agents on demand', color: 'var(--color-primary-light)' },
              { label: 'XDR Audit Trail', desc: 'Every layout decision is linked to a brand rule + confidence score', color: '#a78bfa' },
              { label: 'Eval Harness', desc: 'Auto-scores Brand Fit, Novelty & Pred. Performance — measurable, not just vibes', color: '#10b981' },
            ].map(item => (
              <div key={item.label} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                <ChevronRight size={12} style={{ color: item.color, marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <span style={{ fontWeight: 600, color: item.color }}>{item.label}:</span>{' '}
                  <span style={{ color: 'var(--text-muted)' }}>{item.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT: Tabs panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', minWidth: 0 }}>
          {/* Tab bar */}
          <div style={{
            display: 'flex',
            gap: '4px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid var(--border-light)',
            borderRadius: '10px',
            padding: '4px',
            width: 'fit-content'
          }}>
            {TABS.map(tab => {
              const hasData = (tab.id === 'debate' && debateRound) ||
                (tab.id === 'eval' && evalScores) ||
                (tab.id === 'rationale' && rationale) ||
                tab.id === 'pipeline';
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    background: activeTab === tab.id
                      ? 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(6,182,212,0.1))'
                      : 'none',
                    border: activeTab === tab.id ? '1px solid rgba(139,92,246,0.3)' : '1px solid transparent',
                    color: activeTab === tab.id ? 'var(--text-main)' : 'var(--text-muted)',
                    borderRadius: '7px',
                    padding: '7px 14px',
                    fontSize: '13px',
                    fontWeight: activeTab === tab.id ? 600 : 400,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s',
                    position: 'relative',
                    fontFamily: 'var(--font-sans)',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {tab.icon}
                  {tab.label}
                  {/* Data indicator dot */}
                  {hasData && tab.id !== 'pipeline' && (
                    <span style={{
                      width: '6px', height: '6px', borderRadius: '50%',
                      background: '#10b981',
                      position: 'absolute', top: '4px', right: '4px'
                    }} />
                  )}
                </button>
              );
            })}
          </div>

          {/* Tab content */}
          <div style={{ flexGrow: 1, minHeight: 0 }}>
            {activeTab === 'pipeline' && (
              <AgentVisualizer
                logs={logs}
                activeAgentId={activeAgentId}
                spawnedAgents={spawnedAgents}
              />
            )}
            {activeTab === 'debate' && (
              <DebatePanel round={debateRound} />
            )}
            {activeTab === 'eval' && (
              <EvalDashboard currentScores={evalScores} history={history} />
            )}
            {activeTab === 'rationale' && (
              <RationalePanel rationale={rationale} />
            )}
          </div>
        </div>
      </div>

      {/* ─── FOOTER ─────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: '1px solid var(--border-light)',
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        color: 'var(--text-dark)',
        marginTop: 'auto'
      }}>
        <div>Adversaria AI — Research Preview. Not production-ready. Scores are simulated.</div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <span>Director → Designer → Critics → Synthesis → Eval</span>
          <span style={{ color: 'var(--color-primary)', cursor: 'pointer' }}>Read the Technical Report →</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
