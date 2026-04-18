import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  House, CheckCircle, CalendarCheck, Vault, GearSix,
} from '@phosphor-icons/react';
import './BottomNav.css';

const navItems = [
  { path: '/',          label: 'Home',      icon: House },
  { path: '/today',     label: 'Tasks',     icon: CheckCircle },
  { path: '/checkin',   label: 'Check-in',  icon: CalendarCheck },
  { path: '/vault',     label: 'Vault',     icon: Vault },
  { path: '/settings',  label: 'Settings',  icon: GearSix },
];

export default function BottomNav() {
  const location = useLocation();

  return (
    <nav className="bottom-nav" aria-label="Mobile navigation">
      {navItems.map(item => {
        const Icon = item.icon;
        const isActive = location.pathname === item.path;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            className={`bottom-nav-item ${isActive ? 'active' : ''}`}
          >
            {isActive && <div className="bottom-nav-indicator" />}
            <Icon size={22} weight={isActive ? 'fill' : 'regular'} />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
