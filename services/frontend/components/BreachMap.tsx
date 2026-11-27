"use client";

import { useMemo, useState } from "react";
import type { BreachDetail } from "@/lib/api";

type Node = { id: string; label: string; sub?: string; x: number; y: number; col: 0 | 1 | 2 };
type Link = { a: string; b: string };

const W = 960;
const H = 480;
const COL_X = [150, 480, 810];

function layout(breaches: BreachDetail[]) {
  const techIds = new Set<string>();
  const ctrlIds = new Set<string>();
  const techName: Record<string, string> = {};
  const ctrlName: Record<string, string> = {};
  const links: Link[] = [];

  for (const b of breaches) {
    for (const step of b.attack_steps) {
      for (const t of step.techniques) {
        techIds.add(t.technique_id);
        techName[t.technique_id] = t.name;
        links.push({ a: `t:${t.technique_id}`, b: `b:${b.slug}` });
      }
    }
    for (const c of b.controls) {
      ctrlIds.add(c.control.slug);
      ctrlName[c.control.slug] = c.control.name;
      links.push({ a: `b:${b.slug}`, b: `c:${c.control.slug}` });
    }
  }

  const place = (ids: string[], col: 0 | 1 | 2, mk: (id: string) => Node): Node[] =>
    ids.map((id, i) => {
      const n = mk(id);
      const gap = (H - 80) / Math.max(ids.length, 1);
      return { ...n, x: COL_X[col], y: 40 + gap * (i + 0.5), col };
    });

  const nodes: Node[] = [
    ...place([...techIds], 0, (id) => ({ id: `t:${id}`, label: id, sub: techName[id], x: 0, y: 0, col: 0 })),
    ...place(breaches.map((b) => b.slug), 1, (slug) => {
      const b = breaches.find((x) => x.slug === slug)!;
      return { id: `b:${slug}`, label: b.organization.replace(/\s*\(fictional\)/i, ""), sub: b.sector, x: 0, y: 0, col: 1 };
    }),
    ...place([...ctrlIds], 2, (id) => ({ id: `c:${id}`, label: ctrlName[id], x: 0, y: 0, col: 2 })),
  ];

  const byId: Record<string, Node> = Object.fromEntries(nodes.map((n) => [n.id, n]));
  return { nodes, links, byId };
}

export default function BreachMap({ breaches }: { breaches: BreachDetail[] }) {
  const { nodes, links, byId } = useMemo(() => layout(breaches), [breaches]);
  const [hover, setHover] = useState<string | null>(null);

  const connected = useMemo(() => {
    if (!hover) return null;
    const set = new Set<string>([hover]);
    for (const l of links) {
      if (l.a === hover) set.add(l.b);
      if (l.b === hover) set.add(l.a);
    }
    return set;
  }, [hover, links]);

  const isDim = (id: string) => (connected ? !connected.has(id) : false);
  const linkActive = (l: Link) => connected && (connected.has(l.a) && connected.has(l.b));

  return (
    <div className="w-full">
      <div className="mb-3 flex items-center gap-4 font-mono text-[11px] uppercase tracking-widest text-faint">
        <span>ATT&amp;CK technique</span>
        <span className="text-line-strong">→</span>
        <span>breach</span>
        <span className="text-line-strong">→</span>
        <span>missing control</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Breach map">
        {links.map((l, i) => {
          const a = byId[l.a];
          const b = byId[l.b];
          const active = linkActive(l);
          return (
            <path
              key={i}
              d={`M ${a.x} ${a.y} C ${(a.x + b.x) / 2} ${a.y}, ${(a.x + b.x) / 2} ${b.y}, ${b.x} ${b.y}`}
              fill="none"
              stroke={active ? "var(--color-accent)" : "var(--color-line-strong)"}
              strokeWidth={active ? 1.4 : 0.8}
              opacity={connected ? (active ? 0.95 : 0.12) : 0.5}
            />
          );
        })}
        {nodes.map((n) => {
          const dim = isDim(n.id);
          const active = n.id === hover;
          const anchor = n.col === 0 ? "end" : n.col === 2 ? "start" : "middle";
          const dx = n.col === 0 ? -10 : n.col === 2 ? 10 : 0;
          return (
            <g
              key={n.id}
              onMouseEnter={() => setHover(n.id)}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: "pointer", opacity: dim ? 0.3 : 1, transition: "opacity .15s" }}
            >
              <circle cx={n.x} cy={n.y} r={active ? 4.5 : 3} fill={active || (connected && !dim) ? "var(--color-accent)" : "var(--color-muted)"} />
              <text
                x={n.x + dx}
                y={n.y + (n.col === 1 ? -8 : 3.5)}
                textAnchor={anchor}
                className={n.col === 0 ? "font-mono" : ""}
                fontSize={n.col === 0 ? 11 : 12}
                fill={active ? "var(--color-ink)" : "var(--color-muted)"}
              >
                {n.label}
              </text>
              {n.col === 1 && n.sub && (
                <text x={n.x} y={n.y + 14} textAnchor="middle" className="font-mono" fontSize={9} fill="var(--color-faint)">
                  {n.sub.toLowerCase()}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
