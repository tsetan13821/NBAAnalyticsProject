"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { adjacentSeasons } from "@/lib/format";
import { cn } from "@/lib/utils";

/** "/mvp/{season}", "2023-24" -> "/mvp/2023-24" */
export function seasonHref(template: string, season: string): string {
  return template.replace("{season}", season);
}

/**
 * Previous / next buttons plus a dropdown of every season. `seasons` is sorted oldest first, and
 * `href` is a URL template with a `{season}` placeholder (a string, so a server component can pass it).
 */
export function SeasonPicker({
  seasons,
  current,
  href,
  scroll = true,
}: {
  seasons: string[];
  current: string;
  href: string;
  /** false keeps the scroll position, for pickers that only change part of the page. */
  scroll?: boolean;
}) {
  const router = useRouter();
  const { previous, next } = adjacentSeasons(seasons, current);
  const step = { href, scroll };

  return (
    <div className="flex items-center gap-1.5">
      <StepLink {...step} season={previous} label="Previous season" icon={<ChevronLeftIcon />} />
      <Select value={current} onValueChange={(season) => season && router.push(seasonHref(href, season), { scroll })}>
        <SelectTrigger aria-label="Season" className="tabular w-28">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {[...seasons].reverse().map((season) => (
            <SelectItem key={season} value={season} className="tabular">
              {season}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <StepLink {...step} season={next} label="Next season" icon={<ChevronRightIcon />} />
    </div>
  );
}

function StepLink({
  season,
  label,
  icon,
  href,
  scroll,
}: {
  season?: string;
  label: string;
  icon: React.ReactNode;
  href: string;
  scroll: boolean;
}) {
  const className = cn(buttonVariants({ variant: "outline", size: "icon" }));
  if (!season) {
    return (
      <span className={cn(className, "pointer-events-none opacity-40")} aria-hidden="true">
        {icon}
      </span>
    );
  }
  return (
    <Link href={seasonHref(href, season)} scroll={scroll} className={className} aria-label={`${label}: ${season}`}>
      {icon}
    </Link>
  );
}
