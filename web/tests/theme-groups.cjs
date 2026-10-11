const { chromium, expect } = require('@playwright/test');
const shots = require("node:path").resolve(process.env.DIOPT_SCREENSHOT_DIR ?? "test-results/screenshots");
require("node:fs").mkdirSync(shots, { recursive: true });
(async () => {
 const browser = await chromium.launch({executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH});
 try {
 const page = await browser.newPage({ viewport:{width:1440,height:1050}, colorScheme:'dark' });
 const errors=[]; page.on('pageerror', e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:43100/');
 await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.getByLabel('Gene identifiers').fill('rut\nCG3038\nrut');
 await page.getByRole('button',{name:'Find orthologs'}).click();
 await expect(page.locator('.input-group')).toHaveCount(2);
 await expect(page.locator('.result-row').first().getByRole('button')).toHaveCount(0);
 await page.getByRole('button',{name:'Next',exact:true}).click();
 await expect(page.locator('.input-group')).toHaveCount(2);
 await expect(page.locator('.input-group').first()).toContainText('continued');
 await expect(page.locator('.input-group').last()).toContainText('rut');
 await page.getByLabel('Sort within gene').selectOption('symbol');
 await expect(page.locator('.input-group').first()).toContainText('rut');
 await expect(page.locator('.result-row').first()).toContainText('ADCY1');
 await page.getByRole('button',{name:'Edit search'}).click(); await page.getByLabel('Gene identifiers').fill('rut');
 await page.getByRole('button',{name:'Find orthologs'}).click();
 await expect(page.getByRole('heading',{name:/ orthologs$/})).toBeVisible();
 await expect(page.locator('.input-group')).toHaveCount(1);
 for(const theme of ['dark','light']) {
  if(theme==='light') await page.getByRole('button',{name:'Switch to light mode'}).click();
  for(const width of [1440,900,390]) {
   await page.setViewportSize({width,height:1050});
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
   await page.screenshot({path:`${shots}/groups-${theme}-${width}.png`,fullPage:true});
  }
 }
 await page.reload(); await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 expect(errors).toEqual([]);
 console.log('Passed: theme persistence, grouped/repeated inputs, pagination, sorting, method strip, both themes at 3 widths, no console errors.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
