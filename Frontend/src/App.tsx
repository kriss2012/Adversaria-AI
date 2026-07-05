import React, { useState, useCallback, useRef, useEffect } from 'react';
import './index.css';
import { BriefForm, BriefData } from './components/BriefForm';
import { AgentVisualizer, AgentLog } from './components/AgentVisualizer';
import { DebatePanel, DebateRound } from './components/DebatePanel';
import { EvalDashboard, EvalScores, HistoricalEntry } from './components/EvalDashboard';
import { RationalePanel, RationaleTrace } from './components/RationalePanel';
import { runAgentSimulation } from './agentEngine';
import { Sparkles, Bot, Scale, BarChart3, GitBranch, Key, Activity, Settings, LayoutDashboard, User } from 'lucide-react';

type Tab = 'pipeline' | 'debate' | 'eval' | 'rationale';
const TABS = [
  { id: 'pipeline', label: 'Agent Pipeline', icon: <Bot size={16} /> },
  { id: 'debate', label: 'Critique Panel', icon: <Scale size={16} /> },
  { id: 'eval', label: 'Eval Harness', icon: <BarChart3 size={16} /> },
  { id: 'rationale', label: 'XDR Trace', icon: <GitBranch size={16} /> },
];

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
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
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

    try {
      await runAgentSimulation(data, (step) => {
        if (abortRef.current) return;
        if (step.error) setErrorMsg(step.error);
        if (step.logEntry) setLogs(prev => [...prev, step.logEntry!]);
        if (step.activeAgent !== undefined) setActiveAgentId(step.activeAgent);
        if (step.spawnedAgents) setSpawnedAgents(step.spawnedAgents);
        if (step.debateRound) setDebateRound(step.debateRound);
        if (step.evalScores) setEvalScores(step.evalScores);
        if (step.rationale) setRationale(step.rationale);
        if (step.historyEntry) setHistory(prev => [step.historyEntry!, ...prev]);
        if (step.generatedImageUrl) setGeneratedImage(step.generatedImageUrl);
      });
    } finally {
      if (!abortRef.current) {
        setIsGenerating(false);
        setActiveAgentId(null);
      }
    }
  }, []);

  return (
    <div className="voyage-layout">
      {/* ─── SIDEBAR ─────────────────────────────────────────────────── */}
      <aside className="voyage-sidebar">
        <div className="voyage-logo">
          <Sparkles size={20} color="var(--accent-color)" />
          Adversaria AI
        </div>
        
        <nav className="voyage-nav">
          <a href="#" className="voyage-nav-item active">
            <LayoutDashboard size={18} /> Dashboard
          </a>
          <a href="#" className="voyage-nav-item">
            <Activity size={18} /> Runs
          </a>
          <a href="#" className="voyage-nav-item">
            <Key size={18} /> API Keys
          </a>
          <a href="#" className="voyage-nav-item">
            <Settings size={18} /> Settings
          </a>
          <div style={{ marginTop: 'auto' }}></div>
          <a href="#" className="voyage-nav-item">
            <User size={18} /> Profile
          </a>
        </nav>
      </aside>

      {/* ─── MAIN CONTENT ────────────────────────────────────────────── */}
      <main className="voyage-main">
        {/* Header */}
        <header className="voyage-header">
          <div className="flex items-center gap-2 text-sm text-muted">
            <span className={`status-dot ${isGenerating ? 'active' : 'idle'}`}></span>
            {isGenerating ? 'Pipeline Running...' : 'System Idle'}
          </div>
        </header>

        {/* Content */}
        <div className="voyage-content">
          <h1 className="voyage-page-title">Creative Generation</h1>
          <p className="voyage-page-subtitle">Configure your brief and trigger the adversarial multi-agent pipeline.</p>

          <div className="dashboard-grid">
            {/* Left Column: Form */}
            <div className="flex flex-col gap-4">
              <div className="voyage-card">
                <BriefForm onSubmit={handleSubmit} isGenerating={isGenerating} />
              </div>

              {errorMsg && (
                <div style={{ padding: '16px', background: '#fef2f2', color: '#b91c1c', borderRadius: '8px', border: '1px solid #f87171' }}>
                  <p className="text-sm font-semibold mb-1">Pipeline Error</p>
                  <p className="text-sm">{errorMsg}</p>
                </div>
              )}
            </div>

            {/* Right Column: Results & Visualizer */}
            <div className="flex flex-col gap-4">
              {generatedImage && (
                <div className="voyage-card mb-4" style={{ padding: '0', overflow: 'hidden' }}>
                  <img src={generatedImage} alt="Generated Concept" style={{ width: '100%', height: 'auto', display: 'block' }} />
                </div>
              )}

              <div className="voyage-card" style={{ padding: '0', overflow: 'hidden' }}>
                <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', background: '#f9fafb' }}>
                  {TABS.map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as Tab)}
                      style={{
                        padding: '12px 16px',
                        background: 'transparent',
                        border: 'none',
                        borderBottom: activeTab === tab.id ? '2px solid var(--accent-color)' : '2px solid transparent',
                        color: activeTab === tab.id ? 'var(--text-main)' : 'var(--text-muted)',
                        fontWeight: activeTab === tab.id ? 600 : 500,
                        fontSize: '14px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        transition: 'all 0.2s'
                      }}
                    >
                      {tab.icon}
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div style={{ padding: '24px', minHeight: '400px', maxHeight: '600px', overflowY: 'auto' }}>
                  {activeTab === 'pipeline' && (
                    <AgentVisualizer logs={logs} activeAgentId={activeAgentId} spawnedAgents={spawnedAgents} />
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
        </div>
      </main>
    </div>
  );
}

export default App;
