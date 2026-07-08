import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Sparkles, Mail, Lock, ArrowRight, Eye, EyeOff } from 'lucide-react';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('test@adversaria.ai');
  const [password, setPassword] = useState('password123');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);

  if (localStorage.getItem('auth') === 'true') {
    return <Navigate to="/dashboard" replace />;
  }

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      localStorage.setItem('auth', 'true');
      navigate('/dashboard');
    }, 600);
  };

  return (
    <div className="login-page">
      <div className="login-card animate-fade-in">
        {/* Brand Mark */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '36px' }}>
          <div style={{
            width: '52px',
            height: '52px',
            borderRadius: '14px',
            background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '16px',
            boxShadow: '0 0 30px rgba(124, 58, 237, 0.35)',
          }}>
            <Sparkles size={24} color="white" />
          </div>
          <h1 style={{
            fontSize: '24px',
            fontWeight: '800',
            color: 'var(--text-main)',
            letterSpacing: '-0.03em',
            marginBottom: '6px',
          }}>
            Adversaria AI
          </h1>
          <p style={{ fontSize: '13.5px', color: 'var(--text-muted)' }}>
            Sign in to access your creative studio
          </p>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Email */}
          <div>
            <label className="voyage-label">Email Address</label>
            <div style={{ position: 'relative' }}>
              <Mail
                size={15}
                style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dark)' }}
              />
              <input
                type="email"
                id="login-email"
                className="voyage-input"
                style={{ paddingLeft: '36px' }}
                placeholder="you@company.com"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="voyage-label">Password</label>
            <div style={{ position: 'relative' }}>
              <Lock
                size={15}
                style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dark)' }}
              />
              <input
                type={showPass ? 'text' : 'password'}
                id="login-password"
                className="voyage-input"
                style={{ paddingLeft: '36px', paddingRight: '36px' }}
                placeholder="••••••••"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                style={{
                  position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--text-dark)', padding: '2px',
                }}
              >
                {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            id="login-submit-btn"
            type="submit"
            className="voyage-button"
            disabled={loading}
            style={{ width: '100%', marginTop: '4px', padding: '12px' }}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="animate-spin" style={{ display: 'inline-block', width: '14px', height: '14px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%' }} />
                Authenticating...
              </span>
            ) : (
              <>
                Sign In <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        <p style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-dark)', marginTop: '24px' }}>
          Demo credentials pre-filled · No real auth required
        </p>
      </div>
    </div>
  );
};
