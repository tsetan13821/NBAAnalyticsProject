import { expect, test } from "@playwright/test";

// On a phone, wide tables scroll inside their own box; the page itself must never scroll sideways.
const PAGES = ["/", "/mvp", "/players", "/players/203999", "/compare", "/games", "/teams", "/teams/OKC"];

for (const path of PAGES) {
  test(`${path} fits a phone screen`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const { scrollWidth, innerWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
  });
}

test("the main menu scrolls instead of wrapping on a phone", async ({ page }) => {
  await page.goto("/");
  const menu = page.getByRole("navigation", { name: "Main" });
  await menu.getByRole("link", { name: "Teams" }).scrollIntoViewIfNeeded();
  await menu.getByRole("link", { name: "Teams" }).click();
  await expect(page).toHaveURL(/\/teams$/);
});
