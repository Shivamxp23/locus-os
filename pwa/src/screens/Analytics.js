import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { getModeColor, getFactionColor, getFactionLabel } from '../utils/helpers';
import './Analytics.css';

const TIME_RANGES = ['7D', '30D', '3M', 'All'];
const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function AnalyticsScreen() {
  const { dcs, factions } = useApp();
  const [range, setRange] = useState('30D');

  // Demo data for charts
  const dcsHistory = Array.from({ length: 30 }, (_, i) => ({
    day: i + 1,
    value: 4 + Math.random() * 4,
  }));
  const avgDCS = dcsHistory.reduce((s, d) => s + d.value, 0) / dcsHistory.length;

  return (
    <div className="page-enter">
      <div className="page-container analytics-page">
        <header className="analytics-header">
          <h1 className="display-l">Analytics</h1>
          <div className="analytics-range-selector">
            {TIME_RANGES.map(r => (
              <button
                key={r}
                className={`analytics-range-btn ${range === r ? 'active' : ''}`}
                onClick={() => setRange(r)}
              >
                {r}
              </button>
            ))}
          </div>
        </header>

        {/* Summary Metrics */}
        <div className="analytics-summary">
          <div className="card-metric">
            <div className="metric-label">Avg DCS</div>
            <div className="metric-value data-l" style={{ color: 'var(--gold)' }}>
              {avgDCS.toFixed(1)}
            </div>
          </div>
          <div className="card-metric">
            <div className="metric-label">Tasks Done</div>
            <div className="metric-value data-l" style={{ color: 'var(--success)' }}>47</div>
          </div>
          <div className="card-metric">
            <div className="metric-label">Best Mode</div>
            <div className="metric-value data-l" style={{ color: getModeColor('DEEP_WORK') }}>8</div>
            <div className="metric-sublabel">Deep Work days</div>
          </div>
          <div className="card-metric">
            <div className="metric-label">Streak</div>
            <div className="metric-value data-l" style={{ color: 'var(--gold)' }}>12</div>
            <div className="metric-sublabel">days</div>
          </div>
        </div>

        {/* DCS Trend Chart (CSS-only bar chart) */}
        <section className="card analytics-chart-card">
          <h3 className="heading-3 text-tertiary">DAILY CAPACITY — 30 DAYS</h3>
          <div className="analytics-dcs-chart">
            {dcsHistory.map((d, i) => (
              <div key={i} className="analytics-bar-wrapper">
                <div
                  className="analytics-bar"
                  style={{
                    height: `${(d.value / 10) * 100}%`,
                    background: `linear-gradient(to top, var(--gold) 0%, rgba(201,169,110,0.3) 100%)`,
                  }}
                  title={`Day ${d.day}: ${d.value.toFixed(1)}`}
                />
              </div>
            ))}
          </div>
          <div className="analytics-chart-labels">
            <span className="caption text-tertiary">1</span>
            <span className="caption text-tertiary">15</span>
            <span className="caption text-tertiary">30</span>
          </div>
        </section>

        {/* Faction Hours Chart */}
        <section className="card analytics-chart-card">
          <h3 className="heading-3 text-tertiary">FACTION HOURS — THIS WEEK</h3>
          <div className="analytics-faction-chart">
            {FACTIONS.map(f => {
              const data = factions[f];
              const targetPct = 100;
              const actualPct = data ? (data.actualHours / data.targetHours) * 100 : 0;
              return (
                <div key={f} className="analytics-faction-row">
                  <span className="body-small" style={{ minWidth: 80, color: getFactionColor(f) }}>
                    {getFactionLabel(f)}
                  </span>
                  <div className="analytics-faction-bars">
                    <div className="analytics-faction-target" style={{ width: '100%' }}>
                      <div
                        className="analytics-faction-actual"
                        style={{
                          width: `${Math.min(actualPct, 100)}%`,
                          background: getFactionColor(f),
                        }}
                      />
                    </div>
                  </div>
                  <span className="data-s text-secondary" style={{ minWidth: 60, textAlign: 'right' }}>
                    {data?.actualHours || 0}h / {data?.targetHours || 0}h
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Mood × Energy Heatmap */}
        <section className="card analytics-chart-card">
          <h3 className="heading-3 text-tertiary">PEAK EFFICIENCY WINDOWS</h3>
          <div className="analytics-heatmap">
            <div className="analytics-heatmap-header">
              <span className="caption text-tertiary" style={{ width: 60 }}></span>
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => (
                <span key={d} className="caption text-tertiary analytics-heatmap-day">{d}</span>
              ))}
            </div>
            {['Morning', 'Afternoon', 'Evening', 'Night'].map(period => (
              <div key={period} className="analytics-heatmap-row">
                <span className="caption text-tertiary" style={{ width: 60 }}>{period}</span>
                {Array.from({ length: 7 }).map((_, j) => {
                  const val = Math.random() * 10;
                  const color = val > 7 ? 'var(--gold)' : val > 5 ? 'var(--mode-normal)' : val > 3 ? 'var(--warning)' : 'var(--bg-3)';
                  return (
                    <div
                      key={j}
                      className="analytics-heatmap-cell"
                      style={{ background: color, opacity: val > 0 ? 0.5 + val / 20 : 0.2 }}
                      title={`${val.toFixed(1)}`}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </section>

        {/* Deferral Patterns */}
        <section className="card analytics-chart-card">
          <h3 className="heading-3 text-tertiary">WHAT YOU KEEP AVOIDING</h3>
          <div className="analytics-deferrals">
            {[
              { title: 'Portfolio rebalancing spreadsheet', count: 5, faction: 'leverage', lastDeferred: '2 days ago' },
              { title: 'Dentist appointment booking', count: 3, faction: 'health', lastDeferred: '4 days ago' },
              { title: 'Write article outline', count: 2, faction: 'expression', lastDeferred: '1 day ago' },
            ].map((d, i) => (
              <div key={i} className="analytics-deferral-item">
                <div className="analytics-deferral-left">
                  <span className="body">{d.title}</span>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span className={`tag tag-${d.faction}`}>{getFactionLabel(d.faction)}</span>
                    <span className="caption text-tertiary">Last deferred: {d.lastDeferred}</span>
                  </div>
                </div>
                <span className="data-m text-danger">{d.count}×</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
