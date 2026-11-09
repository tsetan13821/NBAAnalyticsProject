import { describe, expect, it } from "vitest";

import { luminance, readableText } from "./color";

describe("luminance", () => {
  it("spans black to white", () => {
    expect(luminance("#000000")).toBe(0);
    expect(luminance("#ffffff")).toBeCloseTo(1);
    expect(luminance("FFFFFF")).toBeCloseTo(1);
  });

  it("rejects other formats", () => {
    expect(() => luminance("red")).toThrow();
    expect(() => luminance("#fff")).toThrow();
  });
});

describe("readableText", () => {
  it.each([
    ["#007A33", "#ffffff"], // Celtics green
    ["#552583", "#ffffff"], // Lakers purple
    ["#FFC72C", "#000000"], // Warriors gold
    ["#000000", "#ffffff"], // Nets black
    ["#C4CED4", "#000000"], // Spurs silver
  ])("on %s uses %s", (background, expected) => {
    expect(readableText(background)).toBe(expected);
  });
});
