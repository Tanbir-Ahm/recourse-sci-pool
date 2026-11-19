// A real browser through the Reading Desk, using the demo (three invented pages, no model, no cost).
//   node ocr_tests/web/tests/e2e_browser.js http://127.0.0.1:8080 NAME ACCESS-CODE      (needs the playwright package; NODE_PATH=$(npm root -g) if it is installed globally)
// It signs in, runs the demo, opens the result, clicks a "Read these first" item, ticks a page as read, downloads the Word file, opens the report and the marking sheet,
// and visits History, the glossary and Usage. It exits 1 on the first thing that does not work and prints the page errors it saw.
const { chromium } = require('playwright');
const [BASE, NAME, CODE] = [process.argv[2] || 'http://127.0.0.1:8080', process.argv[3] || 'owner', process.argv[4] || ''];
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  const ok = (cond, what) => { if (!cond) throw new Error('FAILED: ' + what); console.log('ok  ' + what); };
  await p.goto(BASE + '/');
  await p.waitForFunction(() => document.querySelector('#ln') || /Read a document/.test(document.body.innerText));
  if (await p.$('#ln')) { await p.fill('#ln', NAME); await p.fill('#lc', CODE); await p.click('button[type=submit]'); }
  await p.waitForSelector('text=Read a document');
  await p.click('text=Try the demo');
  await p.waitForSelector('.tabs', { timeout: 120000 });
  ok((await p.$$eval('.tab[role=tab]', e => e.map(x => x.textContent.trim()))).join('|') === 'Whole document|Page 1|Page 2|Page 3', 'the document and its three pages are tabs');
  ok(await p.$$eval('.first li', e => e.length) === 6, 'Read these first lists six items and a button for the rest');
  await p.click('.first li:first-child .t'); await p.waitForSelector('mark.flash', { timeout: 3000 }); ok(true, 'clicking an item finds its passage in the English');
  ok(await p.$eval('[data-english]', e => e.innerText.includes('[14/3/2024 or 11/3/2024')), 'the English shows both values where the readings disagree');
  ok(await p.$$eval('[data-english] del.mk', e => e.length) === 1 && await p.$$eval('[data-english] ins.mk', e => e.length) === 1, 'a crossed-out word and the word above it are shown as such');
  await p.click('.tab[role=tab]:has-text("Page 2")'); await p.waitForFunction(() => { const i = document.querySelector('.scan img'); return i && i.complete && i.naturalWidth > 0; });
  ok(true, 'a page shows its picture beside the English');
  await p.check('input[id^="rv-"]'); await p.waitForSelector('text=Marked as read by'); ok(true, 'a page can be marked as read, with who and when');
  const [dl] = await Promise.all([p.waitForEvent('download'), p.click('a:has-text("Word file")')]); ok(/\.docx$/.test(dl.suggestedFilename()), 'the Word file downloads (' + dl.suggestedFilename() + ')');
  const [rep] = await Promise.all([ctx.waitForEvent('page'), p.click('a:has-text("Full report")')]); await rep.waitForLoadState();
  ok((await rep.content()).includes('Machine draft. Not a certified translation.'), 'the report carries the stamp'); await rep.close();
  const [ms] = await Promise.all([ctx.waitForEvent('page'), p.click('a:has-text("Marking sheet")')]); await ms.waitForLoadState(); ok(/Marking sheet/.test(await ms.title()), 'the marking sheet opens'); await ms.close();
  await p.click('.nav a:has-text("History")'); await p.waitForSelector('table'); ok(true, 'History lists the job');
  await p.click('.nav a:has-text("Term glossary")'); await p.waitForSelector('text=227 of 227'); await p.fill('#gq', 'jamabandi'); await p.waitForSelector('text=1 of 227'); ok(true, 'the glossary searches');
  await p.click('.nav a:has-text("Usage")'); await p.waitForSelector('text=Today (you)'); ok(true, 'Usage shows');
  await p.setViewportSize({ width: 400, height: 860 }); await p.click('.nav a:has-text("History")'); await p.click('table a'); await p.waitForSelector('.tabs');
  ok(await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth) <= 0, 'no sideways scrolling at phone width');
  console.log('page errors: ' + (errs.length ? JSON.stringify(errs) : 'none'));
  await b.close(); process.exit(errs.length ? 1 : 0);
})().catch(e => { console.error(e.message); process.exit(1); });
