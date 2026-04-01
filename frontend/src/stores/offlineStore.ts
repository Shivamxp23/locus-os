import { create } from 'zustand';

interface OfflineState {
  isOnline: boolean;
  setOnline: (online: boolean) => void;
}

export const useOfflineStore = create<OfflineState>((set) => ({
  isOnline: navigator.onLine,
  setOnline: (online) => set({ isOnline: online }),
}));

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => useOfflineStore.getState().setOnline(true));
  window.addEventListener('offline', () => useOfflineStore.getState().setOnline(false));
}
