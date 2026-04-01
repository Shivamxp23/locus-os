import { useOfflineStore } from '../stores/offlineStore';
import { db } from '../services/db';
import { api } from '../services/api';
import { addToQueue } from '../services/offline';
import type { Task } from '../types/models';

export function useOffline() {
  const isOnline = useOfflineStore((s) => s.isOnline);

  async function executeTask(action: string, payload: Record<string, unknown>) {
    const token = localStorage.getItem('locus_token');
    if (!token) throw new Error('Not authenticated');

    if (isOnline) {
      try {
        let result: Task;
        if (action === 'create') {
          result = await api.tasks.create(token, payload as { title: string; description?: string; source?: string });
        } else if (action === 'complete') {
          result = await api.tasks.complete(token, payload.id as string);
        } else if (action === 'defer') {
          result = await api.tasks.defer(token, payload.id as string);
        } else if (action === 'update') {
          result = await api.tasks.update(token, payload.id as string, payload);
        } else {
          throw new Error(`Unknown action: ${action}`);
        }
        await db.tasks.put(result);
        return { source: 'server' as const, data: result };
      } catch (err) {
        if (!(err instanceof Error && err.message.includes('fetch'))) throw err;
      }
    }

    const localTask: Task = {
      id: crypto.randomUUID(),
      user_id: '',
      title: (payload.title as string) || '',
      description: (payload.description as string) || '',
      parent_task_id: null,
      goal_id: null,
      project_id: null,
      source: 'pwa',
      notion_page_id: null,
      status: action === 'complete' ? 'completed' : 'pending',
      priority_score: null,
      energy_type: null,
      estimated_minutes: null,
      scheduled_at: null,
      deferral_count: 0,
      deferral_flag: null,
      completed_at: action === 'complete' ? new Date().toISOString() : null,
      completion_duration_minutes: null,
      engine_annotations: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      deadline: null,
    };

    await db.tasks.put(localTask);

    await addToQueue({
      id: localTask.id,
      created_at: Date.now(),
      type: action === 'create' ? 'task_create' : action === 'complete' ? 'task_complete' : action === 'defer' ? 'task_defer' : 'task_update',
      payload: { ...payload, task_id: payload.id || localTask.id },
      device_id: 'pwa',
    });

    return { source: 'local' as const, data: localTask };
  }

  return { isOnline, executeTask };
}
