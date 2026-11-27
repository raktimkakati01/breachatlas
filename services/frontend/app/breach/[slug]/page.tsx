"use client";

import { use } from "react";
import Link from "next/link";
import { useAtlas } from "@/components/AtlasProvider";
import {
  cleanOrg,
  confirmationLabel,
  fmt,
  fmtDate,
  phaseLabel,
  relationshipLabel,
  rootCauseLabel,
} from "@/lib/format";

function Badge({ children, tone = "line" }: { children: React.ReactNode; tone?: "line" | "accent" }) {
  const cls =
    tone === "accent"
      ? "border-accent/40 text-accent"
      : "border-line-strong text-muted";
  return (
    <span className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] ${cls}`}>
      {children}
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line py-7">
      <h2 className="mb-4 font-mono text-[11px] uppercase tracking-widest text-faint">{title}</h2>
      {children}
    </section>
  );
}

export default function BreachPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const { breaches, loading, error } = useAtlas();
  const breach = breaches.find((b) => b.slug === slug);

  if (loading && !breach) {
    return <p className="px-5 py-20 text-center font-mono text-xs text-faint">loading…</p>;
  }
  if (!breach) {
    return (
      <div className="px-5 py-20 text-center">
        <p className="font-mono text-xs text-faint">
          {error ? `API unreachable: ${error}` : `No breach found for “${slug}”.`}
        </p>
        <Link href="/" className="mt-4 inline-block text-sm text-ink underline underline-offset-4">
          ← Back to the map
        </Link>
      </div>
    );
  }

  return (
    <article className="mx-auto max-w-3xl px-5 py-10">
      <Link
        href="/"
        className="font-mono text-[11px] uppercase tracking-widest text-faint hover:text-ink"
      >
        ← atlas
      </Link>

      <header className="mt-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={breach.confirmation_status === "confirmed" ? "accent" : "line"}>
            {confirmationLabel(breach.confirmation_status)}
          </Badge>
          <Badge>{rootCauseLabel(breach.root_cause_status)} root cause</Badge>
        </div>
        <h1 className="mt-3 text-2xl text-ink">{cleanOrg(breach.organization)}</h1>
        <p className="mt-2 font-mono text-xs text-muted">
          {breach.sector} · {breach.country} · disclosed {fmtDate(breach.date_disclosed)}
          {breach.date_occurred ? ` · occurred ${fmtDate(breach.date_occurred)}` : ""}
        </p>
        {breach.records_affected != null && (
          <p className="mt-4 text-sm text-ink">
            <span className="font-mono text-2xl tabular-nums text-accent">
              {fmt(breach.records_affected)}
            </span>{" "}
            <span className="text-muted">records affected</span>
          </p>
        )}
      </header>

      {breach.summary && (
        <p className="mt-6 text-[15px] leading-relaxed text-ink">{breach.summary}</p>
      )}

      {breach.attack_steps.length > 0 && (
        <Section title="How it happened — attack path">
          <ol className="space-y-5">
            {[...breach.attack_steps]
              .sort((a, b) => a.step_order - b.step_order)
              .map((step) => (
                <li key={step.step_order} className="relative pl-7">
                  <span className="absolute left-0 top-0.5 font-mono text-xs text-accent">
                    {String(step.step_order).padStart(2, "0")}
                  </span>
                  <div className="mb-1 font-mono text-[11px] uppercase tracking-widest text-faint">
                    {phaseLabel(step.phase)}
                  </div>
                  <p className="text-sm leading-relaxed text-ink">{step.description}</p>
                  {step.techniques.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {step.techniques.map((t) => (
                        <a
                          key={t.technique_id}
                          href={t.url ?? `https://attack.mitre.org/techniques/${t.technique_id}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded border border-line px-2 py-0.5 font-mono text-[11px] text-muted hover:border-accent/50 hover:text-ink"
                          title={t.name}
                        >
                          {t.technique_id} · {t.name}
                        </a>
                      ))}
                    </div>
                  )}
                </li>
              ))}
          </ol>
        </Section>
      )}

      {breach.controls.length > 0 && (
        <Section title="What would have stopped it — controls">
          <ul className="divide-y divide-line">
            {breach.controls.map((c) => (
              <li key={c.control.slug}>
                <Link
                  href={`/control/${c.control.slug}`}
                  className="flex items-center justify-between gap-4 py-3 hover:text-ink"
                >
                  <span className="min-w-0">
                    <span className="block text-sm text-ink">{c.control.name}</span>
                    <span className="block font-mono text-[11px] text-faint">
                      {relationshipLabel(c.relationship_type)}
                      {c.control.cis_control_id ? ` · CIS ${c.control.cis_control_id}` : ""}
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-xs text-faint">→</span>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {(breach.lessons_for_defenders || breach.what_users_should_do) && (
        <Section title="Takeaways">
          <div className="grid gap-6 sm:grid-cols-2">
            {breach.lessons_for_defenders && (
              <div>
                <h3 className="mb-2 text-sm text-ink">For defenders</h3>
                <p className="text-sm leading-relaxed text-muted">
                  {breach.lessons_for_defenders}
                </p>
              </div>
            )}
            {breach.what_users_should_do && (
              <div>
                <h3 className="mb-2 text-sm text-ink">If you were affected</h3>
                <p className="text-sm leading-relaxed text-muted">
                  {breach.what_users_should_do}
                </p>
              </div>
            )}
          </div>
        </Section>
      )}

      {breach.data_types.length > 0 && (
        <Section title="Data exposed">
          <div className="flex flex-wrap gap-1.5">
            {breach.data_types.map((d) => (
              <span
                key={d.slug}
                className="rounded border border-line px-2 py-0.5 font-mono text-[11px] text-muted"
              >
                {d.name}
              </span>
            ))}
          </div>
        </Section>
      )}

      {breach.sources.length > 0 && (
        <Section title="Sources">
          <ul className="space-y-2">
            {breach.sources.map((s) => (
              <li key={s.url}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-ink underline decoration-line-strong underline-offset-4 hover:decoration-accent"
                >
                  {s.title ?? s.url}
                </a>
                <span className="ml-2 font-mono text-[11px] text-faint">
                  {s.publisher ? `${s.publisher} · ` : ""}
                  {fmtDate(s.date_retrieved)}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </article>
  );
}
