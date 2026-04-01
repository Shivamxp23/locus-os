import { useState } from 'react';
import { useTasks } from '../hooks/useData';
import { useOffline } from '../hooks/useOffline';
import { Card, Badge, Button, Input } from '../components/ui';
import { Header } from '../components/layout/Navigation';

export default function Tasks() {
  const { tasks, loading, setTasks } = useTasks();
  const { isOnline, executeTask } = useOffline();
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [filter, setFilter] = useState('all');

  const filtered = tasks.filter((t) => {
    if (filter === 'pending') return t.status === 'pending';
    if (filter === 'completed') return t.status === 'completed';
    return true;
  });

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    const result = await executeTask('create', { title: title.trim(), source: 'pwa' });
    setTasks((prev: typeof tasks) => [result.data as typeof tasks[0], ...prev]);
    setTitle('');
    setShowCreate(false);
  }

  async function handleComplete(id: string) {
    const result = await executeTask('complete', { id });
    setTasks((prev: typeof tasks) => prev.map((t) => (t.id === id ? (result.data as typeof t) : t)));
  }

  async function handleDefer(id: string) {
    const result = await executeTask('defer', { id });
    setTasks((prev: typeof tasks) => prev.map((t) => (t.id === id ? (result.data as typeof t) : t)));
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      <Header title="Tasks" />
      <div className="px-4 py-4 space-y-4">
        {!showCreate ? (
          <Button onClick={() => setShowCreate(true)} fullWidth variant="secondary">
            + New Task
          </Button>
        ) : (
          <form onSubmit={handleCreate} className="flex gap-2">
            <Input
              placeholder="What needs to be done?"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />
            <Button type="submit">Add</Button>
          </form>
        )}

        <div className="flex gap-2">
          {['all', 'pending', 'completed'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                filter === f
                  ? 'bg-primary text-white'
                  : 'bg-surface text-text-secondary'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center text-text-tertiary py-8">Loading tasks...</div>
        ) : filtered.length === 0 ? (
          <Card className="text-center py-8">
            <div className="text-text-tertiary">No tasks here</div>
          </Card>
        ) : (
          <div className="space-y-2">
            {filtered.map((task) => (
              <Card key={task.id} className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className={`font-medium ${task.status === 'completed' ? 'line-through text-text-tertiary' : 'text-text-primary'}`}>
                    {task.title}
                  </div>
                  <div className="flex gap-1 mt-1">
                    <Badge color={task.status === 'completed' ? 'success' : 'default'}>{task.status}</Badge>
                    <Badge color="default">{task.source}</Badge>
                    {task.deferral_count > 0 && <Badge color="warning">{task.deferral_count}x</Badge>}
                  </div>
                </div>
                {task.status !== 'completed' && isOnline && (
                  <div className="flex gap-1 ml-2">
                    <Button variant="ghost" onClick={() => handleComplete(task.id)} className="text-xs px-2 py-1">
                      ✓
                    </Button>
                    <Button variant="ghost" onClick={() => handleDefer(task.id)} className="text-xs px-2 py-1">
                      ↻
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
