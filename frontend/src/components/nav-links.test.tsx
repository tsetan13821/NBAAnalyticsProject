import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { activeHref, NavLinks } from "./nav-links";

const pathname = vi.hoisted(() => ({ current: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

describe("activeHref", () => {
  it("matches the home page exactly", () => {
    expect(activeHref("/")).toBe("/");
  });

  it("matches a section and its sub-pages", () => {
    expect(activeHref("/mvp")).toBe("/mvp");
    expect(activeHref("/mvp/2022-23")).toBe("/mvp");
  });

  it("keeps sub-pages under their section", () => {
    expect(activeHref("/mvp/method")).toBe("/mvp");
    expect(activeHref("/players/203999")).toBe("/players");
  });

  it("does not match on a shared prefix alone", () => {
    expect(activeHref("/mvpx")).toBeUndefined();
  });
});

describe("NavLinks", () => {
  it("marks the current section", () => {
    pathname.current = "/mvp/2015-16";
    render(<NavLinks />);
    expect(screen.getByRole("link", { name: "MVP Race" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Players" })).not.toHaveAttribute("aria-current");
  });
});
