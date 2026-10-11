const { chromium } = require("@playwright/test");
const path = require("node:path");
const shots = require("node:path").resolve(process.env.DIOPT_SCREENSHOT_DIR ?? "test-results/screenshots");
require("node:fs").mkdirSync(shots, { recursive: true });
(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
  });
  const shot = (scheme, name) => `${shots}/${scheme}-${name}.png`;
  for (const scheme of ["light", "dark"]) {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1050 },
      colorScheme: scheme,
    });
    await page.goto((process.env.DIOPT_BASE_URL ?? "http://127.0.0.1:43111") + "/");
    await page.getByLabel("From species").isEnabled();
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: shot(scheme, "desktop-empty"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: shot(scheme, "mobile-empty"), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1050 });
    await page
      .getByLabel("Gene identifiers")
      .fill("ProbeA\nShared\nUnknown\nNoPair");
    await page.getByRole("button", { name: "Find orthologs" }).click();
    await page.getByRole("heading", { name: / orthologs$/ }).waitFor();
    await page.getByRole("img", { name: "Method A: match" }).first().hover();
    await page.screenshot({ path: shot(scheme, "desktop"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: shot(scheme, "mobile"), fullPage: true });
    await page.close();
  }
  await browser.close();
})();
