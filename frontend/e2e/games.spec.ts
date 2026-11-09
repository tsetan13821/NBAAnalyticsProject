import { expect, type Page, test } from "@playwright/test";

/** The first upcoming game on /games (the data changes daily, so the test can't name one). */
async function openFirstUpcomingGame(page: Page) {
  await page.goto("/games");
  const game = page.locator('a[href^="/games/00"]').first();
  test.skip((await game.count()) === 0, "No upcoming games in the data (off-season)");
  await game.click();
  await expect(page).toHaveURL(/\/games\/\d{10}$/);
}

test("a game explains its prediction", async ({ page }) => {
  await openFirstUpcomingGame(page);
  await expect(page.getByText(/win chance/i).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why" })).toBeVisible();
  await expect(page.getByText("Tonight's availability")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Who plays" })).toBeVisible();
});

test("sitting a player changes the prediction, and the report brings it back", async ({ page }) => {
  await openFirstUpcomingGame(page);
  const gameUrl = page.url();

  // The most valuable player listed first in the first roster, as the report has him
  const controls = page.getByRole("group", { name: /^What if for / }).first();
  const name = (await controls.getAttribute("aria-label"))!.replace("What if for ", "");
  await controls.getByRole("link", { name: `${name}: sits` }).click();

  await expect(page).toHaveURL(/\?out=\d+/);
  const banner = page.getByRole("complementary").filter({ hasText: "What if" });
  await expect(banner).toContainText(`Without ${name}`);
  await expect(page.getByRole("link", { name: `${name}: sits` })).toHaveAttribute("aria-current", "true");

  await page.getByRole("link", { name: `${name}: as on the injury report` }).click();
  await expect(page).toHaveURL(gameUrl);
  await expect(banner).toHaveCount(0);
});

test("results can be filtered by team", async ({ page }) => {
  await page.goto("/games/results?team=BOS");
  const cards = page.locator('a[href^="/games/00"]');
  test.skip((await cards.count()) === 0, "No Celtics games played yet");
  for (const card of await cards.all()) {
    await expect(card).toContainText("Boston Celtics");
  }
});
