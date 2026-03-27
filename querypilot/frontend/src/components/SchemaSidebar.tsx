import { useEffect, useState } from 'react';
import {
  ChevronRight,
  Database,
  KeyRound,
  Link2,
  Loader2,
  Table as TableIcon,
} from 'lucide-react';
import { describeError, getSchema } from '../api/client';
import type { ColumnInfo, SchemaData, TableInfo } from '../types';

function ColumnRow({ col }: { col: ColumnInfo }) {
  return (
    <div className="group flex items-baseline gap-2 py-1 pl-7 pr-3">
      {col.primary_key ? (
        <KeyRound
          className="mt-0.5 h-3 w-3 shrink-0 text-status-warn"
          aria-label="primary key"
        />
      ) : col.references ? (
        <Link2
          className="mt-0.5 h-3 w-3 shrink-0 text-teal"
          aria-label="foreign key"
        />
      ) : (
        <span className="mt-0.5 h-3 w-3 shrink-0" />
      )}
      <span className="font-mono text-[12.5px] text-ink-700">{col.name}</span>
      <span className="font-mono text-2xs text-ink-400">{col.type}</span>
      {col.references && (
        <span className="ml-auto truncate font-mono text-2xs text-teal-deep">
          → {col.references}
        </span>
      )}
    </div>
  );
}

function TableSection({
  table,
  defaultOpen,
}: {
  table: TableInfo;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-line/70 last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-canvas focus-visible:focus-ring"
      >
        <ChevronRight
          className={`h-3.5 w-3.5 shrink-0 text-ink-400 transition-transform ${
            open ? 'rotate-90' : ''
          }`}
          aria-hidden
        />
        <TableIcon className="h-3.5 w-3.5 shrink-0 text-ink-500" aria-hidden />
        <span className="font-mono text-[13px] font-medium text-ink-900">
          {table.name}
        </span>
        <span className="ml-auto font-mono text-2xs text-ink-400">
          {table.columns.length}
        </span>
      </button>
      {open && (
        <div className="pb-1">
          {table.columns.map((col) => (
            <ColumnRow key={col.name} col={col} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SchemaSidebar() {
  const [schema, setSchema] = useState<SchemaData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getSchema();
        if (!cancelled) setSchema(data);
      } catch (err) {
        if (!cancelled) setError(describeError(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <Database className="h-4 w-4 text-teal" aria-hidden />
        <h2 className="text-[13px] font-semibold uppercase tracking-wide text-ink-700">
          Schema
        </h2>
        {schema && (
          <span className="ml-auto font-mono text-2xs text-ink-400">
            {schema.tables.length} tables
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {error ? (
          <p className="px-4 py-4 text-2xs text-status-fail">{error}</p>
        ) : !schema ? (
          <div className="flex items-center gap-2 px-4 py-4 text-2xs text-ink-400">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            Loading schema…
          </div>
        ) : (
          schema.tables.map((table, i) => (
            <TableSection key={table.name} table={table} defaultOpen={i < 2} />
          ))
        )}
      </div>

      <div className="border-t border-line px-4 py-2.5">
        <p className="font-mono text-2xs leading-relaxed text-ink-400">
          <KeyRound className="mr-1 inline h-3 w-3 text-status-warn" aria-hidden />
          primary key
          <Link2 className="ml-3 mr-1 inline h-3 w-3 text-teal" aria-hidden />
          foreign key
        </p>
      </div>
    </div>
  );
}
