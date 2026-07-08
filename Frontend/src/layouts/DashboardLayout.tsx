import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Sparkles, Key, Activity, Settings, LayoutDashboard,
  User, Menu, LogOut, ChevronRight
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/runs',      label: 'Run History', icon: Activity },
  { to: '/api-keys',  label: 'API Keys',    icon: Key },
  { to: '/settings',  label: 'Settings',    icon: Settings },
];

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Creative Dashboard',
  '/runs':      'Run History',
  '/api-keys':  'API Keys',
  '/settings':  'Settings',
  '/profile':   'Profile',
};

export const DashboardLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate  = useNavigate();
  const location  = useLocation();

  const pageTitle = PAGE_TITLES[location.pathname] ?? 'Adversaria AI';

  const handleLogout = () => {
    localStorage.removeItem('auth');
    navigate('/login');
  };

  return (
    <div className="voyage-layout">
      {/* ─── Mobile Overlay ─────────────────────────────────────── */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* ─── SIDEBAR ─────────────────────────────────────────────── */}
      <aside className={`voyage-sidebar ${sidebarOpen ? 'open' : ''}`}>
        {/* Logo */}
        <div className="sidebar-header">
          <div className="voyage-logo">
            <div className="logo-icon">
              <Sparkles size={16} color="white" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span className="logo-text">Adversaria</span>
              <span className="logo-badge">AI Studio</span>
            </div>
          </div>
        </div>

        {/* Nav Items */}
        <div className="sidebar-nav-section" style={{ flex: 1, display: 'flex', flexDirection: 'column', paddingBottom: '8px', overflowY: 'auto' }}>
          <div className="sidebar-section-label">Workspace</div>
          <nav className="voyage-nav">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `voyage-nav-item${isActive ? ' active' : ''}`}
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div style={{ marginTop: 'auto', paddingTop: '12px' }}>
            <div className="sidebar-section-label">Account</div>
            <NavLink
              to="/profile"
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) => `voyage-nav-item${isActive ? ' active' : ''}`}
            >
              <User size={16} />
              Profile
            </NavLink>
          </div>
        </div>

        {/* Footer / User Row */}
        <div className="sidebar-footer">
          <div className="sidebar-user-row" onClick={handleLogout} title="Log out">
            <div className="sidebar-avatar">T</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-name">Test User</div>
              <div className="sidebar-user-email">test@adversaria.ai</div>
            </div>
            <LogOut size={14} style={{ color: 'var(--text-dark)', flexShrink: 0 }} />
          </div>
        </div>
      </aside>

      {/* ─── MAIN CONTENT ────────────────────────────────────────── */}
      <main className="voyage-main">
        {/* Header */}
        <header className="voyage-header">
          <div className="header-left">
            <button
              className="mobile-menu-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu size={20} />
            </button>
            <div className="header-breadcrumb">
              Adversaria AI <ChevronRight size={14} style={{ display: 'inline', opacity: 0.4 }} />
              {' '}<strong>{pageTitle}</strong>
            </div>
          </div>

          <div className="header-right">
            <div
              className="header-status-pill"
              id="pipeline-status-indicator"
            >
              <span className="status-dot idle" id="status-dot" />
              <span id="status-label">System Idle</span>
            </div>
            <div style={{
              width: '30px',
              height: '30px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--color-primary), var(--color-primary-light))',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: '700',
              cursor: 'pointer',
              flexShrink: 0,
            }}>
              T
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="voyage-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
