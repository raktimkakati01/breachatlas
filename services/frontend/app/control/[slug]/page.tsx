"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getControl, type ControlPage } from "@/lib/api";
import { cleanOrg, confirmationLabel, fmt, fmtDate } from "@/lib/format";

export default function ControlDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [data, setData] = useState<ControlPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getControl(slug)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load"));
    return () => {
      alive = false;
    };
  }, [slug]);

  if (error) {
    return (
      <div className="px-5 py-20 text-center">
        <p className="font-mono text-xs text-faint">{error}</p>
        <Link
          href="/controls"
          className="mt-4 inline-block text-sm text-ink underline underline-offset-4"
        >
          ← All controls
        </Link>
      </div>
    );
  }
  if (!data) {
    return <p className="px-5 py-20 text-center font-mono text-xs text-faint">loading…</p>;
  }

  const { control, breach_count, breaches } = data;

  return (
    <article className="mx-auto max-w-3xl px-5 py-10">
      <Link
        href="/controls"
        className="font-mono text-[11px] uppercase tracking-widest text-faint hover:text-ink"
      >
        ← controls
      </Link>

      <header className="mt-5">
        {control.cis_control_id && (
          <span className="rounded-full border border-accent/40 px-2.5 py-0.5 font-mono text-[11px] text-accent">
            CIS Control {control.cis_control_id}
            {control.cis_safeguard ? ` · Safeguard ${control.cis_safeguard}` : ""}
          </span>
        )}
        <h1 className="mt-3 text-2xl text-ink">{control.name}</h1>
        {control.description && (
          <p className="mt-3 text-[15px] leading-relaxed text-muted">{control.description}</p>
        )}
      </header>

      <section className="border-t border-line py-7">
        <h2 className="mb-4 font-mono text-[11px] uppercase tracking-widest text-faint">
          A factor in {breach_count} breach{breach_count === 1 ? "" : "es"}
        </h2>

        {breaches.length === 0 ? (
          <p className="font-mono text-xs text-faint">
            No published breaches reference this control yet.
          </p>
        ) : (
          <ul className="divide-y divide-line">
            {breaches.map((b) => (
              <li key={b.slug}>
                <Link
                  href={`/breach/${b.slug}`}
                  className="flex items-center justify-between gap-4 py-3 hover:text-ink"
                >
                  <span className="min-w-0">
                    <span className="block text-sm text-ink">{cleanOrg(b.organization)}</span>
                    <span className="block font-mono text-[11px] text-faint">
                      {b.sector} · {b.country} · {fmtDate(b.date_disclosed)}
                      {b.records_affected != null ? ` · ${fmt(b.records_affected)} records` : ""}
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-[11px] text-faint">
                    {confirmationLabel(b.confirmation_status)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}
