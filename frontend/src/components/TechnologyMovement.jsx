import React from 'react';
import { Link } from 'react-router-dom';

function MovementRow({ item }) {
  return (
    <div className="movement-row">
      <div className="movement-row-head">
        <Link to={`/network?tech=${encodeURIComponent(item.name)}`}>{item.name}</Link>
      </div>
      <p>{item.signal || `${item.people_count} people`}</p>
    </div>
  );
}

export function TechnologyMovement({ movement }) {
  if (!movement) return null;

  const established = movement.established || [];
  const growing = movement.growing || [];
  const fresh = movement.new || [];

  if (!established.length && !growing.length && !fresh.length) {
    return (
      <section className="technology-movement">
        <div className="section-heading">
          <h2>Technology movement</h2>
        </div>
        <div className="panel empty-panel">
          No clear technology movement yet. Patterns will appear as your network becomes active.
        </div>
      </section>
    );
  }

  return (
    <section className="technology-movement">
      <div className="section-heading">
        <h2>Technology movement</h2>
      </div>
      <div className="movement-grid">
        {growing.length > 0 && (
          <div className="movement-panel panel">
            <h3>Growing recently</h3>
            {growing.map((item) => (
              <MovementRow key={item.name} item={item} />
            ))}
          </div>
        )}
        {fresh.length > 0 && (
          <div className="movement-panel panel">
            <h3>New this period</h3>
            {fresh.map((item) => (
              <MovementRow key={item.name} item={item} />
            ))}
          </div>
        )}
        {established.length > 0 && (
          <div className="movement-panel panel">
            <h3>Established in your network</h3>
            {established.map((item) => (
              <div key={item.name} className="movement-row">
                <div className="movement-row-head">
                  <Link to={`/network?tech=${encodeURIComponent(item.name)}`}>{item.name}</Link>
                </div>
                <p>{item.people_count} people active this period</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
