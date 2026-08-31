import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { api } from '../api/client';
import { Loader } from '../components/Loader';
import { persistOwnerId } from '../hooks/ownerStorage';

export function Admin() {
  const { data: owners, loading, refetch } = useApi(api.getOwners, []);
  const [secret, setSecret] = useState(() => localStorage.getItem('whatisup_admin_secret') || '');
  const [label, setLabel] = useState('');
  const [username, setUsername] = useState('');
  const [status, setStatus] = useState('');
  const [running, setRunning] = useState(false);

  const persistSecret = (value) => {
    setSecret(value);
    localStorage.setItem('whatisup_admin_secret', value);
  };

  const handleAddOwner = async (e) => {
    e.preventDefault();
    if (!secret) return setStatus('Secret required');
    try {
      setStatus('Adding owner and seeding following list...');
      const result = await api.addOwner({ label, github_username: username }, secret);
      const seed = result.seed || {};
      if (result.owner?.id) persistOwnerId(result.owner.id);
      setStatus(
        `Owner ${result.created ? 'created' : 'updated'}. Tracked ${seed.tracked_including_self ?? '?'} people ` +
          `(${seed.following_count ?? 0} following + self). Digest/Network will switch to this owner.`
      );
      setLabel('');
      setUsername('');
      refetch();
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  };

  const handleRunPipeline = async () => {
    if (!secret) return setStatus('Secret required to run pipeline');
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

  if (loading) return <Loader />;

  return (
    <div>
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Admin Settings</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Manage owners and run the collect → score → narrate pipeline.</p>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '640px' }}>
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem' }}>Admin Secret</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
            Paste the value of <code>ADMIN_SECRET</code> from <code>.env</code> — not your GitHub or OpenRouter key.
          </p>
          <input
            type="password"
            placeholder="ADMIN_SECRET from .env"
            value={secret}
            onChange={(e) => persistSecret(e.target.value)}
            style={{
              width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)',
              background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)',
              color: 'white', marginBottom: '1rem',
            }}
          />
          {status && <div style={{ color: 'var(--warning)', fontSize: '0.9rem' }}>{status}</div>}
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem' }}>Owners</h2>
          {(owners || []).length === 0 ? (
            <p style={{ color: 'var(--text-tertiary)' }}>None yet.</p>
          ) : (
            <ul style={{ color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {owners.map((o) => (
                <li key={o.id}>
                  #{o.id} {o.label} (@{o.github_username}) · {o.connection_count ?? 0} connections
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ marginLeft: '0.75rem', padding: '0.35rem 0.75rem' }}
                    onClick={() => persistOwnerId(o.id)}
                  >
                    View this owner
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Add / reseed owner</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Uses the GitHub username only. Re-submitting the same username reseeds following (including the owner themselves).
            Accounts that follow nobody (e.g. torvalds) will still track that one person.
          </p>
          <form onSubmit={handleAddOwner} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <input
              required
              type="text"
              placeholder="Owner label (e.g. builder)"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              style={{ padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white' }}
            />
            <input
              required
              type="text"
              placeholder="GitHub username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{ padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white' }}
            />
            <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
              Add Owner
            </button>
          </form>
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Trigger Pipeline</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Collect public events, score them, extract technologies, and generate weekly narratives.
          </p>
          <button onClick={handleRunPipeline} disabled={running} className="btn btn-secondary">
            {running ? 'Running Pipeline...' : 'Run Pipeline Now'}
          </button>
        </div>
      </div>
    </div>
  );
}
