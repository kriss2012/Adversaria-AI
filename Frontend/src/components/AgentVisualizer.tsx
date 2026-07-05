import React from 'react';
import { Bot, Sparkles, Brain, ShieldCheck, RefreshCw, Cpu, Layers } from 'lucide-react';
import type { AgentLog } from '../types';

interface AgentVisualizerProps {
  logs: AgentLog[];
  activeAgentId: string | null;
  spawnedAgents: string[];
}

export const AgentVisualizer: React.FC<AgentVisualizerProps> = ({
  logs,
  activeAgentId,
  spawnedAgents,
}) => {
  const agents = [
    { id: 'director', name: 'Creative Director', icon: Brain, desc: 'Synthesizes brief & critiques, spawns sub-agents' },
    { id: 'designer', name: 'Senior Designer', icon: Sparkles, desc: 'Generates UI layouts, typography & assets' },
    { id: 'purist', name: 'Brand-Purist Critic', icon: ShieldCheck, desc: 'Enforces style guides, logos & brand coherence', group: 'critics' },
    { id: 'marketer', name: 'Performance Critic', icon: Cpu, desc: 'Optimizes for CTR, readability & call-to-action', group: 'critics' },
    { id: 'novelty', name: 'Novelty Critic', icon: Layers, desc: 'Penalizes genericness & matches against history', group: 'critics' },
  ];

  return (
    <div className="glass-panel p-6 animate-fade-in" style={{ gap: '20px', minHeight: '450px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu style={{ color: 'var(--color-primary)', width: '20px', height: '20px' }} />
            Dynamic Agent Execution Graph
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
            Creative Director spawns specialists and monitors adversarial critique panel.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end', maxWidth: '220px' }}>
          {spawnedAgents.map(agent => (
            <span
              key={agent}
              style={{
                fontSize: '11px',
                background: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid rgba(6, 182, 212, 0.2)',
                color: 'var(--color-secondary)',
                padding: '2px 8px',
                borderRadius: '9999px',
                fontWeight: 500,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <span style={{ width: '4px', height: '4px', background: 'var(--color-secondary)', borderRadius: '50%' }} />
              {agent} Agent
            </span>
          ))}
        </div>
      </div>

      {/* Interactive Visual Graph */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'relative',
          padding: '20px 10px',
          background: 'rgba(255, 255, 255, 0.02)',
          borderRadius: '12px',
          border: '1px solid var(--border-light)',
          minHeight: '160px',
          overflow: 'hidden'
        }}
      >
        {/* Connector line */}
        <div style={{
          position: 'absolute', top: '50%', left: '10%', right: '10%',
          height: '2px',
          background: 'linear-gradient(to right, var(--color-primary), var(--color-secondary), var(--color-primary))',
          opacity: 0.2, zIndex: 1
        }} />

        {/* Director node */}
        <AgentNode
          id="director" label="Director" sublabel="Director Node"
          isActive={activeAgentId === 'director'}
          icon={<Brain style={{ color: activeAgentId === 'director' ? 'white' : 'var(--color-primary)', width: '26px', height: '26px' }} />}
          activeColor="var(--color-primary)"
        />

        <div style={{ color: 'var(--text-dark)', zIndex: 2, fontSize: '18px' }}>➔</div>

        {/* Designer node */}
        <AgentNode
          id="designer" label="Senior Designer" sublabel="Generator Node"
          isActive={activeAgentId === 'designer'}
          icon={<Sparkles style={{ color: activeAgentId === 'designer' ? 'white' : 'var(--color-secondary)', width: '26px', height: '26px' }} />}
          activeColor="var(--color-secondary)"
        />

        <div style={{ color: 'var(--text-dark)', zIndex: 2, fontSize: '18px' }}>➔</div>

        {/* Critics cluster */}
        <div style={{ zIndex: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', width: '180px' }}>
          <div style={{
            background: 'rgba(255,255,255,0.01)',
            border: '1px dashed var(--border-light)',
            borderRadius: '12px',
            padding: '6px 8px',
            display: 'flex',
            gap: '6px',
            justifyContent: 'center'
          }}>
            {[
              { id: 'purist', icon: ShieldCheck, color: 'var(--color-accent)' },
              { id: 'marketer', icon: Cpu, color: 'var(--color-primary)' },
              { id: 'novelty', icon: Layers, color: 'var(--color-secondary)' },
            ].map(({ id, icon: Icon, color }) => {
              const isActive = activeAgentId === id;
              return (
                <div
                  key={id}
                  title={agents.find(a => a.id === id)?.name}
                  style={{
                    width: '38px', height: '38px', borderRadius: '8px',
                    background: isActive ? color : 'var(--bg-input)',
                    border: isActive ? '2px solid white' : '1px solid var(--border-light)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: isActive ? `0 0 10px ${color}` : 'none',
                    transition: 'all 0.3s ease', cursor: 'help'
                  }}
                >
                  <Icon style={{ color: isActive ? 'white' : color, width: '18px', height: '18px' }} />
                </div>
              );
            })}
          </div>
          <span style={{ fontSize: '12px', fontWeight: 600, textAlign: 'center' }}>Adversarial Panel</span>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '-4px' }}>Debate & Critique</span>
        </div>
      </div>

      {/* Terminal Log */}
      <div style={{
        flexGrow: 1,
        background: '#06070a',
        borderRadius: '10px',
        padding: '15px',
        border: '1px solid var(--border-light)',
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        overflowY: 'auto',
        maxHeight: '260px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.8)'
      }}>
        {logs.length === 0 ? (
          <div style={{
            color: 'var(--text-dark)', display: 'flex', alignItems: 'center',
            justifyContent: 'center', height: '100%', gap: '8px'
          }}>
            <Bot style={{ opacity: 0.3 }} />
            <span>Idle. Submit a brief to spin up the agent pipeline...</span>
          </div>
        ) : (
          logs.map((log, index) => {
            let color = '#a78bfa';
            if (log.agentName.includes('Purist')) color = 'var(--color-accent)';
            if (log.agentName.includes('Marketer')) color = 'var(--color-primary-light)';
            if (log.agentName.includes('Novelty')) color = 'var(--color-secondary)';
            if (log.agentName.includes('Director')) color = '#e0a7ff';
            if (log.agentName.includes('System')) color = '#10b981';
            return (
              <div
                key={index}
                className="animate-fade-in"
                style={{
                  lineHeight: '1.4',
                  borderBottom: '1px solid rgba(255,255,255,0.02)',
                  paddingBottom: '6px',
                  display: 'flex', flexDirection: 'column', gap: '2px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color, fontWeight: 600 }}>
                    [{log.agentName}]{' '}
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 400 }}>({log.role})</span>
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-dark)' }}>{log.timestamp}</span>
                </div>
                <div style={{ color: 'var(--text-main)', marginTop: '2px', whiteSpace: 'pre-wrap', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                  {log.status === 'thinking' && (
                    <RefreshCw className="animate-spin" style={{ width: '12px', height: '12px', flexShrink: 0, marginTop: '2px', color: 'var(--color-secondary)' }} />
                  )}
                  {log.message}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

// ─── Sub-component: Agent Node ────────────────────────────────────────────────
const AgentNode: React.FC<{
  id: string; label: string; sublabel: string;
  isActive: boolean; icon: React.ReactNode; activeColor: string;
}> = ({ label, sublabel, isActive, icon, activeColor }) => (
  <div style={{ zIndex: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', width: '120px' }}>
    <div
      className={isActive ? 'active-pulse' : ''}
      style={{
        width: '56px', height: '56px', borderRadius: '50%',
        background: isActive ? activeColor : 'var(--bg-input)',
        border: isActive ? `3px solid white` : '1px solid var(--border-light)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all 0.3s ease'
      }}
    >
      {icon}
    </div>
    <span style={{ fontSize: '12px', fontWeight: 600, textAlign: 'center' }}>{label}</span>
    <span style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '-4px' }}>{sublabel}</span>
  </div>
);
