import React, { useState, useCallback, useRef } from 'react';
import { BriefForm } from '../components/BriefForm';
import { AgentVisualizer } from '../components/AgentVisualizer';
import { DebatePanel } from '../components/DebatePanel';
import { EvalDashboard } from '../components/EvalDashboard';
import { RationalePanel } from '../components/RationalePanel';
import type {
  AgentLog, DebateRound, EvalScores,
  HistoricalEntry, RationaleTrace, BriefData,
} from '../types';
import { runAgentSimulation } from '../agentEngine';
import { Bot, Scale, BarChart3, GitBranch, ImageIcon, AlertCircle } from 'lucide-react';

type Tab = 'pipeline' | 'debate' | 'eval' | 'rationale';

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'pipeline',  label: 'Agent Pipeline', icon: <Bot  size={14} /> },
  { id: 'debate',    label: 'Critique Panel',  icon: <Scale size={14} /> },
  { id: 'eval',      label: 'Eval Harness',    icon: <BarChart3 size={14} /> },
  { id: 'rationale', label: 'XDR Trace',       icon: <GitBranch size={14} /> },
];

export default function Dashboard() {
  const [isGenerating, setIsGenerating]       = useState(false);
  const [activeTab, setActiveTab]             = useState<Tab>('pipeline');
  const [logs, setLogs]                       = useState<AgentLog[]>([]);
  const [activeAgentId, setActiveAgentId]     = useState<string | null>(null);
  const [spawnedAgents, setSpawnedAgents]     = useState<string[]>([]);
  const [debateRound, setDebateRound]         = useState<DebateRound | null>(null);
  const [evalScores, setEvalScores]           = useState<EvalScores | null>(null);
  const [rationale, setRationale]             = useState<RationaleTrace | null>(null);
  const [history, setHistory]                 = useState<HistoricalEntry[]>([]);
  const [generatedImage, setGeneratedImage]   = useState<string | null>(null);
  const [errorMsg, setErrorMsg]               = useState<string | null>(null);

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
    setGeneratedImage(null);
    setErrorMsg(null);
    setActiveTab('pipeline');

    // Update header status indicator
    const dot   = document.getElementById('status-dot');
    const label = document.getElementById('status-label');
    const pill  = document.getElementById('pipeline-status-indicator');
    if (dot)   { dot.className   = 'status-dot active'; }
    if (label) { label.textContent = 'Pipeline Running...'; }
    if (pill)  { pill.classList.add('running'); }

    try {
      await runAgentSimulation(data, (step) => {
        if (abortRef.current) return;
        if (step.error)           setErrorMsg(step.error);
        if (step.logEntry)        setLogs(prev => [...prev, step.logEntry!]);
        if (step.activeAgent !== undefined) setActiveAgentId(step.activeAgent);
        if (step.spawnedAgents)   setSpawnedAgents(step.spawnedAgents);
        if (step.debateRound)     setDebateRound(step.debateRound);
        if (step.evalScores)      setEvalScores(step.evalScores);
        if (step.rationale)       setRationale(step.rationale);
        if (step.historyEntry)    setHistory(prev => [step.historyEntry!, ...prev]);
        if (step.generatedImageUrl) setGeneratedImage(step.generatedImageUrl);
      });
    } finally {
      if (!abortRef.current) {
        setIsGenerating(false);
        setActiveAgentId(null);
        if (dot)   { dot.className   = 'status-dot idle'; }
        if (label) { label.textContent = 'System Idle'; }
        if (pill)  { pill.classList.remove('running'); }
      }
    }
  }, []);

  return (
    <>
      {/* ─── Page Header ──────────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <h1 className="voyage-page-title">Creative Generation</h1>
          <p className="voyage-page-subtitle">
            Configure your brief and trigger the adversarial multi-agent pipeline.
          </p>
        </div>
      </div>

      {/* ─── Error Banner ─────────────────────────────────────────── */}
      {errorMsg && (
        <div className="error-banner animate-fade-in" style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
            <AlertCircle size={16} style={{ color: '#ef4444', flexShrink: 0, marginTop: '1px' }} />
            <div>
              <p style={{ fontSize: '13px', fontWeight: 600, marginBottom: '2px' }}>Pipeline Error</p>
              <p style={{ fontSize: '12.5px', opacity: 0.85 }}>{errorMsg}</p>
            </div>
          </div>
        </div>
      )}

      {/* ─── Two-column grid ──────────────────────────────────────── */}
      <div className="dashboard-grid">
        {/* LEFT: Brief Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="voyage-card">
            <BriefForm onSubmit={handleSubmit} isGenerating={isGenerating} />
          </div>
        </div>

        {/* RIGHT: Results Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Generated Image */}
          {generatedImage && (
            <div className="voyage-card animate-fade-in" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid var(--border-light)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--text-sub)',
              }}>
                <ImageIcon size={14} />
                Generated Concept
              </div>
              <img
                src={generatedImage}
                alt="Generated creative concept"
                style={{ width: '100%', height: 'auto', display: 'block' }}
              />
            </div>
          )}

          {/* Tabbed Results Panel */}
          <div className="voyage-card" style={{ padding: 0, overflow: 'hidden' }}>
            {/* Tab bar */}
            <div className="tab-bar">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  className={`tab-btn${activeTab === tab.id ? ' active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div style={{
              padding: '20px',
              minHeight: '420px',
              maxHeight: '640px',
              overflowY: 'auto',
            }}>
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
      </div>
    </>
  );
}
