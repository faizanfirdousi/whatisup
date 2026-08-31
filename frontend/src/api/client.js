const BASE_URL = '/api';
const ADMIN_URL = '/admin';

async function fetchApi(endpoint, options = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  return response.json();
}

async function fetchAdmin(endpoint, adminSecret, options = {}) {
  let secret = (adminSecret || '').trim();
  if (secret.startsWith('ADMIN_SECRET=')) {
    secret = secret.slice('ADMIN_SECRET='.length).trim();
  }
  const response = await fetch(`${ADMIN_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Secret': secret,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  return response.json();
}

export const api = {
  getOwners: () => fetchApi('/owners'),
  getDigest: (ownerId) => fetchApi(`/owners/${ownerId}/digest`),
  getConnections: (ownerId) => fetchApi(`/owners/${ownerId}/connections`),
  getPerson: (personId) => fetchApi(`/people/${personId}`),
  getPersonEvents: (personId) => fetchApi(`/people/${personId}/events`),
  getStats: () => fetchApi('/stats'),

  addOwner: (data, secret) => fetchAdmin('/owners', secret, { method: 'POST', body: JSON.stringify(data) }),
  runPipeline: (secret) => fetchAdmin('/run-pipeline', secret, { method: 'POST' }),
  toggleCloseCircle: (connectionId, isClose, secret) =>
    fetchAdmin(`/connections/${connectionId}`, secret, {
      method: 'PATCH',
      body: JSON.stringify({ is_close: isClose }),
    }),
};
