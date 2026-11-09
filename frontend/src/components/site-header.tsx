import Link from "next/link";
import { Suspense } from "react";

import { NavLinkList, NavLinks } from "@/components/nav-links";
import { ThemeToggle } from "@/components/theme-toggle";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-t-[3px] border-t-brand border-b bg-background/90 backdrop-blur supports-backdrop-filter:bg-background/75">
      <div className="mx-auto flex h-14 max-w-6xl items-stretch gap-4 px-4 sm:gap-8 sm:px-6">
        <Link href="/" aria-label="NBA Analytics home" className="flex shrink-0 items-center gap-2.5">
          <BallMark />
          <span className="hidden font-display text-xl leading-none font-bold tracking-wide uppercase sm:inline">
            NBA&nbsp;Analytics
          </span>
        </Link>
        <Suspense fallback={<NavLinkList />}>
          <NavLinks />
        </Suspense>
        <div className="ml-auto flex items-center">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

/** A basketball drawn with its seams. */
function BallMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-7 text-brand" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="12" cy="12" r="10" fill="currentColor" fillOpacity="0.14" />
      <path d="M2 12h20M12 2v20M5 4.9c3 2.5 3 11.7 0 14.2M19 4.9c-3 2.5-3 11.7 0 14.2" />
    </svg>
  );
}
