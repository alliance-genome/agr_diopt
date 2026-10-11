import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testIgnore: "**/unit/**",
  use: {
    // Defaults to the fixture API port so a bare `npm test` never runs fixture assertions against real data.
    baseURL: process.env.DIOPT_BASE_URL ?? "http://127.0.0.1:43111",
    browserName: "chromium",
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
    },
  },
});
