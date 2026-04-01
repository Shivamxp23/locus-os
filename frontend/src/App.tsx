import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useUserStore } from './stores/userStore';
import { OfflineBanner } from './components/layout/OfflineBanner';
import { BottomNav } from './components/layout/Navigation';
import Dashboard from './pages/Dashboard';
import Tasks from './pages/Tasks';
import Goals from './pages/Goals';
import Chat from './pages/Chat';
import Settings from './pages/Settings';

// Single-user mode — auto-authenticated
const SINGLE_USER_TOKEN = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiMDc0NTg5OTMtMTU5My00NmMxLWI1OTYtMWUwYTMwNGNkN2VjIiwgImV4cCI6IDE4MDY1NzUwNzgsICJ0eXBlIjogImFjY2VzcyJ9.d9YPC1TeEvU4F6eqmdN4jc_1gT9tUPRbP9e-dT4xd6Q';
const SINGLE_USER_EMAIL = 'locus@locus.dev';

// Auto-set token on load
const stored = localStorage.getItem('locus_token');
if (!stored) {
  localStorage.setItem('locus_token', SINGLE_USER_TOKEN);
  localStorage.setItem('locus_email', SINGLE_USER_EMAIL);
} else if (localStorage.getItem('locus_email') !== SINGLE_USER_EMAIL) {
  localStorage.setItem('locus_token', SINGLE_USER_TOKEN);
  localStorage.setItem('locus_email', SINGLE_USER_EMAIL);
}

export default function App() {
  return (
    <BrowserRouter>
      <OfflineBanner />
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/goals" element={<Goals />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <BottomNav />
    </BrowserRouter>
  );
}
