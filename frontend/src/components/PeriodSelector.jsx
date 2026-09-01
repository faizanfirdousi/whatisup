import React from 'react';

const PERIODS = [
  { value: '7d', label: '7 days' },
  { value: '14d', label: '14 days' },
  { value: '30d', label: '30 days' },
  { value: 'this_week', label: 'This week' },
];

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
