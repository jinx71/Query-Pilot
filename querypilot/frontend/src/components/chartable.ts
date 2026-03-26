import type { QueryStep } from '../types';

const MIN_ROWS = 2;
const MAX_ROWS = 30;

/**
 * Whether a result can be drawn as a bar chart: a clean two-column shape with
 * one label column and one finite-numeric measure, and a sensible row count.
 *
 * This lives apart from ChartView so the (heavy) charting library can be
 * lazy-loaded — deciding *whether* to offer a chart must stay cheap.
 */
export function isChartable(step: QueryStep): boolean {
  if (!step.ok || step.columns.length !== 2) return false;
  if (step.rows.length < MIN_ROWS || step.rows.length > MAX_ROWS) return false;
  const measure = step.columns[1];
  return step.rows.every((row) => {
    const v = row[measure];
    return typeof v === 'number' && Number.isFinite(v);
  });
}
