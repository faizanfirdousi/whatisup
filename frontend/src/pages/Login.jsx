import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LandingStory } from '../components/LandingStory';

export function Login() {
  const { loginWithGithub, user, loading } = useAuth();

  if (!loading && user) {
    return <Navigate to="/" replace />;
  }

  return (
    <main className="landing">
      <div className="landing-bg" aria-hidden="true" />
      <div className="landing-scrim" aria-hidden="true" />

      <header className="landing-nav">
        <span className="landing-mark">W</span>
        <div className="landing-nav-brand">
          <strong>WhatIsUp</strong>
          <span>Developer network intelligence</span>
        </div>
      </header>

      <LandingStory onGithubLogin={loginWithGithub} />
    </main>
  );
}
