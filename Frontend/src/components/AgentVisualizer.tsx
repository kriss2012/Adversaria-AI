import React from 'react';
import { Bot, Sparkles, Brain, ShieldCheck, Cpu, Layers, RefreshCw } from 'lucide-react';
import type { AgentLog } from '../types';

interface AgentVisualizerProps {
  logs:          AgentLog[];
  activeAgentId: string | null;
  spawnedAgents: string[];
}

/* ─── Agent Node ──────────────────────────────────────────────────────────────── */
const AgentNode: React.FC<{
  label:       string;
  sublabel:    string;
  isActive:    boolean;
  icon:        React.ReactNode;
  activeColor: string;
}> = ({ label, sublabel, isActive, icon, activeColor }) => (
  <div style={{ zIndex: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', width: '110px' }}>
    <div
      className={isActive ? 'active-pulse' : ''}
      style={{
        width:        '52px',
        height:       '52px',
        borderRadius: '50%',
        background:   isActive ? activeColor : 'var(--bg-input)',
        border:       isActive ? '2px solid rgba(255,255,255,0.3)' : '1px solid var(--border-light)',
        display:      'flex',
        alignItems:   'center',
        justifyContent: 'center',
        transition:   'all 0.3s ease',
        boxShadow:    isActive ? `0 0 16px ${activeColor}66` : 'none',
      }}
    >
      {icon}
    </div>
    <span style={{ fontSize: '11.5px', fontWeight: 600, textAlign: 'center', color: 'var(--text-sub)' }}>{label}</span>
    <span style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '-4px' }}>{sublabel}</span>
  </div>
);

/* ─── Main Component ──────────────────────────────────────────────────────────── */
export const AgentVisualizer: React.FC<AgentVisualizerProps> = ({
  logs, activeAgentId, spawnedAgents,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', minHeight: '380px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
            <Cpu size={16} style={{ color: 'var(--color-primary-light)' }} />
            Dynamic Agent Execution Graph
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '12.5px', marginTop: '3px' }}>
            Creative Director spawns specialists and monitors the adversarial critique panel.
          </p>
        </div>
        {/* Spawned agent badges */}
        {spawnedAgents.length > 0 && (
          <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', justifyContent: 'flex-end', maxWidth: '200px' }}>
            {spawnedAgents.map(agent => (
              <span
                key={agent}
                style={{
                  fontSize: '10.5px',
                  background: 'var(--color-secondary-dim)',
                  border: '1px solid rgba(6, 182, 212, 0.2)',
                  color: 'var(--color-secondary)',
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <span style={{ width: '4px', height: '4px', background: 'var(--color-secondary)', borderRadius: '50%' }} />
                {agent}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Interactive Graph */}
      <div style={{
        display:         'flex',
        justifyContent:  'space-around',
        alignItems:      'center',
        position:        'relative',
        padding:         '20px 16px',
        background:      'var(--bg-elevated)',
        borderRadius:    'var(--radius-lg)',
        border:          '1px solid var(--border-light)',
        minHeight:       '140px',
      }}>
        {/* Connector line */}
        <div style={{
          position:   'absolute',
          top:        '50%',
          left:       '12%',
          right:      '12%',
          height:     '1px',
          background: 'linear-gradient(to right, var(--color-primary), var(--color-secondary), var(--color-primary))',
          opacity:    0.25,
          zIndex:     1,
        }} />

        {/* Director node */}
        <AgentNode
          label="Director"
          sublabel="Orchestrator"
          isActive={activeAgentId === 'director'}
          icon={<Brain size={24} style={{ color: activeAgentId === 'director' ? 'white' : 'var(--color-primary-light)' }} />}
          activeColor="var(--color-primary)"
        />

        <div style={{ color: 'var(--text-dark)', zIndex: 2, fontSize: '16px', userSelect: 'none' }}>→</div>

        {/* Designer node */}
        <AgentNode
          label="Senior Designer"
          sublabel="Generator"
          isActive={activeAgentId === 'designer'}
          icon={<Sparkles size={24} style={{ color: activeAgentId === 'designer' ? 'white' : 'var(--color-secondary)' }} />}
          activeColor="var(--color-secondary)"
        />

        <div style={{ color: 'var(--text-dark)', zIndex: 2, fontSize: '16px', userSelect: 'none' }}>→</div>

        {/* Critics cluster */}
        <div style={{ zIndex: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          <div style={{
            background:    'var(--bg-card)',
            border:        '1px dashed var(--border-medium)',
            borderRadius:  'var(--radius-md)',
            padding:       '8px 10px',
            display:       'flex',
            gap:           '8px',
            justifyContent: 'center',
          }}>
            {([
              { id: 'purist',   Icon: ShieldCheck, color: '#f59e0b' },
              { id: 'marketer', Icon: Cpu,         color: 'var(--color-primary-light)' },
              { id: 'novelty',  Icon: Layers,       color: 'var(--color-secondary)' },
            ] as const).map(({ id, Icon, color }) => {
              const isActive = activeAgentId === id;
              return (
                <div
                  key={id}
                  title={id}
                  style={{
                    width:           '36px',
                    height:          '36px',
                    borderRadius:    'var(--radius-sm)',
                    background:      isActive ? color : 'var(--bg-input)',
                    border:          isActive ? '1.5px solid rgba(255,255,255,0.25)' : '1px solid var(--border-light)',
                    display:         'flex',
                    alignItems:      'center',
                    justifyContent:  'center',
                    boxShadow:       isActive ? `0 0 12px ${color}80` : 'none',
                    transition:      'all 0.3s ease',
                  }}
                >
                  <Icon size={16} style={{ color: isActive ? 'white' : color }} />
                </div>
              );
            })}
          </div>
          <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--text-sub)' }}>Adversarial Panel</span>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '-4px' }}>Debate & Critique</span>
        </div>
      </div>

      {/* Terminal Log */}
      <div style={{
        flex:           1,
        background:     '#070810',
        borderRadius:   'var(--radius-md)',
        padding:        '14px',
        border:         '1px solid var(--border-light)',
        fontFamily:     'var(--font-mono)',
        fontSize:       '12px',
        overflowY:      'auto',
        maxHeight:      '260px',
        display:        'flex',
        flexDirection:  'column',
        gap:            '8px',
        boxShadow:      'inset 0 2px 10px rgba(0,0,0,0.8)',
        lineHeight:     1.5,
      }}>
        {logs.length === 0 ? (
          <div style={{
            color:          'var(--text-dark)',
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'center',
            height:         '100%',
            gap:            '8px',
            minHeight:      '80px',
          }}>
            <Bot size={20} style={{ opacity: 0.3 }} />
            <span>Idle. Submit a brief to spin up the agent pipeline…</span>
          </div>
        ) : (
          logs.map((log, index) => {
            let agentColor = '#f472b6';
            if (log.agentName.includes('Purist'))   agentColor = '#f59e0b';
            if (log.agentName.includes('Marketer'))  agentColor = '#f472b6';
            if (log.agentName.includes('Novelty'))   agentColor = '#06b6d4';
            if (log.agentName.includes('Director'))  agentColor = '#c084fc';
            if (log.agentName === 'System')          agentColor = '#10b981';

            return (
              <div
                key={index}
                className="animate-fade-in"
                style={{
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  paddingBottom: '7px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: agentColor, fontWeight: 700, fontSize: '11.5px' }}>
                    [{log.agentName}]
                    <span style={{ color: 'var(--text-dark)', fontWeight: 400 }}> ({log.role})</span>
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-dark)', flexShrink: 0 }}>{log.timestamp}</span>
                </div>
                <div style={{
                  color:     log.status === 'error' ? '#fca5a5' : 'var(--text-sub)',
                  display:   'flex',
                  alignItems: 'flex-start',
                  gap:        '6px',
                  whiteSpace: 'pre-wrap',
                }}>
                  {log.status === 'thinking' && (
                    <RefreshCw
                      size={11}
                      className="animate-spin"
                      style={{ color: 'var(--color-secondary)', flexShrink: 0, marginTop: '3px' }}
                    />
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
