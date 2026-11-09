import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { PlayerComparison } from "@/lib/api/client";
import { metricLeaders, PLAYER_COLORS } from "@/lib/compare";
import { OKC, player } from "@/test/fixtures";

import { AddPlayerForm, CandidateList } from "./add-player";
import { AddPlayerSlots } from "./add-player-slots";
import { CompareBar } from "./compare-bar";
import { ComparisonTable, PeerToggle, peerDescription } from "./comparison-table";
import { Lineup } from "./lineup";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

function comparison(overrides: Partial<PlayerComparison> = {}): PlayerComparison {
  const metrics: PlayerComparison["metrics"] = [
    { key: "pts_pg", label: "Points", format: "per_game", higher_is_better: true },
    { key: "ts_pct", label: "True Shooting %", format: "percent", higher_is_better: true },
    { key: "tov_pg", label: "Turnovers", format: "per_game", higher_is_better: false },
  ];
  return {
    season: "2025-26",
    peer_group: "ALL",
    metrics,
    players: [
      {
        player: player(1628983, "Shai Gilgeous-Alexander"),
        team_abbr: "OKC",
        peer_group: "ALL",
        stats: { pts_pg: 31.1, ts_pct: 0.665, tov_pg: 2.2 },
        percentiles: { pts_pg: 99.6, ts_pct: 94, tov_pg: 13 },
      },
      {
        player: { ...player(203999, "Nikola Jokić"), position_group: "C" },
        team_abbr: "DEN",
        peer_group: "ALL",
        stats: { pts_pg: 27.7, ts_pct: 0.67, tov_pg: 3.7 },
        percentiles: { pts_pg: 99, ts_pct: 95, tov_pg: 1 },
      },
    ],
    ...overrides,
  };
}

describe("ComparisonTable", () => {
  it("shows each value and percentile, with the leader marked", () => {
    const data = comparison();
    render(<ComparisonTable comparison={data} colors={PLAYER_COLORS} leaders={metricLeaders(data)} />);

    const points = screen.getByRole("row", { name: /Points/ });
    expect(within(points).getByText("31.1")).toHaveClass("font-bold");
    expect(within(points).getByText("27.7")).not.toHaveClass("font-bold");
    expect(within(points).getByText("100th percentile")).toBeInTheDocument();

    const shooting = screen.getByRole("row", { name: /True Shooting/ });
    expect(within(shooting).getByText("67.0%")).toHaveClass("font-bold");

    const turnovers = screen.getByRole("row", { name: /Turnovers/ });
    expect(within(turnovers).getByText("Lower is better")).toBeInTheDocument();
    expect(within(turnovers).getByText("2.2")).toHaveClass("font-bold");
  });

  it("leaves out groups' metrics the API didn't send, and names the columns", () => {
    const data = comparison();
    render(<ComparisonTable comparison={data} colors={PLAYER_COLORS} leaders={metricLeaders(data)} />);
    expect(screen.queryByRole("row", { name: /Rebounds/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("columnheader", { name: /Jokić/ }).length).toBeGreaterThan(0);
  });
});

describe("peerDescription", () => {
  it("names the group the percentiles compare against", () => {
    expect(peerDescription(comparison())).toBe("every player");
    const byPosition = comparison({ peer_group: "POSITION" });
    byPosition.players = byPosition.players.map((p) => ({ ...p, peer_group: "G" }));
    expect(peerDescription(byPosition)).toBe("other guards");
    byPosition.players[1] = { ...byPosition.players[1], peer_group: "C" };
    expect(peerDescription(byPosition)).toBe("players at the same position (guards, centers)");
  });
});

describe("PeerToggle", () => {
  it("links to both peer groups and marks the current one", () => {
    render(<PeerToggle state={{ ids: [1, 2], season: "2025-26", peers: "ALL", q: "x" }} />);
    expect(screen.getByRole("link", { name: "All players" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("link", { name: "Same position" })).toHaveAttribute(
      "href",
      "/compare?ids=1,2&season=2025-26&peers=position",
    );
  });
});

describe("Lineup", () => {
  it("shows each player with a remove link, the season's team and the lead count", () => {
    render(
      <Lineup
        metricCount={22}
        entries={[
          {
            player: { ...player(1628983, "Shai Gilgeous-Alexander"), position: "G" },
            color: PLAYER_COLORS[0],
            removeHref: "/compare?ids=203999",
            team: OKC,
            games: 68,
            leads: 6,
          },
        ]}
      />,
    );
    expect(screen.getByRole("link", { name: "Remove Shai Gilgeous-Alexander" })).toHaveAttribute(
      "href",
      "/compare?ids=203999",
    );
    expect(screen.getByRole("link", { name: "Shai Gilgeous-Alexander" })).toHaveAttribute("href", "/players/1628983");
    expect(screen.getByText("68 games")).toBeInTheDocument();
    expect(screen.getByText("of 22 categories led")).toBeInTheDocument();
  });

  it("leaves the season details out before there is a comparison", () => {
    render(
      <Lineup
        entries={[
          {
            player: { ...player(1, "Solo Player"), position: null },
            color: PLAYER_COLORS[0],
            removeHref: "/compare",
          },
        ]}
      />,
    );
    expect(screen.queryByText(/games/)).not.toBeInTheDocument();
    expect(screen.queryByText(/categories led/)).not.toBeInTheDocument();
  });
});

describe("CandidateList", () => {
  it("links each candidate to the lineup with them added", () => {
    render(
      <CandidateList
        title="Closest in style"
        candidates={[{ player: player(2, "Second Player"), detail: "G · 2020-21 to 2025-26", href: "/compare?ids=1,2" }]}
      />,
    );
    expect(screen.getByRole("link", { name: "Add Second Player" })).toHaveAttribute("href", "/compare?ids=1,2");
  });
});

describe("AddPlayerForm", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    router.push.mockClear();
    router.replace.mockClear();
  });
  afterEach(() => vi.useRealTimers());

  const state = { ids: [1628983], season: "2025-26", peers: "POSITION" as const };

  it("keeps the lineup in hidden fields so it works without JavaScript", () => {
    const { container } = render(<AddPlayerForm state={state} />);
    const hidden = Object.fromEntries(
      [...container.querySelectorAll<HTMLInputElement>("input[type=hidden]")].map((i) => [i.name, i.value]),
    );
    expect(hidden).toEqual({ ids: "1628983", season: "2025-26", peers: "position" });
  });

  it("searches after a pause in typing, replacing the history entry", () => {
    render(<AddPlayerForm state={state} />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "jok" } });
    expect(router.replace).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(300));
    expect(router.replace).toHaveBeenCalledWith("/compare?ids=1628983&season=2025-26&peers=position&q=jok", {
      scroll: false,
    });
  });

  it("searches at once on submit, adding a history entry", () => {
    render(<AddPlayerForm state={state} />);
    const box = screen.getByRole("searchbox");
    fireEvent.change(box, { target: { value: "luka" } });
    fireEvent.submit(box.closest("form")!);
    expect(router.push).toHaveBeenCalledWith("/compare?ids=1628983&season=2025-26&peers=position&q=luka", {
      scroll: false,
    });
    act(() => vi.advanceTimersByTime(300));
    expect(router.replace).not.toHaveBeenCalled();
  });
});

describe("AddPlayerSlots", () => {
  beforeEach(() => router.replace.mockClear());

  function renderSlots(state: Parameters<typeof AddPlayerSlots>[0]["state"]) {
    return render(
      <ol>
        <AddPlayerSlots state={state}>
          <a href="/compare?ids=1,2">Add Second Player</a>
        </AddPlayerSlots>
      </ol>,
    );
  }

  it("shows a button for each open slot", () => {
    renderSlots({ ids: [1], peers: "ALL" });
    expect(screen.getAllByRole("button", { name: "Add player" })).toHaveLength(3);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the picker from any slot", async () => {
    renderSlots({ ids: [1], peers: "ALL" });
    fireEvent.click(screen.getAllByRole("button", { name: "Add player" })[2]);
    const dialog = await screen.findByRole("dialog", { name: "Add a player" });
    expect(within(dialog).getByText(/Player 2 of up to 4/)).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: "Add Second Player" })).toBeInTheDocument();
  });

  it("clears a search left in the URL instead of reopening it", () => {
    renderSlots({ ids: [1], peers: "ALL", q: "jok", show: true });
    expect(router.replace).toHaveBeenCalledWith("/compare?ids=1&show=1", { scroll: false });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("clears the search when dismissed", async () => {
    const { rerender } = renderSlots({ ids: [1], peers: "ALL" });
    fireEvent.click(screen.getAllByRole("button", { name: "Add player" })[0]);
    // The page re-renders with the typed search in the URL; the open picker stays open.
    rerender(
      <ol>
        <AddPlayerSlots state={{ ids: [1], peers: "ALL", q: "jok" }}>
          <a href="/compare?ids=1,2">Add Second Player</a>
        </AddPlayerSlots>
      </ol>,
    );
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(router.replace).toHaveBeenCalledWith("/compare?ids=1", { scroll: false });
  });

  it("closes without touching the URL when a player is picked", async () => {
    renderSlots({ ids: [1], peers: "ALL" });
    fireEvent.click(screen.getAllByRole("button", { name: "Add player" })[0]);
    const dialog = await screen.findByRole("dialog");
    const link = within(dialog).getByRole("link", { name: "Add Second Player" });
    link.addEventListener("click", (event) => event.preventDefault()); // jsdom can't navigate
    fireEvent.click(link);
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(router.replace).not.toHaveBeenCalled();
  });
});

describe("CompareBar", () => {
  it("links to the comparison once there are enough players", () => {
    render(
      <CompareBar count={3} href="/compare?ids=1,2,3&show=1#head-to-head">
        Add up to 1 more.
      </CompareBar>,
    );
    expect(screen.getByRole("link", { name: "Compare 3 players" })).toHaveAttribute(
      "href",
      "/compare?ids=1,2,3&show=1#head-to-head",
    );
    expect(screen.getByText("Add up to 1 more.")).toBeInTheDocument();
  });

  it("shows a disabled button before that", () => {
    render(<CompareBar count={1}>Add at least one more player.</CompareBar>);
    const button = screen.getByRole("link", { name: "Compare players" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).not.toHaveAttribute("href");
  });
});
