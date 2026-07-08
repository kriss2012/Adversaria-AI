import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Info, Sparkles, X } from 'lucide-react';
import type { BriefData } from '../types';

interface BriefFormProps {
  onSubmit: (data: BriefData) => void;
  isGenerating: boolean;
}

export const BriefForm: React.FC<BriefFormProps> = ({ onSubmit, isGenerating }) => {
  const [brandName, setBrandName]           = useState('AuraFit - Gym Wear');
  const [platform, setPlatform]             = useState('Instagram Feed Post (1:1)');
  const [tone, setTone]                     = useState('Energetic & Futuristic');
  const [prompt, setPrompt]                 = useState(
    'Act like my senior designer and creative director. Create high-converting design concepts for Instagram, LinkedIn, and ads.'
  );
  const [uploadedFiles, setUploadedFiles]   = useState<string[]>([
    'aurafit_brand_book.pdf',
    'logo_violet_neon.svg',
  ]);
  const [dragActive, setDragActive]         = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ brandName, platform, tone, files: uploadedFiles, prompt });
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.length) {
      setUploadedFiles(prev => [...prev, ...Array.from(e.dataTransfer.files).map(f => f.name)]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setUploadedFiles(prev => [...prev, ...Array.from(e.target.files!).map(f => f.name)]);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* Form Title */}
      <div>
        <div className="voyage-card-title" style={{ marginBottom: '4px' }}>
          <Sparkles size={15} style={{ color: 'var(--color-primary-light)' }} />
          Creative Brief
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
          Define the creative guidelines and targets for Adversaria's multi-agent panel.
        </p>
      </div>

      {/* Brand Persona */}
      <div>
        <label className="voyage-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          Brand Persona
          <span style={{
            fontSize: '11px',
            color: 'var(--color-primary-light)',
            cursor: 'pointer',
            fontWeight: 600,
            background: 'var(--color-primary-dim)',
            padding: '2px 8px',
            borderRadius: '4px',
          }}>
            + New Brand
          </span>
        </label>
        <select
          id="brief-brand"
          className="voyage-input"
          value={brandName}
          onChange={e => setBrandName(e.target.value)}
          disabled={isGenerating}
        >
          <option value="AuraFit - Gym Wear">AuraFit — Gym Wear (Youth, Neon Purple)</option>
          <option value="KiriApp - Tech Recruiting">KiriApp — Tech Recruiting (Minimalist Indigo)</option>
          <option value="Solaria - Green Energy">Solaria — Eco Solar Tech (Clean Green & Gold)</option>
        </select>
      </div>

      {/* Platform + Tone row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div>
          <label className="voyage-label">Target Platform</label>
          <select
            id="brief-platform"
            className="voyage-input"
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            disabled={isGenerating}
          >
            <option value="Instagram Feed Post (1:1)">Instagram Feed (1:1)</option>
            <option value="LinkedIn Single Image (4:5)">LinkedIn (4:5)</option>
            <option value="Banner Ad (16:9)">Banner Ad (16:9)</option>
          </select>
        </div>
        <div>
          <label className="voyage-label">Tone Profile</label>
          <select
            id="brief-tone"
            className="voyage-input"
            value={tone}
            onChange={e => setTone(e.target.value)}
            disabled={isGenerating}
          >
            <option value="Energetic & Futuristic">Energetic & Bold</option>
            <option value="Minimalist & Authoritative">Minimalist & Clean</option>
            <option value="Warm & Trustworthy">Warm & Trustworthy</option>
          </select>
        </div>
      </div>

      {/* Brand Assets Upload */}
      <div>
        <label className="voyage-label" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          Brand Assets & Guidelines
          <span title="Upload logo SVG, PDF guidelines, or moodboards to ground the Brand-Purist agent">
            <Info size={12} style={{ color: 'var(--text-dark)', cursor: 'help' }} />
          </span>
        </label>

        {/* Drop zone */}
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `1.5px dashed ${dragActive ? 'var(--color-primary-light)' : 'var(--border-medium)'}`,
            background: dragActive ? 'var(--color-primary-dim)' : 'var(--bg-input)',
            borderRadius: 'var(--radius-md)',
            padding: '16px 12px',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            style={{ display: 'none' }}
          />
          <UploadCloud size={22} style={{ color: dragActive ? 'var(--color-primary-light)' : 'var(--text-dark)', margin: '0 auto 6px', display: 'block' }} />
          <p style={{ fontSize: '12.5px', color: 'var(--text-sub)' }}>
            Drop files or{' '}
            <span style={{ color: 'var(--color-primary-light)', fontWeight: 600 }}>browse</span>
          </p>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
            PDF, SVG, PNG, JSON — max 15 MB
          </p>
        </div>

        {/* File chips */}
        {uploadedFiles.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
            {uploadedFiles.map((fileName, idx) => (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-light)',
                  borderRadius: '6px',
                  padding: '3px 8px 3px 6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  fontSize: '11.5px',
                  color: 'var(--text-sub)',
                }}
              >
                <FileText size={11} style={{ color: 'var(--color-primary-light)', flexShrink: 0 }} />
                <span style={{ maxWidth: '110px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={fileName}>
                  {fileName}
                </span>
                <button
                  type="button"
                  onClick={e => { e.stopPropagation(); removeFile(idx); }}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-dark)', padding: '0 0 0 2px',
                    display: 'flex', alignItems: 'center',
                  }}
                >
                  <X size={10} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Creative Prompt */}
      <div>
        <label className="voyage-label">Creative Concept Prompt</label>
        <textarea
          id="brief-prompt"
          className="voyage-input"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          disabled={isGenerating}
          rows={4}
          style={{ resize: 'vertical', minHeight: '90px', lineHeight: 1.55 }}
          placeholder="E.g., Design a high-impact product ad showing our new neon jacket with bold futuristic text..."
        />
      </div>

      {/* Submit */}
      <button
        id="brief-submit-btn"
        type="submit"
        className="voyage-button"
        disabled={isGenerating || !prompt.trim()}
        style={{ width: '100%', padding: '12px' }}
      >
        {isGenerating ? (
          <>
            <span
              style={{
                display: 'inline-block',
                width: '14px',
                height: '14px',
                border: '2px solid rgba(255,255,255,0.3)',
                borderTopColor: 'white',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }}
            />
            Executing Pipeline...
          </>
        ) : (
          <>
            <Play size={15} />
            Synthesize Design Concept
          </>
        )}
      </button>
    </form>
  );
};

// local Play icon (avoid extra import warning)
function Play({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}
