import { lazy, Suspense, useState } from 'react';
import { AlertCircle, BarChart3, Sparkles, Table2, User } from 'lucide-react';
import type { ChatMessage, QueryStep } from '../types';
import SqlBlock from './SqlBlock';
import ResultTable from './ResultTable';
import { isChartable } from './chartable';

// The charting library is heavy and only needed when a user opens a chart, so
// it's split into its own chunk and fetched on demand.
const ChartView = lazy(() => import('./ChartView'));

/** A single executed step: the SQL readout plus its result, with a
 *  table/chart toggle when the shape supports a chart. */
function StepResult({ step, index }: { step: QueryStep; index: number }) {
  const chartable = isChartable(step);
  const [view, setView] = useState<'table' | 'chart'>('table');
  const hasRows = step.ok && step.rows.length > 0;

  return (
    <div className="space-y-2">
      <SqlBlock step={step} index={index} />

      {hasRows && (
        <div className="space-y-2">
          {chartable && (
            <div className="flex items-center gap-1">
              <ToggleButton
                active={view === 'table'}
                onClick={() => setView('table')}
                icon={<Table2 className="h-3.5 w-3.5" aria-hidden />}
                label="Table"
              />
              <ToggleButton
                active={view === 'chart'}
                onClick={() => setView('chart')}
                icon={<BarChart3 className="h-3.5 w-3.5" aria-hidden />}
                label="Chart"
              />
            </div>
          )}
          {chartable && view === 'chart' ? (
            <Suspense
              fallback={
                <div className="rounded-lg border border-line bg-surface px-3 py-6 text-center font-mono text-2xs text-ink-400">
                  Loading chart…
                </div>
              }
            >
              <ChartView step={step} />
            </Suspense>
          ) : (
            <ResultTable step={step} />
          )}
        </div>
      )}
    </div>
  );
}

function ToggleButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1 rounded-md px-2 py-1 text-2xs font-medium transition-colors focus-visible:focus-ring ${
        active
          ? 'bg-teal-soft text-teal-deep'
          : 'text-ink-500 hover:bg-canvas hover:text-ink-700'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex animate-fade-up justify-end gap-3">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-teal px-4 py-2.5 text-[15px] text-white shadow-sm">
          {message.text}
        </div>
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ink-700 text-white">
          <User className="h-4 w-4" aria-hidden />
        </div>
      </div>
    );
  }

  const steps = message.steps ?? [];

  return (
    <div className="flex animate-fade-up gap-3">
      <div
        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          message.error ? 'bg-status-fail/10 text-status-fail' : 'bg-teal-soft text-teal-deep'
        }`}
      >
        {message.error ? (
          <AlertCircle className="h-4 w-4" aria-hidden />
        ) : (
          <Sparkles className="h-4 w-4" aria-hidden />
        )}
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        <div
          className={`rounded-2xl rounded-tl-sm border px-4 py-3 text-[15px] leading-relaxed shadow-panel ${
            message.error
              ? 'border-status-fail/20 bg-status-fail/5 text-status-fail'
              : 'border-line bg-surface text-ink-900'
          }`}
        >
          {message.text}
        </div>

        {steps.length > 0 && (
          <div className="space-y-3 pl-1">
            {steps.map((step, i) => (
              <StepResult key={i} step={step} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
