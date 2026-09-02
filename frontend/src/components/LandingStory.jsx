import React, { useRef } from 'react';
import { ChevronDown } from 'lucide-react';
import { LoginForm } from './ui/LoginForm';
import {
  fade,
  usePrefersReducedMotion,
  useStoryProgress,
  layerStyle,
} from '../hooks/useStoryProgress';

function Scene({ opacity, className, children, y = 22 }) {
  return (
    <div className={`landing-scene ${className || ''}`} style={layerStyle(opacity, y)}>
      {children}
    </div>
  );
}

function StaticLanding({ onGithubLogin }) {
  return (
    <div className="landing-static">
      <section>
        <h1 className="landing-display">WhatIsUp</h1>
        <p className="landing-support">
          Understand what your developer network is building and where it&apos;s headed.
        </p>
      </section>
      <LoginForm
        onGithubLogin={onGithubLogin}
        heading="Ready to see your network differently?"
        subheading="Connect with GitHub and start exploring what's changing around you."
        buttonLabel="Continue with GitHub"
        footnote="Built around public developer activity."
      />
    </div>
  );
}

export function LandingStory({ onGithubLogin }) {
  const trackRef = useRef(null);
  const reduced = usePrefersReducedMotion();
  const p = useStoryProgress(trackRef, reduced);

  if (reduced) {
    return <StaticLanding onGithubLogin={onGithubLogin} />;
  }

  const intro = fade(p, -0.02, 0, 0.35, 0.45);
  const login = fade(p, 0.4, 0.45, 1.05, 1.15);

  const scrollToLogin = () => {
    const track = trackRef.current;
    if (!track) return;
    const total = track.offsetHeight - window.innerHeight;
    window.scrollTo({ top: total * 0.55, behavior: 'smooth' });
  };

  return (
    <div ref={trackRef} className="landing-track">
      <div className="landing-stage">
        <Scene opacity={intro} className="landing-scene-center" y={12}>
          <h1 className="landing-display landing-display-title">WhatIsUp</h1>
          <p className="landing-support">
            Understand what your developer network is building and where it&apos;s headed.
          </p>
          <button type="button" className="landing-scroll-hint" onClick={scrollToLogin}>
            <span>Scroll to continue</span>
            <ChevronDown size={18} />
          </button>
        </Scene>

        <Scene opacity={login} className="landing-scene-center landing-scene-login" y={8}>
          <LoginForm
            onGithubLogin={onGithubLogin}
            heading="Ready to see your network differently?"
            subheading="Connect with GitHub and start exploring what's changing around you."
            buttonLabel="Continue with GitHub"
            footnote="Built around public developer activity."
          />
        </Scene>
      </div>
    </div>
  );
}
