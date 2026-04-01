import { useState } from 'react';
import { useGoals } from '../hooks/useData';
import { api } from '../services/api';
import { useUserStore } from '../stores/userStore';
import { Card, Badge, Button, Input } from '../components/ui';
import { Header } from '../components/layout/Navigation';

export default function Goals() {
  const { goals, loading, setGoals } = useGoals();
  const token = useUserStore((s) => s.token);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [horizon, setHorizon] = useState('month');

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !title.trim()) return;
    const goal = await api.goals.create(token, { title: title.trim(), horizon });
    setGoals((prev: typeof goals) => [goal, ...prev]);
    setTitle('');
    setShowCreate(false);
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      <Header title="Goals" />
      <div className="px-4 py-4 space-y-4">
        {!showCreate ? (
          <Button onClick={() => setShowCreate(true)} fullWidth variant="secondary">
            + New Goal
          </Button>
        ) : (
          <form onSubmit={handleCreate} className="space-y-3">
            <Input
              placeholder="Goal title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />
            <div className="flex gap-2">
              {['week', 'month', 'quarter', 'year', 'lifetime'].map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setHorizon(h)}
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    horizon === h ? 'bg-secondary text-white' : 'bg-surface text-text-secondary'
                  }`}
                >
                  {h}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button type="submit" fullWidth>Create</Button>
              <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="text-center text-text-tertiary py-8">Loading goals...</div>
        ) : goals.length === 0 ? (
          <Card className="text-center py-8">
            <div className="text-text-tertiary">No goals yet. Create one to get started.</div>
          </Card>
        ) : (
          <div className="space-y-2">
            {goals.map((goal) => (
              <Card key={goal.id}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-medium text-text-primary">{goal.title}</div>
                    {goal.description && (
                      <div className="text-sm text-text-secondary mt-1">{goal.description}</div>
                    )}
                  </div>
                  <Badge color="secondary">{goal.horizon}</Badge>
                </div>
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-text-tertiary mb-1">
                    <span>Progress</span>
                    <span>{Math.round((goal.progress_score || 0) * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                    <div
                      className="h-full bg-secondary rounded-full transition-all"
                      style={{ width: `${Math.round((goal.progress_score || 0) * 100)}%` }}
                    />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
