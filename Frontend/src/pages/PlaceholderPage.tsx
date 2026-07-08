import React from 'react';
import { Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  desc: string;
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, desc }) => {
  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="voyage-page-title">{title}</h1>
          <p className="voyage-page-subtitle">{desc}</p>
        </div>
      </div>

      <div className="voyage-card" style={{ minHeight: '400px' }}>
        <div className="placeholder-page animate-fade-in">
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '16px',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-light)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '4px',
          }}>
            <Construction size={28} style={{ color: 'var(--text-dark)' }} />
          </div>
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-sub)' }}>
            Coming Soon
          </h3>
          <p style={{ fontSize: '13.5px', color: 'var(--text-muted)', maxWidth: '340px', lineHeight: 1.6 }}>
            {desc}
          </p>
        </div>
      </div>
    </>
  );
};
