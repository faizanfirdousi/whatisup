import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useSelectedOwner } from '../hooks/useSelectedOwner';
import { api } from '../api/client';
import { Loader } from '../components/Loader';
import { OwnerSelect } from '../components/OwnerSelect';

export function Network() {
  const { data: owners, loading: ownersLoading } = useApi(api.getOwners, []);
  const { ownerId, selectOwner } = useSelectedOwner(owners);
  const { data: connections, loading, error, refetch } = useApi(
    api.getConnections,
    [ownerId],
    { enabled: Boolean(ownerId) }
  );
  const [secret, setSecret] = useState(() => localStorage.getItem('whatisup_admin_secret') || '');
  const [status, setStatus] = useState('');

  const toggle = async (connection) => {
    if (!secret) {
      setStatus('Enter the admin secret to change close-circle flags.');
      return;
    }
    try {
      await api.toggleCloseCircle(connection.id, !connection.is_close, secret);
      setStatus('');
      refetch();
    } catch (err) {
      setStatus(err.message);
    }
  };

  if (ownersLoading || (ownerId && loading)) return <Loader />;
  if (!ownerId) {
    return <div className="glass-panel" style={{ padding: '2rem' }}>Add an owner in Admin first.</div>;
  }
  if (error) {
    return <div className="glass-panel" style={{ padding: '2rem' }}>Could not load network: {error}</div>;
  }

  return (
    <div>
      <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', gap: '1.5rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Network</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            {(connections || []).length} people for this owner. Mark close-circle so they always appear on Digest.
          </p>
        </div>
        <OwnerSelect owners={owners} ownerId={ownerId} onChange={selectOwner} />
      </header>

      <div className="glass-panel" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem' }}>
        <input
          type="password"
          placeholder="Admin secret (needed to toggle close circle)"
          value={secret}
          onChange={(e) => {
            setSecret(e.target.value);
            localStorage.setItem('whatisup_admin_secret', e.target.value);
          }}
          style={{
            width: '100%', padding: '0.75rem', borderRadius: 'var(--radius-md)',
            background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white',
          }}
        />
        {status && <p style={{ color: 'var(--warning)', marginTop: '0.75rem' }}>{status}</p>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
        {(connections || []).map((conn) => (
          <div key={conn.id} className="glass-card">
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <img
                src={conn.person.avatar_url || `https://github.com/${conn.person.github_username}.png`}
                alt={conn.person.github_username}
                style={{ width: '40px', height: '40px', borderRadius: '50%' }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <Link to={`/person/${conn.person.id}`}>
                  {conn.person.display_name || conn.person.github_username}
                </Link>
                <p style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>@{conn.person.github_username}</p>
              </div>
            </div>
            <button
              className={conn.is_close ? 'btn btn-primary' : 'btn btn-secondary'}
              style={{ marginTop: '1rem', width: '100%' }}
              onClick={() => toggle(conn)}
            >
              {conn.is_close ? 'Close circle' : 'Mark close'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
