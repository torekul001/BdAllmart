// Optional visual QA. Run preview_marketplace.py first. Uses only exported test pages.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('node:path');
const fs = require('node:fs');
const { pathToFileURL } = require('node:url');

(async () => {
  const directory = path.join(__dirname, 'instance', 'ui_preview');
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    const results = [];
    page.on('pageerror', error => errors.push(error.message));
    const open = name => page.goto(pathToFileURL(path.join(directory, name + '.html')).href);
    await open('listing_form');
    await page.locator('input[name=title]').fill('Browser test listing');
    await page.locator('textarea[name=description]').fill('Complete description');
    await page.locator('[data-next]').click();
    if ((await page.locator('[data-step-count]').textContent()) !== '2 / 3') throw Error('Wizard step 2 failed');
    await page.locator('input[name=price]').fill('250');
    await page.locator('[data-next]').click();
    if ((await page.locator('[data-step-count]').textContent()) !== '3 / 3') throw Error('Wizard step 3 failed');
    await page.locator('[data-prev]').click();
    if ((await page.locator('input[name=price]').inputValue()) !== '250') throw Error('Wizard lost data');
    await page.evaluate(() => window.scrollTo({top:0, behavior:'instant'}));
    await page.screenshot({ path: path.join(directory, 'listing-wizard.png'), fullPage: true });
    for (const name of ['dashboard', 'catalog', 'listing_form', 'settings', 'jobs', 'jobs_designer', 'job_bid', 'job_contract', 'customer_module', 'designer_module', 'tracking_module']) {
      for (const width of [390, 768, 1440]) {
        await page.setViewportSize({ width, height: 950 });
        await open(name);
        results.push({ page: name, width, overflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth) });
        if (name === 'dashboard' || (['catalog','jobs','jobs_designer','customer_module','designer_module'].includes(name) && width === 1440)) {
          await page.screenshot({ path: path.join(directory, `${name}-${width === 390 ? 'mobile' : width === 768 ? 'tablet' : 'desktop'}.png`), fullPage: true });
        }
      }
    }
    const report = { wizard: 'passed', javascriptErrors: errors, responsive: results };
    fs.writeFileSync(path.join(directory, 'verification.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
    if (errors.length || results.some(item => item.overflow)) process.exitCode = 1;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
