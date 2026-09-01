import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function Login() {
  const { loginWithGithub, user, loading } = useAuth();

  if (!loading && user) {
    return <Navigate to="/" replace />;
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'var(--bg-primary)'
    }}>
      <div className="glass-panel" style={{ padding: '3rem', maxWidth: '400px', width: '100%', textAlign: 'center' }}>
        <div style={{
          width: '64px', height: '64px', margin: '0 auto 1.5rem',
          background: 'var(--accent-gradient)', borderRadius: 'var(--radius-lg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '2rem', fontWeight: 'bold', color: 'white'
        }}>W</div>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>WhatIsUp</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
          Your personal intelligence layer for developer networks.
        </p>
        <button onClick={loginWithGithub} className="btn btn-primary" style={{ width: '100%' }}>
          Sign in with GitHub
        </button>
      </div>
    </div>
  );
}
