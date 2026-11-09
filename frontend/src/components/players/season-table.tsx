import { TrophyIcon } from "lucide-react";
import Link from "next/link";

import type { PlayerProfile, PlayerSeason } from "@/lib/api/client";
import { percent, shortDate, stat } from "@/lib/format";
import { cn } from "@/lib/utils";

/** The numeric fields of a season row. */
type StatKey = { [K in keyof PlayerSeason]: PlayerSeason[K] extends number ? K : never }[keyof PlayerSeason];
type CareerKey = keyof PlayerProfile["career"];

type Column = {
  key: StatKey;
  label: string;
  title: string;
  format: (v: number) => string;
  /** Mark the player's best season in this column. */
  best?: boolean;
  /** Also shown in the career row (the API has career averages for these). */
  career?: boolean;
};

const COLUMNS: Column[] = [
  { key: "games", label: "GP", title: "Games played", format: String, career: true },
  { key: "min_pg", label: "MIN", title: "Minutes per game", format: (v) => stat(v), career: true },
  { key: "pts_pg", label: "PTS", title: "Points per game", format: (v) => stat(v), best: true, career: true },
  { key: "reb_pg", label: "REB", title: "Rebounds per game", format: (v) => stat(v), best: true, career: true },
  { key: "ast_pg", label: "AST", title: "Assists per game", format: (v) => stat(v), best: true, career: true },
  { key: "stl_pg", label: "STL", title: "Steals per game", format: (v) => stat(v), best: true, career: true },
  { key: "blk_pg", label: "BLK", title: "Blocks per game", format: (v) => stat(v), best: true, career: true },
  { key: "ts_pct", label: "TS%", title: "True shooting percentage", format: (v) => percent(v), best: true },
  { key: "usg_pct", label: "USG%", title: "Usage rate", format: (v) => percent(v) },
  { key: "pie", label: "PIE", title: "Player Impact Estimate", format: (v) => percent(v), best: true },
];

/**
 * The season with the highest value in each "best" column. Ties go to the earlier season. The season in
 * progress is left out: a hot start over a handful of games isn't a career best.
 */
export function careerBests(seasons: PlayerSeason[]): Partial<Record<StatKey, string>> {
  const bests: Partial<Record<StatKey, string>> = {};
  const finished = seasons.filter((s) => !s.in_progress);
  for (const column of COLUMNS) {
    if (!column.best || finished.length === 0) continue;
    let top = finished[0];
    for (const s of finished) if (s[column.key] > top[column.key]) top = s;
    bests[column.key] = top.season;
  }
  return bests;
}

const CELL = "tabular px-2.5 py-2 text-right";

/** Every season, oldest first, with a career-average row; each column's best season is in bold. */
export function SeasonTable({ profile, asOf }: { profile: PlayerProfile; asOf?: string | null }) {
  const mvp = new Set(profile.mvp_seasons);
  const bests = careerBests(profile.seasons);
  const inProgress = profile.seasons.find((s) => s.in_progress);
  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[48rem] text-sm">
          <caption className="sr-only">
            {profile.name}, season by season. Per-game averages; the best completed season in each column is in bold.
          </caption>
          <thead>
            <tr className="eyebrow border-b-2 border-foreground text-muted-foreground">
              <th scope="col" className="sticky left-0 bg-background py-2 pr-3 text-left font-semibold">
                Season
              </th>
              <th scope="col" className="px-2.5 py-2 text-left font-semibold">
                Team
              </th>
              {COLUMNS.map((c) => (
                <th key={c.key} scope="col" className="px-2.5 py-2 text-right font-semibold">
                  <abbr title={c.title} className="no-underline">
                    {c.label}
                  </abbr>
                </th>
              ))}
              <th scope="col" className="py-2 pl-2.5 text-left font-semibold">
                Role
              </th>
            </tr>
          </thead>
          <tbody>
            {profile.seasons.map((s) => {
              const isMvp = mvp.has(s.season);
              return (
                <tr key={s.season} className={cn("border-b transition-colors hover:bg-muted/40", isMvp && "bg-brand/8")}>
                  <th scope="row" className={cn("sticky left-0 py-2 pr-3 text-left font-normal", isMvp ? "bg-[color-mix(in_oklch,var(--brand)_8%,var(--background))]" : "bg-background")}>
                    <span className="tabular inline-flex items-center gap-1.5 font-display text-base font-bold">
                      {s.season}
                      {s.in_progress && (
                        <span className="eyebrow rounded-sm bg-brand/15 px-1.5 py-0.5 text-[0.6rem] font-semibold text-brand">
                          So far
                        </span>
                      )}
                      {isMvp && (
                        <Link href={`/mvp/${s.season}`} className="text-brand" aria-label={`MVP in ${s.season}: see the race`}>
                          <TrophyIcon className="size-3.5" aria-hidden="true" />
                        </Link>
                      )}
                    </span>
                  </th>
                  <td className="px-2.5 py-2 text-muted-foreground" title={s.team_abbr_then !== s.team_abbr ? `Now ${s.team_abbr}` : undefined}>
                    {s.team_abbr_then}
                  </td>
                  {COLUMNS.map((c) => (
                    <td key={c.key} className={cn(CELL, bests[c.key] === s.season && "font-bold text-foreground")}>
                      {c.format(s[c.key])}
                    </td>
                  ))}
                  <td className="py-2 pl-2.5 whitespace-nowrap text-muted-foreground">
                    {s.archetype ? `${s.archetype} · ${s.tier}` : s.in_progress ? "After 20 games" : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-foreground font-medium">
              <th scope="row" className="sticky left-0 bg-background py-2 pr-3 text-left">
                <span className="eyebrow">Career</span>
              </th>
              <td className="px-2.5 py-2" />
              {COLUMNS.map((c) => (
                <td key={c.key} className={CELL}>
                  {c.career ? c.format(profile.career[c.key as CareerKey]) : ""}
                </td>
              ))}
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
      {inProgress && (
        <p className="mt-3 text-sm text-muted-foreground">
          {inProgress.season} is under way: these numbers cover {inProgress.games}{" "}
          {inProgress.games === 1 ? "game" : "games"} so far{asOf && <>, as of {shortDate(asOf)}</>}. A role is only
          given after 20 games, and the career row includes these games.
        </p>
      )}
    </div>
  );
}
