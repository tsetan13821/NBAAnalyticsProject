import { expect, test } from "@playwright/test";

test("the standings list all thirty teams and open a franchise", async ({ page }) => {
  await page.goto("/teams");
  const tables = page.getByRole("table");
  await expect(tables).toHaveCount(2);
  await expect(tables.locator('a[href^="/teams/"]')).toHaveCount(30);

  await tables.getByRole("link", { name: /Oklahoma City Thunder/ }).click();
  await expect(page).toHaveURL(/\/teams\/OKC$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Oklahoma City\s*Thunder/);
});

test("a franchise page shows its titles and its Seattle years", async ({ page }) => {
  await page.goto("/teams/OKC");
  const seasons = page.getByRole("table", { name: /season by season/ });
  await expect(seasons.getByRole("row", { name: /2024-25/ })).toContainText("Champions");
  await expect(seasons.getByRole("row", { name: /2000-01/ })).toContainText("SEA");
});

test("the leaders re-rank and keep the roster season", async ({ page }) => {
  await page.goto("/teams/LAL?season=2009-10");
  await expect(page.locator("#roster").locator("..").locator("..")).toBeVisible();
  await expect(page.getByRole("table", { name: /players in 2009-10/ })).toContainText("Kobe Bryant");

  await page.getByRole("navigation", { name: "Rank the leaders by" }).getByRole("link", { name: "Assists" }).click();
  await expect(page).toHaveURL(/\/teams\/LAL\?season=2009-10&by=assists#leaders$/);
  const leaders = page.getByRole("table", { name: /career leaders in assists/ });
  await expect(leaders.getByRole("row").nth(1)).toContainText("Kobe Bryant");
  await expect(page.getByRole("table", { name: /players in 2009-10/ })).toBeVisible();
});

test("the roster's season picker steps back a season", async ({ page }) => {
  await page.goto("/teams/LAL?season=2009-10");
  await page.getByRole("link", { name: "Previous season: 2008-09" }).click();
  await expect(page).toHaveURL(/season=2008-09/);
  await expect(page.getByRole("table", { name: /players in 2008-09/ })).toBeVisible();
});

test("a season in the table opens its roster", async ({ page }) => {
  await page.goto("/teams/SAS");
  await page.getByRole("link", { name: "2013-14: see the roster" }).click();
  await expect(page).toHaveURL(/\/teams\/SAS\?season=2013-14#roster$/);
  await expect(page.getByRole("table", { name: /players in 2013-14/ })).toContainText("Tim Duncan");
});
