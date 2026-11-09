import Link from "next/link";
import { Suspense } from "react";

import { NavLinkList, NavLinks } from "@/components/nav-links";
import { ThemeToggle } from "@/components/theme-toggle";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:gap-6">
        <Link href="/" aria-label="NBA Analytics home" className="flex items-center gap-2 font-semibold tracking-tight">
          <BallMark />
          <span className="hidden whitespace-nowrap sm:inline">NBA Analytics</span>
        </Link>
        <Suspense fallback={<NavLinkList />}>
          <NavLinks />
        </Suspense>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function BallMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-6 text-brand" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.75">
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2v20M5 4.9c3 2.5 3 11.7 0 14.2M19 4.9c-3 2.5-3 11.7 0 14.2" />
    </svg>
  );
}
