// Locus API client
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  try {
    const res = await fetch(url, config);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`API request failed: ${path}`, err);
    return null;
  }
}

export const api = {
  // Check-ins
  morningCheckin: (data) => request('/checkins/morning', { method: 'POST', body: JSON.stringify(data) }),
  afternoonCheckin: (data) => request('/checkins/afternoon', { method: 'POST', body: JSON.stringify(data) }),
  eveningCheckin: (data) => request('/checkins/evening', { method: 'POST', body: JSON.stringify(data) }),
  nightCheckin: (data) => request('/checkins/night', { method: 'POST', body: JSON.stringify(data) }),
  getTodayCheckins: () => request('/checkins/today'),

  // Tasks
  createTask: (data) => request('/tasks', { method: 'POST', body: JSON.stringify(data) }),
  getTodayTasks: () => request('/tasks/today'),
  getAllTasks: (status = 'pending', faction = null) => {
    let path = `/tasks?status=${status}`;
    if (faction) path += `&faction=${faction}`;
    return request(path);
  },
  completeTask: (id, data) => request(`/tasks/${id}/complete`, { method: 'POST', body: JSON.stringify(data) }),
  deferTask: (id, data) => request(`/tasks/${id}/defer`, { method: 'POST', body: JSON.stringify(data) }),

  // Captures
  createCapture: (data) => request('/captures', { method: 'POST', body: JSON.stringify(data) }),
  getCaptures: (processed = false, limit = 20) => request(`/captures?processed=${processed}&limit=${limit}`),

  // Vault
  searchVault: (query) => request(`/vault/search?q=${encodeURIComponent(query)}`),
  getVaultStats: () => request('/vault/stats'),
};
