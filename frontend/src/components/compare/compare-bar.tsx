import { ArrowRightIcon } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

/**
 * The Compare button under the lineup, with a line on what to do next. Without `href` (fewer than
 * two players) the button is shown disabled, so it's clear where the comparison will come from.
 */
export function CompareBar({ count, href, children }: { count: number; href?: string; children: React.ReactNode }) {
  const label = count >= 2 ? `Compare ${count} players` : "Compare players";
  const className =
    "inline-flex h-12 shrink-0 items-center gap-2 px-6 font-display text-lg font-bold tracking-[0.06em] uppercase transition-colors";
  return (
    <div className="mt-6 flex flex-col gap-x-6 gap-y-3 border-y py-5 sm:flex-row sm:items-center">
      {href ? (
        <Link href={href} className={cn(className, "bg-brand text-brand-foreground hover:bg-foreground hover:text-background")}>
          {label}
          <ArrowRightIcon className="size-5" aria-hidden="true" />
        </Link>
      ) : (
        <span role="link" aria-disabled="true" className={cn(className, "cursor-not-allowed bg-muted text-muted-foreground")}>
          {label}
        </span>
      )}
      <p className="text-muted-foreground">{children}</p>
    </div>
  );
}
