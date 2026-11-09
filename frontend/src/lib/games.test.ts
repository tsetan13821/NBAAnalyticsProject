import { describe, expect, it } from "vitest";

import {
  byDate,
  chances,
  choiceOf,
  easternStamp,
  gameHref,
  hasWhatIf,
  marginText,
  parseWhatIf,
  signedPoints,
  tipTime,
  withChoice,
} from "./games";

describe("what-if URL state", () => {
  it("parses commas and repeated parameters, dropping junk", () => {
    expect(parseWhatIf({ out: "1,2,x", in: ["3", "4"] })).toEqual({ out: [1, 2], in: [3, 4] });
    expect(parseWhatIf({})).toEqual({ out: [], in: [] });
  });

  it("never has a player both out and in", () => {
    expect(parseWhatIf({ out: "5", in: "5,6" })).toEqual({ out: [5], in: [6] });
  });

  it("round-trips through the URL", () => {
    const state = { out: [201939, 2544], in: [1629029] };
    expect(gameHref("0022600150", state)).toBe("/games/0022600150?out=201939,2544&in=1629029");
    expect(parseWhatIf({ out: "201939,2544", in: "1629029" })).toEqual(state);
    expect(gameHref("0022600150")).toBe("/games/0022600150");
  });

  it("sets, switches and clears one player's choice", () => {
    let state = withChoice({ out: [], in: [] }, 7, "out");
    expect(choiceOf(state, 7)).toBe("out");
    state = withChoice(state, 7, "in");
    expect(state).toEqual({ out: [], in: [7] });
    state = withChoice(state, 7, null);
    expect(hasWhatIf(state)).toBe(false);
    expect(choiceOf(state, 7)).toBeNull();
  });
});

describe("prediction wording", () => {
  it("names the favourite and the margin", () => {
    expect(marginText(4.46, "BOS", "LAL")).toBe("BOS by 4.5");
    expect(marginText(-7.04, "BOS", "LAL")).toBe("LAL by 7.0");
    expect(marginText(0.3, "BOS", "LAL")).toBe("Toss-up");
  });

  it("splits the chance into whole percentages that add up to 100", () => {
    expect(chances(0.734)).toEqual({ home: 73, away: 27 });
    expect(chances(0.505)).toEqual({ home: 51, away: 49 });
    expect(chances(0.999)).toEqual({ home: 99, away: 1 });
  });

  it("formats times and points", () => {
    expect(tipTime("19:30")).toBe("7:30 PM ET");
    expect(tipTime("12:00")).toBe("12:00 PM ET");
    expect(tipTime(null)).toBeUndefined();
    expect(easternStamp("2026-11-09T03:45-05:00")).toBe("9 Nov, 3:45 AM ET");
    expect(signedPoints(2.345)).toBe("+2.3");
    expect(signedPoints(-1.96)).toBe("−2.0");
    expect(signedPoints(-0.04)).toBe("0.0");
  });

  it("groups games by date in order", () => {
    const games = [{ date: "2026-11-09", id: 1 }, { date: "2026-11-09", id: 2 }, { date: "2026-11-10", id: 3 }];
    expect(byDate(games).map(([day, g]) => [day, g.map((x) => x.id)])).toEqual([
      ["2026-11-09", [1, 2]],
      ["2026-11-10", [3]],
    ]);
  });
});
