import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { db } from '../services/db';
import { useUserStore } from '../stores/userStore';
import type { Task, Goal } from '../types/models';

export function useTasks() {
  const token = useUserStore((s) => s.token);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    async function load() {
      try {
        const serverTasks = await api.tasks.list(token);
        if (!cancelled) {
          await db.tasks.bulkPut(serverTasks, { allKeys: true });
          setTasks(serverTasks);
        }
      } catch {
        const cached = await db.tasks.toArray();
        if (!cancelled) setTasks(cached);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [token]);

  return { tasks, loading, setTasks };
}

export function useGoals() {
  const token = useUserStore((s) => s.token);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    async function load() {
      try {
        const serverGoals = await api.goals.list(token);
        if (!cancelled) {
          await db.goals.bulkPut(serverGoals, { allKeys: true });
          setGoals(serverGoals);
        }
      } catch {
        const cached = await db.goals.toArray();
        if (!cancelled) setGoals(cached);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [token]);

  return { goals, loading, setGoals };
}
