import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { path: '/dashboard', label: 'Home', icon: '🏠' },
  { path: '/tasks', label: 'Tasks', icon: '📋' },
  { path: '/goals', label: 'Goals', icon: '🎯' },
  { path: '/chat', label: 'Chat', icon: '💬' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
];

export function BottomNav() {
  const location = useLocation();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-default bg-background/95 backdrop-blur-sm safe-area-bottom">
      <div className="flex items-center justify-around py-2">
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors ${
                active ? 'text-secondary' : 'text-text-tertiary'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function Header({ title }: { title: string }) {
  return (
    <header className="sticky top-0 z-40 border-b border-default bg-background/95 backdrop-blur-sm">
      <div className="flex h-14 items-center px-4">
        <h1 className="text-lg font-semibold text-text-primary">{title}</h1>
      </div>
    </header>
  );
}
