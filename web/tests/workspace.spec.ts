import { test, expect } from "@playwright/test";

test("entrance page is search-first with Alliance branding and examples", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "DIOPT" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Alliance of Genome Resources" })).toHaveAttribute(
    "href", "https://www.alliancegenome.org",
  );
  await expect(page.getByText("Local prototype")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "About the scores and methods" })).toHaveCount(1);
  const find = page.getByRole("button", { name: "Find orthologs" });
  await expect(find).toBeDisabled();
  await expect(page.getByLabel("From species")).toBeEnabled();
  await page.getByRole("button", { name: /Load example: PAX6/ }).click();
  await expect(page.getByLabel("Gene identifiers")).toHaveValue("PAX6");
  await expect(page.getByLabel("From species")).toHaveValue("9606");
  await expect(page.getByLabel("To species")).toHaveValue("7227");
  await expect(page.getByLabel("Gene identifiers")).toBeFocused();
  await expect(find).toBeEnabled();
  await expect(page.getByRole("heading", { name: /orthologs$/ })).toHaveCount(0);
});

test("search collapses to a summary bar and Edit search restores inputs", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Gene identifiers").fill("ProbeA\nShared\nUnknown\nNoPair");
  await page.getByRole("button", { name: "Find orthologs" }).click();
  const heading = page.getByRole("heading", { name: "Fly to Human orthologs" });
  await expect(heading).toBeVisible();
  await expect(heading).toBeFocused();
  await expect(page.getByLabel("Gene identifiers")).toHaveCount(0);
  await expect(page.getByText("ProbeA, Shared, Unknown +1 more")).toBeVisible();
  await page.getByRole("button", { name: "Edit search" }).click();
  await expect(page.getByLabel("Gene identifiers")).toHaveValue("ProbeA\nShared\nUnknown\nNoPair");
  await page.getByLabel("Gene identifiers").fill("Another query");
  await expect(page.getByText(/Search inputs have changed/)).toBeVisible();
  await page.getByRole("button", { name: "Close search" }).click();
  await expect(page.getByLabel("Gene identifiers")).toHaveCount(0);
});

test("errors preserve inputs and narrow layout stays within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Gene identifiers").fill("ProbeA");
  await page.route("**/v1/orthologs/search", (route) =>
    route.fulfill({
      status: 504,
      contentType: "application/json",
      body: JSON.stringify({ error: "Search timed out. Try a smaller list." }),
    }),
  );
  await page.getByRole("button", { name: "Find orthologs" }).click();
  await expect(page.getByRole("alert")).toContainText("Search timed out");
  await expect(page.getByLabel("Gene identifiers")).toHaveValue("ProbeA");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("dark theme swaps to the white Alliance logo and persists", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("img", { name: "Alliance of Genome Resources" })).toHaveAttribute(
    "src", "/alliance_logo_white.png",
  );
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("results table shows score/max, best-match flags, and method strip without expansion", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Gene identifiers").fill("ProbeA\nShared\nUnknown\nNoPair");
  await page.getByRole("button", { name: "Find orthologs" }).click();
  await expect(page.getByText("1 of 4 inputs has orthologs")).toBeVisible();
  await page.getByText("3 identifiers need attention").click();
  await expect(page.getByText(/Ambiguous match:/)).toBeVisible();
  await expect(page.getByRole("columnheader", { name: /Score\s*of species-pair max/ })).toBeVisible();
  const a = page.locator(".result-row", { hasText: "TargetA" });
  await expect(a.getByRole("cell", { name: "5/5" })).toBeVisible();
  await expect(a.getByText("Yes (adjusted)")).toBeVisible();
  await expect(a.getByRole("img", { name: "Method A: match" })).toBeVisible();
  await expect(a.getByRole("img", { name: "Method B: match" })).toBeVisible();
  await expect(a.getByRole("img", { name: "Method C: no match" })).toBeVisible();
  await expect(a.getByRole("button")).toHaveCount(0);
  const b = page.locator(".result-row", { hasText: "TargetB" });
  await expect(b.getByRole("cell", { name: "—" }).first()).toBeVisible();
  await expect(b.getByTitle("Not supplied")).toHaveCount(2);
  await expect(b.getByRole("img", { name: "Method A: no match" })).toBeVisible();
  await expect(page.getByText(/weighted/i)).toHaveCount(0);
  await expect(page.getByText("Scroll the table sideways to see confidence and methods.")).toBeHidden();

  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Query + results · JSON" }).click();
  const fs = await import("node:fs/promises");
  const data = JSON.parse(await fs.readFile((await (await jsonDownload).path())!, "utf8"));
  expect(data.query.identifiers).toEqual(["ProbeA", "Shared", "Unknown", "NoPair"]);
  expect(data.species_pair_methods).toEqual(["Method A", "Method B", "Method C"]);
  expect(data.max_score).toBe(5);
  expect(JSON.stringify(data)).not.toContain("weighted_score");
  const tsvDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "All results · TSV" }).click();
  const tsv = await tsvDownload;
  expect(tsv.suggestedFilename()).toBe("diopt-results.tsv");
  const header = (await fs.readFile((await tsv.path())!, "utf8")).split("\n")[0].split("\t");
  expect(header).not.toContain("weighted_score");
  expect(header).toEqual(expect.arrayContaining(["mapping", "input_gene_id", "output_gene_id", "methods"]));
});

test("coverage-unknown cells never read as 'no match'", async ({ page }) => {
  await page.route("**/v1/orthologs/search", async (route) => {
    const real = await route.fetch();
    const body = await real.json();
    body.species_pair_methods = [];
    body.max_score = null;
    await route.fulfill({ response: real, json: body });
  });
  await page.goto("/");
  await page.getByLabel("Gene identifiers").fill("ProbeA");
  await page.getByRole("button", { name: "Find orthologs" }).click();
  const b = page.locator(".result-row", { hasText: "TargetB" });
  await expect(b.getByRole("img", { name: "Method A: coverage unknown" })).toBeVisible();
  await expect(b.getByRole("img", { name: /no match/ })).toHaveCount(0);
  await expect(page.locator(".result-row", { hasText: "TargetA" }).getByRole("cell", { name: "5", exact: true })).toBeVisible();
});

test("narrow screens show a methods disclosure and no horizontal page scroll", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByLabel("Gene identifiers")
    .fill(["ProbeA", ...Array.from({ length: 99 }, (_, i) => `Missing${i}`)].join("\n"));
  await page.getByRole("button", { name: "Find orthologs" }).click();
  await expect(page.getByText("ProbeA, Missing0, Missing1 +97 more")).toBeVisible();
  const a = page.locator(".result-row", { hasText: "TargetA" });
  await expect(a.getByRole("img", { name: "Method A: match" })).toBeHidden();
  await expect(page.getByText("Scroll the table sideways to see confidence and methods.")).toBeVisible();
  await a.getByText("2/3 methods").click();
  await expect(a.getByText("Method C: no match")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("footer sits at the bottom of short pages", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1600 });
  await page.goto("/");
  await expect(page.getByLabel("From species")).toBeEnabled();
  const box = await page.locator(".site-footer").boundingBox();
  expect(Math.round(box!.y + box!.height)).toBe(1600);
});

test("disabled export uses the readable disabled style, not faded opacity", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Gene identifiers").fill("NoPair");
  await page.getByRole("button", { name: "Find orthologs" }).click();
  await expect(page.getByText("0 of 1 inputs have orthologs")).toBeVisible();
  const tsv = page.getByRole("button", { name: "All results · TSV" });
  await expect(tsv).toBeDisabled();
  await expect(tsv).toHaveCSS("opacity", "1");
  await expect(tsv).toHaveCSS("background-color", "rgb(227, 232, 235)");
});
