"use client";

import { useEffect, useState } from "react";
import BreachMap from "@/components/BreachMap";
import { getBreach, getStats, listBreaches, type BreachDetail, type Stats } from "@/lib/api";

const TABS = ["Breaches", "Controls", "Techniques"];

function Stat({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-widest text-faint">{label}</span>
      <span className={`${mono ? "font-mono" : ""} text-xl text-ink tabular-nums`}>{value}</span>
    </div>
  );
}

export default function Home() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [breaches, setBreaches] = useState<BreachDetail[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, list] = await Promise.all([getStats(), listBreaches()]);
        setStats(s);
        const details = await Promise.all(list.items.map((b) => getBreach(b.slug)));
        setBreaches(details);
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Failed to load");
      }
    })();
  }, []);

  const fmt = (n: number) => n.toLocaleString("en-US");

  return (
    <div className="flex min-h-screen flex-col">
      {/* --- Nav --- */}
      <header className="flex items-center justify-between border-b border-line px-5 py-3">
        <nav className="flex items-center gap-1 rounded-full border border-line p-0.5 text-sm">
          {TABS.map((t, i) => (
            <button
              key={t}
              className={`rounded-full px-3 py-1 transition-colors ${
                i === 0 ? "bg-ink text-bg" : "text-muted hover:text-ink"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
        <div className="flex items-center gap-2.5 text-ink">
          <span className="text-accent" aria-hidden>
            ◆
          </span>
          <span className="font-mono text-sm uppercase tracking-[0.35em]">BreachAtlas</span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <button className="flex items-center gap-2 text-muted hover:text-ink">
            Find
            <kbd className="rounded border border-line px-1.5 py-0.5 font-mono text-[11px] text-faint">
              ⌘K
            </kbd>
          </button>
          <button className="rounded-full border border-line px-3 py-1 text-ink hover:border-line-strong">
            Sign in
          </button>
        </div>
      </header>

      {/* --- Centerpiece map --- */}
      <main className="relative flex-1 overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center px-6 pb-56 pt-6">
          {breaches.length > 0 ? (
            <BreachMap breaches={breaches} />
          ) : (
            <p className="font-mono text-xs text-faint">
              {err ? `API unreachable: ${err}` : "loading the map…"}
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
                <a className="text-ink underline decoration-line-strong underline-offset-4 hover:decoration-accent">
                  Explore the map
                </a>
                <span className="text-faint"> or </span>
                <a className="text-ink underline decoration-line-strong underline-offset-4 hover:decoration-accent">
                  search breaches
                </a>
                .
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
    </div>
  );
}
