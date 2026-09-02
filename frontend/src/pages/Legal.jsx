import React from 'react';
import { Link } from 'react-router-dom';

export function TermsOfService() {
  return (
    <article className="legal-page panel">
      <h1>Terms of Service</h1>
      <p>
        WhatIsUp helps you follow public GitHub activity from people in your network.
        By using the product you agree to use it only for lawful purposes and to connect
        accounts you are authorized to manage.
      </p>
      <p>
        Activity summaries are generated from public repository events. We do not guarantee
        completeness or accuracy of inferred themes and rankings.
      </p>
      <p><Link to="/">Back to home</Link></p>
    </article>
  );
}

export function PrivacyPolicy() {
  return (
    <article className="legal-page panel">
      <h1>Privacy Policy</h1>
      <p>
        WhatIsUp stores your GitHub connection, the people you follow, and collected
        public activity needed to build digests. We do not sell personal data.
      </p>
      <p>
        OAuth tokens are used only to read permitted GitHub data for your account.
        You can disconnect at any time by logging out and revoking access in GitHub settings.
      </p>
      <p><Link to="/">Back to home</Link></p>
    </article>
  );
}
