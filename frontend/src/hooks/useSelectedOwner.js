import { useEffect, useState } from 'react';
import { persistOwnerId, readStoredOwnerId, resolveOwnerId } from './ownerStorage';

export function useSelectedOwner(owners) {
  const [ownerId, setOwnerId] = useState(readStoredOwnerId);

  useEffect(() => {
    const next = resolveOwnerId(owners, ownerId);
    if (next !== ownerId) {
      setOwnerId(next);
      persistOwnerId(next);
    }
  }, [owners, ownerId]);

  useEffect(() => {
    const onChange = (event) => setOwnerId(event.detail ?? null);
    window.addEventListener('whatisup-owner', onChange);
    return () => window.removeEventListener('whatisup-owner', onChange);
  }, []);

  const selectOwner = (id) => {
    persistOwnerId(Number(id));
  };

  return { ownerId, selectOwner };
}
