import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function Sidebar() {
  const { user, logout } = useAuth();

  const navItems = [
    { name: 'Home', path: '/' },
    { name: 'Network', path: '/network' },
  ];

  if (user?.is_builder) {
    navItems.push({ name: 'Admin', path: '/admin' });
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-mark">W</span>
        <h2>WhatIsUp</h2>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) => (isActive ? 'active' : undefined)}
          >
            {item.name}
          </NavLink>
        ))}
      </nav>

      {user && (
        <div className="sidebar-user">
          <div className="sidebar-user-row">
            <img
              src={`https://github.com/${user.github_username}.png`}
              alt={user.github_username}
            />
            <span>@{user.github_username}</span>
          </div>
          <button type="button" className="sidebar-logout" onClick={logout}>
            Log out
          </button>
        </div>
      )}
    </aside>
  );
}
