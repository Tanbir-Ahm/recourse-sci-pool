// Print report HTML files to PDF (A4 landscape) with Chromium through Playwright.
//   NODE_PATH=$(npm root -g) node print_pdf.js /absolute/path/one.html [/absolute/path/two.html ...]
// Needs Node and the playwright package. The HTML and PDF hold the page image and text: case data, keep them outside the repository.
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const f of process.argv.slice(2)) {
    const p = await b.newPage();
    await p.goto('file://' + f);
    await p.pdf({ path: f.replace(/\.html$/, '.pdf'), format: 'A4', landscape: true, printBackground: true, margin: { top: '12mm', bottom: '12mm', left: '12mm', right: '12mm' } });
    await p.close();
    console.log('pdf ' + f.replace(/\.html$/, '.pdf'));
  }
  await b.close();
})();
