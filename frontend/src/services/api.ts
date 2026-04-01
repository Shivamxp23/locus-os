import type { Task, Goal, AuthTokens, User, SyncStatus, IntegrationStatus, AiConversation, FullConversation } from '../types/models';

const API_BASE = 'https://api.locusapp.online';

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err);
  }
  return res.json();
}

export const api = {
  auth: {
    register: (email: string, password: string, display_name: string) =>
      request<AuthTokens>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, display_name }),
      }),
    login: (email: string, password: string) =>
      request<AuthTokens>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    me: (token: string) =>
      request<User>('/auth/me', { headers: authHeaders(token) }),
  },

  tasks: {
    list: (token: string) =>
      request<Task[]>('/api/tasks', { headers: authHeaders(token) }),
    get: (token: string, id: string) =>
      request<Task>(`/api/tasks/${id}`, { headers: authHeaders(token) }),
    create: (token: string, data: { title: string; description?: string; source?: string }) =>
      request<Task>('/api/tasks', {
        method: 'POST',
        body: JSON.stringify(data),
        headers: authHeaders(token),
      }),
    update: (token: string, id: string, data: Partial<Task>) =>
      request<Task>(`/api/tasks/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
        headers: authHeaders(token),
      }),
    complete: (token: string, id: string) =>
      request<Task>(`/api/tasks/${id}/complete`, {
        method: 'POST',
        headers: authHeaders(token),
      }),
    defer: (token: string, id: string) =>
      request<Task>(`/api/tasks/${id}/defer`, {
        method: 'POST',
        headers: authHeaders(token),
      }),
  },

  goals: {
    list: (token: string) =>
      request<Goal[]>('/api/goals', { headers: authHeaders(token) }),
    create: (token: string, data: { title: string; description?: string; horizon?: string }) =>
      request<Goal>('/api/goals', {
        method: 'POST',
        body: JSON.stringify(data),
        headers: authHeaders(token),
      }),
  },

  ai: {
    chat: (token: string, messages: Array<{ role: string; content: string }>) =>
      request<{ response: string; model: string; source: string }>('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ messages }),
        headers: authHeaders(token),
      }),
    conversations: (token: string) =>
      request<AiConversation[]>('/api/ai/conversations', { headers: authHeaders(token) }),
    conversation: (token: string, id: string) =>
      request<FullConversation>(`/api/ai/conversations/${id}`, { headers: authHeaders(token) }),
  },

  sync: {
    flush: (token: string, items: Array<{ id: string; created_at: number; type: string; payload: Record<string, unknown>; device_id: string }>) =>
      request<{ processed: number; conflicts: number; errors: unknown[] }>('/api/sync/flush', {
        method: 'POST',
        body: JSON.stringify({ items }),
        headers: authHeaders(token),
      }),
    snapshot: (token: string) =>
      request<Record<string, unknown>>('/api/sync/snapshot', { headers: authHeaders(token) }),
    status: (token: string) =>
      request<SyncStatus>('/api/sync/status', { headers: authHeaders(token) }),
  },

  integrations: {
    status: (token: string) =>
      request<IntegrationStatus>('/api/integrations/status', { headers: authHeaders(token) }),
  },
};
