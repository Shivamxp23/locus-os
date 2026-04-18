import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from '@phosphor-icons/react';
import TreeOrganism from '../components/TreeOrganism';
import { useApp } from '../context/AppContext';
import { getFactionColor, getFactionLabel } from '../utils/helpers';
import './Organism.css';

const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function OrganismScreen() {
  const navigate = useNavigate();
  const { dcs, factions } = useApp();
  const [compositeScore, setCompositeScore] = useState(5.0);

  useEffect(() => {
    const avgCompletion = FACTIONS.reduce((sum, f) => sum + (factions[f]?.completionRate || 0), 0) / 4;
    const avgDcs = dcs || 5.0;
    const score = ((avgCompletion / 100) * 0.35 + (avgDcs / 10) * 0.30 + 0.6 * 0.20 + 0.5 * 0.15) * 10;
    setCompositeScore(Math.min(10, Math.max(0, score)));
  }, [factions, dcs]);

  const stateLabels = {
    dead: 'Systems critical.',
    struggling: 'Needs attention.',
    growing: 'Moving forward.',
    thriving: 'Thriving.',
    peak: 'Peak condition.',
  };

  const getState = () => {
    if (compositeScore < 2) return 'dead';
    if (compositeScore < 4) return 'struggling';
    if (compositeScore < 6) return 'growing';
    if (compositeScore < 8) return 'thriving';
    return 'peak';
  };

  return (
    <div className="organism-page page-enter">
      <button className="btn-icon organism-back" onClick={() => navigate('/')}>
        <ArrowLeft size={20} />
      </button>

      <div className="organism-content">
        <TreeOrganism compositeScore={compositeScore} size={300} />

        <div className="organism-score">
          <span className="data-xl" style={{ color: 'var(--gold)' }}>
            {compositeScore.toFixed(1)}
          </span>
          <span className="display-m text-secondary" style={{ marginTop: 8 }}>
            {stateLabels[getState()]}
          </span>
        </div>

        <div className="organism-factions">
          {FACTIONS.map(f => {
            const data = factions[f];
            return (
              <div key={f} className="organism-faction-bar">
                <div className="organism-faction-label">
                  <div className="organism-faction-dot" style={{ background: getFactionColor(f) }} />
                  <span className="body-small">{getFactionLabel(f)}</span>
                </div>
                <div className="progress-bar" style={{ flex: 1 }}>
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${data?.completionRate || 0}%`, background: getFactionColor(f) }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <p className="caption text-tertiary" style={{ textAlign: 'center', marginTop: 24 }}>
          Last updated — this morning's check-in ·{' '}
          <button className="btn-ghost" style={{ display: 'inline', padding: 0, fontSize: 11 }} onClick={() => navigate('/checkin')}>
            Log now →
          </button>
        </p>
      </div>
    </div>
  );
}
