import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests: a real browser against the running site, with its API and database.
 *
 *   docker compose up --build        # from the repository root, then, from frontend/:
 *   npx playwright install chromium  # once
 *   npm run test:e2e
 *
 * BASE_URL points them at another address (default http://localhost:3000). The data changes every day
 * (games, injury reports), so the tests find games and players on the page instead of naming them,
 * except for finished seasons, which never change.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, testIgnore: /mobile\.spec/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /mobile\.spec/ },
  ],
});
