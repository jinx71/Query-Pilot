import { useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  Clock,
  Rows3,
  Terminal,
} from 'lucide-react';
import type { QueryStep } from '../types';

interface Props {
  step: QueryStep;
  index: number;
}

function formatMs(ms: number): string {
  if (ms < 1) return '<1 ms';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/**
 * The "lab readout": a monospace panel that shows the exact SQL the agent ran,
 * the row count, and the wall-clock time. This is the audit trail — the user
 * never has to take the answer on faith.
 */
export default function SqlBlock({ step, index }: Props) {
  const [open, setOpen] = useState(true);
  const label = step.purpose?.trim() || `Query ${index + 1}`;

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-ink-900 shadow-readout">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-white/5 focus-visible:focus-ring"
      >
        <Terminal className="h-3.5 w-3.5 shrink-0 text-teal" aria-hidden />
        <span className="flex-1 truncate font-mono text-2xs uppercase tracking-wide text-ink-400">
          {label}
        </span>
        {!step.ok && (
          <span className="flex items-center gap-1 font-mono text-2xs font-medium text-status-fail">
            <AlertTriangle className="h-3 w-3" aria-hidden />
            error
          </span>
        )}
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-ink-500 transition-transform ${
            open ? 'rotate-180' : ''
          }`}
          aria-hidden
        />
      </button>

      {open && (
        <div className="border-t border-white/5">
          <pre className="overflow-x-auto px-3 py-3 font-mono text-[12.5px] leading-relaxed text-slate-100">
            <code>{step.sql}</code>
          </pre>

          {step.error ? (
            <div className="flex items-start gap-2 border-t border-white/5 bg-status-fail/10 px-3 py-2 font-mono text-2xs text-red-300">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
              <span>{step.error}</span>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/5 px-3 py-2 font-mono text-2xs text-ink-400">
              <span className="flex items-center gap-1">
                <Rows3 className="h-3 w-3" aria-hidden />
                {step.row_count} {step.row_count === 1 ? 'row' : 'rows'}
                {step.truncated && (
                  <span className="text-status-warn"> · truncated</span>
                )}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" aria-hidden />
                {formatMs(step.elapsed_ms)}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
