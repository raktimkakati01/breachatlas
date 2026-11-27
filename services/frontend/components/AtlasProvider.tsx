"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  getControls,
  getStats,
  getBreach,
  listBreaches,
  type BreachDetail,
  type Control,
  type Stats,
} from "@/lib/api";

export type TechniqueIndexEntry = {
  technique_id: string;
  name: string;
  url: string | null;
  breachSlugs: string[];
};

type AtlasState = {
  stats: Stats | null;
  breaches: BreachDetail[];
  controls: Control[];
  techniques: TechniqueIndexEntry[];
  loading: boolean;
  error: string | null;
};

const AtlasContext = createContext<AtlasState | null>(null);

export function AtlasProvider({ children }: { children: React.ReactNode }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [breaches, setBreaches] = useState<BreachDetail[]>([]);
  const [controls, setControls] = useState<Control[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [s, list, ctrls] = await Promise.all([
          getStats(),
          listBreaches(),
          getControls(),
        ]);
        const details = await Promise.all(list.items.map((b) => getBreach(b.slug)));
        if (!alive) return;
        setStats(s);
        setBreaches(details);
        setControls(ctrls);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Derive a technique index (ATT&CK technique -> which breaches used it).
  const techniques = useMemo<TechniqueIndexEntry[]>(() => {
    const byId = new Map<string, TechniqueIndexEntry>();
    for (const b of breaches) {
      for (const step of b.attack_steps) {
        for (const t of step.techniques) {
          const e = byId.get(t.technique_id) ?? {
            technique_id: t.technique_id,
            name: t.name,
            url: t.url ?? null,
            breachSlugs: [],
          };
          if (!e.breachSlugs.includes(b.slug)) e.breachSlugs.push(b.slug);
          byId.set(t.technique_id, e);
        }
      }
    }
    return [...byId.values()].sort((a, b) =>
      a.technique_id.localeCompare(b.technique_id),
    );
  }, [breaches]);

  const value = useMemo<AtlasState>(
    () => ({ stats, breaches, controls, techniques, loading, error }),
    [stats, breaches, controls, techniques, loading, error],
  );

  return <AtlasContext.Provider value={value}>{children}</AtlasContext.Provider>;
}

export function useAtlas(): AtlasState {
  const ctx = useContext(AtlasContext);
  if (!ctx) throw new Error("useAtlas must be used within <AtlasProvider>");
  return ctx;
}
