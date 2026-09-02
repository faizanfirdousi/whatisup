import React from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from './Sidebar';

export function Layout({ children }) {
  return (
    <div className="app-container">
      <Sidebar />
      <div className="page-shell">
        <main className="main-content">{children}</main>
        <footer className="site-footer">
          <span>WhatIsUp</span>
          <Link to="/terms">Terms of Service</Link>
          <Link to="/privacy">Privacy Policy</Link>
        </footer>
      </div>
    </div>
  );
}
