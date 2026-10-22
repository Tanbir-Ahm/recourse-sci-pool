// Gauhati High Court "Judgements / Orders" search (ghcservices.assam.gov.in/casestatus/JudgementFilters.php): collects the result rows of many date windows, one search at a time.
// Runs in YOUR browser on the empty search form, as a person would use the page: one search every ~8 seconds, nothing in parallel. It stops by itself on a CAPTCHA, a block, an error or a timeout,
// and saves what it has. It never tries to get around anything. Stop it at any time with:  window.GHC_STOP = true
// Output: one TSV file per calendar year (window <TAB> slno <TAB> row text <TAB> link(s)), downloaded to your Downloads folder (Chrome may ask "allow multiple downloads": click Allow).
// Use:  1) open the page, click "Multiple Parameter Search" so the empty form shows;  2) paste this whole file in the Console and press Enter;  3) then run ONE of:
//   await GHC.test()                          // January 2018 only (the court shows 474 entries for it); check the count it prints
//   await GHC.run('2018-01', '2026-10')       // every month in the range, newest last; saves one file per year
(() => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const pad = n => String(n).padStart(2, '0');
  const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const log = (...a) => console.log('[GHC]', ...a);
  const fmt = d => `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()}`;
  const iso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parseDMY = s => { const [d, m, y] = s.split('-').map(Number); return new Date(y, m - 1, d); };

  function controlAfterLabel(text, selector) {
    const want = text.toLowerCase().replace(/:$/, '');
    const labels = [...document.querySelectorAll('label, span, div, p, b, strong, td, th')]
      .filter(e => visible(e) && !e.querySelector('label,select,input') && norm(e.textContent).toLowerCase().replace(/:$/, '') === want);
    for (const lab of labels) {
      if (lab.tagName === 'LABEL' && lab.htmlFor) { const c = document.getElementById(lab.htmlFor); if (c && visible(c)) return c; }
      const all = [...document.querySelectorAll(selector)].filter(visible);
      const after = all.find(c => lab.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING);
      if (after) return after;
    }
    return null;
  }
  function fire(el, types) { for (const t of types) el.dispatchEvent(new Event(t, { bubbles: true })); if (window.jQuery) { try { window.jQuery(el).trigger('change'); } catch (e) {} } }
  function setSelect(label, optionText) {
    const sel = controlAfterLabel(label, 'select');
    if (!sel) throw new Error(`cannot find the "${label}" drop-down`);
    const opt = [...sel.options].find(o => norm(o.textContent).toLowerCase() === optionText.toLowerCase());
    if (!opt) throw new Error(`"${label}" has no option "${optionText}" (options: ${[...sel.options].map(o => norm(o.textContent)).join(', ')})`);
    sel.value = opt.value; fire(sel, ['input', 'change']);
    if (norm(sel.options[sel.selectedIndex].textContent).toLowerCase() !== optionText.toLowerCase()) throw new Error(`could not set "${label}" to "${optionText}"`);
  }
  function setDate(label, d) {
    const inp = controlAfterLabel(label, 'input');
    if (!inp) throw new Error(`cannot find the "${label}" date box`);
    const isoMode = inp.type === 'date';
    inp.value = isoMode ? iso(d) : fmt(d); fire(inp, ['input', 'change', 'blur']);
    if (inp.value !== (isoMode ? iso(d) : fmt(d))) throw new Error(`could not set "${label}" to ${fmt(d)} (box holds "${inp.value}")`);
  }
  function button(textRe) {
    return [...document.querySelectorAll('button, input[type=submit], input[type=button], a.btn, a')].filter(visible).find(b => textRe.test(norm(b.value || b.textContent)));
  }
  function checkForBlock() {
    const t = norm(document.body.innerText).toLowerCase();
    if (/captcha|access denied|too many requests|temporarily blocked|forbidden|are you a robot/.test(t)) throw new Error('the page shows a CAPTCHA or a block: STOPPED, nothing was bypassed');
  }
  function resultsTable() { return [...document.querySelectorAll('table')].find(t => visible(t) && /Case Details|Slno/i.test(t.textContent)); }
  async function waitFor(fn, ms, what) {
    const t0 = Date.now();
    while (Date.now() - t0 < ms) { if (window.GHC_STOP) throw new Error('stopped by you'); checkForBlock(); const v = fn(); if (v) return v; await sleep(300); }
    throw new Error(`timed out waiting for ${what}`);
  }
  function download(name, text) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' })); a.download = name; document.body.appendChild(a); a.click(); a.remove();
  }
  function entryCount() {
    const info = [...document.querySelectorAll('div, span, p')].filter(e => visible(e) && !e.querySelector('div,p') && /^Showing\b.*\bentries/i.test(norm(e.textContent)))[0];
    if (!info) return null;
    const m = /of\s+([\d,]+)\s+entries/i.exec(info.textContent);
    return m ? +m[1].replace(/,/g, '') : null;
  }
  let prevSig = '';
  const sigOf = tbl => { const tr = tbl.querySelector('tbody tr'); return entryCount() + '|' + (tr ? norm(tr.textContent).slice(0, 80) : ''); };

  async function oneWindow(from, to) {
    // form -> search -> collect -> back
    await waitFor(() => controlAfterLabel('From', 'input'), 20000, 'the search form');
    setSelect('Category', 'All');
    await sleep(500);
    setSelect('Judgement / Order', 'Judgement');
    setDate('From', from); setDate('To', to);
    await sleep(400);
    const go = button(/^search$/i);
    if (!go) throw new Error('cannot find the Search button');
    go.click();
    const tbl = await waitFor(() => { const t = resultsTable(); return t && entryCount() !== null ? t : null; }, 90000, 'the results');
    await sleep(800);
    if (sigOf(tbl) === prevSig) { await sleep(4000); }          // looks like the previous window's table: give the page time to replace it
    prevSig = sigOf(tbl);
    let nodes;
    if (window.jQuery && window.jQuery.fn.dataTable && window.jQuery.fn.dataTable.isDataTable(tbl)) nodes = window.jQuery(tbl).DataTable().rows().nodes().toArray();
    else nodes = [...tbl.querySelectorAll('tbody tr')];
    const total = entryCount();
    const rows = nodes.filter(tr => tr.cells && tr.cells.length >= 2).map(tr => [norm(tr.cells[0].innerText), norm(tr.cells[1].innerText), [...tr.cells[1].querySelectorAll('a')].map(a => a.href).join(' | ')]);
    if (total !== null && rows.length !== total) log(`WARNING: the page says ${total} entries but I read ${rows.length} rows`);
    const back = button(/^\s*back\s*$/i);
    if (!back) throw new Error('cannot find the Back button');
    back.click();
    await waitFor(() => controlAfterLabel('From', 'input'), 20000, 'the form to come back');
    return { total, rows };
  }

  async function windowRows(from, to, depth = 0) {
    const r = await oneWindow(from, to);
    log(`${fmt(from)} to ${fmt(to)}: ${r.total} entries, ${r.rows.length} rows read`);
    if (r.total >= 1000) {                                              // the page shows at most 1000 rows: split the window in two and redo both halves
      if (depth >= 4 || from.getTime() >= to.getTime()) { log(`CAP reached for ${fmt(from)} to ${fmt(to)} and it cannot be split further: rows may be missing`); return r.rows.map(x => [`${fmt(from)}..${fmt(to)} (CAPPED)`, ...x]); }
      const mid = new Date(from.getTime() + Math.floor((to - from) / 86400000 / 2) * 86400000);
      const next = new Date(mid.getTime() + 86400000);
      log(`cap: splitting into ${fmt(from)}..${fmt(mid)} and ${fmt(next)}..${fmt(to)}`);
      await sleep(7000);
      const a = await windowRows(from, mid, depth + 1); await sleep(7000);
      const b = await windowRows(next, to, depth + 1); return a.concat(b);
    }
    return r.rows.map(x => [`${fmt(from)}..${fmt(to)}`, ...x]);
  }

  const G = {
    async test() {
      window.GHC_STOP = false;
      const from = new Date(2018, 0, 1), to = new Date(2018, 0, 31);
      const rows = await windowRows(from, to);
      download('ghc_rows_2018-01.tsv', rows.map(r => r.join('\t')).join('\n'));
      log(`test done: ${rows.length} rows (the court showed 474 for January 2018). File ghc_rows_2018-01.tsv saved.`);
      return rows.length;
    },
    async run(startYM, endYM) {
      window.GHC_STOP = false;
      let [y, m] = startYM.split('-').map(Number); const [ey, em] = endYM.split('-').map(Number);
      let bucket = [], done = 0;
      try {
        while (y < ey || (y === ey && m <= em)) {
          const from = new Date(y, m - 1, 1), to = new Date(y, m, 0);
          const rows = await windowRows(from, to);
          bucket = bucket.concat(rows); done++;
          if (m === 12 || (y === ey && m === em)) { download(`ghc_rows_${y}.tsv`, bucket.map(r => r.join('\t')).join('\n')); log(`saved ghc_rows_${y}.tsv (${bucket.length} rows)`); bucket = []; }
          m++; if (m > 12) { m = 1; y++; }
          await sleep(6000 + Math.floor(Math.random() * 3000));
        }
        log(`ALL DONE: ${done} months`);
      } catch (e) {
        log('STOPPED:', e.message);
        if (bucket.length) { download(`ghc_rows_${y}_partial_to_${y}-${pad(m)}.tsv`, bucket.map(r => r.join('\t')).join('\n')); log('the rows collected so far were saved as a partial file'); }
        log(`next month to do would have been ${y}-${pad(m)}`);
      }
    },
  };
  G._win = windowRows;                                                    // for tests only
  window.GHC = G;
  log('ready. Run  await GHC.test()  first.');
})();
