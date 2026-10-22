const { chromium } = require('playwright-core'); const fs = require('fs');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox'] });
  const ctx = await b.newContext({ acceptDownloads: true }); const p = await ctx.newPage();
  const files = {}; p.on('download', async d => { const path = '/tmp/claude-0/ghcmock/dl_' + d.suggestedFilename(); await d.saveAs(path); files[d.suggestedFilename()] = path; });
  p.on('console', m => { if (m.text().startsWith('[GHC]')) console.log(m.text()); });
  await p.goto('file:///tmp/claude-0/ghcmock/mock.html');
  await p.evaluate(fs.readFileSync('/home/user/recourse-sci-pool/ghc/court_search/ghc_month_loop.js', 'utf8'));
  const mode = process.argv[2];
  if (mode === 'test') { const n = await p.evaluate(() => GHC.test()); console.log('rows returned:', n); console.log('last query set on the form:', await p.evaluate(() => window.__lastQuery)); }
  if (mode === 'run') { await p.evaluate(() => { window.GHC_FAST = true; }); await p.evaluate(() => GHC.run('2018-01', '2018-03')); }
  if (mode === 'cap') { const r = await p.evaluate(async () => { const rows = await GHC._win(new Date(2018,0,1), new Date(2018,2,31)); return rows.length; }); console.log('cap test rows:', r); }
  await new Promise(r => setTimeout(r, 1500));
  for (const [n, path] of Object.entries(files)) { const t = fs.readFileSync(path, 'utf8').split('\n'); console.log('file', n, t.length, 'lines; first:', t[0].slice(0, 160)); }
  await b.close();
})().catch(e => { console.error('TEST ERROR', e.message); process.exit(1); });
