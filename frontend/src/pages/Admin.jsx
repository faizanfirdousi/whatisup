import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';

export function Admin() {
  const { user } = useAuth();
  const [secret, setSecret] = useState('');
  const [status, setStatus] = useState('');
  const [running, setRunning] = useState(false);

  useEffect(() => {
    localStorage.removeItem('whatisup_admin_secret');
  }, []);

  if (user && !user.is_builder) {
    return <Navigate to="/" replace />;
  }

  const handleRunPipeline = async () => {
    if (!secret) return setStatus('ADMIN_SECRET required to run the full pipeline');
    try {
      setRunning(true);
      setStatus('Pipeline running... this can take several minutes.');
      const result = await api.runPipeline(secret);
      setStatus(`Pipeline finished for ${result.people_processed} people.`);
    } catch (err) {
      setStatus(`Pipeline error: ${err.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Admin</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Builder-only. Nightly collect should come from the VM timer; this is the local override.
        </p>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '640px' }}>
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem' }}>Admin Secret</h2>
          <input
            type="password"
            placeholder="ADMIN_SECRET from .env"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            style={{
              width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)',
              background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)',
              color: 'white', marginBottom: '1rem',
            }}
          />
          {status && <div style={{ color: 'var(--warning)', fontSize: '0.9rem' }}>{status}</div>}
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem' }}>Run pipeline</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Collect, score, and narrate (including network stories). Prefer the cron endpoint in production.
          </p>
          <button onClick={handleRunPipeline} disabled={running} className="btn btn-secondary">
            {running ? 'Running Pipeline...' : 'Run Pipeline Now'}
          </button>
        </div>
      </div>
    </div>
  );
}
