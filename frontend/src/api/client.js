const BASE_URL = '/api';
const ADMIN_URL = '/admin';

async function fetchApi(endpoint, options = {}) {
  const prefix = endpoint.startsWith('/auth') ? '' : BASE_URL;
  const response = await fetch(`${prefix}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized');
    }
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (response.status === 204) return {};
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

async function fetchAdmin(endpoint, adminSecret, options = {}) {
  let secret = (adminSecret || '').trim();
  if (secret.startsWith('ADMIN_SECRET=')) {
    secret = secret.slice('ADMIN_SECRET='.length).trim();
  }
  const response = await fetch(`${ADMIN_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
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

  const text = await response.text();
  if (!text) return {};
  return JSON.parse(text);
}

export const api = {
  getMe: () => fetchApi('/me'),
  logout: () => fetchApi('/auth/logout', { method: 'POST' }),

  getDigest: (period = '2d') => fetchApi(`/me/digest?period=${encodeURIComponent(period)}`),
  getDigestV2: (period = '2d') => fetchApi(`/me/digest/v2?period=${encodeURIComponent(period)}`),
  getConnections: (tech) => fetchApi(tech ? `/me/connections?tech=${encodeURIComponent(tech)}` : '/me/connections'),
  getPerson: (personId) => fetchApi(`/people/${personId}`),
  getPersonEvents: (personId) => fetchApi(`/people/${personId}/events`),
  getStats: (period = '2d') => fetchApi(`/me/stats?period=${encodeURIComponent(period)}`),
  getSince: (period = '2d') => fetchApi(`/me/since?period=${encodeURIComponent(period)}`),
  getHighlightsRefresh: (period = '2d') => fetchApi(`/me/highlights?refresh=1&period=${encodeURIComponent(period)}`),
  getNetworkStory: () => fetchApi('/me/network-story'),
  ackHighlights: (body) => fetchApi('/me/ack', { method: 'POST', body: JSON.stringify(body || { surface: 'dashboard' }) }),
  collectNow: () => fetchApi('/me/collect', { method: 'POST' }),
  syncFollowing: () => fetchApi('/me/sync-following', { method: 'POST' }),
  toggleCloseCircle: (connectionId, isClose) =>
    fetchApi(`/me/connections/${connectionId}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_close: isClose }),
    }),

  runPipeline: (secret) => fetchAdmin('/run-pipeline', secret, { method: 'POST' }),
};
