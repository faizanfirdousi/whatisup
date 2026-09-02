import React from 'react';

export function SharedActivity({ items }) {
  const rows = items || [];

  return (
    <section className="shared-activity">
      <div className="section-heading">
        <h2>Active across your network</h2>
      </div>
      {rows.length === 0 ? (
        <div className="panel empty-panel">
          No broader network pattern is visible yet.
        </div>
      ) : (
        <div className="emerging-grid">
          {rows.map((item, index) => (
            <article
              key={`${item.type}:${item.headline}:${index}`}
              className="emerging-card"
            >
              <h3>{item.headline}</h3>
              <p>{item.detail}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
