import { create } from 'zustand';

interface UserState {
  token: string | null;
  email: string | null;
  setToken: (token: string, email: string) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  token: localStorage.getItem('locus_token'),
  email: localStorage.getItem('locus_email'),
  setToken: (token, email) => {
    localStorage.setItem('locus_token', token);
    localStorage.setItem('locus_email', email);
    set({ token, email });
  },
  logout: () => {
    localStorage.removeItem('locus_token');
    localStorage.removeItem('locus_email');
    set({ token: null, email: null });
  },
}));
