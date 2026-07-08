import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import Dashboard from './pages/Dashboard';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { DashboardLayout } from './layouts/DashboardLayout';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuth = localStorage.getItem('auth') === 'true';
  return isAuth ? <>{children}</> : <Navigate to="/login" replace />;
};

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="runs" element={<PlaceholderPage title="Runs" desc="History of your generated concepts and pipelines." />} />
          <Route path="api-keys" element={<PlaceholderPage title="API Keys" desc="Manage your secret keys for fal.ai, Replicate, and Anthropic." />} />
          <Route path="settings" element={<PlaceholderPage title="Settings" desc="Configure your default generation budget, webhooks, and billing." />} />
          <Route path="profile" element={<PlaceholderPage title="Profile" desc="Manage your personal account settings." />} />
        </Route>
      </Routes>
    </Router>
  );
}
