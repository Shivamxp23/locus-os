import React, { useState, useEffect } from 'react';
import { CaretDown, CaretUp, Plus } from '@phosphor-icons/react';
import {
  getFactionColor, getFactionDimColor, getFactionLabel,
} from '../utils/helpers';
import { api } from '../utils/api';
import './Projects.css';

const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function ProjectsScreen() {
  const [projects, setProjects] = useState({});
  const [factionHealth, setFactionHealth] = useState({});
  const [expanded, setExpanded] = useState({
    health: true, leverage: true, craft: true, expression: true,
  });
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjects();
    loadFactions();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    const res = await api.getProjects('active');
    if (res?.projects) {
      // Group by faction
      const grouped = {};
      for (const f of FACTIONS) grouped[f] = [];
      for (const p of res.projects) {
        if (grouped[p.faction]) {
          grouped[p.faction].push(p);
        }
      }
      setProjects(grouped);
    }
    setLoading(false);
  };

  const loadFactions = async () => {
    const res = await api.getFactionHealth();
    if (res?.factions) setFactionHealth(res.factions);
  };

  const toggleFaction = (f) => {
    setExpanded(prev => ({ ...prev, [f]: !prev[f] }));
  };

  const statusBadge = (status) => {
    const map = {
      active: 'badge-working',
      paused: 'badge-planned',
      idea: 'badge-idea',
      done: 'badge-working',
      completed: 'badge-working',
    };
    return <span className={`badge ${map[status] || 'badge-planned'}`}>{status}</span>;
  };

  const totalActive = Object.values(projects).flat().filter(p => p.status === 'active').length;
  const totalPaused = Object.values(projects).flat().filter(p => p.status === 'paused').length;

  return (
    <div className="page-enter">
      <div className="page-container projects-page">
        <header className="projects-header">
          <div>
            <h1 className="display-l">Projects</h1>
            <p className="body-small text-secondary">
              {totalActive} active · {totalPaused} paused
            </p>
          </div>
          <button className="btn-primary" onClick={() => setShowNew(true)}>
            <Plus size={16} /> New
          </button>
        </header>

        {loading ? (
          <div>
            {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 100, marginBottom: 12 }} />)}
          </div>
        ) : (
          <div className="projects-factions">
            {FACTIONS.map(f => {
              const fProjects = projects[f] || [];
              const fData = factionHealth[f] || {};
              const isExpanded = expanded[f];
              const Caret = isExpanded ? CaretUp : CaretDown;

              return (
                <div key={f} className="projects-faction">
                  <button
                    className="projects-faction-header"
                    onClick={() => toggleFaction(f)}
                    style={{
                      background: `${getFactionDimColor(f)}80`,
                      borderBottomColor: `${getFactionColor(f)}33`,
                    }}
                  >
                    <div className="projects-faction-title">
                      <div className="projects-faction-dot" style={{ background: getFactionColor(f) }} />
                      <span className="heading-1">{getFactionLabel(f)}</span>
                    </div>
                    <div className="projects-faction-meta">
                      <span className="body-small text-secondary">
                        {fProjects.filter(p => p.status === 'active').length} active
                      </span>
                      <Caret size={18} color="var(--text-secondary)" />
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="projects-faction-content">
                      {/* Real faction stats */}
                      <div className="projects-faction-stats">
                        <div className="card-metric">
                          <div className="metric-label">Week Hours</div>
                          <div className="data-m" style={{ color: getFactionColor(f) }}>
                            {fData.actual_hours || 0} / {fData.target_hours || 0}
                          </div>
                        </div>
                        <div className="card-metric">
                          <div className="metric-label">Completion</div>
                          <div className="data-m" style={{ color: getFactionColor(f) }}>
                            {fData.completion_rate || 0}%
                          </div>
                        </div>
                        <div className="card-metric">
                          <div className="metric-label">Action Gap</div>
                          <div className="data-m" style={{ color: (fData.action_gap || 0) > 5 ? 'var(--warning)' : getFactionColor(f) }}>
                            {fData.action_gap || 0}
                          </div>
                        </div>
                      </div>

                      {/* Real project cards */}
                      {fProjects.length > 0 ? fProjects.map(p => (
                        <div
                          key={p.id}
                          className="project-card card"
                          style={{ borderLeftColor: getFactionColor(f) }}
                        >
                          <div className="project-card-header">
                            <h3 className="heading-2">{p.title}</h3>
                            {statusBadge(p.status)}
                          </div>
                          <p className="body-small text-secondary">
                            {p.completed_tasks || 0} of {(p.pending_tasks || 0) + (p.completed_tasks || 0)} tasks done
                            {p.total_hours_spent > 0 && ` · ${p.total_hours_spent}h logged`}
                          </p>
                          {p.difficulty && (
                            <div className="project-difficulty">
                              {Array.from({ length: 10 }).map((_, i) => (
                                <div
                                  key={i}
                                  className="project-pip"
                                  style={{
                                    background: i < p.difficulty ? getFactionColor(f) : 'var(--bg-4)',
                                  }}
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      )) : (
                        <p className="body-small text-tertiary" style={{ padding: '12px 16px' }}>
                          No projects yet in this faction
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* New Project Sheet */}
        {showNew && (
          <NewProjectSheet onClose={() => setShowNew(false)} onCreated={loadProjects} />
        )}
      </div>
    </div>
  );
}

function NewProjectSheet({ onClose, onCreated }) {
  const [title, setTitle] = useState('');
  const [faction, setFaction] = useState('craft');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setLoading(true);
    const res = await api.createProject({
      title: title.trim(),
      description: description.trim() || null,
      faction,
    });
    setLoading(false);
    if (res?.status === 'ok') {
      onCreated();
      onClose();
    }
  };

  return (
    <>
      <div className="backdrop" onClick={onClose} />
      <div className="bottom-sheet" style={{ padding: 'var(--space-24)' }}>
        <div className="drag-handle" />
        <h2 className="heading-1" style={{ marginBottom: 'var(--space-20)' }}>New Project</h2>

        <div className="input-wrapper">
          <label className="input-label">Title</label>
          <input className="input-field" type="text" placeholder="Project name" value={title} onChange={e => setTitle(e.target.value)} autoFocus />
        </div>

        <div className="input-wrapper">
          <label className="input-label">Description</label>
          <textarea className="input-field" placeholder="What is this project about?" value={description} onChange={e => setDescription(e.target.value)} rows={3} />
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

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
          <button className="btn-primary" onClick={handleCreate} disabled={!title.trim() || loading}>
            {loading ? 'Creating...' : 'Create Project →'}
          </button>
        </div>
      </div>
    </>
  );
}
