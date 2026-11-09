import type { TeamRef } from "@/lib/api/client";
import { readableText } from "@/lib/color";
import { cn } from "@/lib/utils";

/** Team abbreviation on the team's primary colour, with the full name for screen readers and on hover. */
export function TeamBadge({ team, className }: { team: Pick<TeamRef, "abbr" | "name" | "primary_color">; className?: string }) {
  return (
    <span
      title={team.name}
      className={cn(
        "inline-flex h-5 min-w-9 shrink-0 items-center justify-center rounded px-1.5 text-[10px] font-bold tracking-wide ring-1 ring-foreground/15",
        className,
      )}
      style={{ backgroundColor: team.primary_color, color: readableText(team.primary_color) }}
    >
      <span aria-hidden="true">{team.abbr}</span>
      <span className="sr-only">{team.name}</span>
    </span>
  );
}
