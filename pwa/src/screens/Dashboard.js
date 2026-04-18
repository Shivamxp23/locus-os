import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, MagnifyingGlass, Timer, Plus } from '@phosphor-icons/react';
import { useApp } from '../context/AppContext';
import TreeOrganism from '../components/TreeOrganism';
import {
  getGreeting, formatDate, getModeColor, getModeBgColor,
  getModeLabel, getFactionColor, getFactionDimColor, getFactionLabel,
} from '../utils/helpers';
import './Dashboard.css';

const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function Dashboard() {
  const navigate = useNavigate();
  const { dcs, mode, checkins, factions, user, tasks } = useApp();
  const [compositeScore, setCompositeScore] = useState(5.0);
  const dcsRef = useRef(null);

  // Calculate composite score from factions + DCS
  useEffect(() => {
    const avgCompletion = FACTIONS.reduce((sum, f) => sum + (factions[f]?.completionRate || 0), 0) / 4;
    const avgDcs = dcs || 5.0;
    const score = ((avgCompletion / 100) * 0.35 + (avgDcs / 10) * 0.30 + 0.6 * 0.20 + 0.5 * 0.15) * 10;
    setCompositeScore(Math.min(10, Math.max(0, score)));
  }, [factions, dcs]);

  // Animate DCS number
  useEffect(() => {
    if (dcsRef.current && dcs !== null) {
      const start = 0;
      const end = dcs;
      const duration = 800;
      const startTime = performance.now();
      function update(t) {
        const elapsed = t - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        if (dcsRef.current) dcsRef.current.textContent = (start + (end - start) * eased).toFixed(1);
        if (progress < 1) requestAnimationFrame(update);
      }
      requestAnimationFrame(update);
    }
  }, [dcs]);

  const checkinTypes = ['morning', 'afternoon', 'evening', 'night'];
  const checkinLabels = { morning: 'Morning', afternoon: 'Afternoon', evening: 'Evening', night: 'Night' };

  const getCurrentCheckin = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'morning';
    if (hour < 17) return 'afternoon';
    if (hour < 21) return 'evening';
    return 'night';
  };

  return (
    <div className="page-enter">
      <div className="page-container dashboard">
        {/* Header */}
        <header className="dash-header">
          <div>
            <p className="body text-secondary">{getGreeting()}, {user.name}</p>
            <p className="heading-2">{formatDate()}</p>
          </div>
          <div className="dash-header-right">
            <button className="btn-icon" aria-label="Notifications">
              <Bell size={22} />
            </button>
            <div className="dash-avatar">
              <div className="tree-mini" />
            </div>
          </div>
        </header>

        {/* Organism Card */}
        <section className="dash-organism card" onClick={() => navigate('/organism')}>
          <TreeOrganism compositeScore={compositeScore} size={180} />
        </section>

        {/* DCS Command Strip */}
        <section className="dash-dcs card">
          {dcs !== null ? (
            <div className="dash-dcs-inner">
              <div className="dash-dcs-left">
                <span className="caption text-tertiary">DCS</span>
                <span className="data-xl" ref={dcsRef} style={{ color: getModeColor(mode) }}>
                  {dcs?.toFixed(1)}
                </span>
              </div>
              <div className="dash-dcs-divider" />
              <div className="dash-dcs-right">
                <span
                  className="mode-badge"
                  style={{
                    background: getModeBgColor(mode),
                    color: getModeColor(mode),
                  }}
                >
                  {getModeLabel(mode)}
                </span>
                <span className="caption text-tertiary" style={{ marginTop: 4 }}>
                  Based on this morning's check-in
                </span>
              </div>
            </div>
          ) : (
            <button
              className="dash-dcs-empty"
              onClick={() => navigate('/checkin')}
            >
              <div className="dash-pulse-dot pulse-dot" />
              <span className="body text-secondary">Log your morning first →</span>
            </button>
          )}
        </section>

        {/* Faction Health */}
        <section className="dash-factions">
          <h3 className="heading-3 text-tertiary" style={{ marginBottom: 'var(--space-16)' }}>
            FACTION HEALTH
          </h3>
          <div className="dash-factions-list">
            {FACTIONS.map(f => {
              const faction = factions[f];
              const pct = faction?.completionRate || 0;
              return (
                <div key={f} className="dash-faction-row">
                  <div className="dash-faction-label">
                    <div
                      className="dash-faction-dot"
                      style={{ background: getFactionColor(f) }}
                    />
                    <span className="body-small">{getFactionLabel(f)}</span>
                  </div>
                  <div className="progress-bar" style={{ flex: 1 }}>
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${pct}%`,
                        background: getFactionColor(f),
                      }}
                    />
                  </div>
                  <span className="data-s text-secondary" style={{ minWidth: 80, textAlign: 'right' }}>
                    {pct}% · {faction?.actualHours || 0}/{faction?.targetHours || 0}h
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Today's Tasks */}
        <section className="dash-today">
          <div className="dash-section-header">
            <h3 className="heading-3 text-tertiary">TODAY</h3>
            <span className="body-small text-secondary">
              {tasks.length > 0 ? `${tasks.filter(t => t.status === 'done').length} of ${tasks.length} done` : 'No tasks yet'}
            </span>
          </div>
          {tasks.length > 0 ? (
            <div className="dash-task-list">
              {tasks.slice(0, 4).map((task, i) => (
                <div key={i} className="dash-task-card card" style={{ borderLeftColor: getFactionColor(task.faction) }}>
                  <div className="dash-task-checkbox" style={{ borderColor: getFactionColor(task.faction) }} />
                  <div className="dash-task-content">
                    <span className="body">{task.title}</span>
                    <div className="dash-task-meta">
                      <span className={`tag tag-${task.faction}`}>{getFactionLabel(task.faction)}</span>
                      {task.tws && <span className="data-s text-tertiary">TWS {task.tws}</span>}
                    </div>
                  </div>
                </div>
              ))}
              <button className="btn-ghost" onClick={() => navigate('/today')}>
                See all →
              </button>
            </div>
          ) : (
            <div className="dash-empty card">
              <p className="heading-2">Your day is clear.</p>
              <p className="body-small text-secondary">Add your first task to get started</p>
              <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/today')}>
                <Plus size={16} /> Add Task
              </button>
            </div>
          )}
        </section>

        {/* Check-in Status */}
        <section className="dash-checkin-status">
          <h3 className="heading-3 text-tertiary" style={{ marginBottom: 'var(--space-16)' }}>
            TODAY'S CHECK-INS
          </h3>
          <div className="dash-checkin-dots">
            {checkinTypes.map(type => {
              const done = checkins[type] !== null;
              const isCurrent = type === getCurrentCheckin() && !done;
              return (
                <button
                  key={type}
                  className="dash-checkin-dot-wrapper"
                  onClick={() => navigate('/checkin', { state: { type } })}
                >
                  <div className={`dash-checkin-dot ${done ? 'done' : ''} ${isCurrent ? 'current pulse-dot' : ''}`} />
                  <span className="caption text-tertiary">{checkinLabels[type]}</span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Quick Actions */}
        <section className="dash-quick-actions">
          <button className="btn-secondary" onClick={() => navigate('/capture')}>
            <Plus size={16} /> Capture
          </button>
          <button className="btn-secondary">
            <Timer size={16} /> Focus
          </button>
          <button className="btn-secondary" onClick={() => navigate('/vault')}>
            <MagnifyingGlass size={16} /> Search Vault
          </button>
        </section>
      </div>
    </div>
  );
}
