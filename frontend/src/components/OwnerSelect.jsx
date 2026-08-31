import React from 'react';

export function OwnerSelect({ owners, ownerId, onChange }) {
  if (!owners?.length) return null;

  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', minWidth: '240px' }}>
      <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>Viewing digest for</span>
      <select
        value={ownerId ?? ''}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{
          padding: '0.65rem 0.75rem',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(0,0,0,0.2)',
          border: '1px solid var(--glass-border)',
          color: 'white',
        }}
      >
        {owners.map((owner) => (
          <option key={owner.id} value={owner.id}>
            {owner.label} (@{owner.github_username}) · {owner.connection_count ?? 0} people
          </option>
        ))}
      </select>
    </label>
  );
}
