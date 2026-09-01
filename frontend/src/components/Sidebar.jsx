import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export function Sidebar() {
  const { user, logout } = useAuth();
  
  const navItems = [
    { name: 'Home', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Network', path: '/network', icon: <Users size={20} /> },
  ];

  if (user?.is_builder) {
    navItems.push({ name: 'Admin', path: '/admin', icon: <Settings size={20} /> });
  }

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

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
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

      {user && (
        <div style={{
          borderTop: '1px solid var(--glass-border)',
          paddingTop: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
            <img 
              src={`https://github.com/${user.github_username}.png`} 
              alt={user.github_username}
              style={{ width: '32px', height: '32px', borderRadius: '50%' }}
            />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.9rem' }}>
              @{user.github_username}
            </span>
          </div>
          <button 
            onClick={logout}
            style={{
              background: 'transparent', border: 'none', color: 'var(--text-tertiary)',
              cursor: 'pointer', padding: '0.25rem', display: 'flex'
            }}
            title="Log out"
          >
            <LogOut size={18} />
          </button>
        </div>
      )}
    </aside>
  );
}
