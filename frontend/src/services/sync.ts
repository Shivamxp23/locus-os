import { db } from './db';
import { api } from './api';
import type { Task, Goal } from '../types/models';

export async function downloadSnapshot(token: string) {
  try {
    const snapshot = await api.sync.snapshot(token);
    if (snapshot && snapshot.tasks) {
      await db.tasks.bulkPut(snapshot.tasks as Task[], { allKeys: true });
    }
    if (snapshot && snapshot.goals) {
      await db.goals.bulkPut(snapshot.goals as Goal[], { allKeys: true });
    }
    return snapshot;
  } catch {
    return null;
  }
}

export async function syncCache(token: string) {
  try {
    const [tasks, goals] = await Promise.all([
      api.tasks.list(token),
      api.goals.list(token),
    ]);
    await db.tasks.bulkPut(tasks, { allKeys: true });
    await db.goals.bulkPut(goals, { allKeys: true });
    return { tasks: tasks.length, goals: goals.length };
  } catch {
    return { tasks: 0, goals: 0 };
  }
}
