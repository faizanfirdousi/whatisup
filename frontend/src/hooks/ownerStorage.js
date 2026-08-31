const OWNER_KEY = 'whatisup_owner_id';

export function readStoredOwnerId() {
  const raw = localStorage.getItem(OWNER_KEY);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isFinite(id) ? id : null;
}

export function persistOwnerId(id) {
  if (id == null) {
    localStorage.removeItem(OWNER_KEY);
  } else {
    localStorage.setItem(OWNER_KEY, String(id));
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('whatisup-owner', { detail: id }));
  }
}

export function pickDefaultOwnerId(owners) {
  if (!owners?.length) return null;
  const ranked = [...owners].sort((a, b) => {
    const byCount = (b.connection_count || 0) - (a.connection_count || 0);
    if (byCount !== 0) return byCount;
    return (b.id || 0) - (a.id || 0);
  });
  return ranked[0].id;
}

export function resolveOwnerId(owners, preferredId) {
  if (!owners?.length) return null;
  if (preferredId && owners.some((o) => o.id === preferredId)) return preferredId;
  return pickDefaultOwnerId(owners);
}
