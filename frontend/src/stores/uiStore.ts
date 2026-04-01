import { create } from 'zustand';

interface UiState {
  activePage: string;
  setActivePage: (page: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activePage: 'dashboard',
  setActivePage: (page) => set({ activePage: page }),
}));
