import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import TreeOrganism from '../components/TreeOrganism';
import { getFactionColor, getFactionLabel } from '../utils/helpers';
import './Onboarding.css';

const FACTIONS = ['health', 'leverage', 'craft', 'expression'];

export default function OnboardingScreen() {
  const { setOnboarded, updateState, user } = useApp();
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [totalHours, setTotalHours] = useState(50);
  const [factionSplit, setFactionSplit] = useState({ health: 25, leverage: 30, craft: 25, expression: 20 });
  const [goals, setGoals] = useState({ health: '', leverage: '', craft: '', expression: '' });
  const [notifTimes] = useState({ morning: '07:00', afternoon: '13:00', evening: '19:00', night: '22:00' });

  const handleFinish = () => {
    // Calculate actual hours from percentages
    const factionData = {};
    FACTIONS.forEach(f => {
      const hours = Math.round((factionSplit[f] / 100) * totalHours * 10) / 10;
      factionData[f] = { targetHours: hours, actualHours: 0, completionRate: 0 };
    });

    updateState({
      user: { ...user, name: name || 'Shivam' },
      factions: factionData,
      settings: {
        reducedMotion: false,
        compactMode: false,
        notificationTimes: notifTimes,
      },
    });
    setOnboarded();
  };

  return (
    <div className="onboarding-page page-enter">
      {/* Step 1: The Promise */}
      {step === 1 && (
        <div className="onboarding-step onboarding-hero">
          <h1 className="display-l" style={{ color: 'var(--gold)' }}>Finally.</h1>
          <p className="body text-secondary" style={{ maxWidth: 360, textAlign: 'center', marginTop: 16 }}>
            A system that knows you. That works with how you actually are.
          </p>
          <button className="btn-primary" style={{ marginTop: 40 }} onClick={() => setStep(2)}>
            Begin Setup →
          </button>
        </div>
      )}

      {/* Step 2: Name */}
      {step === 2 && (
        <div className="onboarding-step">
          <h2 className="display-m">What do I call you?</h2>
          <input
            className="input-field onboarding-name-input"
            type="text"
            placeholder="Your name"
            value={name}
            onChange={e => setName(e.target.value)}
            autoFocus
          />
          <div className="onboarding-buttons">
            <button className="btn-secondary" onClick={() => setStep(1)}>← Back</button>
            <button className="btn-primary" onClick={() => setStep(3)} disabled={!name.trim()}>
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Faction Hours */}
      {step === 3 && (
        <div className="onboarding-step">
          <h2 className="display-m">How many hours a week do you have?</h2>
          <div className="onboarding-total-slider">
            <span className="data-l" style={{ color: 'var(--gold)' }}>{totalHours}h</span>
            <input
              type="range" min={20} max={80} value={totalHours}
              onChange={e => setTotalHours(parseInt(e.target.value))}
              className="locus-slider"
            />
          </div>

          <div className="onboarding-faction-splits">
            {FACTIONS.map(f => (
              <div key={f} className="onboarding-faction-split">
                <div className="onboarding-faction-info">
                  <div className="onboarding-faction-dot" style={{ background: getFactionColor(f) }} />
                  <span className="body">{getFactionLabel(f)}</span>
                  <span className="data-s text-tertiary" style={{ marginLeft: 'auto' }}>
                    {Math.round((factionSplit[f] / 100) * totalHours)}h ({factionSplit[f]}%)
                  </span>
                </div>
                <input
                  type="range" min={5} max={50} value={factionSplit[f]}
                  onChange={e => setFactionSplit({ ...factionSplit, [f]: parseInt(e.target.value) })}
                  className="locus-slider"
                  style={{ '--slider-color': getFactionColor(f) }}
                />
              </div>
            ))}
          </div>

          {/* Pie visualization */}
          <div className="onboarding-pie">
            <svg viewBox="0 0 100 100" width="120" height="120">
              {(() => {
                let offset = 0;
                const colors = { health: '#5A9E78', leverage: '#5B8FBF', craft: '#C97B4B', expression: '#9B79C4' };
                return FACTIONS.map(f => {
                  const pct = factionSplit[f];
                  const dashArray = pct * 3.14;
                  const dashOffset = -offset * 3.14;
                  offset += pct;
                  return (
                    <circle
                      key={f}
                      cx="50" cy="50" r="40"
                      fill="none"
                      stroke={colors[f]}
                      strokeWidth="12"
                      strokeDasharray={`${dashArray} ${314 - dashArray}`}
                      strokeDashoffset={dashOffset}
                      transform="rotate(-90 50 50)"
                    />
                  );
                });
              })()}
            </svg>
          </div>

          <div className="onboarding-buttons">
            <button className="btn-secondary" onClick={() => setStep(2)}>← Back</button>
            <button className="btn-primary" onClick={() => setStep(4)}>Next →</button>
          </div>
        </div>
      )}

      {/* Step 4: First Goals */}
      {step === 4 && (
        <div className="onboarding-step">
          <h2 className="display-m">Name one outcome for each faction.</h2>
          <p className="caption text-tertiary" style={{ marginBottom: 24 }}>
            All optional. I'll remind you to fill these in properly later.
          </p>
          {FACTIONS.map(f => (
            <div key={f} className="input-wrapper">
              <label className="input-label" style={{ color: getFactionColor(f) }}>
                {getFactionLabel(f)}
              </label>
              <input
                className="input-field"
                type="text"
                placeholder={
                  f === 'health' ? 'e.g., Run a half marathon' :
                  f === 'leverage' ? 'e.g., Launch SaaS to first 10 users' :
                  f === 'craft' ? 'e.g., Master distributed systems' :
                  'e.g., Write 12 blog posts'
                }
                value={goals[f]}
                onChange={e => setGoals({ ...goals, [f]: e.target.value })}
              />
            </div>
          ))}
          <div className="onboarding-buttons">
            <button className="btn-secondary" onClick={() => setStep(3)}>← Back</button>
            <button className="btn-primary" onClick={() => setStep(5)}>
              {Object.values(goals).some(g => g.trim()) ? 'Next →' : 'Skip →'}
            </button>
          </div>
        </div>
      )}

      {/* Step 5: Notifications */}
      {step === 5 && (
        <div className="onboarding-step">
          <h2 className="display-m">Remind me to check in:</h2>
          <div className="onboarding-notif-list">
            {['morning', 'afternoon', 'evening', 'night'].map(t => (
              <div key={t} className="onboarding-notif-row">
                <span className="body" style={{ textTransform: 'capitalize' }}>{t}</span>
                <span className="data-s text-secondary">{notifTimes[t]}</span>
              </div>
            ))}
          </div>
          <button className="btn-primary" style={{ marginTop: 24, width: '100%' }} onClick={() => setStep(6)}>
            Continue →
          </button>
          <div className="onboarding-buttons">
            <button className="btn-secondary" onClick={() => setStep(4)}>← Back</button>
          </div>
        </div>
      )}

      {/* Step 6: Ready */}
      {step === 6 && (
        <div className="onboarding-step onboarding-hero">
          <TreeOrganism compositeScore={5.0} size={200} />
          <h2 className="display-m" style={{ marginTop: 24 }}>Your second brain is ready.</h2>
          <button className="btn-primary" style={{ marginTop: 32 }} onClick={handleFinish}>
            Enter Locus →
          </button>
        </div>
      )}
    </div>
  );
}
