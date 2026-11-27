"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAtlas } from "@/components/AtlasProvider";

type Item = {
  kind: "breach" | "control" | "technique";
  title: string;
  sub: string;
  href?: string; // internal route
  external?: string; // external url (ATT&CK)
};

const KIND_LABEL: Record<Item["kind"], string> = {
  breach: "breach",
  control: "control",
  technique: "technique",
};

export default function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const { breaches, controls, techniques } = useAtlas();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const all = useMemo<Item[]>(() => {
    const b = breaches.map<Item>((x) => ({
      kind: "breach",
      title: x.organization.replace(/\s*\(fictional\)/i, ""),
      sub: `${x.sector} · ${x.country} · ${x.date_disclosed}`,
      href: `/breach/${x.slug}`,
    }));
    const c = controls.map<Item>((x) => ({
      kind: "control",
      title: x.name,
      sub: x.cis_control_id ? `CIS Control ${x.cis_control_id}` : "CIS Control",
      href: `/control/${x.slug}`,
    }));
    const t = techniques.map<Item>((x) => ({
      kind: "technique",
      title: `${x.technique_id} · ${x.name}`,
      sub: `${x.breachSlugs.length} breach${x.breachSlugs.length === 1 ? "" : "es"}`,
      external: x.url ?? `https://attack.mitre.org/techniques/${x.technique_id}/`,
    }));
    return [...b, ...c, ...t];
  }, [breaches, controls, techniques]);

  const results = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = !needle
      ? all
      : all.filter(
          (i) =>
            i.title.toLowerCase().includes(needle) ||
            i.sub.toLowerCase().includes(needle),
        );
    return list.slice(0, 24);
  }, [q, all]);

  // Reset + focus when opened.
  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      const id = requestAnimationFrame(() => inputRef.current?.focus());
      return () => cancelAnimationFrame(id);
    }
  }, [open]);

  useEffect(() => setActive(0), [q]);

  const go = (item: Item) => {
    onClose();
    if (item.external) window.open(item.external, "_blank", "noopener,noreferrer");
    else if (item.href) router.push(item.href);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") return onClose();
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[active]) go(results[active]);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-bg/70 px-4 pt-[14vh] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-xl border border-line-strong bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-line px-4">
          <span className="font-mono text-xs text-faint">/</span>
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search breaches, controls, techniques…"
            className="w-full bg-transparent py-3.5 text-sm text-ink outline-none placeholder:text-faint"
          />
          <kbd className="rounded border border-line px-1.5 py-0.5 font-mono text-[10px] text-faint">
            esc
          </kbd>
        </div>
        <ul className="max-h-[52vh] overflow-y-auto py-1">
          {results.length === 0 && (
            <li className="px-4 py-6 text-center font-mono text-xs text-faint">
              no matches
            </li>
          )}
          {results.map((item, i) => (
            <li key={`${item.kind}:${item.title}`}>
              <button
                onMouseEnter={() => setActive(i)}
                onClick={() => go(item)}
                className={`flex w-full items-center justify-between gap-4 px-4 py-2.5 text-left ${
                  i === active ? "bg-line/60" : ""
                }`}
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm text-ink">{item.title}</span>
                  <span className="block truncate font-mono text-[11px] text-faint">
                    {item.sub}
                  </span>
                </span>
                <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-accent">
                  {KIND_LABEL[item.kind]}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
