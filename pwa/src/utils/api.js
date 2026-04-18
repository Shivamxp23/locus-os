// Locus API client — v2 with all endpoints
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
  // ── Check-ins ──
  morningCheckin: (data) => request('/checkins/morning', { method: 'POST', body: JSON.stringify(data) }),
  afternoonCheckin: (data) => request('/checkins/afternoon', { method: 'POST', body: JSON.stringify(data) }),
  eveningCheckin: (data) => request('/checkins/evening', { method: 'POST', body: JSON.stringify(data) }),
  nightCheckin: (data) => request('/checkins/night', { method: 'POST', body: JSON.stringify(data) }),
  getTodayCheckins: () => request('/checkins/today'),

  // ── Tasks ──
  createTask: (data) => request('/tasks', { method: 'POST', body: JSON.stringify(data) }),
  getTodayTasks: () => request('/tasks/today'),
  getAllTasks: (status = 'pending', faction = null) => {
    let path = `/tasks?status=${status}`;
    if (faction) path += `&faction=${faction}`;
    return request(path);
  },
  completeTask: (id, data) => request(`/tasks/${id}/complete`, { method: 'POST', body: JSON.stringify(data) }),
  deferTask: (id, data) => request(`/tasks/${id}/defer`, { method: 'POST', body: JSON.stringify(data) }),

  // ── Captures ──
  createCapture: (data) => request('/captures', { method: 'POST', body: JSON.stringify(data) }),
  getCaptures: (processed = false, limit = 20) => request(`/captures?processed=${processed}&limit=${limit}`),

  // ── Vault ──
  searchVault: (query) => request(`/vault/search?q=${encodeURIComponent(query)}`),
  getVaultStats: () => request('/vault/stats'),
  getVaultHealth: () => request('/vault/health'),

  // ── Goal Stack (NEW) ──
  // Outcomes
  createOutcome: (data) => request('/outcomes', { method: 'POST', body: JSON.stringify(data) }),
  getOutcomes: (status = 'active') => request(`/outcomes?status=${status}`),
  getOutcomeDetail: (id) => request(`/outcomes/${id}`),
  updateOutcome: (id, data) => request(`/outcomes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Projects
  createProject: (data) => request('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProjects: (status = 'active', faction = null) => {
    let path = `/projects?status=${status}`;
    if (faction) path += `&faction=${faction}`;
    return request(path);
  },
  getProjectDetail: (id) => request(`/projects/${id}`),
  updateProject: (id, data) => request(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Goal Stack overview
  getGoalStack: () => request('/goals/stack'),

  // ── Schedule (NEW) ──
  getTodaySchedule: () => request('/schedule/today'),
  generateSchedule: (data) => request('/schedule/generate', { method: 'POST', body: JSON.stringify(data) }),

  // ── Factions (NEW) ──
  getFactionHealth: () => request('/factions/health'),
  getFactionHistory: (weeks = 8) => request(`/factions/history?weeks=${weeks}`),

  // ── Analytics (NEW) ──
  getDcsTrend: (days = 30) => request(`/analytics/dcs-trend?days=${days}`),
  getMoodTrend: (days = 30) => request(`/analytics/mood-trend?days=${days}`),
  getCompletionRates: (days = 30) => request(`/analytics/completion-rates?days=${days}`),
  getBehavioralPatterns: (days = 14) => request(`/analytics/behavioral-patterns?days=${days}`),
  getAvoidanceReport: () => request('/analytics/avoidance-report'),
  getAnalyticsSummary: () => request('/analytics/summary'),

  // ── Auth ──
  getCalendarStatus: () => request('/auth/calendar/status'),

  // ── Push ──
  getVapidPublicKey: () => request('/push/vapid-public-key'),
  subscribeToPush: (subscription) => request('/push/subscribe', { method: 'POST', body: JSON.stringify(subscription) }),
};
