/** The /players URL <-> API query mapping. Invalid values are dropped rather than sent to the API. */
import type { PlayerQuery, PositionGroup } from "@/lib/api/client";
import { isSeason } from "@/lib/format";

export const PAGE_SIZE = 25;

export const POSITIONS: { value: PositionGroup; label: string }[] = [
  { value: "G", label: "Guards" },
  { value: "F", label: "Forwards" },
  { value: "C", label: "Centers" },
];

export type PlayerFilters = {
  q?: string;
  position?: PositionGroup;
  team?: string;
  season?: string;
  /** 1-based */
  page: number;
};

type SearchParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string | undefined {
  const single = Array.isArray(value) ? value[0] : value;
  const trimmed = single?.trim();
  return trimmed ? trimmed : undefined;
}

export function parsePlayerFilters(params: SearchParams): PlayerFilters {
  const q = first(params.q)?.slice(0, 50);
  const position = first(params.pos)?.toUpperCase();
  const team = first(params.team)?.toUpperCase();
  const season = first(params.season);
  const page = Number(first(params.page) ?? 1);
  return {
    q,
    position: POSITIONS.some((p) => p.value === position) ? (position as PositionGroup) : undefined,
    team: team && /^[A-Z]{2,3}$/.test(team) ? team : undefined,
    season: season && isSeason(season) ? season : undefined,
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  };
}

export function toPlayerQuery(filters: PlayerFilters): PlayerQuery {
  return {
    q: filters.q,
    position_group: filters.position,
    team: filters.team,
    season: filters.season,
    limit: PAGE_SIZE,
    offset: (filters.page - 1) * PAGE_SIZE,
  };
}

/** The /players URL for these filters; page 1 and empty filters are left out. */
export function playersHref(filters: PlayerFilters): string {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.position) params.set("pos", filters.position);
  if (filters.team) params.set("team", filters.team);
  if (filters.season) params.set("season", filters.season);
  if (filters.page > 1) params.set("page", String(filters.page));
  const query = params.toString();
  return query ? `/players?${query}` : "/players";
}

export function hasFilters(filters: PlayerFilters): boolean {
  return Boolean(filters.q || filters.position || filters.team || filters.season);
}

/** "203999" -> 203999; anything that isn't a positive whole number -> null */
export function parsePlayerId(value: string): number | null {
  if (!/^\d{1,10}$/.test(value)) return null;
  const id = Number(value);
  return id >= 1 && id <= 2 ** 31 - 1 ? id : null;
}
