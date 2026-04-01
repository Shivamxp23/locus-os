import { db } from './db';
import type { OfflineQueueItem } from '../types/models';
import { api } from './api';

export async function addToQueue(item: Omit<OfflineQueueItem, 'local_id' | 'sync_status' | 'retry_count' | 'last_retry'>) {
  await db.offline_queue.add({
    ...item,
    sync_status: 'pending',
    retry_count: 0,
    last_retry: null,
  });

  if ('serviceWorker' in navigator && 'sync' in ServiceWorkerRegistration.prototype) {
    const reg = await navigator.serviceWorker.ready;
    try {
      await (reg as any).sync.register('offline-queue-flush');
    } catch {
      // Background sync not available
    }
  }
}

export async function flushQueue(token: string) {
  const pending = await db.offline_queue
    .where('sync_status')
    .equals('pending')
    .sortBy('created_at');

  if (pending.length === 0) return { processed: 0, conflicts: 0, errors: [] };

  const items = pending.map(p => ({
    id: p.id,
    created_at: p.created_at,
    type: p.type,
    payload: p.payload,
    device_id: p.device_id,
  }));

  try {
    const result = await api.sync.flush(token, items);

    for (const p of pending) {
      await db.offline_queue.update(p.local_id!, { sync_status: 'synced' });
    }

    return result;
  } catch (err) {
    for (const p of pending) {
      await db.offline_queue.update(p.local_id!, {
        sync_status: 'failed',
        retry_count: p.retry_count + 1,
        last_retry: Date.now(),
      });
    }
    throw err;
  }
}
