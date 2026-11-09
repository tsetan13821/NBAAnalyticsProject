import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { isActive, NavLinks } from "./nav-links";

const pathname = vi.hoisted(() => ({ current: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

describe("isActive", () => {
  it("matches the home page exactly", () => {
    expect(isActive("/", "/")).toBe(true);
    expect(isActive("/mvp", "/")).toBe(false);
  });

  it("matches a section and its sub-pages", () => {
    expect(isActive("/mvp", "/mvp")).toBe(true);
    expect(isActive("/mvp/2022-23", "/mvp")).toBe(true);
    expect(isActive("/mvpx", "/mvp")).toBe(false);
  });
});

describe("NavLinks", () => {
  it("marks the current section", () => {
    pathname.current = "/mvp/2015-16";
    render(<NavLinks />);
    expect(screen.getByRole("link", { name: "MVP Race" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current");
  });
});
