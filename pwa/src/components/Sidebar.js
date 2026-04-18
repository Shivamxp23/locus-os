import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  House, CheckCircle, ClipboardText, Vault, GearSix,
  CalendarCheck, ChartBar,
} from '@phosphor-icons/react';
import { useApp } from '../context/AppContext';
import { getModeLabel } from '../utils/helpers';
import './Sidebar.css';

const navItems = [
  { path: '/',          label: 'Dashboard',  icon: House },
  { path: '/checkin',   label: 'Check-in',   icon: CalendarCheck },
  { path: '/today',     label: 'Today',      icon: CheckCircle },
  { path: '/projects',  label: 'Projects',   icon: ClipboardText },
  { path: '/vault',     label: 'Vault',      icon: Vault },
  { path: '/analytics', label: 'Analytics',  icon: ChartBar },
  { path: '/settings',  label: 'Settings',   icon: GearSix },
];

export default function Sidebar() {
  const { dcs, mode } = useApp();
  const location = useLocation();

  return (
    <aside className="sidebar" aria-label="Main navigation">
      {/* Logo */}
      <div className="sidebar-logo">
        <span className="sidebar-wordmark">Locus</span>
        <span className="sidebar-subtitle">COGNITIVE OS</span>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`sidebar-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={20} weight={isActive ? 'bold' : 'regular'} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom DCS readout */}
      <div className="sidebar-bottom">
        {dcs !== null && (
          <div className="sidebar-dcs">
            <span className="data-s">DCS {dcs?.toFixed(1)}</span>
            <span className="caption text-tertiary"> · {getModeLabel(mode)}</span>
          </div>
        )}
        <div className="sidebar-avatar-thumb">
          <div className="tree-mini" />
        </div>
      </div>
    </aside>
  );
}
