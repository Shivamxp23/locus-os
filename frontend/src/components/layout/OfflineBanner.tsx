import { useOfflineStore } from '../../stores/offlineStore';

export function OfflineBanner() {
  const isOnline = useOfflineStore((s) => s.isOnline);
  if (isOnline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-warning px-4 py-2 text-center text-sm font-medium text-white">
      You are offline — changes will sync when reconnected
    </div>
  );
}
