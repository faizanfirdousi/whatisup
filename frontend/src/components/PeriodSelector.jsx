import React from 'react';
import { PERIODS } from '../period';

export function PeriodSelector({ value, onChange }) {
  const selectPeriod = (period) => {
    localStorage.setItem('whatisup:period', period);
    onChange(period);
  };

  return (
    <div className="period-selector" role="group" aria-label="Digest period">
      {PERIODS.map((period) => (
        <button
          key={period.value}
          type="button"
          className={period.value === value ? 'active' : ''}
          onClick={() => selectPeriod(period.value)}
        >
          {period.label}
        </button>
      ))}
    </div>
  );
}
