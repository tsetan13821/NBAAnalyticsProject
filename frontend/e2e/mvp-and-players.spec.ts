import { expect, test } from "@playwright/test";

test("a finished season's MVP race shows the real winner", async ({ page }) => {
  await page.goto("/mvp/2015-16");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("2015-16 MVP Race");
  await expect(page.getByText("Stephen Curry").first()).toBeVisible();
});

test("the season picker steps between MVP races", async ({ page }) => {
  await page.goto("/mvp/2015-16");
  await page.getByRole("link", { name: "Previous season: 2014-15" }).click();
  await expect(page).toHaveURL(/\/mvp\/2014-15$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("2014-15 MVP Race");
});

test("searching ignores accents and opens a profile", async ({ page }) => {
  await page.goto("/players");
  await page.getByPlaceholder("Search by name…").fill("jokic");
  await expect(page).toHaveURL(/q=jokic/);
  await page.getByRole("link", { name: /Nikola Jokić/ }).first().click();

  await expect(page).toHaveURL(/\/players\/203999/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Nikola Jokić");
  await expect(page.getByRole("heading", { name: "Season by season" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Most similar players" })).toBeVisible();
});

test("the career chart switches stats", async ({ page }) => {
  await page.goto("/players/203999");
  const stats = page.getByRole("group", { name: "Stat shown in the chart" });
  await expect(stats.getByRole("button", { name: "Points" })).toHaveAttribute("aria-pressed", "true");
  await stats.getByRole("button", { name: "Assists" }).click();
  await expect(stats.getByRole("button", { name: "Assists" })).toHaveAttribute("aria-pressed", "true");
  await expect(stats.getByRole("button", { name: "Points" })).toHaveAttribute("aria-pressed", "false");
});

test("a shared comparison link opens on the comparison", async ({ page }) => {
  await page.goto("/compare?ids=203999,201939&season=2015-16&show=1");
  await expect(page).toHaveTitle(/Nikola Jokić vs Stephen Curry/);
  const scoring = page.getByRole("table").first();
  await expect(scoring.getByRole("columnheader")).toContainText(["Stat", "N. Jokić", "S. Curry"]);
  // Curry's unanimous MVP season: 30.1 points a game, the best of the two
  await expect(scoring.getByRole("row", { name: /^Points/ })).toContainText("30.1 (best)");
});
