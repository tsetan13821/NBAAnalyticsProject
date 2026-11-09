import { expect, test } from "@playwright/test";

const SECTIONS = [
  { link: "MVP Race", path: "/mvp", heading: "Can a model call the MVP?" },
  { link: "Players", path: "/players", heading: /players/i },
  { link: "Compare", path: "/compare", heading: "Compare players" },
  { link: "Games", path: "/games", heading: "Who wins this week" },
  { link: "Teams", path: "/teams", heading: "All thirty teams" },
];

test("the home page shows the MVP model's record", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Twenty-six seasons");
  await expect(page.getByText("Seasons called correctly")).toBeVisible();
});

for (const section of SECTIONS) {
  test(`the main menu opens ${section.link}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: section.link }).click();
    await expect(page).toHaveURL(new RegExp(`${section.path}$`));
    await expect(page.getByRole("heading", { level: 1 })).toContainText(section.heading);
    await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: section.link })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
}

test("unknown players and teams show the not-found page", async ({ page }) => {
  for (const path of ["/players/1", "/teams/XYZ", "/games/0000000000"]) {
    await page.goto(path);
    await expect(page.getByText(/not found/i).first()).toBeVisible();
  }
});
