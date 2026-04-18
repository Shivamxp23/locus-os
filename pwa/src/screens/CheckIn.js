import React, { useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { api } from '../utils/api';
import {
  calculateDCS, getModeColor, getModeBgColor,
  getModeLabel, getModeDescription, formatTime,
} from '../utils/helpers';
import './CheckIn.css';

export default function CheckInScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setDCS, setCheckin, addToast, checkins } = useApp();

  // Determine which check-in to show
  const getDefaultType = () => {
    if (location.state?.type) return location.state.type;
    const hour = new Date().getHours();
    if (hour < 12 && !checkins.morning) return 'morning';
    if (hour < 17 && !checkins.afternoon) return 'afternoon';
    if (hour < 21 && !checkins.evening) return 'evening';
    return 'night';
  };
  const [type] = useState(getDefaultType);

  if (type === 'morning') return <MorningCheckIn navigate={navigate} setDCS={setDCS} setCheckin={setCheckin} addToast={addToast} />;
  if (type === 'afternoon') return <AfternoonCheckIn navigate={navigate} setCheckin={setCheckin} addToast={addToast} />;
  if (type === 'evening') return <EveningCheckIn navigate={navigate} setCheckin={setCheckin} addToast={addToast} />;
  return <NightCheckIn navigate={navigate} setCheckin={setCheckin} addToast={addToast} />;
}

/* ═══ MORNING CHECK-IN ═══ */
function MorningCheckIn({ navigate, setDCS, setCheckin, addToast }) {
  const [step, setStep] = useState(1);
  const [energy, setEnergy] = useState(5);
  const [mood, setMood] = useState(5);
  const [sleep, setSleep] = useState(5);
  const [stress, setStress] = useState(5);
  const [intention, setIntention] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    const { dcs, mode } = calculateDCS(energy, mood, sleep, stress);
    const res = await api.morningCheckin({
      energy, mood, sleep_quality: sleep, stress, intention: intention || null,
    });
    setLoading(false);
    const finalDCS = res?.dcs || dcs;
    const finalMode = res?.mode || mode;
    setDCS(finalDCS, finalMode);
    setCheckin('morning', { energy, mood, sleep, stress, dcs: finalDCS, mode: finalMode });
    setResult({ dcs: finalDCS, mode: finalMode });
  }, [energy, mood, sleep, stress, intention, setDCS, setCheckin]);

  if (result) {
    return (
      <div className="checkin-page page-enter">
        <div className="checkin-result" style={{ '--mode-color': getModeColor(result.mode) }}>
          <div className="checkin-result-glow" style={{ background: getModeBgColor(result.mode) }} />
          <span className="checkin-dcs-number data-xl" style={{ color: getModeColor(result.mode) }}>
            {result.dcs.toFixed(1)}
          </span>
          <span
            className="mode-badge"
            style={{
              background: getModeBgColor(result.mode),
              color: getModeColor(result.mode),
              marginTop: 16,
            }}
          >
            {getModeLabel(result.mode)}
          </span>
          <p className="body text-secondary" style={{ marginTop: 16, textAlign: 'center', maxWidth: 300 }}>
            {getModeDescription(result.mode)}
          </p>
          <div className="checkin-result-breakdown">
            {[
              { label: 'E', value: energy },
              { label: 'M', value: mood },
              { label: 'S', value: sleep },
              { label: 'ST', value: stress },
            ].map(item => (
              <div key={item.label} className="card-metric" style={{ textAlign: 'center' }}>
                <div className="metric-label">{item.label}</div>
                <div className="data-m">{item.value}</div>
              </div>
            ))}
          </div>
          <button
            className="btn-primary"
            style={{ marginTop: 32 }}
            onClick={() => {
              addToast('Morning check-in logged ✓', 'success');
              navigate('/');
            }}
          >
            Begin Day →
          </button>
        </div>
      </div>
    );
  }

  const stepLabels = [
    null,
    { q: "How's your energy right now?", sub: 'Before coffee. Be honest.', low: '1 = can barely move', high: '10 = completely locked in' },
    { q: 'How do you feel emotionally?', sub: '', low: '1 = very low or distressed', high: '10 = genuinely good' },
    { q: 'How did you sleep?', sub: '', low: '1 = broken, exhausted', high: '10 = full and rested' },
    { q: "What's your background stress level?", sub: '', low: '1 = completely calm', high: '10 = overwhelmed' },
  ];

  const values = [null, energy, mood, sleep, stress];
  const setters = [null, setEnergy, setMood, setSleep, setStress];

  return (
    <div className="checkin-page page-enter">
      <div className="page-container">
        <header className="checkin-header">
          <h1 className="display-m">Good morning.</h1>
          <span className="data-s text-tertiary">{formatTime()}</span>
          <div className="checkin-progress-dots">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className={`checkin-dot ${i <= step ? 'active' : ''} ${i === step ? 'current' : ''}`} />
            ))}
          </div>
        </header>

        {step <= 4 ? (
          <div className="checkin-step" key={step}>
            <p className="heading-2 text-secondary" style={{ marginBottom: 8 }}>
              {stepLabels[step].q}
            </p>
            {stepLabels[step].sub && (
              <p className="body-small text-tertiary" style={{ marginBottom: 32 }}>
                {stepLabels[step].sub}
              </p>
            )}

            <div className="checkin-slider-container">
              <div className="checkin-slider-value data-l">{values[step]}</div>
              <input
                type="range"
                min={1}
                max={10}
                value={values[step]}
                onChange={e => setters[step](parseInt(e.target.value))}
                className="locus-slider"
              />
              <div className="checkin-slider-labels">
                <span className="caption text-tertiary">{stepLabels[step].low}</span>
                <span className="caption text-tertiary">{stepLabels[step].high}</span>
              </div>
            </div>

            <div className="checkin-nav-buttons">
              {step > 1 && (
                <button className="btn-secondary" onClick={() => setStep(s => s - 1)}>
                  ← Back
                </button>
              )}
              <button
                className="btn-primary"
                style={{ marginLeft: 'auto' }}
                onClick={() => {
                  if (step < 4) setStep(s => s + 1);
                  else setStep(5);
                }}
              >
                {step < 4 ? 'Next →' : 'Continue →'}
              </button>
            </div>
          </div>
        ) : (
          <div className="checkin-step">
            <p className="heading-2 text-secondary" style={{ marginBottom: 16 }}>
              Set your intention for today
            </p>
            <input
              type="text"
              className="input-field"
              placeholder="One thing that matters most..."
              value={intention}
              onChange={e => setIntention(e.target.value)}
            />
            <div className="checkin-nav-buttons" style={{ marginTop: 32 }}>
              <button className="btn-secondary" onClick={() => setStep(4)}>← Back</button>
              <button
                className="btn-primary"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? 'Calculating...' : 'Calculate →'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══ AFTERNOON CHECK-IN ═══ */
function AfternoonCheckIn({ navigate, setCheckin, addToast }) {
  const [mood, setMood] = useState(5);
  const [focus, setFocus] = useState(5);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    await api.afternoonCheckin({ mood, focus });
    setCheckin('afternoon', { mood, focus });
    addToast('Afternoon check-in logged ✓', 'success');
    setLoading(false);
    navigate('/');
  };

  return (
    <div className="checkin-page page-enter">
      <div className="page-container">
        <h1 className="display-m" style={{ marginBottom: 32 }}>Afternoon check-in.</h1>

        <div className="checkin-slider-container">
          <label className="input-label">Mood</label>
          <div className="checkin-slider-value data-l">{mood}</div>
          <input type="range" min={1} max={10} value={mood} onChange={e => setMood(parseInt(e.target.value))} className="locus-slider" />
        </div>

        <div className="checkin-slider-container" style={{ marginTop: 32 }}>
          <label className="input-label">Focus</label>
          <div className="checkin-slider-value data-l">{focus}</div>
          <input type="range" min={1} max={10} value={focus} onChange={e => setFocus(parseInt(e.target.value))} className="locus-slider" />
        </div>

        <button className="btn-primary" style={{ marginTop: 40, width: '100%' }} onClick={handleSubmit} disabled={loading}>
          {loading ? 'Logging...' : 'Log →'}
        </button>
      </div>
    </div>
  );
}

/* ═══ EVENING CHECK-IN ═══ */
function EveningCheckIn({ navigate, setCheckin, addToast }) {
  const [didToday, setDidToday] = useState('');
  const [avoided, setAvoided] = useState(false);
  const [avoidedWhat, setAvoidedWhat] = useState('');
  const [tomorrowPriority, setTomorrowPriority] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    await api.eveningCheckin({
      did_today: didToday,
      avoided: avoided ? avoidedWhat : null,
      avoided_reason: null,
      tomorrow_priority: tomorrowPriority,
    });
    setCheckin('evening', { didToday, avoided: avoided ? avoidedWhat : null, tomorrowPriority });
    addToast('Evening check-in logged ✓', 'success');
    setLoading(false);
    navigate('/');
  };

  return (
    <div className="checkin-page page-enter">
      <div className="page-container">
        <h1 className="display-m" style={{ marginBottom: 32 }}>End of day.</h1>

        <div className="input-wrapper">
          <label className="input-label">What did you actually do?</label>
          <textarea className="input-field" rows={3} value={didToday} onChange={e => setDidToday(e.target.value)} />
        </div>

        <div className="input-wrapper">
          <label className="input-label">Did you avoid anything?</label>
          <div style={{ display: 'flex', gap: 8, marginBottom: avoided ? 12 : 0 }}>
            <button className={`btn-secondary ${avoided ? '' : 'active-toggle'}`} onClick={() => setAvoided(false)}
              style={!avoided ? { background: 'var(--bg-3)', borderColor: 'var(--gold)' } : {}}>No</button>
            <button className={`btn-secondary ${avoided ? 'active-toggle' : ''}`} onClick={() => setAvoided(true)}
              style={avoided ? { background: 'var(--bg-3)', borderColor: 'var(--gold)' } : {}}>Yes</button>
          </div>
          {avoided && (
            <textarea className="input-field" placeholder="What and why?" rows={2} value={avoidedWhat} onChange={e => setAvoidedWhat(e.target.value)} />
          )}
        </div>

        <div className="input-wrapper">
          <label className="input-label">Tomorrow's one priority:</label>
          <input className="input-field" type="text" value={tomorrowPriority} onChange={e => setTomorrowPriority(e.target.value)} />
        </div>

        <button className="btn-primary" style={{ marginTop: 16, width: '100%' }} onClick={handleSubmit} disabled={loading || !didToday.trim()}>
          {loading ? 'Logging...' : 'Log →'}
        </button>
      </div>
    </div>
  );
}

/* ═══ NIGHT CHECK-IN ═══ */
function NightCheckIn({ navigate, setCheckin, addToast }) {
  const [reflection, setReflection] = useState('');
  const [sleepIntention, setSleepIntention] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    await api.nightCheckin({
      reflection: reflection || null,
      sleep_intention: sleepIntention || null,
    });
    setCheckin('night', { reflection, sleepIntention });
    addToast('Night check-in logged ✓', 'success');
    setLoading(false);
    navigate('/');
  };

  return (
    <div className="checkin-page page-enter checkin-night-mode">
      <div className="page-container">
        <h1 className="display-m" style={{ marginBottom: 32, opacity: 0.8 }}>Before you sleep.</h1>

        <div className="input-wrapper">
          <label className="input-label">Reflection</label>
          <textarea className="input-field" placeholder="What stuck with you today?" rows={3} value={reflection} onChange={e => setReflection(e.target.value)} />
        </div>

        <div className="input-wrapper">
          <label className="input-label">Sleep intention</label>
          <input className="input-field" type="text" placeholder="Aiming for ___ hours" value={sleepIntention} onChange={e => setSleepIntention(e.target.value)} />
        </div>

        <button className="btn-primary" style={{ marginTop: 16, width: '100%' }} onClick={handleSubmit} disabled={loading}>
          {loading ? 'Logging...' : 'Log →'}
        </button>
      </div>
    </div>
  );
}
