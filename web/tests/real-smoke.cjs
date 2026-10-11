// Run explicitly after check_real_search.py against the restored-data API.
const { chromium, expect } = require("@playwright/test");
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
const shots = require("node:path").resolve(process.env.DIOPT_SCREENSHOT_DIR ?? "test-results/screenshots");
require("node:fs").mkdirSync(shots, { recursive: true });

(async () => {
  const corpus = JSON.parse(
    await fs.readFile(
      path.join(process.env.DIOPT_DATA_DIR ?? path.join(os.homedir(), "diopt-data"), "benchmarks/real-corpus.json"),
      "utf8",
    ),
  );
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1050 },
    });
    await page.goto("http://127.0.0.1:43100/");
    await expect(page.getByLabel("From species")).toBeEnabled();
    const query = corpus[0];
    await page
      .getByLabel("From species")
      .selectOption(String(query.input_species));
    await page
      .getByLabel("To species")
      .selectOption(String(query.output_species));
    await page
      .getByLabel("Gene identifiers")
      .fill(query.identifiers.join("\n"));
    await page.getByRole("button", { name: "Find orthologs" }).click();
    await expect(
      page.getByRole("heading", { name: / orthologs$/ }),
    ).toBeVisible();
    await expect(
      page.locator(".result-row").first().getByRole("img", { name: /: match$/ }).first(),
    ).toBeVisible();
    const pending = page.waitForEvent("download");
    await page.getByRole("button", { name: "Query + results · JSON" }).click();
    const download = await pending;
    const result = JSON.parse(await fs.readFile(await download.path(), "utf8"));
    expect(result.dataset_id).not.toMatch(/^synthetic-/);
    expect(result.query.identifiers).toEqual(query.identifiers);
    expect(result.results[0].orthologs.length).toBeGreaterThan(0);
    await page.getByRole("button", { name: "Edit search" }).click();
    await page.getByLabel("From species").selectOption("9606");
    await page.getByLabel("To species").selectOption("7227");
    await page.getByLabel("Gene identifiers").fill("PAX6");
    await page.getByRole("button", { name: "Find orthologs" }).click();
    await expect(page.getByRole("heading", { name: "Human to Fly orthologs" })).toBeVisible();
    await expect(page.locator(".result-row").first().getByRole("img", { name: /: match$/ }).first()).toBeVisible();
    await page.screenshot({
      path: `${shots}/real-desktop.png`,
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `${shots}/real-mobile.png`,
      fullPage: true,
    });
    console.log(
      "Real-data browser search (corpus query and PAX6 human→fly), method strip, JSON export, and mobile overflow checks passed.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
