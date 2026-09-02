import React from 'react';
import { Link } from 'react-router-dom';

function GitHubMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 10.0.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.564 9.564 0 0 1 12 6.844a9.56 9.56 0 0 1 2.504.337c1.909-1.294 2.748-1.025 2.748-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.936.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48A10.02 10.02 0 0 0 22 12c0-5.523-4.477-10-10-10z"
      />
    </svg>
  );
}

export function LoginForm({
  onGithubLogin,
  heading = 'Ready to see your network differently?',
  subheading = "Connect with GitHub and start exploring what's changing around you.",
  buttonLabel = 'Continue with GitHub',
  footnote = 'Built around public developer activity.',
}) {
  return (
    <div className="login-panel">
      <div className="login-panel-header">
        <h1>{heading}</h1>
        <p>{subheading}</p>
      </div>

      <button type="button" onClick={onGithubLogin} className="login-github">
        <GitHubMark />
        {buttonLabel}
      </button>

      <p className="login-footnote">{footnote}</p>

      <p className="login-legal">
        By continuing you agree to the{' '}
        <Link to="/terms">Terms</Link> and <Link to="/privacy">Privacy Policy</Link>.
      </p>
    </div>
  );
}
