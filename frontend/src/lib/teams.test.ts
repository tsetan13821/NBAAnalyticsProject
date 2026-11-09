import { describe, expect, it } from "vitest";

import type { TeamSeason, TeamSummary } from "@/lib/api/client";
import {
  bestSeason,
  gamesBehind,
  gamesBehindText,
  parseTeamAbbr,
  parseTeamQuery,
  record,
  signed,
  standings,
  teamQueryHref,
  winningStreak,
} from "@/lib/teams";

function team(abbr: string, conference: "East" | "West", rank: number, wins: number, losses: number): TeamSummary {
  return {
    abbr,
    name: abbr,
    primary_color: "#000000",
    secondary_color: "#ffffff",
    logo_url: "",
    city: abbr,
    nickname: abbr,
    conference,
    titles: 0,
    latest: {
      season: "2026-27",
      wins,
      losses,
      win_pct: wins / (wins + losses),
      conference_rank: rank,
      point_diff_pg: 0,
      in_progress: true,
    },
  };
}

function season(name: string, winPct: number, inProgress = false): TeamSeason {
  return {
    season: name,
    wins: Math.round(winPct * 82),
    losses: 82 - Math.round(winPct * 82),
    win_pct: winPct,
    conference_rank: 1,
    point_diff_pg: 0,
    in_progress: inProgress,
    team_abbr_then: "BOS",
    conference: "East",
    is_champion: false,
  };
}

describe("team query", () => {
  it("accepts abbreviations in any case", () => {
    expect(parseTeamAbbr("bos")).toBe("BOS");
    expect(parseTeamAbbr("boston")).toBeNull();
    expect(parseTeamAbbr("B0S")).toBeNull();
  });

  it("keeps a valid season and stat, and falls back to points", () => {
    expect(parseTeamQuery({ season: "2023-24", by: "assists" })).toEqual({ season: "2023-24", by: "assists" });
    expect(parseTeamQuery({ season: "2023-25", by: "steals" })).toEqual({ season: undefined, by: "points" });
    expect(parseTeamQuery({ season: ["2010-11", "2011-12"] }).season).toBe("2010-11");
  });

  it("leaves the defaults out of the URL", () => {
    expect(teamQueryHref("BOS", { by: "points" })).toBe("/teams/BOS");
    expect(teamQueryHref("BOS", { season: "2023-24", by: "games" }, "leaders")).toBe(
      "/teams/BOS?season=2023-24&by=games#leaders",
    );
  });
});

describe("numbers", () => {
  it("formats records and signed differentials", () => {
    expect(record(8, 2)).toBe("8–2");
    expect(signed(6)).toBe("+6.0");
    expect(signed(-2.25)).toBe("−2.3");
    expect(signed(-0.01)).toBe("0.0");
  });

  it("measures games behind the leader", () => {
    const leader = team("BOS", "East", 1, 8, 2);
    expect(gamesBehind(leader, team("NYK", "East", 2, 7, 4))).toBe(1.5);
    expect(gamesBehindText(1.5)).toBe("1.5");
    expect(gamesBehindText(2)).toBe("2");
    expect(gamesBehindText(0)).toBe("—");
  });
});

describe("standings", () => {
  it("sorts one conference by rank", () => {
    const teams = [team("NYK", "East", 2, 7, 3), team("DEN", "West", 1, 9, 1), team("BOS", "East", 1, 8, 2)];
    expect(standings(teams, "East").map((t) => t.abbr)).toEqual(["BOS", "NYK"]);
  });
});

describe("franchise history", () => {
  it("ignores the season in progress for bests and streaks", () => {
    const seasons = [season("2022-23", 0.7), season("2023-24", 0.6), season("2024-25", 0.55), season("2025-26", 0.9, true)];
    expect(bestSeason(seasons)?.season).toBe("2022-23");
    expect(winningStreak(seasons)).toBe(3);
    expect(winningStreak([...seasons.slice(0, 2), season("2024-25", 0.5)])).toBe(0);
    expect(bestSeason([season("2025-26", 0.9, true)])).toBeUndefined();
  });
});
