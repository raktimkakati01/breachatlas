"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useAtlas } from "@/components/AtlasProvider";

export default function ControlsIndex() {
  const { controls, breaches, loading, error } = useAtlas();

  // How many breaches reference each control (as a missing/relevant control).
  const counts = useMemo(() => {
    const m = new Map<string, number>();
    for (const b of breaches) {
      const seen = new Set<string>();
      for (const c of b.controls) seen.add(c.control.slug);
      for (const slug of seen) m.set(slug, (m.get(slug) ?? 0) + 1);
    }
    return m;
  }, [breaches]);

  const sorted = useMemo(
    () =>
      [...controls].sort(
        (a, b) =>
          (counts.get(b.slug) ?? 0) - (counts.get(a.slug) ?? 0) ||
          a.name.localeCompare(b.name),
      ),
    [controls, counts],
  );

  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <h1 className="text-2xl text-ink">Controls</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        CIS Controls v8 safeguards, ranked by how often a missing one shows up across the
        breaches we track. Open a control to see every breach it was a factor in.
      </p>

      {loading && controls.length === 0 && (
        <p className="mt-10 font-mono text-xs text-faint">loading…</p>
      )}
      {error && <p className="mt-10 font-mono text-xs text-faint">API unreachable: {error}</p>}

      <ul className="mt-8 divide-y divide-line">
        {sorted.map((c) => {
          const n = counts.get(c.slug) ?? 0;
          return (
            <li key={c.slug}>
              <Link
                href={`/control/${c.slug}`}
                className="flex items-center justify-between gap-4 py-3.5 hover:text-ink"
              >
                <span className="min-w-0">
                  <span className="block text-sm text-ink">{c.name}</span>
                  <span className="block font-mono text-[11px] text-faint">
                    {c.cis_control_id ? `CIS Control ${c.cis_control_id}` : "CIS Control"}
                    {c.cis_safeguard ? ` · Safeguard ${c.cis_safeguard}` : ""}
                  </span>
                </span>
                <span className="shrink-0 font-mono text-[11px] text-faint tabular-nums">
                  {n > 0 ? `${n} breach${n === 1 ? "" : "es"}` : "—"}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
