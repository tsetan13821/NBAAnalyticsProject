import { describe, expect, it } from "vitest";

import type { MetricKey, PlayerComparison } from "@/lib/api/client";
import {
  compareHref,
  formatMetric,
  leadCounts,
  METRIC_GROUPS,
  metricLeaders,
  parseCompareState,
  sharedSeasons,
  withoutPlayer,
  withPlayer,
} from "@/lib/compare";
import { player } from "@/test/fixtures";

// Every metric the API can return; the compile-time check below fails if the API gains one.
const ALL_KEYS = [
  "min_pg", "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg", "tov_pg",
  "fg_pct", "fg3_pct", "ft_pct", "ts_pct", "efg_pct", "usg_pct", "pie",
  "off_rating", "def_rating", "net_rating", "ast_to", "oreb_pct", "dreb_pct", "ast_pct", "reb_pct",
] as const satisfies readonly MetricKey[];
type Missing = Exclude<MetricKey, (typeof ALL_KEYS)[number]>;
const everyKeyListed: Missing extends never ? true : Missing = true;

describe("parseCompareState", () => {
  it("reads comma-separated and repeated ids, dropping junk and duplicates", () => {
    expect(parseCompareState({ ids: "2544,201939,x,2544" }).ids).toEqual([2544, 201939]);
    expect(parseCompareState({ ids: ["2544", "201939,203999"] }).ids).toEqual([2544, 201939, 203999]);
    expect(parseCompareState({ ids: "-1,0,1.5" }).ids).toEqual([]);
  });

  it("keeps at most four players", () => {
    expect(parseCompareState({ ids: "1,2,3,4,5" }).ids).toEqual([1, 2, 3, 4]);
  });

  it("validates the season and peer group", () => {
    expect(parseCompareState({ season: "2023-24", peers: "POSITION" })).toMatchObject({
      season: "2023-24",
      peers: "POSITION",
    });
    expect(parseCompareState({ season: "2023-25", peers: "team" })).toMatchObject({ season: undefined, peers: "ALL" });
  });

  it("trims the search text", () => {
    expect(parseCompareState({ q: "  jok " }).q).toBe("jok");
    expect(parseCompareState({ q: "   " }).q).toBeUndefined();
  });

  it("shows the comparison only when asked to", () => {
    expect(parseCompareState({ ids: "1,2" }).show).toBe(false);
    expect(parseCompareState({ ids: "1,2", show: "1" }).show).toBe(true);
    expect(parseCompareState({ ids: "1,2", show: "yes" }).show).toBe(false);
  });
});

describe("compareHref", () => {
  it("keeps the ids readable and leaves out defaults", () => {
    expect(compareHref({ ids: [], peers: "ALL" })).toBe("/compare");
    expect(compareHref({ ids: [2544, 201939], season: "2015-16", peers: "POSITION", q: "Luka D" })).toBe(
      "/compare?ids=2544,201939&season=2015-16&peers=position&q=Luka%20D",
    );
    expect(compareHref({ ids: [2544, 201939], peers: "ALL", show: true })).toBe("/compare?ids=2544,201939&show=1");
  });

  it("round-trips through parseCompareState", () => {
    const state = { ids: [1, 2, 3], season: "2010-11", peers: "POSITION" as const, q: "Tim D", show: true };
    const params = Object.fromEntries(new URL(compareHref(state), "http://x").searchParams);
    expect(parseCompareState(params)).toEqual(state);
  });

  it("can carry the season picker's placeholder", () => {
    expect(compareHref({ ids: [1, 2], season: "{season}", peers: "ALL" })).toBe("/compare?ids=1,2&season={season}");
  });
});

describe("withPlayer and withoutPlayer", () => {
  const state = { ids: [1, 2], season: "2015-16", peers: "ALL" as const, q: "ste", show: true };

  it("adds a player, resetting the season, clearing the search and hiding the comparison", () => {
    expect(withPlayer(state, 3)).toEqual({ ids: [1, 2, 3], season: undefined, peers: "ALL", q: undefined, show: false });
  });

  it("ignores a player already in, or a fifth", () => {
    expect(withPlayer(state, 2).ids).toEqual([1, 2]);
    expect(withPlayer({ ...state, ids: [1, 2, 3, 4] }, 5).ids).toEqual([1, 2, 3, 4]);
  });

  it("removes a player, keeping the season but hiding the comparison", () => {
    expect(withoutPlayer(state, 1)).toMatchObject({ ids: [2], season: "2015-16", show: false });
  });
});

describe("sharedSeasons", () => {
  const career = (...seasons: string[]) => ({ seasons: seasons.map((season) => ({ season })) });

  it("returns the seasons everyone played, oldest first", () => {
    expect(sharedSeasons([career("2003-04", "2004-05", "2005-06"), career("2005-06", "2004-05")])).toEqual([
      "2004-05",
      "2005-06",
    ]);
  });

  it("is empty for careers that never overlapped, or no players", () => {
    expect(sharedSeasons([career("2000-01"), career("2020-21")])).toEqual([]);
    expect(sharedSeasons([])).toEqual([]);
  });
});

describe("METRIC_GROUPS", () => {
  it("lists every metric exactly once", () => {
    expect(everyKeyListed).toBe(true);
    const keys = METRIC_GROUPS.flatMap((g) => g.keys);
    expect(keys.toSorted()).toEqual([...ALL_KEYS].sort());
  });
});

describe("formatMetric", () => {
  it("formats each kind of metric", () => {
    expect(formatMetric({ format: "per_game" }, 27.345)).toBe("27.3");
    expect(formatMetric({ format: "percent" }, 0.6123)).toBe("61.2%");
    expect(formatMetric({ format: "ratio" }, 2.456)).toBe("2.46");
    expect(formatMetric({ format: "rating" }, 115.27)).toBe("115.3");
  });
});

describe("metricLeaders and leadCounts", () => {
  const compared = (id: number, stats: Partial<Record<MetricKey, number>>) => ({
    player: player(id, `Player ${id}`),
    team_abbr: "OKC",
    peer_group: "ALL" as const,
    stats,
    percentiles: {},
  });
  const comparison = (players: ReturnType<typeof compared>[]): Pick<PlayerComparison, "metrics" | "players"> => ({
    metrics: [
      { key: "pts_pg", label: "Points", format: "per_game", higher_is_better: true },
      { key: "tov_pg", label: "Turnovers", format: "per_game", higher_is_better: false },
      { key: "blk_pg", label: "Blocks", format: "per_game", higher_is_better: true },
    ],
    players: players as PlayerComparison["players"],
  });

  it("picks the best value, lowest where lower is better", () => {
    const leaders = metricLeaders(
      comparison([compared(1, { pts_pg: 30, tov_pg: 3, blk_pg: 1 }), compared(2, { pts_pg: 25, tov_pg: 2, blk_pg: 0.4 })]),
    );
    expect(leaders.get("pts_pg")).toEqual([1]);
    expect(leaders.get("tov_pg")).toEqual([2]);
    expect(leadCounts(leaders)).toEqual(new Map([[1, 2], [2, 1]]));
  });

  it("treats values that display the same as a tie, and a level row as having no leader", () => {
    const leaders = metricLeaders(
      comparison([
        compared(1, { pts_pg: 30.04, tov_pg: 2, blk_pg: 0.83 }),
        compared(2, { pts_pg: 30.01, tov_pg: 2, blk_pg: 0.76 }),
        compared(3, { pts_pg: 20, tov_pg: 3, blk_pg: 0.2 }),
      ]),
    );
    expect(leaders.get("pts_pg")).toEqual([1, 2]);
    expect(leaders.get("blk_pg")).toEqual([1, 2]);
    expect(leaders.get("tov_pg")).toEqual([1, 2]);

    const level = metricLeaders(comparison([compared(1, { pts_pg: 20, tov_pg: 2, blk_pg: 1 }), compared(2, { pts_pg: 20, tov_pg: 2, blk_pg: 1 })]));
    expect(level.get("pts_pg")).toEqual([]);
  });
});
