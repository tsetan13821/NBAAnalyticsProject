import { describe, expect, it } from "vitest";

import { hasFilters, PAGE_SIZE, parsePlayerFilters, parsePlayerId, playersHref, toPlayerQuery } from "./player-search";

describe("parsePlayerFilters", () => {
  it("reads every filter from the URL", () => {
    expect(parsePlayerFilters({ q: " jokic ", pos: "c", team: "den", season: "2023-24", page: "3" })).toEqual({
      q: "jokic",
      position: "C",
      team: "DEN",
      season: "2023-24",
      page: 3,
    });
  });

  it("defaults to no filters on page 1", () => {
    expect(parsePlayerFilters({})).toEqual({ page: 1 });
    expect(parsePlayerFilters({ q: "  ", pos: "" })).toEqual({ page: 1 });
  });

  it("drops values the API would reject", () => {
    expect(parsePlayerFilters({ pos: "X", team: "DENVER", season: "2023-25", page: "-2" })).toEqual({ page: 1 });
    expect(parsePlayerFilters({ page: "2.5" }).page).toBe(1);
    expect(parsePlayerFilters({ q: "x".repeat(80) }).q).toHaveLength(50);
  });

  it("uses the first value of a repeated parameter", () => {
    expect(parsePlayerFilters({ q: ["curry", "james"] }).q).toBe("curry");
  });
});

describe("toPlayerQuery", () => {
  it("turns the page number into an offset", () => {
    expect(toPlayerQuery({ q: "james", page: 3 })).toEqual({
      q: "james",
      position_group: undefined,
      team: undefined,
      season: undefined,
      limit: PAGE_SIZE,
      offset: 2 * PAGE_SIZE,
    });
  });
});

describe("playersHref", () => {
  it("round-trips through parsePlayerFilters", () => {
    const filters = { q: "Luka Dončić", position: "G", team: "DAL", season: "2023-24", page: 2 } as const;
    const href = playersHref(filters);
    const params = Object.fromEntries(new URL(href, "http://x").searchParams);
    expect(parsePlayerFilters(params)).toEqual(filters);
  });

  it("leaves out empty filters and page 1", () => {
    expect(playersHref({ page: 1 })).toBe("/players");
    expect(playersHref({ team: "BOS", page: 1 })).toBe("/players?team=BOS");
  });
});

describe("hasFilters", () => {
  it("ignores the page number", () => {
    expect(hasFilters({ page: 4 })).toBe(false);
    expect(hasFilters({ season: "2010-11", page: 1 })).toBe(true);
  });
});

describe("parsePlayerId", () => {
  it("accepts positive whole numbers", () => {
    expect(parsePlayerId("203999")).toBe(203999);
  });

  it.each(["abc", "0", "-5", "1.5", "1e5", "", "99999999999"])("rejects %j", (value) => {
    expect(parsePlayerId(value)).toBeNull();
  });
});
