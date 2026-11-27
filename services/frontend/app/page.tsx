"use client";

import BreachMap from "@/components/BreachMap";
import { useAtlas } from "@/components/AtlasProvider";
import { useUI } from "@/components/UIProvider";
import { fmt } from "@/lib/format";

function Stat({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-widest text-faint">{label}</span>
      <span className={`${mono ? "font-mono" : ""} text-xl text-ink tabular-nums`}>{value}</span>
    </div>
  );
}

export default function Home() {
  const { stats, breaches, error } = useAtlas();
  const { openPalette } = useUI();

  return (
    <main className="relative min-h-[calc(100vh-56px)] overflow-hidden">
      {/* --- Centerpiece map --- */}
      <div className="absolute inset-0 flex items-center justify-center px-6 pb-56 pt-6">
        {breaches.length > 0 ? (
          <BreachMap breaches={breaches} />
        ) : (
          <p className="font-mono text-xs text-faint">
            {error ? `API unreachable: ${error}` : "loading the map…"}
          </p>
        )}
      </div>

      {/* --- Hero + stats, anchored bottom --- */}
      <div className="absolute inset-x-0 bottom-0 border-t border-line bg-bg/80 px-5 py-6 backdrop-blur-[2px]">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-md">
            <h1 className="text-xl leading-snug text-ink">
              Every breach, mapped to how it happened —<br className="hidden sm:block" /> and what
              would have stopped it.
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              {stats
                ? `${fmt(stats.breaches_tracked)} breaches tracked across ${stats.countries} ${
                    stats.countries === 1 ? "country" : "countries"
                  }. Open one to see the attack path and the controls that would have blocked it.`
                : "Loading…"}
            </p>
            <p className="mt-3 text-sm">
              <span className="text-faint">Hover a node to trace a path, click to open it — or </span>
              <button
                onClick={openPalette}
                className="text-ink underline decoration-line-strong underline-offset-4 hover:decoration-accent"
              >
                search breaches
              </button>
              <span className="text-faint"> (⌘K).</span>
            </p>
          </div>

          {stats && (
            <div className="grid grid-cols-2 gap-x-10 gap-y-5 sm:grid-cols-3">
              <Stat label="breaches" value={fmt(stats.breaches_tracked)} />
              <Stat label="records exposed" value={fmt(stats.records_exposed)} />
              <Stat label="countries" value={fmt(stats.countries)} />
              <Stat label="organizations" value={fmt(stats.organizations)} />
              <Stat label="undisclosed cause" value={`${stats.pct_undisclosed_root_cause}%`} />
              <Stat
                label="top missing control"
                value={stats.most_common_missing_control ?? "—"}
                mono={false}
              />
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
