export const PERIODS = [
  { value: '2d', label: 'Recently' },
  { value: 'this_week', label: 'This week' },
  { value: '30d', label: 'This month' },
];

export const DEFAULT_PERIOD = '2d';

const ALLOWED = new Set(PERIODS.map((p) => p.value));

export function readStoredPeriod() {
  const stored = localStorage.getItem('whatisup:period');
  return ALLOWED.has(stored) ? stored : DEFAULT_PERIOD;
}
