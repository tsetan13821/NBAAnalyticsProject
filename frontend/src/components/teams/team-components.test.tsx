import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { FranchiseLeaders, TeamDetail, TeamSeason, TeamSummary } from "@/lib/api/client";
import { OKC, player } from "@/test/fixtures";

import { buildHistoryOption, HISTORY_METRICS } from "./history-chart";
import { FranchiseSeasons, LeadersTable, LeaderStatLinks, StandingsTable } from "./team-parts";

function summary(abbr: string, rank: number, wins: number, losses: number, titles = 0): TeamSummary {
  return {
    ...OKC,
    abbr,
    name: `${abbr} team`,
    city: abbr,
    nickname: abbr,
    conference: "West",
    titles,
    latest: { season: "2026-27", wins, losses, win_pct: wins / (wins + losses), conference_rank: rank, point_diff_pg: 2.5, in_progress: true },
  };
}

function season(name: string, winPct: number, extra: Partial<TeamSeason> = {}): TeamSeason {
  return {
    season: name,
    wins: Math.round(winPct * 82),
    losses: 82 - Math.round(winPct * 82),
    win_pct: winPct,
    conference_rank: 3,
    point_diff_pg: 1,
    in_progress: false,
    team_abbr_then: "OKC",
    conference: "West",
    is_champion: false,
    ...extra,
  };
}

const TEAM: TeamDetail = {
  ...summary("OKC", 1, 8, 2, 1),
  name: "Oklahoma City Thunder",
  first_season: "2007-08",
  championships: ["2024-25"],
  total_wins: 0,
  total_losses: 0,
  seasons: [
    season("2007-08", 0.24, { team_abbr_then: "SEA" }),
    season("2024-25", 0.83, { is_champion: true }),
    season("2026-27", 0.8, { in_progress: true }),
  ],
  mvps: [{ season: "2024-25", player: player(1628983, "Shai Gilgeous-Alexander") }],
};

describe("StandingsTable", () => {
  it("lists a conference in rank order with games behind and titles", () => {
    const teams = [summary("DEN", 2, 7, 4), summary("OKC", 1, 8, 2, 1), { ...summary("BOS", 1, 9, 1), conference: "East" as const }];
    render(<StandingsTable teams={teams} conference="West" since="2000-01" />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows.map((r) => within(r).getByRole("link").getAttribute("href"))).toEqual(["/teams/OKC", "/teams/DEN"]);
    expect(within(rows[0]).getByText("—")).toBeInTheDocument(); // the leader is 0 games behind
    expect(within(rows[1]).getByText("1.5")).toBeInTheDocument();
    expect(screen.queryByText("BOS team")).not.toBeInTheDocument();
  });
});

describe("FranchiseSeasons", () => {
  it("lists seasons newest first with titles, MVPs and the name of the time", () => {
    render(<FranchiseSeasons team={TEAM} query={{ by: "points" }} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("So far")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Champions")).toBeInTheDocument();
    expect(within(rows[1]).getByRole("link", { name: /MVP: Shai Gilgeous-Alexander/ })).toHaveAttribute("href", "/mvp/2024-25");
    expect(within(rows[2]).getByText("SEA")).toBeInTheDocument();
    expect(within(rows[2]).getByRole("link", { name: "2007-08: see the roster" })).toHaveAttribute(
      "href",
      "/teams/OKC?season=2007-08#roster",
    );
  });
});

describe("leaders", () => {
  const leaders: FranchiseLeaders = {
    team: OKC,
    by: "assists",
    since: "2000-01",
    leaders: [
      { player: player(201566, "Russell Westbrook"), seasons: 11, first_season: "2008-09", last_season: "2018-19", games: 821, points: 18859, rebounds: 5634, assists: 6356, pts_pg: 23, on_roster: false },
      { player: player(1628983, "Shai Gilgeous-Alexander"), seasons: 8, first_season: "2019-20", last_season: "2026-27", games: 500, points: 13000, rebounds: 2400, assists: 3000, pts_pg: 26, on_roster: true },
    ],
  };

  it("ranks by the chosen total and marks players still on the roster", () => {
    render(<LeadersTable leaders={leaders} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("6,356")).toHaveClass("font-bold");
    expect(within(rows[0]).queryByText("On the roster")).not.toBeInTheDocument();
    expect(within(rows[1]).getByText("On the roster")).toBeInTheDocument();
  });

  it("keeps the roster season when re-ranking", () => {
    render(<LeaderStatLinks abbr="OKC" query={{ season: "2010-11", by: "assists" }} />);
    expect(screen.getByRole("link", { name: "Assists" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("link", { name: "Points" })).toHaveAttribute("href", "/teams/OKC?season=2010-11#leaders");
  });
});

describe("buildHistoryOption", () => {
  const palette = { brand: "orange", muted: "grey", text: "white", subtle: "silver", grid: "black", popover: "navy" };

  it("colours title seasons and outlines the season in progress", () => {
    const option = buildHistoryOption(TEAM.seasons, HISTORY_METRICS[0], palette) as {
      xAxis: { data: string[] };
      series: { data: { value: number; itemStyle: { color: string } }[]; markLine: { data: { yAxis: number }[] } }[];
    };
    const bars = option.series[0].data;
    expect(option.xAxis.data).toEqual(["’08", "’25", "’27*"]);
    expect(bars.map((b) => b.itemStyle.color)).toEqual(["grey", "orange", "transparent"]);
    expect(option.series[0].markLine.data).toEqual([{ yAxis: 0.5 }]);
  });
});
