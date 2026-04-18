import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import Sidebar from './components/Sidebar';
import BottomNav from './components/BottomNav';
import ToastContainer from './components/ToastContainer';
import QuickCapture from './components/QuickCapture';

// Screens
import Dashboard from './screens/Dashboard';
import CheckIn from './screens/CheckIn';
import Today from './screens/Today';
import Projects from './screens/Projects';
import Vault from './screens/Vault';
import Analytics from './screens/Analytics';
import Settings from './screens/Settings';
import Onboarding from './screens/Onboarding';
import Organism from './screens/Organism';

import './App.css';

function AppContent() {
  const { onboarded } = useApp();
  const [captureOpen, setCaptureOpen] = useState(false);

  if (!onboarded) {
    return <Onboarding />;
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/checkin" element={<CheckIn />} />
          <Route path="/today" element={<Today />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/vault" element={<Vault />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/organism" element={<Organism />} />
          <Route path="/capture" element={<CaptureRedirect openCapture={() => setCaptureOpen(true)} />} />
        </Routes>
      </main>
      <BottomNav />
      <ToastContainer />
      <QuickCapture isOpen={captureOpen} onClose={() => setCaptureOpen(false)} />
    </div>
  );
}

// Redirect /capture to open the QuickCapture sheet then go back
function CaptureRedirect({ openCapture }) {
  React.useEffect(() => {
    openCapture();
  }, [openCapture]);
  return <Dashboard />;
}

function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppContent />
      </AppProvider>
    </BrowserRouter>
  );
}

export default App;
