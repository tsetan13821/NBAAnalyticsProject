/** Helpers for the franchise pages. */
import type { LeaderStat, TeamSeason, TeamSummary } from "@/lib/api/client";
import { isSeason } from "@/lib/format";

export const LEADER_STATS: { key: LeaderStat; label: string }[] = [
  { key: "points", label: "Points" },
  { key: "rebounds", label: "Rebounds" },
  { key: "assists", label: "Assists" },
  { key: "games", label: "Games" },
];

export function teamHref(abbr: string): string {
  return `/teams/${abbr}`;
}

/** "bos" -> "BOS"; anything that can't be a team abbreviation -> null */
export function parseTeamAbbr(raw: string): string | null {
  const abbr = raw.toUpperCase();
  return /^[A-Z]{2,3}$/.test(abbr) ? abbr : null;
}

/** The franchise page's query string: `?season=` picks the roster, `?by=` ranks the leaders. */
export type TeamQuery = { season?: string; by: LeaderStat };

export function parseTeamQuery(params: Record<string, string | string[] | undefined>): TeamQuery {
  const season = [params.season].flat()[0];
  const by = [params.by].flat()[0];
  return {
    season: season && isSeason(season) ? season : undefined,
    by: LEADER_STATS.find((s) => s.key === by)?.key ?? "points",
  };
}

/** The franchise page URL with one part of the query changed; defaults are left out. */
export function teamQueryHref(abbr: string, query: TeamQuery, anchor?: string): string {
  const parts = [query.season && `season=${query.season}`, query.by !== "points" && `by=${query.by}`].filter(Boolean);
  return `${teamHref(abbr)}${parts.length ? `?${parts.join("&")}` : ""}${anchor ? `#${anchor}` : ""}`;
}

/** 8, 2 -> "8–2" */
export function record(wins: number, losses: number): string {
  return `${wins}–${losses}`;
}

/** 6 -> "+6.0", -2.25 -> "−2.3" (a real minus sign), 0 -> "0.0" */
export function signed(value: number, digits = 1): string {
  const text = Math.abs(value).toFixed(digits);
  if (Number(text) === 0) return text;
  return `${value > 0 ? "+" : "−"}${text}`;
}

/** One conference's teams in standings order (conference rank, then win %). */
export function standings(teams: TeamSummary[], conference: TeamSummary["conference"]): TeamSummary[] {
  return teams
    .filter((t) => t.conference === conference)
    .sort((a, b) => a.latest.conference_rank - b.latest.conference_rank || b.latest.win_pct - a.latest.win_pct);
}

/** Games behind the leader: half the difference in wins plus half the difference in losses. */
export function gamesBehind(leader: TeamSummary, team: TeamSummary): number {
  return (leader.latest.wins - team.latest.wins + (team.latest.losses - leader.latest.losses)) / 2;
}

/** 0 -> "—", 1.5 -> "1.5", 2 -> "2" */
export function gamesBehindText(gb: number): string {
  if (gb <= 0) return "—";
  return Number.isInteger(gb) ? String(gb) : gb.toFixed(1);
}

/** The completed season with the best win % (ties: the earlier one). */
export function bestSeason(seasons: TeamSeason[]): TeamSeason | undefined {
  return seasons
    .filter((s) => !s.in_progress)
    .reduce<TeamSeason | undefined>((best, s) => (!best || s.win_pct > best.win_pct ? s : best), undefined);
}

/** Seasons in a row (up to the latest completed one) with a winning record. */
export function winningStreak(seasons: TeamSeason[]): number {
  let streak = 0;
  for (const s of [...seasons].reverse()) {
    if (s.in_progress) continue;
    if (s.win_pct <= 0.5) break;
    streak += 1;
  }
  return streak;
}
