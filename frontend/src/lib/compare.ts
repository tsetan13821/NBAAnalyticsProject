/** The /compare URL <-> page state, the metric groups, and who leads each metric. */
import type { MetricInfo, MetricKey, PlayerComparison, PlayerSeason } from "@/lib/api/client";
import { isSeason, percent, stat } from "@/lib/format";
import { parsePlayerId } from "@/lib/player-search";

export const MIN_PLAYERS = 2;
export const MAX_PLAYERS = 4;

/** Percentiles against every player that season, or against players in the same position group. */
export type PeerGroup = "ALL" | "POSITION";

export type CompareState = {
  /** In the order they were added; unique; at most MAX_PLAYERS */
  ids: number[];
  season?: string;
  peers: PeerGroup;
  /** Text typed into the "add a player" search */
  q?: string;
  /** The comparison is shown: the Compare button was pressed (or a link went straight to it). */
  show?: boolean;
};

type SearchParams = Record<string, string | string[] | undefined>;

/** Accepts "?ids=1,2" and "?ids=1&ids=2"; anything that isn't a player id is dropped. */
export function parseCompareState(params: SearchParams): CompareState {
  const raw = [params.ids ?? []].flat().flatMap((value) => value.split(","));
  const ids = [...new Set(raw.map((value) => parsePlayerId(value.trim())).filter((id) => id !== null))];
  const season = [params.season].flat()[0]?.trim();
  const peers = [params.peers].flat()[0]?.trim().toLowerCase();
  const q = [params.q].flat()[0]?.trim().slice(0, 50);
  return {
    ids: ids.slice(0, MAX_PLAYERS),
    season: season && isSeason(season) ? season : undefined,
    peers: peers === "position" ? "POSITION" : "ALL",
    q: q || undefined,
    show: [params.show].flat()[0] === "1",
  };
}

/**
 * The /compare URL for a state. Built by hand rather than with URLSearchParams so the ids keep their
 * readable commas and `season` can be the `{season}` placeholder the season picker fills in.
 */
export function compareHref(state: CompareState): string {
  const parts: string[] = [];
  if (state.ids.length) parts.push(`ids=${state.ids.join(",")}`);
  if (state.season) parts.push(`season=${state.season}`);
  if (state.peers === "POSITION") parts.push("peers=position");
  if (state.q) parts.push(`q=${encodeURIComponent(state.q)}`);
  if (state.show) parts.push("show=1");
  return parts.length ? `/compare?${parts.join("&")}` : "/compare";
}

/**
 * The new player may not have played the chosen season, so the season goes back to the default.
 * A changed lineup hides the comparison until Compare is pressed again.
 */
export function withPlayer(state: CompareState, id: number): CompareState {
  if (state.ids.includes(id) || state.ids.length >= MAX_PLAYERS) return { ...state, q: undefined };
  return { ...state, ids: [...state.ids, id], season: undefined, q: undefined, show: false };
}

/** Everyone left played the chosen season, so it stays; the comparison is hidden, as when adding. */
export function withoutPlayer(state: CompareState, id: number): CompareState {
  return { ...state, ids: state.ids.filter((other) => other !== id), show: false };
}

/** Seasons every one of these players played, oldest first. */
export function sharedSeasons(players: { seasons: Pick<PlayerSeason, "season">[] }[]): string[] {
  if (players.length === 0) return [];
  const [first, ...rest] = players.map((p) => new Set(p.seasons.map((s) => s.season)));
  return [...first].filter((season) => rest.every((seasons) => seasons.has(season))).sort();
}

/** Every metric the API compares, grouped the way a scout would read them. */
export const METRIC_GROUPS: { title: string; note: string; keys: MetricKey[] }[] = [
  {
    title: "Scoring",
    note: "How much a player scores, how efficiently, and how much of the offence runs through them.",
    keys: ["pts_pg", "ts_pct", "efg_pct", "fg_pct", "fg3_pct", "ft_pct", "usg_pct"],
  },
  {
    title: "Playmaking",
    note: "Creating for teammates, and looking after the ball.",
    keys: ["ast_pg", "ast_pct", "ast_to", "tov_pg"],
  },
  {
    title: "Rebounding and defence",
    note: "Rebound rates are the share of available rebounds a player grabbed while on the floor.",
    keys: ["reb_pg", "reb_pct", "oreb_pct", "dreb_pct", "stl_pg", "blk_pg", "def_rating"],
  },
  {
    title: "Overall impact",
    note: "Ratings are points scored or allowed per 100 possessions with the player on the floor.",
    keys: ["min_pg", "pie", "off_rating", "net_rating"],
  },
];

/** A metric value as the table shows it. */
export function formatMetric(metric: Pick<MetricInfo, "format">, value: number): string {
  switch (metric.format) {
    case "percent":
      return percent(value);
    case "ratio":
      return value.toFixed(2);
    default:
      return stat(value);
  }
}

/** The value at the precision it is shown, so two values that look the same count as a tie. */
function shown(metric: Pick<MetricInfo, "format">, value: number): number {
  return Number.parseFloat(formatMetric(metric, value));
}

/**
 * For each metric, the ids of the players with the best value as displayed (several when tied). A
 * metric where everyone is level has no leader.
 */
export function metricLeaders(comparison: Pick<PlayerComparison, "metrics" | "players">): Map<MetricKey, number[]> {
  const leaders = new Map<MetricKey, number[]>();
  for (const metric of comparison.metrics) {
    const values = comparison.players.map((p) => shown(metric, p.stats[metric.key]));
    const best = metric.higher_is_better ? Math.max(...values) : Math.min(...values);
    const ids = comparison.players.filter((_, i) => values[i] === best).map((p) => p.player.id);
    leaders.set(metric.key, ids.length < comparison.players.length ? ids : []);
  }
  return leaders;
}

/** How many metrics each player leads (ties count for everyone tied). */
export function leadCounts(leaders: Map<MetricKey, number[]>): Map<number, number> {
  const counts = new Map<number, number>();
  for (const ids of leaders.values()) {
    for (const id of ids) counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  return counts;
}

/** One colour per lineup slot, from the chart palette (defined for both themes). */
export const PLAYER_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)"] as const;
