import type {
  MvpCandidate,
  MvpSeasonResult,
  PlayerProfile,
  PlayerRef,
  PlayerSeason,
  PlayerSummary,
  TeamRef,
} from "@/lib/api/client";

export function player(id: number, name: string): PlayerRef {
  return { id, name, position_group: "G", headshot_url: `https://cdn.nba.com/headshots/nba/latest/1040x760/${id}.png` };
}

export const OKC: TeamRef = {
  abbr: "OKC",
  name: "Oklahoma City Thunder",
  primary_color: "#007AC1",
  secondary_color: "#EF3B24",
  logo_url: "https://cdn.nba.com/logos/nba/1610612760/global/L/logo.svg",
};

export const PHI: TeamRef = {
  abbr: "PHI",
  name: "Philadelphia 76ers",
  primary_color: "#006BB6",
  secondary_color: "#ED174C",
  logo_url: "https://cdn.nba.com/logos/nba/1610612755/global/L/logo.svg",
};

export function candidate(rank: number, name: string, overrides: Partial<MvpCandidate> = {}): MvpCandidate {
  return {
    rank,
    player: player(1000 + rank, name),
    team: OKC,
    model_score: 1 / rank,
    score_share: 0.5 / rank,
    is_mvp: false,
    stats: { games: 75, pts_pg: 30.1, reb_pg: 5.5, ast_pg: 6.2, ts_pct: 0.62, pie: 0.2 },
    team_win_pct: 0.78,
    team_conference_rank: 1,
    ...overrides,
  };
}

export function seasonResult(overrides: Partial<MvpSeasonResult> = {}): MvpSeasonResult {
  return {
    season: "2024-25",
    era: 2,
    predicted: player(1, "Shai Gilgeous-Alexander"),
    actual: player(1, "Shai Gilgeous-Alexander"),
    actual_rank: 1,
    correct: true,
    candidates: 12,
    ...overrides,
  };
}

export function playerSeason(season: string, overrides: Partial<PlayerSeason> = {}): PlayerSeason {
  return {
    season,
    team_abbr: "OKC",
    team_abbr_then: "OKC",
    archetype: "Scorer",
    tier: "Elite",
    in_progress: false,
    games: 75,
    min_pg: 34,
    pts_pg: 25,
    reb_pg: 5,
    ast_pg: 6,
    stl_pg: 1.5,
    blk_pg: 0.8,
    tov_pg: 2.5,
    fg_pct: 0.5,
    fg3_pct: 0.36,
    ft_pct: 0.88,
    ts_pct: 0.6,
    efg_pct: 0.54,
    usg_pct: 0.3,
    pie: 0.17,
    off_rating: 118,
    def_rating: 110,
    net_rating: 8,
    ast_to: 2.4,
    oreb_pct: 0.02,
    dreb_pct: 0.12,
    ast_pct: 0.3,
    reb_pct: 0.07,
    ...overrides,
  };
}

export function playerSummary(id: number, name: string, overrides: Partial<PlayerSummary> = {}): PlayerSummary {
  return {
    ...player(id, name),
    position: "G",
    first_season: "2018-19",
    last_season: "2025-26",
    latest_team: OKC,
    current_team: OKC,
    ...overrides,
  };
}

export function profile(overrides: Partial<PlayerProfile> = {}): PlayerProfile {
  return {
    ...playerSummary(1628983, "Shai Gilgeous-Alexander", { first_season: "2023-24", last_season: "2024-25" }),
    height_in: 78,
    weight_lb: 195,
    country: "Canada",
    college: "Kentucky",
    draft_year: 2018,
    draft_round: 1,
    draft_number: 11,
    seasons_played: 2,
    mvp_seasons: ["2024-25"],
    career: { games: 151, min_pg: 34, pts_pg: 31.4, reb_pg: 5.5, ast_pg: 6.2, stl_pg: 1.8, blk_pg: 0.9 },
    seasons: [
      playerSeason("2023-24", { pts_pg: 30.1, reb_pg: 5.5, ts_pct: 0.636 }),
      playerSeason("2024-25", { pts_pg: 32.7, reb_pg: 5.0, ts_pct: 0.637 }),
    ],
    ...overrides,
  };
}
