import type { QueryStep } from '../types';

interface Props {
  step: QueryStep;
}

const MAX_RENDER_ROWS = 50;

// Pharma-meaningful status words get a colored pill so a result table reads
// like an instrument panel, not a wall of text.
const STATUS_TONE: Record<string, string> = {
  released: 'bg-status-pass/10 text-status-pass',
  pass: 'bg-status-pass/10 text-status-pass',
  passed: 'bg-status-pass/10 text-status-pass',
  open: 'bg-status-warn/10 text-status-warn',
  quarantine: 'bg-status-warn/10 text-status-warn',
  investigating: 'bg-status-warn/10 text-status-warn',
  minor: 'bg-status-warn/10 text-status-warn',
  rejected: 'bg-status-fail/10 text-status-fail',
  fail: 'bg-status-fail/10 text-status-fail',
  failed: 'bg-status-fail/10 text-status-fail',
  major: 'bg-status-fail/10 text-status-fail',
  critical: 'bg-status-critical/10 text-status-critical',
};

function formatCell(value: unknown): { text: string; muted?: boolean } {
  if (value === null || value === undefined) return { text: 'null', muted: true };
  if (typeof value === 'boolean') return { text: value ? 'true' : 'false' };
  if (typeof value === 'number') return { text: value.toLocaleString() };
  return { text: String(value) };
}

function Cell({ value }: { value: unknown }) {
  const { text, muted } = formatCell(value);
  const tone = STATUS_TONE[text.toLowerCase()];

  if (tone) {
    return (
      <span
        className={`inline-block rounded px-1.5 py-0.5 text-2xs font-medium uppercase tracking-wide ${tone}`}
      >
        {text}
      </span>
    );
  }
  return (
    <span className={muted ? 'text-ink-400 italic' : undefined}>{text}</span>
  );
}

/** Tabular render of a query result, capped so a giant result set can't blow
 *  up the chat. The full row count is always shown in the SQL readout above. */
export default function ResultTable({ step }: Props) {
  if (step.columns.length === 0 || step.rows.length === 0) {
    return (
      <p className="px-1 py-2 font-mono text-2xs text-ink-400">
        No rows returned.
      </p>
    );
  }

  const visible = step.rows.slice(0, MAX_RENDER_ROWS);
  const hidden = step.rows.length - visible.length;

  return (
    <div className="overflow-hidden rounded-lg border border-line">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-[13px]">
          <thead>
            <tr className="border-b border-line bg-canvas">
              {step.columns.map((col) => (
                <th
                  key={col}
                  className="whitespace-nowrap px-3 py-2 font-mono text-2xs font-semibold uppercase tracking-wide text-ink-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, r) => (
              <tr
                key={r}
                className="border-b border-line/70 last:border-0 hover:bg-canvas/60"
              >
                {step.columns.map((col) => (
                  <td
                    key={col}
                    className="whitespace-nowrap px-3 py-1.5 align-top tabular-nums text-ink-700"
                  >
                    <Cell value={row[col]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hidden > 0 && (
        <div className="border-t border-line bg-canvas px-3 py-1.5 font-mono text-2xs text-ink-400">
          + {hidden} more {hidden === 1 ? 'row' : 'rows'} not shown
        </div>
      )}
    </div>
  );
}
