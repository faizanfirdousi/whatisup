import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Settings } from 'lucide-react';

export function Sidebar() {
  const navItems = [
    { name: 'Digest', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Network', path: '/network', icon: <Users size={20} /> },
    { name: 'Admin', path: '/admin', icon: <Settings size={20} /> },
  ];

  return (
    <aside style={{
      width: '240px',
      borderRight: '1px solid var(--glass-border)',
      background: 'var(--bg-secondary)',
      padding: '1.5rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '2rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          width: '32px', height: '32px',
          background: 'var(--accent-gradient)',
          borderRadius: 'var(--radius-md)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 'bold', color: 'white'
        }}>W</div>
        <h2 style={{ fontSize: '1.25rem', letterSpacing: '-0.03em' }}>WhatIsUp</h2>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              color: isActive ? 'white' : 'var(--text-secondary)',
              background: isActive ? 'rgba(255,255,255,0.05)' : 'transparent',
              fontWeight: isActive ? 500 : 400,
            })}
          >
            {item.icon}
            {item.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
