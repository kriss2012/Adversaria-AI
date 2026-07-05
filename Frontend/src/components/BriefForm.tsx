import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, Play, Info, Sparkles, HelpCircle } from 'lucide-react';

interface BriefFormProps {
  onSubmit: (data: BriefData) => void;
  isGenerating: boolean;
}

export interface BriefData {
  brandName: string;
  platform: string;
  tone: string;
  files: string[];
  prompt: string;
}

export const BriefForm: React.FC<BriefFormProps> = ({ onSubmit, isGenerating }) => {
  const [brandName, setBrandName] = useState('AuraFit - Gym Wear');
  const [platform, setPlatform] = useState('Instagram Feed Post (1:1)');
  const [tone, setTone] = useState('Energetic & Futuristic');
  const [prompt, setPrompt] = useState('Act like my senior designer and creative director. Create high-converting design concepts for Instagram, LinkedIn, and ads.');
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([
    'aurafit_brand_book.pdf',
    'logo_violet_neon.svg'
  ]);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      brandName,
      platform,
      tone,
      files: uploadedFiles,
      prompt
    });
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const newFiles = Array.from(e.dataTransfer.files).map(f => f.name);
      setUploadedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const newFiles = Array.from(e.target.files).map(f => f.name);
      setUploadedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <form onSubmit={handleSubmit} className="glass-panel p-6 flex flex-col" style={{ gap: '16px', height: '100%' }}>
      <div>
        <h3 style={{ fontSize: '18px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles className="text-secondary" style={{ color: 'var(--color-secondary)', width: '20px', height: '20px' }} />
          Creative Brief Workshop
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
          Define the creative guidelines and targets for Adversaria's Agentic Panel.
        </p>
      </div>

      {/* Brand Selection */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <label style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-main)', display: 'flex', justifyContent: 'space-between' }}>
          Brand Persona
          <span style={{ fontSize: '11px', color: 'var(--color-primary-light)', cursor: 'pointer' }}>+ New Brand</span>
        </label>
        <select 
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
          disabled={isGenerating}
          style={{
            background: 'var(--bg-input)',
            border: '1px solid var(--border-light)',
            color: 'var(--text-main)',
            borderRadius: '8px',
            padding: '10px',
            fontSize: '14px',
            outline: 'none',
            fontFamily: 'var(--font-sans)'
          }}
        >
          <option value="AuraFit - Gym Wear">AuraFit (Gym Wear, Youth, Vibrant Neon Purple)</option>
          <option value="KiriApp - Tech Recruiting">KiriApp (Tech Job Recruiting, Minimalist Indigo)</option>
          <option value="Solaria - Green Energy">Solaria (Eco Solar Tech, Clean Green & Gold)</option>
        </select>
      </div>

      {/* Format / Target Platform */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 500 }}>Target Platform</label>
          <select 
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            disabled={isGenerating}
            style={{
              background: 'var(--bg-input)',
              border: '1px solid var(--border-light)',
              color: 'var(--text-main)',
              borderRadius: '8px',
              padding: '10px',
              fontSize: '13px',
              outline: 'none'
            }}
          >
            <option value="Instagram Feed Post (1:1)">Instagram Feed (1:1)</option>
            <option value="LinkedIn Single Image (4:5)">LinkedIn (4:5)</option>
            <option value="Banner Ad (16:9)">Banner Ad (16:9)</option>
          </select>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label style={{ fontSize: '13px', fontWeight: 500 }}>Tone Profile</label>
          <select 
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            disabled={isGenerating}
            style={{
              background: 'var(--bg-input)',
              border: '1px solid var(--border-light)',
              color: 'var(--text-main)',
              borderRadius: '8px',
              padding: '10px',
              fontSize: '13px',
              outline: 'none'
            }}
          >
            <option value="Energetic & Futuristic">Energetic & Bold</option>
            <option value="Minimalist & Authoritative">Minimalist & Clean</option>
            <option value="Warm & Trustworthy">Warm & Trustworthy</option>
          </select>
        </div>
      </div>

      {/* Upload Brand Assets (Guidelines, fonts, logos, Moodboards) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <label style={{ fontSize: '13px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
          Brand Assets & Guidelines
          <Info size={13} style={{ color: 'var(--text-muted)', cursor: 'help' }} title="Upload logo SVG, PDF Guidelines, or winner moodboards to ground the Brand-Purist agent" />
        </label>
        
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: dragActive ? '2px dashed var(--color-primary)' : '1px dashed var(--border-light)',
            background: dragActive ? 'rgba(139, 92, 246, 0.05)' : 'rgba(255, 255, 255, 0.01)',
            borderRadius: '8px',
            padding: '14px',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange}
            multiple 
            style={{ display: 'none' }} 
          />
          <UploadCloud size={24} style={{ color: 'var(--text-muted)', margin: '0 auto 6px' }} />
          <p style={{ fontSize: '12px', color: 'var(--text-main)' }}>
            Drag and drop files or <span style={{ color: 'var(--color-primary-light)', fontWeight: 500 }}>Browse</span>
          </p>
          <p style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Supports PDF, SVG, PNG, JSON (Max 15MB)
          </p>
        </div>

        {/* Uploaded File List */}
        {uploadedFiles.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px', maxHeight: '72px', overflowY: 'auto' }}>
            {uploadedFiles.map((fileName, idx) => (
              <div 
                key={idx}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--border-light)',
                  borderRadius: '6px',
                  padding: '3px 8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11px'
                }}
              >
                <FileText size={12} style={{ color: 'var(--color-primary-light)' }} />
                <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '100px' }} title={fileName}>
                  {fileName}
                </span>
                <button 
                  type="button" 
                  onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '10px', marginLeft: '4px' }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Creative Prompt */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flexGrow: 1 }}>
        <label style={{ fontSize: '13px', fontWeight: 500 }}>Creative Concept Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={isGenerating}
          rows={3}
          style={{
            background: 'var(--bg-input)',
            border: '1px solid var(--border-light)',
            color: 'var(--text-main)',
            borderRadius: '8px',
            padding: '10px',
            fontSize: '13px',
            outline: 'none',
            resize: 'none',
            flexGrow: 1,
            fontFamily: 'var(--font-sans)',
            lineHeight: '1.4'
          }}
          placeholder="E.g., Design a high-impact product ad showing our new neon jacket with bold futuristic text..."
        />
      </div>

      {/* Submit Button */}
      <button 
        type="submit" 
        className="glow-btn" 
        disabled={isGenerating || !prompt}
        style={{ justifyContent: 'center', padding: '12px' }}
      >
        {isGenerating ? (
          <>
            <span className="animate-spin" style={{ marginRight: '6px' }}>⚙️</span>
            Executing Agentic Pipeline...
          </>
        ) : (
          <>
            <Play size={16} fill="white" />
            Synthesize Design Concept
          </>
        )}
      </button>
    </form>
  );
};
