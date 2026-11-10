import { describe, expect, it } from "vitest";

import headshotLoader from "./image-loader";

const LARGE = "https://cdn.nba.com/headshots/nba/latest/1040x760/203999.png";
const SMALL = "https://cdn.nba.com/headshots/nba/latest/260x190/203999.png";

describe("headshotLoader", () => {
  it("uses the CDN's small headshot for avatars", () => {
    expect(headshotLoader({ src: LARGE, width: 88 })).toBe(SMALL);
    expect(headshotLoader({ src: LARGE, width: 260 })).toBe(SMALL);
  });

  it("keeps the large headshot when the small one would be blurry", () => {
    expect(headshotLoader({ src: LARGE, width: 261 })).toBe(LARGE);
    expect(headshotLoader({ src: LARGE, width: 1080 })).toBe(LARGE);
  });

  it("leaves other images alone", () => {
    expect(headshotLoader({ src: "/logo.svg", width: 64 })).toBe("/logo.svg");
  });
});
