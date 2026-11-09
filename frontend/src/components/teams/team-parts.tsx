/** The pieces of the franchise pages: hero, standings, season ledger, roster and leaders. */
import { TrophyIcon } from "lucide-react";
import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import { TeamBadge } from "@/components/team-badge";
import type {
  FranchiseLeaders,
  Roster,
  SeasonInfo,
  TeamDetail,
  TeamSummary,
} from "@/lib/api/client";
import { readableText } from "@/lib/color";
import { ordinal, percent, seasonSpan, stat } from "@/lib/format";
import {
  gamesBehind,
  gamesBehindText,
  LEADER_STATS,
  record,
  signed,
  standings,
  teamHref,
  type TeamQuery,
  teamQueryHref,
} from "@/lib/teams";
import { cn } from "@/lib/utils";

const HEAD = "eyebrow border-b-2 border-foreground text-muted-foreground";
const NUM = "tabular px-2.5 py-2 text-right";

/** Name and identity on a band of the team's colour. */
export function TeamHero({ team }: { team: TeamDetail }) {
  const ink = readableText(team.primary_color);
  return (
    <header className="mb-10">
      <div
        className="flex flex-wrap items-end justify-between gap-6 px-5 py-8 sm:px-8"
        style={{ backgroundColor: team.primary_color, color: ink }}
      >
        <div>
          <p className="eyebrow opacity-80">
            {team.conference}ern Conference · since {team.first_season}
          </p>
          <h1 className="mt-2 font-display text-5xl leading-[0.92] font-bold tracking-tight uppercase sm:text-7xl">
            {team.city}
            <br />
            {team.nickname}
          </h1>
        </div>
        <span
          aria-hidden="true"
          className="font-display text-7xl leading-none font-bold tracking-tight opacity-25 sm:text-9xl"
        >
          {team.abbr}
        </span>
      </div>
      <div className="h-2" style={{ backgroundColor: team.secondary_color }} />
    </header>
  );
}

/** One conference's standings for the latest season. */
export function StandingsTable({
  teams,
  conference,
  since,
}: {
  teams: TeamSummary[];
  conference: TeamSummary["conference"];
  /** First season in the data, for the titles column */
  since: string;
}) {
  const rows = standings(teams, conference);
  const leader = rows[0];
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[30rem] text-sm">
        <caption className="mb-3 text-left font-display text-xl font-bold uppercase">{conference}</caption>
        <thead>
          <tr className={HEAD}>
            <th scope="col" className="w-8 py-2 pr-2 text-right font-semibold">
              #
            </th>
            <th scope="col" className="px-2.5 py-2 text-left font-semibold">
              Team
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Wins and losses" className="no-underline">W–L</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Games behind the conference leader" className="no-underline">GB</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Point differential per game" className="no-underline">+/−</abbr>
            </th>
            <th scope="col" className="py-2 pl-2.5 text-right font-semibold">
              <abbr title={`Championships since ${since}`} className="no-underline">Titles</abbr>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.abbr} className="border-b transition-colors hover:bg-muted/40">
              <td className="tabular py-2 pr-2 text-right text-muted-foreground">{t.latest.conference_rank}</td>
              <th scope="row" className="px-2.5 py-2 text-left font-normal">
                <Link href={teamHref(t.abbr)} className="inline-flex items-center gap-2 hover:text-brand">
                  <TeamBadge team={t} />
                  <span className="font-medium">{t.name}</span>
                </Link>
              </th>
              <td className={NUM}>{record(t.latest.wins, t.latest.losses)}</td>
              <td className={cn(NUM, "text-muted-foreground")}>{gamesBehindText(gamesBehind(leader, t))}</td>
              <td className={NUM}>{signed(t.latest.point_diff_pg)}</td>
              <td className="tabular py-2 pl-2.5 text-right">
                {t.titles > 0 ? (
                  <span className="inline-flex items-center gap-1 font-medium text-brand">
                    <TrophyIcon className="size-3.5" aria-hidden="true" />
                    {t.titles}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Every champion since the start of the data, newest first. */
export function ChampionsList({ seasons }: { seasons: SeasonInfo[] }) {
  const won = seasons.filter((s) => s.champion).reverse();
  return (
    <ol className="grid grid-cols-2 gap-x-6 sm:grid-cols-3 lg:grid-cols-5">
      {won.map((s) => (
        <li key={s.season} className="flex items-center justify-between gap-3 border-b py-2">
          <span className="tabular font-display text-base font-bold">{s.season}</span>
          <Link href={teamHref(s.champion!.abbr)} className="hover:opacity-80" aria-label={`${s.champion!.name}, ${s.season} champions`}>
            <TeamBadge team={s.champion!} />
          </Link>
        </li>
      ))}
    </ol>
  );
}

/** Every season of the franchise, newest first: record, rank, differential, titles and MVPs. */
export function FranchiseSeasons({ team, query }: { team: TeamDetail; query: TeamQuery }) {
  const mvps = new Map(team.mvps.map((m) => [m.season, m.player]));
  const best = Math.max(...team.seasons.filter((s) => !s.in_progress).map((s) => s.win_pct));
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[38rem] text-sm">
        <caption className="sr-only">
          {team.name}, season by season since {team.first_season}, newest first. The best record is in bold.
        </caption>
        <thead>
          <tr className={HEAD}>
            <th scope="col" className="py-2 pr-3 text-left font-semibold">Season</th>
            <th scope="col" className="px-2.5 py-2 text-left font-semibold">
              <abbr title="The abbreviation the franchise used that season" className="no-underline">As</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">W–L</th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">Win %</th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Rank in the conference" className="no-underline">Conf.</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Point differential per game" className="no-underline">+/−</abbr>
            </th>
            <th scope="col" className="py-2 pl-2.5 text-left font-semibold">Honours</th>
          </tr>
        </thead>
        <tbody>
          {[...team.seasons].reverse().map((s) => {
            const mvp = mvps.get(s.season);
            return (
              <tr key={s.season} className={cn("border-b transition-colors hover:bg-muted/40", s.is_champion && "bg-brand/8")}>
                <th scope="row" className="py-2 pr-3 text-left font-normal">
                  <Link
                    href={teamQueryHref(team.abbr, { ...query, season: s.season }, "roster")}
                    scroll={false}
                    className="tabular inline-flex items-center gap-1.5 font-display text-base font-bold hover:text-brand"
                    aria-label={`${s.season}: see the roster`}
                  >
                    {s.season}
                    {s.in_progress && (
                      <span className="eyebrow rounded-sm bg-brand/15 px-1.5 py-0.5 text-[0.6rem] font-semibold text-brand">
                        So far
                      </span>
                    )}
                  </Link>
                </th>
                <td className="px-2.5 py-2 text-muted-foreground">{s.team_abbr_then}</td>
                <td className={cn(NUM, !s.in_progress && s.win_pct === best && "font-bold")}>{record(s.wins, s.losses)}</td>
                <td className={NUM}>{percent(s.win_pct)}</td>
                <td className={NUM}>{ordinal(s.conference_rank)}</td>
                <td className={NUM}>{signed(s.point_diff_pg)}</td>
                <td className="py-2 pl-2.5">
                  <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    {s.is_champion && (
                      <span className="inline-flex items-center gap-1 font-medium text-brand">
                        <TrophyIcon className="size-3.5" aria-hidden="true" />
                        Champions
                      </span>
                    )}
                    {mvp && (
                      <Link href={`/mvp/${s.season}`} className="text-muted-foreground hover:text-brand">
                        MVP: <span className="text-foreground">{mvp.name}</span>
                      </Link>
                    )}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** A season's players, top scorers first. */
export function TeamRoster({ roster, inProgress = false }: { roster: Roster; inProgress?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <caption className="sr-only">
          {roster.team.name} players in {roster.season}, per-game averages, top scorers first.
        </caption>
        <thead>
          <tr className={HEAD}>
            <th scope="col" className="py-2 pr-3 text-left font-semibold">Player</th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Games played" className="no-underline">GP</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Minutes per game" className="no-underline">MIN</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Points per game" className="no-underline">PTS</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Rebounds per game" className="no-underline">REB</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="Assists per game" className="no-underline">AST</abbr>
            </th>
            <th scope="col" className="px-2.5 py-2 text-right font-semibold">
              <abbr title="True shooting percentage" className="no-underline">TS%</abbr>
            </th>
            <th scope="col" className="py-2 pl-2.5 text-left font-semibold">Role</th>
          </tr>
        </thead>
        <tbody>
          {roster.players.map((p) => (
            <tr key={p.player.id} className="border-b transition-colors hover:bg-muted/40">
              <th scope="row" className="py-1.5 pr-3 text-left font-normal">
                <Link href={`/players/${p.player.id}`} className="inline-flex items-center gap-2.5 hover:text-brand">
                  <PlayerAvatar player={p.player} size="sm" />
                  <span className="font-medium">{p.player.name}</span>
                </Link>
              </th>
              <td className={NUM}>{p.games}</td>
              <td className={NUM}>{stat(p.min_pg)}</td>
              <td className={cn(NUM, "font-medium")}>{stat(p.pts_pg)}</td>
              <td className={NUM}>{stat(p.reb_pg)}</td>
              <td className={NUM}>{stat(p.ast_pg)}</td>
              <td className={NUM}>{percent(p.ts_pct)}</td>
              <td className="py-2 pl-2.5 whitespace-nowrap text-muted-foreground">
                {p.archetype ? `${p.archetype} · ${p.tier}` : inProgress ? "After 20 games" : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Links that re-rank the leaders table; the choice lives in the URL. */
export function LeaderStatLinks({ abbr, query }: { abbr: string; query: TeamQuery }) {
  return (
    <nav aria-label="Rank the leaders by" className="mb-4 flex flex-wrap gap-1.5">
      {LEADER_STATS.map((s) => (
        <Link
          key={s.key}
          href={teamQueryHref(abbr, { ...query, by: s.key }, "leaders")}
          scroll={false}
          aria-current={s.key === query.by ? "true" : undefined}
          className={cn(
            "eyebrow inline-flex h-8 items-center border px-3 transition-colors",
            s.key === query.by
              ? "border-foreground bg-foreground text-background"
              : "text-muted-foreground hover:border-foreground/50 hover:text-foreground",
          )}
        >
          {s.label}
        </Link>
      ))}
    </nav>
  );
}

/** The franchise's career leaders since the start of the data, ranked by one total. */
export function LeadersTable({ leaders }: { leaders: FranchiseLeaders }) {
  const columns = [
    { key: "games", label: "GP", title: "Games played" },
    { key: "points", label: "PTS", title: "Points" },
    { key: "rebounds", label: "REB", title: "Rebounds" },
    { key: "assists", label: "AST", title: "Assists" },
  ] as const;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <caption className="sr-only">
          {leaders.team.name} career leaders in {leaders.by} since {leaders.since}, totals with the franchise.
        </caption>
        <thead>
          <tr className={HEAD}>
            <th scope="col" className="w-8 py-2 pr-2 text-right font-semibold">#</th>
            <th scope="col" className="px-2.5 py-2 text-left font-semibold">Player</th>
            <th scope="col" className="px-2.5 py-2 text-left font-semibold">Seasons</th>
            {columns.map((c) => (
              <th key={c.key} scope="col" className={cn("px-2.5 py-2 text-right font-semibold", c.key === leaders.by && "text-foreground")}>
                <abbr title={c.title} className="no-underline">{c.label}</abbr>
              </th>
            ))}
            <th scope="col" className="py-2 pl-2.5 text-right font-semibold">
              <abbr title="Points per game with the franchise" className="no-underline">PPG</abbr>
            </th>
          </tr>
        </thead>
        <tbody>
          {leaders.leaders.map((l, i) => (
            <tr key={l.player.id} className="border-b transition-colors hover:bg-muted/40">
              <td className="tabular py-2 pr-2 text-right text-muted-foreground">{i + 1}</td>
              <th scope="row" className="px-2.5 py-1.5 text-left font-normal">
                <Link href={`/players/${l.player.id}`} className="inline-flex items-center gap-2.5 hover:text-brand">
                  <PlayerAvatar player={l.player} size="sm" />
                  <span className="font-medium">{l.player.name}</span>
                  {l.on_roster && (
                    <span className="eyebrow rounded-sm bg-brand/15 px-1.5 py-0.5 text-[0.6rem] font-semibold text-brand">
                      On the roster
                    </span>
                  )}
                </Link>
              </th>
              <td className="tabular px-2.5 py-2 whitespace-nowrap text-muted-foreground">
                {seasonSpan(l.first_season, l.last_season)}
                <span className="ml-1.5 text-xs">({l.seasons})</span>
              </td>
              {columns.map((c) => (
                <td key={c.key} className={cn(NUM, c.key === leaders.by && "font-bold")}>
                  {l[c.key].toLocaleString("en-US")}
                </td>
              ))}
              <td className="tabular py-2 pl-2.5 text-right">{stat(l.pts_pg)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
