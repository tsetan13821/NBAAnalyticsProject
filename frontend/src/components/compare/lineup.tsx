import { XIcon } from "lucide-react";
import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import { positionName } from "@/components/players/player-hero";
import { TeamBadge } from "@/components/team-badge";
import type { PlayerRef, TeamSummary } from "@/lib/api/client";

export type LineupEntry = {
  player: PlayerRef & { position: string | null };
  color: string;
  removeHref: string;
  /** The team and games in the season being compared; absent when there is no shared season yet. */
  team?: Pick<TeamSummary, "abbr" | "name" | "primary_color">;
  games?: number;
  /** Metrics this player leads, out of `metricCount`. */
  leads?: number;
};

/**
 * The players being compared, one card each in their comparison colour, followed by `openSlots`
 * (list items for the places still free; the page passes the add-player buttons).
 */
export function Lineup({
  entries,
  metricCount,
  openSlots,
}: {
  entries: LineupEntry[];
  metricCount?: number;
  openSlots?: React.ReactNode;
}) {
  return (
    <ol className="grid grid-cols-2 gap-3 md:grid-cols-4" aria-label="Players being compared">
      {entries.map((entry) => (
        <LineupCard key={entry.player.id} entry={entry} metricCount={metricCount} />
      ))}
      {openSlots}
    </ol>
  );
}

function LineupCard({ entry, metricCount }: { entry: LineupEntry; metricCount?: number }) {
  const { player, color, team, games, leads } = entry;
  return (
    <li className="relative flex min-w-0 flex-col border bg-paper p-3 pt-4" style={{ borderTop: `4px solid ${color}` }}>
      <Link
        href={entry.removeHref}
        scroll={false}
        aria-label={`Remove ${player.name}`}
        title="Remove"
        className="absolute top-1.5 right-1.5 grid size-7 place-items-center text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        <XIcon className="size-4" />
      </Link>
      <PlayerAvatar player={player} size="lg" />
      <Link
        href={`/players/${player.id}`}
        className="mt-2 font-display text-xl leading-tight font-bold tracking-tight uppercase hover:text-brand sm:text-2xl"
      >
        {player.name}
      </Link>
      <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
        {team && <TeamBadge team={team} />}
        <span>{positionName(player.position, player.position_group)}</span>
        {games !== undefined && (
          <>
            <span aria-hidden="true">·</span>
            <span className="tabular">
              {games} {games === 1 ? "game" : "games"}
            </span>
          </>
        )}
      </p>
      {leads !== undefined && metricCount !== undefined && (
        <p className="mt-auto pt-3">
          <span className="tabular font-display text-3xl leading-none font-bold" style={{ color }}>
            {leads}
          </span>
          <span className="ml-1.5 text-xs text-muted-foreground">of {metricCount} categories led</span>
        </p>
      )}
    </li>
  );
}
