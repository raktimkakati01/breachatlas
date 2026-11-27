"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

type UIState = {
  paletteOpen: boolean;
  openPalette: () => void;
  closePalette: () => void;
};

const UIContext = createContext<UIState | null>(null);

export function UIProvider({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);

  const openPalette = useCallback(() => setPaletteOpen(true), []);
  const closePalette = useCallback(() => setPaletteOpen(false), []);

  // Global ⌘K / Ctrl+K to toggle the search palette.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const value = useMemo<UIState>(
    () => ({ paletteOpen, openPalette, closePalette }),
    [paletteOpen, openPalette, closePalette],
  );

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
}

export function useUI(): UIState {
  const ctx = useContext(UIContext);
  if (!ctx) throw new Error("useUI must be used within <UIProvider>");
  return ctx;
}
