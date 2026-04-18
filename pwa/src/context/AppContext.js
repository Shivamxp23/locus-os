import React, { createContext, useContext, useState, useCallback } from 'react';

const AppContext = createContext();

// Default user state
const defaultState = {
  user: {
    name: 'Shivam',
    timezone: 'Asia/Kolkata',
  },
  dcs: null,
  mode: null,
  checkins: {
    morning: null,
    afternoon: null,
    evening: null,
    night: null,
  },
  factions: {
    health:     { targetHours: 17.5, actualHours: 0, completionRate: 0 },
    leverage:   { targetHours: 20,   actualHours: 0, completionRate: 0 },
    craft:      { targetHours: 15,   actualHours: 0, completionRate: 0 },
    expression: { targetHours: 7.5,  actualHours: 0, completionRate: 0 },
  },
  tasks: [],
  settings: {
    reducedMotion: false,
    compactMode: false,
    notificationTimes: {
      morning: '07:00',
      afternoon: '13:00',
      evening: '19:00',
      night: '22:00',
    },
  },
  onboarded: false,
};

export function AppProvider({ children }) {
  const [state, setState] = useState(() => {
    const saved = localStorage.getItem('locus-state');
    if (saved) {
      try {
        return { ...defaultState, ...JSON.parse(saved) };
      } catch { return defaultState; }
    }
    return defaultState;
  });

  const [toasts, setToasts] = useState([]);

  const updateState = useCallback((updates) => {
    setState(prev => {
      const next = { ...prev, ...updates };
      localStorage.setItem('locus-state', JSON.stringify(next));
      return next;
    });
  }, []);

  const setDCS = useCallback((dcs, mode) => {
    updateState({ dcs, mode });
  }, [updateState]);

  const setCheckin = useCallback((type, data) => {
    setState(prev => {
      const next = {
        ...prev,
        checkins: { ...prev.checkins, [type]: data },
      };
      localStorage.setItem('locus-state', JSON.stringify(next));
      return next;
    });
  }, []);

  const addToast = useCallback((message, type = 'success', duration = 3000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, duration);
  }, []);

  const setOnboarded = useCallback(() => {
    updateState({ onboarded: true });
  }, [updateState]);

  const value = {
    ...state,
    toasts,
    updateState,
    setDCS,
    setCheckin,
    addToast,
    setOnboarded,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
