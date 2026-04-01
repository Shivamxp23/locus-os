import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useUserStore } from './stores/userStore';
import { OfflineBanner } from './components/layout/OfflineBanner';
import { BottomNav } from './components/layout/Navigation';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Tasks from './pages/Tasks';
import Goals from './pages/Goals';
import Chat from './pages/Chat';
import Settings from './pages/Settings';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useUserStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const token = useUserStore((s) => s.token);

  return (
    <BrowserRouter>
      <OfflineBanner />
      <Routes>
        <Route path="/login" element={!token ? <Login /> : <Navigate to="/dashboard" replace />} />
        <Route path="/register" element={!token ? <Register /> : <Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/tasks" element={<ProtectedRoute><Tasks /></ProtectedRoute>} />
        <Route path="/goals" element={<ProtectedRoute><Goals /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to={token ? '/dashboard' : '/login'} replace />} />
      </Routes>
      {token && <BottomNav />}
    </BrowserRouter>
  );
}
