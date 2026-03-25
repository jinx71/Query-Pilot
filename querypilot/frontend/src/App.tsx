import { useState } from 'react';
import { PanelLeft, X } from 'lucide-react';
import SchemaSidebar from './components/SchemaSidebar';
import ChatPanel from './components/ChatPanel';

export default function App() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-canvas text-ink-700">
      {/* Schema browser — fixed column on large screens. */}
      <aside className="hidden w-72 shrink-0 border-r border-line bg-surface lg:block xl:w-80">
        <SchemaSidebar />
      </aside>

      {/* Mobile slide-over for the schema. */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-ink-900/30 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div className="absolute left-0 top-0 h-full w-72 max-w-[85%] animate-fade-up border-r border-line bg-surface shadow-panel">
            <div className="flex items-center justify-end px-2 pt-2">
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close schema"
                className="rounded-lg p-1.5 text-ink-500 hover:bg-canvas focus-visible:focus-ring"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
            <div className="h-[calc(100%-2.5rem)]">
              <SchemaSidebar />
            </div>
          </div>
        </div>
      )}

      <main className="relative flex min-w-0 flex-1 flex-col">
        <ChatPanel />

        {/* Mobile-only schema toggle. */}
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-label="Open schema"
          className="absolute bottom-24 left-4 z-30 flex h-11 w-11 items-center justify-center rounded-full border border-line bg-surface text-ink-700 shadow-panel transition-colors hover:bg-canvas lg:hidden focus-visible:focus-ring"
        >
          <PanelLeft className="h-5 w-5" aria-hidden />
        </button>
      </main>
    </div>
  );
}
