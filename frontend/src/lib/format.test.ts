import { describe, expect, it } from "vitest";

import {
  adjacentSeasons,
  height,
  initials,
  isSeason,
  ordinal,
  percent,
  ratio,
  seasonCount,
  seasonsBetween,
  seasonSpan,
  shortDate,
  shortName,
  stat,
} from "./format";

describe("isSeason", () => {
  it.each(["2000-01", "2025-26", "1999-00"])("accepts %s", (value) => {
    expect(isSeason(value)).toBe(true);
  });

  it.each(["2023", "2023-2024", "2023-25", "abcd-ef", "2023-24 ", ""])("rejects %j", (value) => {
    expect(isSeason(value)).toBe(false);
  });
});

describe("number formatting", () => {
  it("formats fractions as percentages", () => {
    expect(percent(0.5123)).toBe("51.2%");
    expect(percent(0.731, 0)).toBe("73%");
    expect(percent(1)).toBe("100.0%");
  });

  it("formats stats and ratios", () => {
    expect(stat(27.345)).toBe("27.3");
    expect(stat(5)).toBe("5.0");
    expect(ratio(19, 26)).toBe("19/26");
  });

  it.each([
    [1, "1st"], [2, "2nd"], [3, "3rd"], [4, "4th"], [11, "11th"], [12, "12th"], [13, "13th"], [21, "21st"], [112, "112th"],
  ])("ordinal(%i) is %s", (n, expected) => {
    expect(ordinal(n)).toBe(expected);
  });
});

describe("names", () => {
  it("builds initials from the first and last name", () => {
    expect(initials("Shai Gilgeous-Alexander")).toBe("SG");
    expect(initials("Giannis Sina Ugo Antetokounmpo")).toBe("GA");
    expect(initials("Nenê")).toBe("N");
  });

  it("shortens names for chart axes", () => {
    expect(shortName("LeBron James")).toBe("L. James");
    expect(shortName("Karl-Anthony Towns")).toBe("K. Towns");
    expect(shortName("Nenê")).toBe("Nenê");
  });
});

describe("seasons", () => {
  it("counts seasons inclusively", () => {
    expect(seasonCount("2000-01", "2025-26")).toBe(26);
    expect(seasonCount("2024-25", "2024-25")).toBe(1);
  });

  it("finds neighbouring seasons", () => {
    const seasons = ["2022-23", "2023-24", "2024-25"];
    expect(adjacentSeasons(seasons, "2023-24")).toEqual({ previous: "2022-23", next: "2024-25" });
    expect(adjacentSeasons(seasons, "2022-23")).toEqual({ previous: undefined, next: "2023-24" });
    expect(adjacentSeasons(seasons, "1990-91")).toEqual({});
  });
});

describe("seasonsBetween", () => {
  it("lists every season, oldest first", () => {
    expect(seasonsBetween("2000-01", "2002-03")).toEqual(["2000-01", "2001-02", "2002-03"]);
    expect(seasonsBetween("2025-26", "2025-26")).toEqual(["2025-26"]);
  });

  it("handles the century turn", () => {
    expect(seasonsBetween("1998-99", "2000-01")).toEqual(["1998-99", "1999-00", "2000-01"]);
  });
});

describe("height and seasonSpan", () => {
  it("formats inches as feet and inches", () => {
    expect(height(83)).toBe("6′11″");
    expect(height(72)).toBe("6′0″");
  });

  it("collapses a single season", () => {
    expect(seasonSpan("2003-04", "2025-26")).toBe("2003-04 to 2025-26");
    expect(seasonSpan("2010-11", "2010-11")).toBe("2010-11");
  });
});

describe("shortDate", () => {
  it("formats an ISO date without shifting it by time zone", () => {
    expect(shortDate("2026-11-09")).toBe("9 Nov 2026");
    expect(shortDate("2027-01-01")).toBe("1 Jan 2027");
  });
});
