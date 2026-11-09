"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { adjacentSeasons } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Previous / next buttons plus a dropdown of every season. `seasons` is sorted oldest first. */
export function SeasonPicker({ seasons, current }: { seasons: string[]; current: string }) {
  const router = useRouter();
  const { previous, next } = adjacentSeasons(seasons, current);

  return (
    <div className="flex items-center gap-1.5">
      <StepLink season={previous} label="Previous season" icon={<ChevronLeftIcon />} />
      <Select value={current} onValueChange={(season) => season && router.push(`/mvp/${season}`)}>
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
      <StepLink season={next} label="Next season" icon={<ChevronRightIcon />} />
    </div>
  );
}

function StepLink({ season, label, icon }: { season?: string; label: string; icon: React.ReactNode }) {
  const className = cn(buttonVariants({ variant: "outline", size: "icon" }));
  if (!season) {
    return (
      <span className={cn(className, "pointer-events-none opacity-40")} aria-hidden="true">
        {icon}
      </span>
    );
  }
  return (
    <Link href={`/mvp/${season}`} className={className} aria-label={`${label}: ${season}`}>
      {icon}
    </Link>
  );
}
