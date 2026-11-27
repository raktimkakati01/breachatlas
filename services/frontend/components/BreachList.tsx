"use client";

import Link from "next/link";
import type { BreachDetail } from "@/lib/api";
import { cleanOrg, fmt, fmtDate } from "@/lib/format";

export default function BreachList({ breaches }: { breaches: BreachDetail[] }) {
  return (
    <ul className="divide-y divide-line">
      {breaches.map((b) => {
        const controls = b.controls.map((c) => c.control.name).slice(0, 3);
        return (
          <li key={b.slug}>
            <Link href={`/breach/${b.slug}`} className="block py-4 active:opacity-70">
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-sm text-ink">{cleanOrg(b.organization)}</span>
                {b.records_affected != null && (
                  <span className="shrink-0 font-mono text-xs tabular-nums text-accent">
                    {fmt(b.records_affected)}
                  </span>
                )}
              </div>
              <div className="mt-1 font-mono text-[11px] text-faint">
                {b.sector} · {b.country} · {fmtDate(b.date_disclosed)}
              </div>
              {controls.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {controls.map((name) => (
                    <span
                      key={name}
                      className="rounded border border-line px-2 py-0.5 font-mono text-[11px] text-muted"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
