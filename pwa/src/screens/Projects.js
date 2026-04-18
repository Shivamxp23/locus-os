import React, { useState } from 'react';
import { CaretDown, CaretUp } from '@phosphor-icons/react';
import {
  getFactionColor, getFactionDimColor, getFactionLabel,
} from '../utils/helpers';
import { useApp } from '../context/AppContext';
import './Projects.css';

const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

// Demo projects data
const DEMO_PROJECTS = {
  health: [
    { id: 1, title: 'Morning Routine Optimization', status: 'active', progress: '6 of 12 tasks done', difficulty: 4 },
    { id: 2, title: 'Strength Training Program', status: 'active', progress: '3 of 8 tasks done', difficulty: 6 },
  ],
  leverage: [
    { id: 3, title: 'Locus Cognitive OS', status: 'active', progress: '18 of 32 tasks done', difficulty: 9 },
    { id: 4, title: 'Investment Portfolio Review', status: 'paused', progress: '2 of 5 tasks done', difficulty: 5 },
  ],
  craft: [
    { id: 5, title: 'Systems Architecture Knowledge', status: 'active', progress: '14 of 20 tasks done', difficulty: 8 },
  ],
  expression: [
    { id: 6, title: 'Writing Second Brain Setup', status: 'active', progress: '10 of 15 tasks done', difficulty: 6 },
    { id: 7, title: 'Photography Portfolio', status: 'idea', progress: '0 of 0 tasks done', difficulty: 3 },
  ],
};

export default function ProjectsScreen() {
  const { factions } = useApp();
  const [expanded, setExpanded] = useState({
    health: true, leverage: true, craft: true, expression: true,
  });

  const toggleFaction = (f) => {
    setExpanded(prev => ({ ...prev, [f]: !prev[f] }));
  };

  const statusBadge = (status) => {
    const map = {
      active: 'badge-working',
      paused: 'badge-planned',
      idea: 'badge-idea',
      done: 'badge-working',
    };
    return <span className={`badge ${map[status] || 'badge-planned'}`}>{status}</span>;
  };

  return (
    <div className="page-enter">
      <div className="page-container projects-page">
        <header className="projects-header">
          <h1 className="display-l">Projects</h1>
          <p className="body-small text-secondary">
            {Object.values(DEMO_PROJECTS).flat().filter(p => p.status === 'active').length} active ·{' '}
            {Object.values(DEMO_PROJECTS).flat().filter(p => p.status === 'paused').length} paused
          </p>
        </header>

        <div className="projects-factions">
          {FACTIONS.map(f => {
            const projects = DEMO_PROJECTS[f] || [];
            const factionData = factions[f];
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
                    <span className="body-small text-secondary">{projects.filter(p => p.status === 'active').length} active</span>
                    <Caret size={18} color="var(--text-secondary)" />
                  </div>
                </button>

                {isExpanded && (
                  <div className="projects-faction-content">
                    {/* Faction stats */}
                    <div className="projects-faction-stats">
                      <div className="card-metric">
                        <div className="metric-label">Week Hours</div>
                        <div className="data-m" style={{ color: getFactionColor(f) }}>
                          {factionData?.actualHours || 0} / {factionData?.targetHours || 0}
                        </div>
                      </div>
                      <div className="card-metric">
                        <div className="metric-label">Completion</div>
                        <div className="data-m" style={{ color: getFactionColor(f) }}>
                          {factionData?.completionRate || 0}%
                        </div>
                      </div>
                      <div className="card-metric">
                        <div className="metric-label">Momentum</div>
                        <div className="data-m" style={{ color: getFactionColor(f) }}>→</div>
                      </div>
                    </div>

                    {/* Project cards */}
                    {projects.map(p => (
                      <div
                        key={p.id}
                        className="project-card card"
                        style={{ borderLeftColor: getFactionColor(f) }}
                      >
                        <div className="project-card-header">
                          <h3 className="heading-2">{p.title}</h3>
                          {statusBadge(p.status)}
                        </div>
                        <p className="body-small text-secondary">{p.progress}</p>
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
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
