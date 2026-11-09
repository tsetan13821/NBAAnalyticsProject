"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/mvp", label: "MVP Race" },
  { href: "/players", label: "Players" },
] as const;

/** The link whose section contains the path; the most specific wins if sections ever nest. */
export function activeHref(pathname: string): string | undefined {
  const matches = LINKS.map((link) => link.href).filter((href) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`),
  );
  return matches.sort((a, b) => b.length - a.length)[0];
}

/** The links with no active state: the static fallback while the current path streams in. */
export function NavLinkList({ pathname }: { pathname?: string }) {
  const active = pathname === undefined ? undefined : activeHref(pathname);
  return (
    <nav aria-label="Main" className="-mx-1 flex min-w-0 items-stretch gap-4 overflow-x-auto px-1 [scrollbar-width:none] sm:gap-6">
      {LINKS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          aria-current={href === active ? "page" : undefined}
          className={cn(
            "flex items-center border-b-2 border-transparent pt-0.5 font-display text-[0.95rem] font-semibold tracking-[0.08em] whitespace-nowrap text-muted-foreground uppercase transition-colors hover:text-foreground",
            href === active && "border-brand text-foreground",
          )}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}

/** Highlights the current section. Render inside <Suspense> (the path is only known at request time). */
export function NavLinks() {
  return <NavLinkList pathname={usePathname()} />;
}
