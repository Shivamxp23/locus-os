import { useEffect, useState } from 'react';
import { useUserStore } from '../stores/userStore';
import { useOfflineStore } from '../stores/offlineStore';
import { useTasks, useGoals } from '../hooks/useData';
import { api } from '../services/api';
import { syncCache } from '../services/sync';
import { Card, Badge } from '../components/ui';
import { Header } from '../components/layout/Navigation';

export default function Dashboard() {
  const token = useUserStore((s) => s.token);
  const isOnline = useOfflineStore((s) => s.isOnline);
  const { tasks, loading } = useTasks();
  const { goals } = useGoals();
  const [synced, setSynced] = useState(false);

  useEffect(() => {
    if (!token || synced) return;
    syncCache(token).then(() => setSynced(true));
  }, [token, synced]);

  const pendingTasks = tasks.filter((t) => t.status === 'pending');
  const completedToday = tasks.filter((t) => {
    if (t.status !== 'completed' || !t.completed_at) return false;
    return new Date(t.completed_at).toDateString() === new Date().toDateString();
  });

  return (
    <div className="min-h-screen bg-background pb-20">
      <Header title="Dashboard" />
      <div className="px-4 py-4 space-y-4">
        {!isOnline && (
          <div className="rounded-lg bg-warning/10 p-3 text-sm text-warning">
            Offline mode — changes will sync when reconnected
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          <Card className="text-center">
            <div className="text-2xl font-bold text-text-primary">{pendingTasks.length}</div>
            <div className="text-xs text-text-tertiary">Pending</div>
          </Card>
          <Card className="text-center">
            <div className="text-2xl font-bold text-success">{completedToday.length}</div>
            <div className="text-xs text-text-tertiary">Done today</div>
          </Card>
          <Card className="text-center">
            <div className="text-2xl font-bold text-secondary">{goals.length}</div>
            <div className="text-xs text-text-tertiary">Active goals</div>
          </Card>
        </div>

        {pendingTasks.length > 0 && (
          <div>
            <h2 className="mb-2 text-sm font-semibold text-text-secondary uppercase tracking-wide">Today's Tasks</h2>
            <div className="space-y-2">
              {pendingTasks.slice(0, 5).map((task) => (
                <Card key={task.id} className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-text-primary">{task.title}</div>
                    {task.source && (
                      <Badge color="default">{task.source}</Badge>
                    )}
                  </div>
                  {task.deferral_count > 0 && (
                    <Badge color="warning">{task.deferral_count} deferred</Badge>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}

        {pendingTasks.length === 0 && !loading && (
          <Card className="text-center py-8">
            <div className="text-text-tertiary">No pending tasks. Enjoy your free time!</div>
          </Card>
        )}
      </div>
    </div>
  );
}
