/** Game predictor helpers: the what-if URL state and how a prediction is put into words. */
import { parsePlayerId } from "@/lib/player-search";

/** Players forced out of, or into, the game. A player is never in both. */
export type WhatIfState = { out: number[]; in: number[] };

export type WhatIfChoice = "out" | "in" | null;

type SearchParams = Record<string, string | string[] | undefined>;

function ids(value: string | string[] | undefined): number[] {
  const raw = [value ?? []].flat().flatMap((v) => v.split(","));
  return [...new Set(raw.map((v) => parsePlayerId(v.trim())).filter((id) => id !== null))];
}

/** Accepts "?out=1,2&in=3" and repeated parameters; a player listed both ways counts as out. */
export function parseWhatIf(params: SearchParams): WhatIfState {
  const out = ids(params.out);
  return { out, in: ids(params.in).filter((id) => !out.includes(id)) };
}

export function hasWhatIf(state: WhatIfState): boolean {
  return state.out.length > 0 || state.in.length > 0;
}

/** The game page URL for a what-if state, with readable commas. */
export function gameHref(gameId: string, state: WhatIfState = { out: [], in: [] }): string {
  const parts: string[] = [];
  if (state.out.length) parts.push(`out=${state.out.join(",")}`);
  if (state.in.length) parts.push(`in=${state.in.join(",")}`);
  return parts.length ? `/games/${gameId}?${parts.join("&")}` : `/games/${gameId}`;
}

/** Set one player's what-if (null puts him back to his injury-report status). */
export function withChoice(state: WhatIfState, playerId: number, choice: WhatIfChoice): WhatIfState {
  const out = state.out.filter((id) => id !== playerId);
  const into = state.in.filter((id) => id !== playerId);
  if (choice === "out") out.push(playerId);
  if (choice === "in") into.push(playerId);
  return { out, in: into };
}

export function choiceOf(state: WhatIfState, playerId: number): WhatIfChoice {
  if (state.out.includes(playerId)) return "out";
  if (state.in.includes(playerId)) return "in";
  return null;
}

/** 4.46, "BOS", "LAL" -> "BOS by 4.5"; under half a point -> "Toss-up" */
export function marginText(homeMargin: number, home: string, away: string): string {
  if (Math.abs(homeMargin) < 0.5) return "Toss-up";
  return `${homeMargin > 0 ? home : away} by ${Math.abs(homeMargin).toFixed(1)}`;
}

/** 0.734 -> { home: 73, away: 27 }: whole percentages that always add up to 100 */
export function chances(homeProbability: number): { home: number; away: number } {
  const home = Math.min(99, Math.max(1, Math.round(homeProbability * 100)));
  return { home, away: 100 - home };
}

/** "19:30" -> "7:30 PM ET" */
export function tipTime(tip: string | null | undefined): string | undefined {
  if (!tip) return undefined;
  const [h, m] = tip.split(":").map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"} ET`;
}

/** "2026-11-09" -> "Monday 9 November" */
export function longDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }).format(
    new Date(`${isoDate}T00:00:00Z`),
  );
}

/** "2026-11-09T03:45-05:00" -> "9 Nov, 3:45 AM ET" (the clock time as published, Eastern) */
export function easternStamp(iso: string | null | undefined): string | undefined {
  if (!iso) return undefined;
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (!match) return undefined;
  const day = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(
    new Date(`${match[1]}T00:00:00Z`),
  );
  return `${day}, ${tipTime(`${match[2]}:${match[3]}`)}`;
}

/** Signed points: 2.345 -> "+2.3", -0.04 -> "0.0" */
export function signedPoints(points: number): string {
  const rounded = Math.round(points * 10) / 10;
  if (rounded === 0) return "0.0";
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toFixed(1)}`;
}

/** Group games by date, keeping their order. */
export function byDate<T extends { date: string }>(games: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>();
  for (const game of games) groups.set(game.date, [...(groups.get(game.date) ?? []), game]);
  return [...groups];
}
