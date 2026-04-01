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
const SINGLE_USER_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwNzQ1ODk5My0xNTkzLTQ2YzEtYjU5Ni0xZTBhMzA0Y2Q3ZWMiLCJleHAiOjE3NzUwMjA1MTEsInR5cGUiOiJhY2Nlc3MifQ.X3VU7t8ZKeIMQ1J6zOrMlRf3pfJ887hPrp3Mz3oTBwU';
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
