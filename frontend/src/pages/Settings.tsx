import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useUserStore } from '../stores/userStore';
import { useOfflineStore } from '../stores/offlineStore';
import { Card, Badge, Button } from '../components/ui';
import { Header } from '../components/layout/Navigation';
import { flushQueue } from '../services/offline';
import { syncCache } from '../services/sync';

export default function Settings() {
  const token = useUserStore((s) => s.token);
  const email = useUserStore((s) => s.email);
  const isOnline = useOfflineStore((s) => s.isOnline);
  const logout = useUserStore((s) => s.logout);
  const navigate = useNavigate();
  const [integrations, setIntegrations] = useState<{ notion: { connected: boolean }; google_calendar: { connected: boolean }; telegram: { connected: boolean } } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');

  useEffect(() => {
    if (!token) return;
    api.integrations.status(token).then(setIntegrations).catch(() => {});
  }, [token]);

  async function handleSync() {
    if (!token) return;
    setSyncing(true);
    setSyncMsg('Syncing...');
    try {
      await flushQueue(token);
      await syncCache(token);
      setSyncMsg('Sync complete!');
    } catch {
      setSyncMsg('Sync failed. Will retry when online.');
    } finally {
      setSyncing(false);
    }
  }

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      <Header title="Settings" />
      <div className="px-4 py-4 space-y-4">
        <Card>
          <div className="font-medium text-text-primary">{email}</div>
          <div className="flex items-center gap-2 mt-1">
            <Badge color={isOnline ? 'success' : 'warning'}>{isOnline ? 'Online' : 'Offline'}</Badge>
          </div>
        </Card>

        <Card>
          <h3 className="font-medium text-text-primary mb-3">Sync</h3>
          <Button onClick={handleSync} disabled={syncing || !isOnline} fullWidth>
            {syncing ? 'Syncing...' : 'Sync Now'}
          </Button>
          {syncMsg && <div className="mt-2 text-sm text-text-secondary">{syncMsg}</div>}
        </Card>

        <Card>
          <h3 className="font-medium text-text-primary mb-3">Integrations</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Google Calendar</span>
              <Badge color={integrations?.google_calendar?.connected ? 'success' : 'default'}>
                {integrations?.google_calendar?.connected ? 'Connected' : 'Not connected'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Notion</span>
              <Badge color={integrations?.notion?.connected ? 'success' : 'default'}>
                {integrations?.notion?.connected ? 'Connected' : 'Not connected'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Telegram</span>
              <Badge color={integrations?.telegram?.connected ? 'success' : 'default'}>
                {integrations?.telegram?.connected ? 'Connected' : 'Not connected'}
              </Badge>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="font-medium text-text-primary mb-3">About</h3>
          <div className="text-sm text-text-secondary">
            <div>Locus v0.1.0</div>
            <div className="mt-1">Your intelligence. Organized.</div>
          </div>
        </Card>

        <Button variant="ghost" onClick={handleLogout} fullWidth className="text-danger">
          Sign Out
        </Button>
      </div>
    </div>
  );
}
