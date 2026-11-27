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

function Tabs({ pathname, className = "" }: { pathname: string; className?: string }) {
  return (
    <nav className={`flex items-center gap-1 rounded-full border border-line p-0.5 text-sm ${className}`}>
      {TABS.map((t) => {
        const act = isActive(t.href, pathname);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`flex-1 whitespace-nowrap rounded-full px-3 py-1 text-center transition-colors ${
              act ? "bg-ink text-bg" : "text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}

function Wordmark() {
  return (
    <Link href="/" className="flex items-center gap-2.5 text-ink">
      <span className="text-accent" aria-hidden>
        ◆
      </span>
      <span className="font-mono text-sm uppercase tracking-[0.3em] sm:tracking-[0.35em]">
        BreachAtlas
      </span>
    </Link>
  );
}

export default function Chrome() {
  const pathname = usePathname();
  const { paletteOpen, openPalette, closePalette } = useUI();

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-[2px]">
        {/* Desktop: tabs · wordmark · actions */}
        <div className="hidden items-center justify-between px-5 py-3 sm:flex">
          <Tabs pathname={pathname} />
          <Wordmark />
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
        </div>

        {/* Mobile: wordmark + search icon on top, full-width tabs below */}
        <div className="sm:hidden">
          <div className="flex items-center justify-between px-4 py-3">
            <Wordmark />
            <div className="flex items-center gap-1.5">
              <button
                onClick={openPalette}
                aria-label="Search"
                className="flex h-8 w-8 items-center justify-center rounded-full border border-line text-muted hover:text-ink"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                  <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
              <button className="rounded-full border border-line px-3 py-1 text-sm text-ink">
                Sign in
              </button>
            </div>
          </div>
          <div className="px-4 pb-3">
            <Tabs pathname={pathname} className="w-full" />
          </div>
        </div>
      </header>

      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </>
  );
}
