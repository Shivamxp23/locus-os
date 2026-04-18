import React, { useState, useEffect } from 'react';
import { getModeColor, getFactionColor, getFactionLabel } from '../utils/helpers';
import { api } from '../utils/api';
import './Analytics.css';

const TIME_RANGES = ['7D', '30D', '3M', 'All'];
const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function AnalyticsScreen() {
  const [range, setRange] = useState('30D');
  const [dcsTrend, setDcsTrend] = useState([]);
  const [factionHealth, setFactionHealth] = useState({});
  const [summary, setSummary] = useState({});
  const [completionRates, setCompletionRates] = useState({});
  const [avoidances, setAvoidances] = useState([]);
  const [loading, setLoading] = useState(true);

  const rangeToDays = { '7D': 7, '30D': 30, '3M': 90, 'All': 365 };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range]);

  const loadAll = async () => {
    setLoading(true);
    const days = rangeToDays[range] || 30;

    const [dcsRes, factionRes, summaryRes, ratesRes, avoidRes] = await Promise.all([
      api.getDcsTrend(days),
      api.getFactionHealth(),
      api.getAnalyticsSummary(),
      api.getCompletionRates(days),
      api.getAvoidanceReport(),
    ]);

    if (dcsRes?.trend) setDcsTrend(dcsRes.trend);
    if (factionRes?.factions) setFactionHealth(factionRes.factions);
    if (summaryRes) setSummary(summaryRes);
    if (ratesRes?.rates) setCompletionRates(ratesRes.rates);
    if (avoidRes?.avoidances) setAvoidances(avoidRes.avoidances);

    setLoading(false);
  };

  const avgDCS = dcsTrend.length > 0
    ? dcsTrend.reduce((s, d) => s + (d.dcs || 0), 0) / dcsTrend.filter(d => d.dcs).length
    : 0;

  const modeCount = dcsTrend.filter(d => d.mode === 'DEEP_WORK' || d.mode === 'PEAK').length;

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

        {loading ? (
          <div>
            {[1, 2, 3, 4].map(i => <div key={i} className="skeleton" style={{ height: 80, marginBottom: 12 }} />)}
          </div>
        ) : (
          <>
            {/* Summary Metrics — REAL DATA */}
            <div className="analytics-summary">
              <div className="card-metric">
                <div className="metric-label">Avg DCS</div>
                <div className="metric-value data-l" style={{ color: 'var(--gold)' }}>
                  {avgDCS > 0 ? avgDCS.toFixed(1) : '—'}
                </div>
              </div>
              <div className="card-metric">
                <div className="metric-label">Tasks Done</div>
                <div className="metric-value data-l" style={{ color: 'var(--success)' }}>
                  {summary.total_completed || 0}
                </div>
              </div>
              <div className="card-metric">
                <div className="metric-label">Peak Days</div>
                <div className="metric-value data-l" style={{ color: getModeColor('DEEP_WORK') }}>
                  {modeCount}
                </div>
                <div className="metric-sublabel">Deep Work + Peak</div>
              </div>
              <div className="card-metric">
                <div className="metric-label">Streak</div>
                <div className="metric-value data-l" style={{ color: 'var(--gold)' }}>
                  {summary.checkin_streak || 0}
                </div>
                <div className="metric-sublabel">days</div>
              </div>
            </div>

            {/* DCS Trend Chart — REAL DATA */}
            <section className="card analytics-chart-card">
              <h3 className="heading-3 text-tertiary">DAILY CAPACITY — {range}</h3>
              <div className="analytics-dcs-chart">
                {dcsTrend.length > 0 ? dcsTrend.map((d, i) => (
                  <div key={i} className="analytics-bar-wrapper">
                    <div
                      className="analytics-bar"
                      style={{
                        height: `${((d.dcs || 0) / 10) * 100}%`,
                        background: `linear-gradient(to top, var(--gold) 0%, rgba(201,169,110,0.3) 100%)`,
                      }}
                      title={`${d.date}: DCS ${d.dcs?.toFixed(1)} — ${d.mode}`}
                    />
                  </div>
                )) : (
                  <p className="body-small text-tertiary" style={{ padding: 20, textAlign: 'center', width: '100%' }}>
                    No DCS data yet — log your morning check-ins
                  </p>
                )}
              </div>
              {dcsTrend.length > 0 && (
                <div className="analytics-chart-labels">
                  <span className="caption text-tertiary">{dcsTrend[0]?.date?.slice(5)}</span>
                  <span className="caption text-tertiary">{dcsTrend[Math.floor(dcsTrend.length / 2)]?.date?.slice(5)}</span>
                  <span className="caption text-tertiary">{dcsTrend[dcsTrend.length - 1]?.date?.slice(5)}</span>
                </div>
              )}
            </section>

            {/* Faction Hours — REAL DATA */}
            <section className="card analytics-chart-card">
              <h3 className="heading-3 text-tertiary">FACTION HOURS — THIS WEEK</h3>
              <div className="analytics-faction-chart">
                {FACTIONS.map(f => {
                  const data = factionHealth[f] || {};
                  const actualPct = data.target_hours ? (data.actual_hours / data.target_hours) * 100 : 0;
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
                        {data.actual_hours || 0}h / {data.target_hours || 0}h
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Completion Rates by Faction — REAL DATA */}
            <section className="card analytics-chart-card">
              <h3 className="heading-3 text-tertiary">TASK COMPLETION BY FACTION</h3>
              <div className="analytics-faction-chart">
                {FACTIONS.map(f => {
                  const data = completionRates[f] || {};
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
                              width: `${data.rate || 0}%`,
                              background: getFactionColor(f),
                            }}
                          />
                        </div>
                      </div>
                      <span className="data-s text-secondary" style={{ minWidth: 80, textAlign: 'right' }}>
                        {data.completed || 0}/{data.total || 0} ({data.rate || 0}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Deferral Patterns — REAL DATA from avoidance report */}
            <section className="card analytics-chart-card">
              <h3 className="heading-3 text-tertiary">WHAT YOU KEEP AVOIDING</h3>
              <div className="analytics-deferrals">
                {avoidances.length > 0 ? avoidances.map((d, i) => (
                  <div key={i} className="analytics-deferral-item">
                    <div className="analytics-deferral-left">
                      <span className="body">{d.what}</span>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        {d.why && <span className="caption text-tertiary">Why: {d.why}</span>}
                        <span className="caption text-tertiary">Since: {d.first_seen}</span>
                      </div>
                    </div>
                    <span className="data-m text-danger">{d.frequency}×</span>
                  </div>
                )) : (
                  <p className="body-small text-tertiary" style={{ padding: 16, textAlign: 'center' }}>
                    No avoidance patterns recorded yet — log evening check-ins
                  </p>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
