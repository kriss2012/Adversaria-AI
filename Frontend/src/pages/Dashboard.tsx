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
import {
  Bot, Scale, BarChart3, GitBranch, ImageIcon, AlertCircle,
  Sparkles, Wand2, ShieldCheck, Timer, TrendingUp, Layers3,
} from 'lucide-react';

type Tab = 'pipeline' | 'debate' | 'eval' | 'rationale';

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'pipeline',  label: 'Agent Pipeline', icon: <Bot  size={14} /> },
  { id: 'debate',    label: 'Critique Panel',  icon: <Scale size={14} /> },
  { id: 'eval',      label: 'Eval Harness',    icon: <BarChart3 size={14} /> },
  { id: 'rationale', label: 'XDR Trace',       icon: <GitBranch size={14} /> },
];

const WORKFLOW_STATS = [
  { label: 'Specialists', value: '06', icon: <Layers3 size={16} /> },
  { label: 'Brand Guards', value: '98%', icon: <ShieldCheck size={16} /> },
  { label: 'Avg. pass', value: '2.4m', icon: <Timer size={16} /> },
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

  const completion = evalScores?.overallScore ?? (isGenerating ? 48 : 0);

  return (
    <div className="studio-page">
      <section className="studio-hero">
        <div className="studio-hero-copy">
          <div className="eyebrow-pill"><Sparkles size={14} /> Adversarial creative studio</div>
          <h1 className="voyage-page-title studio-title">Build campaign-ready AI concepts with a critic loop.</h1>
          <p className="voyage-page-subtitle studio-subtitle">
            Configure a creative brief, launch specialist agents, review their debate, and ship an explainable design rationale.
          </p>
        </div>
        <div className="hero-command-card">
          <div className="hero-command-top">
            <Wand2 size={18} /> Live concept pipeline
          </div>
          <div className="hero-progress-track"><span style={{ width: `${completion}%` }} /></div>
          <div className="hero-command-meta">
            <span>{isGenerating ? 'Synthesizing and scoring concept' : 'Ready for a new brief'}</span>
            <strong>{completion}%</strong>
          </div>
        </div>
      </section>

      <div className="workflow-stat-grid">
        {WORKFLOW_STATS.map(stat => (
          <div className="workflow-stat-card" key={stat.label}>
            <div className="workflow-stat-icon">{stat.icon}</div>
            <div><strong>{stat.value}</strong><span>{stat.label}</span></div>
          </div>
        ))}
        <div className="workflow-stat-card accent">
          <div className="workflow-stat-icon"><TrendingUp size={16} /></div>
          <div><strong>{history.length}</strong><span>Runs in session</span></div>
        </div>
      </div>

      {errorMsg && (
        <div className="error-banner animate-fade-in" style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
            <AlertCircle size={16} style={{ color: '#ef4444', flexShrink: 0, marginTop: '1px' }} />
            <div><p style={{ fontSize: '13px', fontWeight: 600, marginBottom: '2px' }}>Pipeline Error</p><p style={{ fontSize: '12.5px', opacity: 0.85 }}>{errorMsg}</p></div>
          </div>
        </div>
      )}

      <div className="dashboard-grid studio-grid">
        <div className="studio-left-rail"><div className="voyage-card brief-card"><BriefForm onSubmit={handleSubmit} isGenerating={isGenerating} /></div></div>
        <div className="studio-results-stack">
          {generatedImage && (
            <div className="voyage-card generated-card animate-fade-in">
              <div className="generated-card-header"><ImageIcon size={14} /> Generated Concept</div>
              <img src={generatedImage} alt="Generated creative concept" />
            </div>
          )}
          <div className="voyage-card results-card">
            <div className="tab-bar">
              {TABS.map(tab => <button key={tab.id} id={`tab-${tab.id}`} className={`tab-btn${activeTab === tab.id ? ' active' : ''}`} onClick={() => setActiveTab(tab.id)}>{tab.icon}{tab.label}</button>)}
            </div>
            <div className="results-panel-body">
              {activeTab === 'pipeline' && <AgentVisualizer logs={logs} activeAgentId={activeAgentId} spawnedAgents={spawnedAgents} />}
              {activeTab === 'debate' && <DebatePanel round={debateRound} />}
              {activeTab === 'eval' && <EvalDashboard currentScores={evalScores} history={history} />}
              {activeTab === 'rationale' && <RationalePanel rationale={rationale} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
