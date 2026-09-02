import React, { useRef } from 'react';
import { ChevronDown } from 'lucide-react';
import { LoginForm } from './ui/LoginForm';
import {
  fade,
  layerStyle,
  usePrefersReducedMotion,
  useStoryProgress,
} from '../hooks/useStoryProgress';

const EVENTS = [
  { label: 'Commit', x: 8, y: 18 },
  { label: 'Pull Request', x: 72, y: 14 },
  { label: 'Release', x: 42, y: 8 },
  { label: 'Repository', x: 12, y: 62 },
  { label: 'Issue', x: 78, y: 58 },
  { label: 'Contribution', x: 50, y: 78 },
  { label: 'Fork', x: 28, y: 38 },
];

const TECHS = [
  { name: 'Go', x: 10, y: 14 },
  { name: 'Kubernetes', x: 38, y: 10 },
  { name: 'TypeScript', x: 68, y: 12 },
  { name: 'Rust', x: 88, y: 18 },
  { name: 'Docker', x: 18, y: 28 },
  { name: 'React', x: 48, y: 24 },
  { name: 'AWS', x: 78, y: 30 },
  { name: 'Python', x: 8, y: 44 },
  { name: 'Node.js', x: 32, y: 42 },
  { name: 'AI', x: 52, y: 40 },
  { name: 'PostgreSQL', x: 74, y: 46 },
  { name: 'Swift', x: 92, y: 42 },
  { name: 'Terraform', x: 14, y: 60 },
  { name: 'Next.js', x: 42, y: 58 },
  { name: 'PyTorch', x: 64, y: 62 },
  { name: 'Java', x: 86, y: 58 },
  { name: 'Helm', x: 22, y: 76 },
  { name: 'GraphQL', x: 50, y: 78 },
  { name: 'Kafka', x: 72, y: 80 },
  { name: 'Flutter', x: 90, y: 74 },
];

const MOVEMENT = [
  { name: 'Developer Tooling', dir: '↑' },
  { name: 'Cloud Infrastructure', dir: '↑' },
  { name: 'AI Systems', dir: '→' },
  { name: 'Web Development', dir: '↓' },
];

const WORDS = ['Patterns.', 'Technologies.', 'Connections.', 'Direction.'];

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
        <p className="landing-kicker">WHATISUP</p>
        <h1>Your developer network is always changing.</h1>
        <p>People are building, learning, contributing, and moving toward new technologies.</p>
      </section>
      <section>
        <h2>GitHub shows you what happened.</h2>
        <p>Someone pushed code.</p>
        <p>A pull request was opened.</p>
        <p>A repository was released.</p>
      </section>
      <section>
        <h2>But activity alone doesn't show the bigger picture.</h2>
        <p>When you follow dozens of developers, individual events quickly become noise.</p>
      </section>
      <section>
        <h2>Patterns. Technologies. Connections. Direction.</h2>
      </section>
      <section>
        <h2>WhatIsUp shows you what it means.</h2>
        <p>
          It turns scattered public GitHub activity into a clearer picture of what your
          developer network is building.
        </p>
      </section>
      <section>
        <p>See what your network is building.</p>
        <p>See which technologies are gaining momentum.</p>
        <p>See what has actually changed.</p>
      </section>
      <section>
        <p>Because the important question isn't only what someone did.</p>
        <h2>It's where your network is moving.</h2>
      </section>
      <section>
        <h2>Your developer network, explained.</h2>
        <p>
          WhatIsUp helps you understand what developers in your network are building, which
          technologies are emerging, and what changes are worth your attention.
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

  const opening = fade(p, -0.02, 0, 0.07, 0.12);
  const github = fade(p, 0.1, 0.14, 0.2, 0.25);
  const noise = fade(p, 0.22, 0.27, 0.34, 0.4);
  const scatter = fade(p, 0.24, 0.3, 0.42, 0.48);
  const gather = Math.min(1, Math.max(0, (p - 0.3) / 0.14));
  const words = fade(p, 0.4, 0.45, 0.56, 0.61);
  const wordLocal = Math.min(1, Math.max(0, (p - 0.4) / 0.18));
  const techs = fade(p, 0.44, 0.48, 0.57, 0.62);
  const cluster = Math.min(1, Math.max(0, (p - 0.48) / 0.1));
  const reveal = fade(p, 0.56, 0.6, 0.66, 0.7);
  const value1 = fade(p, 0.69, 0.71, 0.78, 0.81);
  const value2 = fade(p, 0.73, 0.75, 0.78, 0.81);
  const value3 = fade(p, 0.76, 0.775, 0.78, 0.81);
  const did = fade(p, 0.805, 0.82, 0.835, 0.85);
  const where = fade(p, 0.845, 0.86, 0.89, 0.91);
  const explained = fade(p, 0.905, 0.92, 0.935, 0.955);
  const login = fade(p, 0.945, 0.96, 1.2, 1.3);

  const scrollToStory = () => {
    const track = trackRef.current;
    if (!track) return;
    const total = track.offsetHeight - window.innerHeight;
    window.scrollTo({ top: total * 0.13, behavior: 'smooth' });
  };

  return (
    <div ref={trackRef} className="landing-track">
      <div className="landing-stage">
        <Scene opacity={opening} className="landing-scene-center" y={12}>
          <p className="landing-kicker">WHATISUP</p>
          <h1 className="landing-display">Your developer network is always changing.</h1>
          <p className="landing-support">
            People are building, learning, contributing, and moving toward new technologies.
          </p>
          <button type="button" className="landing-scroll-hint" onClick={scrollToStory}>
            <span>Scroll to understand</span>
            <ChevronDown size={18} />
          </button>
        </Scene>

        <Scene opacity={github} className="landing-scene-center">
          <h2 className="landing-display landing-display-md">GitHub shows you what happened.</h2>
          <ul className="landing-examples">
            <li>Someone pushed code.</li>
            <li>A pull request was opened.</li>
            <li>A repository was released.</li>
          </ul>
        </Scene>

        <div className="landing-float-layer" aria-hidden="true">
          {EVENTS.map((event) => {
            const x = event.x + (50 - event.x) * gather;
            const y = event.y + (46 - event.y) * gather;
            const opacity = scatter * (1 - gather * 0.88);
            return (
              <span
                key={event.label}
                className="landing-chip"
                style={{
                  left: `${x}%`,
                  top: `${y}%`,
                  opacity,
                  transform: `translate(-50%, -50%) scale(${0.92 + gather * 0.12})`,
                }}
              >
                {event.label}
              </span>
            );
          })}
        </div>

        <Scene opacity={noise} className="landing-scene-center">
          <h2 className="landing-display landing-display-md">
            But activity alone doesn't show the bigger picture.
          </h2>
          <p className="landing-support">
            When you follow dozens of developers, individual events quickly become noise.
          </p>
        </Scene>

        <div className="landing-float-layer" aria-hidden="true">
          {TECHS.map((tech) => {
            const x = tech.x + (50 - tech.x) * cluster;
            const y = tech.y + (48 - tech.y) * cluster;
            return (
              <span
                key={tech.name}
                className="landing-chip landing-chip-tech"
                style={{
                  left: `${x}%`,
                  top: `${y}%`,
                  opacity: techs * (1 - cluster * 0.35),
                  transform: `translate(-50%, -50%) scale(${0.95 + cluster * 0.18})`,
                }}
              >
                {tech.name}
              </span>
            );
          })}
        </div>

        <Scene opacity={words} className="landing-scene-center landing-scene-words" y={8}>
          {WORDS.map((word, index) => {
            const start = index * 0.22;
            const local = fade(wordLocal, start, start + 0.08, start + 0.18, start + 0.3);
            const shown = local > 0.012;
            return (
              <p
                key={word}
                className="landing-word"
                style={{
                  opacity: local,
                  transform: `translate(-50%, calc(-50% + ${(1 - local) * 22}px)) scale(${0.98 + local * 0.04})`,
                  visibility: shown ? 'visible' : 'hidden',
                }}
              >
                {word}
              </p>
            );
          })}
        </Scene>

        <Scene opacity={reveal} className="landing-scene-center">
          <h2 className="landing-display landing-display-md">WhatIsUp shows you what it means.</h2>
          <p className="landing-support landing-support-narrow">
            It turns scattered public GitHub activity into a clearer picture of what your
            developer network is building.
          </p>
        </Scene>

        <div
          className="landing-scene landing-scene-center"
          style={{
            opacity: Math.max(value1, value2, value3) > 0.01 ? 1 : 0,
            visibility: Math.max(value1, value2, value3) > 0.01 ? 'visible' : 'hidden',
            pointerEvents: 'none',
          }}
        >
          <p className="landing-value" style={layerStyle(value1, 16)}>
            See what your network is building.
          </p>
          <p className="landing-value" style={layerStyle(value2, 16)}>
            See which technologies are gaining momentum.
          </p>
          <p className="landing-value" style={layerStyle(value3, 16)}>
            See what has actually changed.
          </p>
        </div>

        <Scene opacity={did} className="landing-scene-center">
          <p className="landing-support landing-support-wide">
            Because the important question isn't only what someone did.
          </p>
        </Scene>

        <Scene opacity={where} className="landing-scene-center" y={10}>
          <h2 className="landing-display">It's where your network is moving.</h2>
          <ul className="landing-movement">
            {MOVEMENT.map((row) => (
              <li key={row.name}>
                <span>{row.name}</span>
                <span className="landing-dir">{row.dir}</span>
              </li>
            ))}
          </ul>
        </Scene>

        <Scene opacity={explained} className="landing-scene-center">
          <h2 className="landing-display landing-display-md">Your developer network, explained.</h2>
          <p className="landing-support landing-support-narrow">
            WhatIsUp helps you understand what developers in your network are building, which
            technologies are emerging, and what changes are worth your attention.
          </p>
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
