"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import CommandPalette from "@/components/CommandPalette";
import { useUI } from "@/components/UIProvider";

const TABS = [
  { label: "Breaches", href: "/" },
  { label: "Controls", href: "/controls" },
  { label: "Techniques", href: "/techniques" },
];

function isActive(tabHref: string, pathname: string): boolean {
  if (tabHref === "/") return pathname === "/" || pathname.startsWith("/breach");
  if (tabHref === "/controls")
    return pathname.startsWith("/controls") || pathname.startsWith("/control");
  return pathname.startsWith("/techniques");
}

export default function Chrome() {
  const pathname = usePathname();
  const { paletteOpen, openPalette, closePalette } = useUI();

  return (
    <>
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-line bg-bg/85 px-5 py-3 backdrop-blur-[2px]">
        <nav className="flex items-center gap-1 rounded-full border border-line p-0.5 text-sm">
          {TABS.map((t) => {
            const act = isActive(t.href, pathname);
            return (
              <Link
                key={t.href}
                href={t.href}
                className={`rounded-full px-3 py-1 transition-colors ${
                  act ? "bg-ink text-bg" : "text-muted hover:text-ink"
                }`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>

        <Link href="/" className="flex items-center gap-2.5 text-ink">
          <span className="text-accent" aria-hidden>
            ◆
          </span>
          <span className="font-mono text-sm uppercase tracking-[0.35em]">BreachAtlas</span>
        </Link>

        <div className="flex items-center gap-3 text-sm">
          <button
            onClick={openPalette}
            className="flex items-center gap-2 text-muted hover:text-ink"
          >
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

      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </>
  );
}
