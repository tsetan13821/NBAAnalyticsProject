import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import type { SimilarPlayers as SimilarPlayersData } from "@/lib/api/client";
import { compareHref, MAX_PLAYERS } from "@/lib/compare";
import { stat } from "@/lib/format";

/** The five players whose role scores were closest to this player's in one season. */
export function SimilarPlayers({ data }: { data: SimilarPlayersData }) {
  return (
    <div>
      <p className="mb-4 text-sm text-muted-foreground">
        In {data.season}, {data.player.name} profiled as{" "}
        <span className="font-medium text-foreground">
          {data.tier === "Average" ? "an average" : `${data.tier === "Elite" ? "an elite" : "a very good"}`}{" "}
          {data.archetype.toLowerCase()}
        </span>
        . The closest matches that season:
      </p>
      <ol className="border-t-2 border-foreground">
        {data.similar.map((s) => (
          <li
            key={s.player.id}
            className="group relative grid grid-cols-[1.5rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 border-b py-3 transition-colors hover:bg-muted/40 sm:grid-cols-[1.5rem_minmax(0,1fr)_10rem_5rem]"
          >
            <span className="tabular font-display text-xl font-bold text-muted-foreground">{s.rank}</span>
            <span className="flex min-w-0 items-center gap-3">
              <PlayerAvatar player={s.player} />
              <span className="min-w-0">
                <Link
                  href={`/players/${s.player.id}`}
                  className="block truncate font-medium after:absolute after:inset-0 group-hover:text-brand"
                >
                  {s.player.name}
                </Link>
                <span className="block text-xs text-muted-foreground">
                  {s.team_abbr} · {s.archetype ? `${s.archetype}, ${s.tier?.toLowerCase()}` : "No role"}
                </span>
              </span>
            </span>
            <span className="tabular hidden text-sm text-muted-foreground sm:block">
              {stat(s.pts_pg)} / {stat(s.reb_pg)} / {stat(s.ast_pg)}
            </span>
            <span className="tabular text-right font-display text-lg font-bold">{s.distance.toFixed(2)}</span>
          </li>
        ))}
      </ol>
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <p className="text-xs text-muted-foreground">
          <span className="hidden sm:inline">Points / rebounds / assists per game, then </span>
          <span className="sm:hidden">Right: </span>distance between role scores (lower is closer).
        </p>
        <Link
          href={compareHref({
            ids: [data.player.id, ...data.similar.slice(0, MAX_PLAYERS - 1).map((s) => s.player.id)],
            season: data.season,
            peers: "ALL",
            show: true,
          })}
          className="eyebrow text-brand underline-offset-4 hover:underline"
        >
          Compare with the top {Math.min(data.similar.length, MAX_PLAYERS - 1)} →
        </Link>
      </div>
    </div>
  );
}
