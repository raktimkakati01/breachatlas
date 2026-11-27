"use client";

import BreachMap from "@/components/BreachMap";
import BreachList from "@/components/BreachList";
import { useAtlas } from "@/components/AtlasProvider";
import { useUI } from "@/components/UIProvider";
import { fmt } from "@/lib/format";
import type { Stats } from "@/lib/api";

function Stat({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-widest text-faint">{label}</span>
      <span className={`${mono ? "font-mono" : ""} text-xl text-ink tabular-nums`}>{value}</span>
    </div>
  );
}

function StatGrid({ stats, className = "" }: { stats: Stats; className?: string }) {
  return (
    <div className={`grid grid-cols-2 gap-x-8 gap-y-5 sm:grid-cols-3 ${className}`}>
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
  );
}

function HeroCopy({ stats, onSearch }: { stats: Stats | null; onSearch: () => void }) {
  return (
    <div className="max-w-md">
      <h1 className="text-2xl leading-snug text-ink lg:text-xl">
        Every breach, mapped to how it happened — and what would have stopped it.
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-muted">
        {stats
          ? `${fmt(stats.breaches_tracked)} breaches tracked across ${stats.countries} ${
              stats.countries === 1 ? "country" : "countries"
            }. Open one to see the attack path and the controls that would have blocked it.`
          : "Loading…"}
      </p>
      <p className="mt-3 text-sm">
        <span className="text-faint">Open a breach to trace it, or </span>
        <button
          onClick={onSearch}
          className="text-ink underline decoration-line-strong underline-offset-4 hover:decoration-accent"
        >
          search breaches
        </button>
        <span className="text-faint"> (⌘K).</span>
      </p>
    </div>
  );
}

export default function Home() {
  const { stats, breaches, error } = useAtlas();
  const { openPalette } = useUI();

  const empty = (
    <p className="font-mono text-xs text-faint">
      {error ? `API unreachable: ${error}` : "loading the map…"}
    </p>
  );

  return (
    <main>
      {/* --- Desktop: cinematic map centrepiece with hero overlaid at the bottom --- */}
      <section className="relative hidden min-h-[calc(100vh-57px)] overflow-hidden lg:block">
        <div className="absolute inset-0 flex items-center justify-center px-6 pb-56 pt-6">
          {breaches.length > 0 ? <BreachMap breaches={breaches} maxBreaches={14} /> : empty}
        </div>
        <div className="absolute inset-x-0 bottom-0 border-t border-line bg-bg/80 px-5 py-6 backdrop-blur-[2px]">
          <div className="flex flex-row items-end justify-between gap-8">
            <HeroCopy stats={stats} onSearch={openPalette} />
            {stats && <StatGrid stats={stats} />}
          </div>
        </div>
      </section>

      {/* --- Mobile / tablet: stacked, with a tappable list instead of the wide map --- */}
      <section className="mx-auto max-w-2xl px-5 py-8 lg:hidden">
        <HeroCopy stats={stats} onSearch={openPalette} />
        {stats && <StatGrid stats={stats} className="mt-8" />}

        <h2 className="mt-10 font-mono text-[11px] uppercase tracking-widest text-faint">
          Breaches
        </h2>
        {breaches.length > 0 ? (
          <BreachList breaches={breaches} />
        ) : (
          <div className="mt-4">{empty}</div>
        )}
      </section>
    </main>
  );
}
