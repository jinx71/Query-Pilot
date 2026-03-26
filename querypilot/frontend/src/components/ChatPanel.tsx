import { useEffect, useRef, useState } from 'react';
import {
  ArrowUp,
  Compass,
  Loader2,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { useChat } from '../hooks/useChat';
import MessageBubble from './MessageBubble';

const EXAMPLES = [
  'How many batches were rejected in 2024?',
  'Which equipment had the most critical deviations?',
  'What is the QC failure rate by product?',
  'Show the top 5 operators by number of batches run.',
];

function ThinkingRow() {
  return (
    <div className="flex animate-fade-up gap-3">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-teal-soft text-teal-deep">
        <Sparkles className="h-4 w-4 animate-pulse-dot" aria-hidden />
      </div>
      <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-line bg-surface px-4 py-3 text-[14px] text-ink-500 shadow-panel">
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
        Inspecting the schema and writing SQL…
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto max-w-xl px-2 py-10 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-soft text-teal-deep">
        <Compass className="h-6 w-6" aria-hidden />
      </div>
      <h2 className="text-lg font-semibold text-ink-900">
        Ask your database anything
      </h2>
      <p className="mx-auto mt-2 max-w-md text-[14px] leading-relaxed text-ink-500">
        Questions are answered with read-only SQL against a sample pharma
        manufacturing database. Every answer shows the exact query it ran.
      </p>
      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="rounded-xl border border-line bg-surface px-3.5 py-2.5 text-left text-[13.5px] text-ink-700 shadow-sm transition-all hover:border-teal/40 hover:bg-teal-soft/40 hover:text-ink-900 focus-visible:focus-ring"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatPanel() {
  const { messages, sending, sessionReady, send, reset } = useChat();
  const [draft, setDraft] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages, sending]);

  const submit = () => {
    const text = draft.trim();
    if (!text || sending) return;
    setDraft('');
    if (taRef.current) taRef.current.style.height = 'auto';
    void send(text);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const grow = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-line bg-surface/80 px-5 py-3 backdrop-blur">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink-900 text-white">
          <Sparkles className="h-4 w-4 text-teal" aria-hidden />
        </div>
        <div className="min-w-0">
          <h1 className="text-[15px] font-semibold leading-tight text-ink-900">
            QueryPilot
          </h1>
          <p className="text-2xs text-ink-400">
            Natural-language data analyst · read-only
          </p>
        </div>
        <button
          type="button"
          onClick={() => void reset()}
          disabled={messages.length === 0 || sending}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-2xs font-medium text-ink-500 transition-colors hover:bg-canvas hover:text-ink-700 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:focus-ring"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden />
          New session
        </button>
      </header>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          {messages.length === 0 && !sending ? (
            <EmptyState onPick={(q) => void send(q)} />
          ) : (
            <div className="space-y-5">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              {sending && <ThinkingRow />}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-line bg-surface px-4 py-3">
        <div className="mx-auto w-full max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border border-line-strong bg-surface px-3 py-2 shadow-sm transition-colors focus-within:border-teal/50">
            <textarea
              ref={taRef}
              rows={1}
              value={draft}
              disabled={!sessionReady}
              onChange={(e) => {
                setDraft(e.target.value);
                grow(e.target);
              }}
              onKeyDown={onKeyDown}
              placeholder="Ask a question about the data…"
              className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-[15px] text-ink-900 placeholder:text-ink-400 focus:outline-none"
            />
            <button
              type="button"
              onClick={submit}
              disabled={!draft.trim() || sending || !sessionReady}
              aria-label="Send question"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal text-white transition-colors hover:bg-teal-deep disabled:cursor-not-allowed disabled:bg-line-strong focus-visible:focus-ring"
            >
              <ArrowUp className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <p className="mt-1.5 px-1 text-center text-2xs text-ink-400">
            QueryPilot runs read-only <span className="font-mono">SELECT</span>{' '}
            queries only. Results come from a sample database.
          </p>
        </div>
      </div>
    </div>
  );
}
