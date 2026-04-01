import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useUserStore } from '../stores/userStore';
import { useOfflineStore } from '../stores/offlineStore';
import { Card, Badge, Button } from '../components/ui';
import { Header } from '../components/layout/Navigation';
import { flushQueue } from '../services/offline';
import { syncCache } from '../services/sync';

export default function Settings() {
  const token = useUserStore((s) => s.token);
  const isOnline = useOfflineStore((s) => s.isOnline);
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

  return (
    <div className="min-h-screen bg-background pb-20">
      <Header title="Settings" />
      <div className="px-4 py-4 space-y-4">
        <Card>
          <div className="font-medium text-text-primary">Locus — Single User</div>
          <div className="flex items-center gap-2 mt-1">
            <Badge color={isOnline ? 'success' : 'warning'}>{isOnline ? 'Online' : 'Offline'}</Badge>
            <span className="text-xs text-text-tertiary">v0.1.0</span>
          </div>
        </Card>

        <Card>
          <h3 className="font-medium text-text-primary mb-3">Sync</h3>
          <p className="text-sm text-text-secondary mb-3">Push offline changes to the server and pull the latest data.</p>
          <Button onClick={handleSync} disabled={syncing || !isOnline} fullWidth>
            {syncing ? 'Syncing...' : 'Sync Now'}
          </Button>
          {syncMsg && <div className="mt-2 text-sm text-text-secondary">{syncMsg}</div>}
        </Card>

        <Card>
          <h3 className="font-medium text-text-primary mb-3">Integrations</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-text-primary">Google Calendar</div>
                <div className="text-xs text-text-tertiary">Reads events, writes time blocks</div>
              </div>
              <Badge color={integrations?.google_calendar?.connected ? 'success' : 'default'}>
                {integrations?.google_calendar?.connected ? 'Connected' : 'Not connected'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-text-primary">Notion</div>
                <div className="text-xs text-text-tertiary">Bidirectional task sync (60s poll)</div>
              </div>
              <Badge color={integrations?.notion?.connected ? 'success' : 'default'}>
                {integrations?.notion?.connected ? 'Connected' : 'Not connected'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-text-primary">Telegram</div>
                <div className="text-xs text-text-tertiary">Voice + text ingestion</div>
              </div>
              <Badge color={integrations?.telegram?.connected ? 'success' : 'default'}>
                {integrations?.telegram?.connected ? 'Connected' : 'Not connected'}
              </Badge>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="font-medium text-text-primary mb-3">About</h3>
          <div className="text-sm text-text-secondary space-y-1">
            <div>Locus v0.1.0 — Personal Cognitive Operating System</div>
            <div>Your intelligence. Organized.</div>
            <div className="text-xs text-text-tertiary mt-2">
              Backend: api.locusapp.online<br />
              Frontend: locusapp.online
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

