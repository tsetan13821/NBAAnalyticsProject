import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildCareerOption, CAREER_METRICS } from "@/components/charts/career-chart";
import { seasonHref } from "@/components/season-picker";
import { PAGE_SIZE } from "@/lib/player-search";
import { OKC, PHI, player, playerSeason, playerSummary, profile } from "@/test/fixtures";

import { draftText, PlayerHero, positionName } from "./player-hero";
import { PlayerResults } from "./player-results";
import { PlayerSearchForm } from "./player-search-form";
import { careerBests, SeasonTable } from "./season-table";
import { SimilarPlayers } from "./similar-players";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

describe("positionName and draftText", () => {
  it("spells out positions", () => {
    expect(positionName("G-F", "G")).toBe("Guard-Forward");
    expect(positionName(null, "C")).toBe("Center");
  });

  it("describes the draft", () => {
    expect(draftText({ draft_year: 2014, draft_round: 2, draft_number: 41 })).toBe("2014, round 2, 41st pick");
    expect(draftText({ draft_year: null, draft_round: null, draft_number: null })).toBe("Undrafted");
  });
});

describe("PlayerHero", () => {
  it("shows the name, MVP seasons as links, and the bio", () => {
    render(<PlayerHero profile={profile()} rostersAsOf="2026-11-09" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Shai Gilgeous-Alexander");
    expect(screen.getByRole("link", { name: "2024-25" })).toHaveAttribute("href", "/mvp/2024-25");
    expect(screen.getByText("6′6″, 195 lb")).toBeInTheDocument();
    expect(screen.getByText("2018, round 1, 11th pick")).toBeInTheDocument();
  });

  it("leaves out missing facts and the MVP line", () => {
    render(<PlayerHero profile={profile({ college: null, height_in: null, mvp_seasons: [] })} rostersAsOf="2026-11-09" />);
    expect(screen.queryByText("Before the NBA")).not.toBeInTheDocument();
    expect(screen.queryByText("Size")).not.toBeInTheDocument();
    expect(screen.queryByText(/MVP/)).not.toBeInTheDocument();
  });

  it("shows today's team and when the roster was read", () => {
    render(<PlayerHero profile={profile()} rostersAsOf="2026-11-09" />);
    expect(screen.getByRole("link", { name: "Oklahoma City Thunder" })).toHaveAttribute("href", "/teams/OKC");
    expect(screen.getByText("· Roster as of 9 Nov 2026")).toBeInTheDocument();
    expect(screen.queryByText(/Now with/)).not.toBeInTheDocument();
  });

  it("explains when the player has moved since the last season of stats", () => {
    render(<PlayerHero profile={profile({ current_team: PHI })} rostersAsOf="2026-11-09" />);
    expect(screen.getByRole("link", { name: "Philadelphia 76ers" })).toHaveAttribute("href", "/teams/PHI");
    expect(screen.getByText(/Now with the Philadelphia 76ers\. The numbers on this page run to 2024-25/)).toHaveTextContent(
      "when the player was with the Oklahoma City Thunder",
    );
  });

  it("shows the last team for a player no longer on a roster", () => {
    render(<PlayerHero profile={profile({ current_team: null })} rostersAsOf="2026-11-09" />);
    const line = screen.getByText((_, el) => el?.tagName === "SPAN" && el.textContent === "Last played for the Oklahoma City Thunder, 2024-25");
    expect(line).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Oklahoma City Thunder" })).toHaveAttribute("href", "/teams/OKC");
    expect(screen.queryByText(/Roster as of/)).not.toBeInTheDocument();
  });
});

describe("SeasonTable", () => {
  it("bolds each column's best season, earlier season on a tie", () => {
    const seasons = [
      playerSeason("2021-22", { pts_pg: 20, reb_pg: 8 }),
      playerSeason("2022-23", { pts_pg: 28, reb_pg: 8 }),
    ];
    expect(careerBests(seasons)).toMatchObject({ pts_pg: "2022-23", reb_pg: "2021-22" });
  });

  it("leaves the season in progress out of the career bests", () => {
    const seasons = [playerSeason("2025-26", { pts_pg: 25 }), playerSeason("2026-27", { pts_pg: 40, in_progress: true })];
    expect(careerBests(seasons).pts_pg).toBe("2025-26");
  });

  it("labels the season in progress and says how many games it covers", () => {
    const current = playerSeason("2025-26", { games: 9, in_progress: true, archetype: null, tier: null });
    render(<SeasonTable profile={profile({ seasons: [playerSeason("2024-25"), current] })} asOf="2026-11-09" />);
    const row = screen.getByRole("rowheader", { name: /2025-26/ }).closest("tr")!;
    expect(within(row).getByText("So far")).toBeInTheDocument();
    expect(within(row).getByText("After 20 games")).toBeInTheDocument();
    expect(screen.getByText(/2025-26 is under way: these numbers cover 9 games so far, as of 9 Nov 2026/)).toBeInTheDocument();
  });

  it("marks MVP seasons and ends with career averages", () => {
    render(<SeasonTable profile={profile()} />);
    const mvpRow = screen.getByRole("rowheader", { name: /2024-25/ }).closest("tr")!;
    expect(within(mvpRow).getByRole("link", { name: /MVP in 2024-25/ })).toHaveAttribute("href", "/mvp/2024-25");
    expect(within(mvpRow).getByText("32.7")).toHaveClass("font-bold");

    const careerRow = screen.getByRole("rowheader", { name: "Career" }).closest("tr")!;
    expect(within(careerRow).getByText("31.4")).toBeInTheDocument();
    expect(within(careerRow).getByText("151")).toBeInTheDocument();
  });
});

describe("SimilarPlayers", () => {
  it("describes the player's role and links each match", () => {
    render(
      <SimilarPlayers
        data={{
          season: "2024-25",
          player: player(1, "Shai Gilgeous-Alexander"),
          archetype: "Scorer",
          tier: "Elite",
          similar: [
            { rank: 1, player: player(2, "Anthony Edwards"), team_abbr: "MIN", archetype: "Scorer", tier: "Very Good", distance: 0.513, pts_pg: 27.6, reb_pg: 5.7, ast_pg: 4.5 },
          ],
        }}
      />,
    );
    expect(screen.getByText("an elite scorer")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Anthony Edwards" })).toHaveAttribute("href", "/players/2");
    expect(screen.getByText("MIN · Scorer, very good")).toBeInTheDocument();
    expect(screen.getByText("0.51")).toBeInTheDocument();
  });
});

describe("PlayerResults", () => {
  const items = [playerSummary(1, "Stephen Curry"), playerSummary(2, "Seth Curry", { latest_team: OKC })];

  it("summarises the search and links each player", () => {
    render(<PlayerResults page={{ items, total: 2, limit: PAGE_SIZE, offset: 0 }} filters={{ q: "curry", page: 1 }} />);
    expect(screen.getByText("2 players matching “curry”")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Stephen Curry" })).toHaveAttribute("href", "/players/1");
    expect(screen.queryByRole("navigation", { name: "Pages" })).not.toBeInTheDocument();
  });

  it("shows today's team, or the last team faded for players not on a roster", () => {
    const retired = playerSummary(3, "Tim Duncan", { current_team: null, last_season: "2015-16" });
    const moved = playerSummary(4, "LeBron James", { current_team: PHI });
    render(<PlayerResults page={{ items: [retired, moved], total: 2, limit: PAGE_SIZE, offset: 0 }} filters={{ page: 1 }} />);
    const [retiredRow, movedRow] = screen.getAllByRole("listitem");
    expect(within(retiredRow).getByTitle("Last: Oklahoma City Thunder, 2015-16")).toBeInTheDocument();
    expect(within(movedRow).getAllByTitle("Philadelphia 76ers").length).toBeGreaterThan(0);
    expect(within(movedRow).queryByText(/Last:/)).not.toBeInTheDocument();
  });

  it("links to the neighbouring pages and keeps the filters", () => {
    render(
      <PlayerResults page={{ items, total: 60, limit: PAGE_SIZE, offset: PAGE_SIZE }} filters={{ team: "GSW", page: 2 }} />,
    );
    const pages = screen.getByRole("navigation", { name: "Pages" });
    expect(within(pages).getByText("Page 2 of 3")).toBeInTheDocument();
    expect(within(pages).getByRole("link", { name: "← Previous" })).toHaveAttribute("href", "/players?team=GSW");
    expect(within(pages).getByRole("link", { name: "Next →" })).toHaveAttribute("href", "/players?team=GSW&page=3");
  });

  it("says so when nothing matches", () => {
    render(<PlayerResults page={{ items: [], total: 0, limit: PAGE_SIZE, offset: 0 }} filters={{ q: "zzz", page: 1 }} />);
    expect(screen.getByText("No players found")).toBeInTheDocument();
  });

  it("offers the first page when the page is out of range", () => {
    render(<PlayerResults page={{ items: [], total: 3, limit: PAGE_SIZE, offset: 250 }} filters={{ page: 11 }} />);
    expect(screen.getByRole("link", { name: "Back to the first page" })).toHaveAttribute("href", "/players");
  });
});

describe("PlayerSearchForm", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    router.push.mockClear();
    router.replace.mockClear();
  });
  afterEach(() => vi.useRealTimers());

  const renderForm = () =>
    render(<PlayerSearchForm filters={{ page: 3 }} teams={[{ abbr: "GSW", name: "Golden State Warriors" }]} seasons={["2024-25"]} />);

  it("searches after a pause in typing, replacing the history entry", () => {
    renderForm();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "cur" } });
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "curry" } });
    expect(router.replace).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(300));
    expect(router.replace).toHaveBeenCalledExactlyOnceWith("/players?q=curry", { scroll: false });
  });

  it("marks the season in progress in the season list", () => {
    render(
      <PlayerSearchForm filters={{ page: 1 }} teams={[]} seasons={["2026-27", "2025-26"]} currentSeason="2026-27" />,
    );
    expect(screen.getByRole("option", { name: "2026-27 (in progress)" })).toHaveValue("2026-27");
    expect(screen.getByRole("option", { name: "2025-26" })).toBeInTheDocument();
  });

  it("applies a filter at once, adding a history entry and going back to page 1", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText("Played for"), { target: { value: "GSW" } });
    expect(router.push).toHaveBeenCalledExactlyOnceWith("/players?team=GSW", { scroll: false });
  });
});

describe("career chart and season picker helpers", () => {
  const palette = { brand: "orange", muted: "grey", text: "white", subtle: "silver", grid: "black", popover: "navy" };

  it("highlights MVP seasons", () => {
    const seasons = [playerSeason("2023-24", { pts_pg: 30 }), playerSeason("2024-25", { pts_pg: 32 })];
    const option = buildCareerOption(seasons, ["2024-25"], CAREER_METRICS[0], palette) as {
      xAxis: { data: string[] };
      series: { data: { value: number; itemStyle: { color: string } }[] }[];
    };
    expect(option.xAxis.data).toEqual(["’24", "’25"]);
    expect(option.series[0].data.map((d) => [d.value, d.itemStyle.color])).toEqual([
      [30, "grey"],
      [32, "orange"],
    ]);
  });

  it("draws the season in progress as an outline", () => {
    const seasons = [playerSeason("2025-26"), playerSeason("2026-27", { in_progress: true })];
    const option = buildCareerOption(seasons, [], CAREER_METRICS[0], palette) as {
      xAxis: { data: string[] };
      series: { data: { itemStyle: { color: string; borderType?: string } }[] }[];
    };
    expect(option.xAxis.data).toEqual(["’26", "’27*"]);
    expect(option.series[0].data[1].itemStyle).toMatchObject({ color: "transparent", borderType: "dashed" });
  });

  it("fills the season into a URL template", () => {
    expect(seasonHref("/mvp/{season}", "2010-11")).toBe("/mvp/2010-11");
    expect(seasonHref("/players/1?season={season}", "2010-11")).toBe("/players/1?season=2010-11");
  });
});
