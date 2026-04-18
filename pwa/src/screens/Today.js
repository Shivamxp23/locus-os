import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Check, Clock, ArrowRight } from '@phosphor-icons/react';
import { useApp } from '../context/AppContext';
import { api } from '../utils/api';
import {
  formatDate, getModeColor, getModeLabel,
  getFactionColor, getFactionDimColor, getFactionLabel, calculateTWS,
} from '../utils/helpers';
import './Today.css';

const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function TodayScreen() {
  const { dcs, mode, addToast, updateState, tasks: stateTasks } = useApp();
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load tasks
  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    setLoading(true);
    const res = await api.getTodayTasks();
    if (res?.tasks) {
      setTasks(res.tasks);
      updateState({ tasks: res.tasks });
    }
    setLoading(false);
  };

  const filteredTasks = filter === 'all' ? tasks : tasks.filter(t => t.faction === filter);

  // Group by TWS tier
  const highPriority = filteredTasks.filter(t => t.tws >= 7);
  const standard = filteredTasks.filter(t => t.tws >= 4 && t.tws < 7);
  const optional = filteredTasks.filter(t => t.tws < 4);

  const doneTasks = tasks.filter(t => t.status === 'done').length;
  const totalTasks = tasks.length;

  const handleComplete = async (taskId) => {
    const res = await api.completeTask(taskId, { actual_hours: 1, quality: 7 });
    if (res?.status === 'ok') {
      addToast('Task completed ✓', 'success');
      loadTasks();
    }
  };

  const handleDefer = async (taskId) => {
    const res = await api.deferTask(taskId);
    if (res?.status === 'ok') {
      addToast(`Task deferred. ${res.message}`, 'warning');
      loadTasks();
    }
  };

  return (
    <div className="page-enter">
      <div className="page-container today-page">
        {/* Header */}
        <header className="today-header">
          <div>
            <h1 className="display-l">Today</h1>
            <p className="body text-tertiary">{formatDate()}</p>
          </div>
          <div className="today-header-right">
            {dcs !== null && (
              <span
                className="mode-badge"
                style={{
                  background: `${getModeColor(mode)}22`,
                  color: getModeColor(mode),
                  fontSize: 11,
                }}
              >
                {dcs?.toFixed(1)} · {getModeLabel(mode)}
              </span>
            )}
          </div>
        </header>

        {/* Progress Summary */}
        <div className="today-progress">
          <div className="today-progress-metrics">
            <div className="today-metric">
              <span className="data-l text-success">{doneTasks}</span>
              <span className="caption text-tertiary">Done</span>
            </div>
            <div className="today-metric">
              <span className="data-l">{totalTasks - doneTasks}</span>
              <span className="caption text-tertiary">Remaining</span>
            </div>
            <div className="today-metric">
              <span className="data-l text-warning">0</span>
              <span className="caption text-tertiary">Deferred</span>
            </div>
          </div>
          {totalTasks > 0 && (
            <div className="progress-bar">
              <div
                className="progress-bar-fill"
                style={{
                  width: `${(doneTasks / totalTasks) * 100}%`,
                  background: 'var(--gold)',
                }}
              />
            </div>
          )}
        </div>

        {/* Filter Tabs */}
        <div className="today-filters">
          <button
            className={`today-filter ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          {FACTIONS.map(f => (
            <button
              key={f}
              className={`today-filter ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
              style={filter === f ? {
                background: getFactionDimColor(f),
                color: getFactionColor(f),
                borderColor: getFactionColor(f),
              } : {}}
            >
              {getFactionLabel(f)}
            </button>
          ))}
        </div>

        {/* Task Groups */}
        {loading ? (
          <div className="today-loading">
            {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 72, marginBottom: 8 }} />)}
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="today-empty card">
            <CheckCircleEmpty />
            <h2 className="heading-2" style={{ marginTop: 16 }}>Your day is clear.</h2>
            <p className="body-small text-secondary">Add your first task to get started</p>
            <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => setShowNew(true)}>
              <Plus size={16} /> Add Task
            </button>
          </div>
        ) : (
          <>
            {highPriority.length > 0 && (
              <TaskGroup label="HIGH PRIORITY" tasks={highPriority} onComplete={handleComplete} onDefer={handleDefer} />
            )}
            {standard.length > 0 && (
              <TaskGroup label="STANDARD" tasks={standard} onComplete={handleComplete} onDefer={handleDefer} />
            )}
            {optional.length > 0 && (
              <TaskGroup label="OPTIONAL" tasks={optional} onComplete={handleComplete} onDefer={handleDefer} />
            )}
          </>
        )}

        {/* FAB */}
        <button className="fab" onClick={() => setShowNew(true)} aria-label="Add task">
          <Plus size={24} weight="bold" />
        </button>

        {/* New Task Sheet */}
        {showNew && (
          <NewTaskSheet onClose={() => setShowNew(false)} onCreated={loadTasks} addToast={addToast} />
        )}
      </div>
    </div>
  );
}

function TaskGroup({ label, tasks, onComplete, onDefer }) {
  return (
    <div className="task-group">
      <h3 className="heading-3 text-tertiary task-group-label">{label}</h3>
      <div className="task-group-list">
        {tasks.map(task => (
          <TaskCard key={task.id} task={task} onComplete={onComplete} onDefer={onDefer} />
        ))}
      </div>
    </div>
  );
}

function TaskCard({ task, onComplete, onDefer }) {
  const factionColor = getFactionColor(task.faction);
  const isDone = task.status === 'done';

  return (
    <div className={`task-card card ${isDone ? 'task-done' : ''}`} style={{ borderLeftColor: factionColor }}>
      <button
        className="task-checkbox"
        style={{ borderColor: factionColor, background: isDone ? factionColor : 'transparent' }}
        onClick={() => !isDone && onComplete(task.id)}
        aria-label={isDone ? 'Completed' : 'Complete task'}
      >
        {isDone && <Check size={14} color="var(--bg-0)" weight="bold" />}
      </button>
      <div className="task-content">
        <span className={`body ${isDone ? 'task-title-done' : ''}`}>{task.title}</span>
        <div className="task-meta">
          <span className={`tag tag-${task.faction}`}>{getFactionLabel(task.faction)}</span>
          <span className="data-s text-tertiary">TWS {task.tws?.toFixed?.(1) || task.tws}</span>
          {task.estimated_hours && (
            <span className="body-small text-tertiary">
              <Clock size={12} style={{ verticalAlign: 'middle' }} /> ~{task.estimated_hours}h
            </span>
          )}
        </div>
      </div>
      <div className="task-right">
        <span className="data-m text-secondary">{task.priority}</span>
      </div>
    </div>
  );
}

function NewTaskSheet({ onClose, onCreated, addToast }) {
  const [title, setTitle] = useState('');
  const [faction, setFaction] = useState('craft');
  const [priority, setPriority] = useState(5);
  const [urgency, setUrgency] = useState(5);
  const [difficulty, setDifficulty] = useState(5);
  const [estimatedHours, setEstimatedHours] = useState('');
  const [loading, setLoading] = useState(false);

  const tws = calculateTWS(priority, urgency, difficulty);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setLoading(true);
    const res = await api.createTask({
      title: title.trim(),
      faction,
      priority,
      urgency,
      difficulty,
      estimated_hours: estimatedHours ? parseFloat(estimatedHours) : null,
    });
    setLoading(false);
    if (res?.status === 'ok') {
      addToast('Task created ✓', 'success');
      onCreated();
      onClose();
    } else {
      addToast('Failed to create task', 'error');
    }
  };

  return (
    <>
      <div className="backdrop" onClick={onClose} />
      <div className="bottom-sheet" style={{ padding: 'var(--space-24)' }}>
        <div className="drag-handle" />
        <h2 className="heading-1" style={{ marginBottom: 'var(--space-20)' }}>New Task</h2>

        <div className="input-wrapper">
          <label className="input-label">Title</label>
          <input className="input-field" type="text" placeholder="What needs to be done?" value={title} onChange={e => setTitle(e.target.value)} autoFocus />
        </div>

        <div className="input-wrapper">
          <label className="input-label">Faction</label>
          <div className="new-task-factions">
            {FACTIONS.map(f => (
              <button
                key={f}
                className={`tag tag-${f} ${faction === f ? 'tag-selected' : ''}`}
                onClick={() => setFaction(f)}
                style={faction === f ? { opacity: 1, transform: 'scale(1.05)' } : { opacity: 0.5 }}
              >
                {getFactionLabel(f)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <div className="input-wrapper">
            <label className="input-label">Priority ({priority})</label>
            <input type="range" min={1} max={10} value={priority} onChange={e => setPriority(parseInt(e.target.value))} className="locus-slider" />
          </div>
          <div className="input-wrapper">
            <label className="input-label">Urgency ({urgency})</label>
            <input type="range" min={1} max={10} value={urgency} onChange={e => setUrgency(parseInt(e.target.value))} className="locus-slider" />
          </div>
          <div className="input-wrapper">
            <label className="input-label">Difficulty ({difficulty})</label>
            <input type="range" min={1} max={10} value={difficulty} onChange={e => setDifficulty(parseInt(e.target.value))} className="locus-slider" />
          </div>
        </div>

        <div className="input-wrapper">
          <label className="input-label">Estimated Hours (optional)</label>
          <input className="input-field" type="number" step="0.5" placeholder="1.5" value={estimatedHours} onChange={e => setEstimatedHours(e.target.value)} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
          <span className="data-s text-secondary">TWS: {tws.toFixed(1)}</span>
          <button className="btn-primary" onClick={handleCreate} disabled={!title.trim() || loading}>
            {loading ? 'Creating...' : 'Create Task →'}
          </button>
        </div>
      </div>
    </>
  );
}

function CheckCircleEmpty() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
      <circle cx="24" cy="24" r="20" stroke="var(--text-tertiary)" strokeWidth="2" />
      <path d="M16 24l5 5 11-11" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
