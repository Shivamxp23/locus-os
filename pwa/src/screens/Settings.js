import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import './Settings.css';

export default function SettingsScreen() {
  const { user, settings, factions, updateState, addToast } = useApp();
  const [name, setName] = useState(user.name);

  const handleSaveName = () => {
    updateState({ user: { ...user, name } });
    addToast('Name updated ✓', 'success');
  };

  const toggleSetting = (key) => {
    updateState({
      settings: { ...settings, [key]: !settings[key] },
    });
  };

  return (
    <div className="page-enter">
      <div className="page-container settings-page">
        <h1 className="display-l" style={{ marginBottom: 'var(--space-32)' }}>Settings</h1>

        {/* Profile */}
        <section className="settings-section">
          <h2 className="heading-3 text-tertiary settings-section-title">PROFILE</h2>
          <div className="card settings-group">
            <div className="input-wrapper">
              <label className="input-label">Name</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <input className="input-field" type="text" value={name} onChange={e => setName(e.target.value)} />
                <button className="btn-primary" style={{ padding: '10px 16px' }} onClick={handleSaveName}>Save</button>
              </div>
            </div>
          </div>
        </section>

        {/* Factions */}
        <section className="settings-section">
          <h2 className="heading-3 text-tertiary settings-section-title">FACTIONS</h2>
          <div className="card settings-group">
            {['health', 'leverage', 'craft', 'expression'].map(f => (
              <div key={f} className="settings-faction-row">
                <span className="body" style={{ textTransform: 'capitalize', minWidth: 100 }}>{f}</span>
                <span className="data-s text-secondary">{factions[f]?.targetHours || 0}h / week</span>
              </div>
            ))}
          </div>
        </section>

        {/* Notifications */}
        <section className="settings-section">
          <h2 className="heading-3 text-tertiary settings-section-title">NOTIFICATIONS</h2>
          <div className="card settings-group">
            {['morning', 'afternoon', 'evening', 'night'].map(time => (
              <div key={time} className="settings-notif-row">
                <span className="body" style={{ textTransform: 'capitalize' }}>{time} Check-in</span>
                <span className="data-s text-secondary">{settings.notificationTimes?.[time] || '—'}</span>
              </div>
            ))}
            <div className="settings-toggle-row" style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
              <span className="body">Push Notifications</span>
              <button 
                className="btn-secondary" 
                style={{ padding: '6px 14px', fontSize: 12 }}
                onClick={async () => {
                  try {
                    const { subscribeToPushNotifications } = await import('../utils/pushUtils');
                    await subscribeToPushNotifications();
                    addToast('Push enabled ✓', 'success');
                  } catch (err) {
                    addToast('Push failed to enable', 'error');
                  }
                }}
              >
                Enable
              </button>
            </div>
          </div>
        </section>

        {/* Appearance */}
        <section className="settings-section">
          <h2 className="heading-3 text-tertiary settings-section-title">APPEARANCE</h2>
          <div className="card settings-group">
            <div className="settings-toggle-row">
              <div>
                <span className="body">Theme</span>
                <span className="body-small text-tertiary"> Dark (default)</span>
              </div>
            </div>
            <div className="settings-toggle-row">
              <span className="body">Reduced Motion</span>
              <button
                className={`settings-toggle ${settings.reducedMotion ? 'active' : ''}`}
                onClick={() => toggleSetting('reducedMotion')}
                role="switch"
                aria-checked={settings.reducedMotion}
              >
                <div className="settings-toggle-thumb" />
              </button>
            </div>
            <div className="settings-toggle-row">
              <span className="body">Compact Mode</span>
              <button
                className={`settings-toggle ${settings.compactMode ? 'active' : ''}`}
                onClick={() => toggleSetting('compactMode')}
                role="switch"
                aria-checked={settings.compactMode}
              >
                <div className="settings-toggle-thumb" />
              </button>
            </div>
          </div>
        </section>

        {/* System */}
        <section className="settings-section">
          <h2 className="heading-3 text-tertiary settings-section-title">SYSTEM</h2>
          <div className="card settings-group">
            <div className="settings-toggle-row">
              <span className="body">Export Data (JSON)</span>
              <button className="btn-secondary" style={{ padding: '6px 14px', fontSize: 12 }}>Export</button>
            </div>
            <div className="settings-toggle-row">
              <span className="body">Vault Sync Status</span>
              <span className="badge badge-working">Synced</span>
            </div>
            <button className="btn-secondary" style={{ width: '100%', marginTop: 8 }}>Force Sync</button>
          </div>
        </section>

        {/* Danger Zone */}
        <section className="settings-section settings-danger">
          <h2 className="heading-3 text-tertiary settings-section-title">DANGER ZONE</h2>
          <div className="card settings-group" style={{ borderLeft: '3px solid var(--danger)' }}>
            <button className="btn-ghost text-danger">Clear all check-in data</button>
            <button className="btn-ghost text-danger">Reset faction stats</button>
          </div>
        </section>
      </div>
    </div>
  );
}
