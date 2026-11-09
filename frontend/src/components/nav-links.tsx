"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/mvp", label: "MVP Race" },
  { href: "/mvp/method", label: "Method" },
] as const;

/** The most specific link that matches wins, so /mvp/method highlights "Method", not "MVP Race". */
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
    <nav aria-label="Main" className="flex items-stretch gap-4 sm:gap-6">
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
