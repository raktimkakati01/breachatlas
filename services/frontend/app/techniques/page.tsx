"use client";

import Link from "next/link";
import { useAtlas } from "@/components/AtlasProvider";
import { cleanOrg } from "@/lib/format";

export default function TechniquesIndex() {
  const { techniques, breaches, loading, error } = useAtlas();

  const orgFor = (slug: string) =>
    cleanOrg(breaches.find((b) => b.slug === slug)?.organization ?? slug);

  const sorted = [...techniques].sort(
    (a, b) => b.breachSlugs.length - a.breachSlugs.length || a.technique_id.localeCompare(b.technique_id),
  );

  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <h1 className="text-2xl text-ink">Techniques</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        MITRE ATT&amp;CK techniques observed across the breaches we track, with the breaches each
        one appears in. Technique IDs link to the ATT&amp;CK knowledge base.
      </p>

      {loading && techniques.length === 0 && (
        <p className="mt-10 font-mono text-xs text-faint">loading…</p>
      )}
      {error && <p className="mt-10 font-mono text-xs text-faint">API unreachable: {error}</p>}

      <ul className="mt-8 divide-y divide-line">
        {sorted.map((t) => (
          <li key={t.technique_id} className="py-4">
            <div className="flex items-baseline justify-between gap-4">
              <a
                href={t.url ?? `https://attack.mitre.org/techniques/${t.technique_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-ink hover:text-accent"
              >
                <span className="font-mono text-accent">{t.technique_id}</span> · {t.name}
              </a>
              <span className="shrink-0 font-mono text-[11px] text-faint tabular-nums">
                {t.breachSlugs.length} breach{t.breachSlugs.length === 1 ? "" : "es"}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {t.breachSlugs.map((slug) => (
                <Link
                  key={slug}
                  href={`/breach/${slug}`}
                  className="rounded border border-line px-2 py-0.5 font-mono text-[11px] text-muted hover:border-accent/50 hover:text-ink"
                >
                  {orgFor(slug)}
                </Link>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
