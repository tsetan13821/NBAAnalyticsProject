import type { MvpCandidate, MvpSeasonResult, PlayerRef, TeamRef } from "@/lib/api/client";

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
