/* Reading Desk front end. Plain JavaScript, no libraries, nothing loaded from another site. Every string that comes from the server or from a model is put in the page with
   textContent (through h()), never as HTML. */
(function () {
  'use strict';
  var app = document.getElementById('app');
  var STAMP = 'Machine draft. Not a certified translation.';
  var S = { pub: { site_name: 'Reading Desk', retention_hours: 72, contact: '' }, me: null, timer: null, glossary: null, files: [], form: { label: '', language: 'Assamese', page_type: 'handwritten', grouped: true, known: '', gate: false } };

  /* ---------- helpers ---------- */
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === 'class') el.className = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (k === 'value' || k === 'checked' || k === 'disabled') el[k] = v;
      else el.setAttribute(k, v === true ? '' : v);
    });
    (function add(list) {
      list.forEach(function (c) {
        if (c == null || c === false) return;
        if (Array.isArray(c)) return add(c);
        el.appendChild(c.nodeType ? c : document.createTextNode(String(c)));
      });
    })(Array.prototype.slice.call(arguments, 2));
    return el;
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function put(el, nodes) { clear(el); (Array.isArray(nodes) ? nodes : [nodes]).forEach(function (n) { if (n) el.appendChild(n); }); }
  function norm(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }
  function cap(s) { s = String(s || ''); return s.charAt(0).toUpperCase() + s.slice(1); }
  function fmt(iso) { if (!iso) return ''; var d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }); }
  function inr(x) { return 'Rs ' + (Math.round((x || 0) * 100) / 100).toFixed(2).replace(/\.00$/, ''); }
  function bytes(n) { return n < 1048576 ? Math.max(1, Math.round(n / 1024)) + ' KB' : (n / 1048576).toFixed(1) + ' MB'; }
  function field(label, id, input, hint) { return h('div', { class: 'field' }, h('label', { for: id }, label), input, hint ? h('span', { class: 'small' }, hint) : null); }
  function banner(kind, text) { return h('div', { class: 'banner ' + kind, role: kind === 'error' ? 'alert' : 'status' }, h('p', null, text)); }
  function pill(light) { return light ? h('span', { class: 'pill ' + light }, h('i'), cap(light)) : null; }
  var tt;
  function toast(msg) { var t = document.getElementById('toast') || document.body.appendChild(h('div', { class: 'toast', id: 'toast', role: 'status' })); t.textContent = msg; t.hidden = false; clearTimeout(tt); tt = setTimeout(function () { t.hidden = true; }, 3200); }
  function stopTimer() { if (S.timer) { clearTimeout(S.timer); S.timer = null; } }

  function api(method, path, body) {
    var headers = { 'X-RD': '1' }, payload;
    if (typeof Blob !== 'undefined' && body instanceof Blob) { headers['Content-Type'] = 'application/octet-stream'; payload = body; }
    else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    return fetch('/api' + path, { method: method, headers: headers, body: payload, credentials: 'same-origin' }).then(function (r) {
      return r.json().catch(function () { return null; }).then(function (d) {
        if (r.status === 401 && path !== '/login') { S.me = null; stopTimer(); render(); }
        if (!r.ok) { var e = new Error((d && d.error) || ('Something went wrong (' + r.status + ').')); e.status = r.status; throw e; }
        return d;
      });
    });
  }

  /* ---------- the English with the reader's marks ---------- */
  var TOKEN = /(~~[^~\n]+?~~|\^[^^\n]+?\^|<doubtful:[^>]*>|\[[^\[\]\n]*?: check\]|\[(?:margin|footer|header):[^\]]*\]|\[(?:unclear|sic|stamp over text|seal over text|signature|struck: \?)\]|\(\?\))/;
  function inline(text) {
    var frag = document.createDocumentFragment();
    String(text).split(TOKEN).forEach(function (part) {
      if (!part) return;
      var c = part.charAt(0), n;
      if (part.length > 4 && part.slice(0, 2) === '~~' && part.slice(-2) === '~~') n = h('del', { class: 'mk', title: 'Crossed out on the page' }, part.slice(2, -2));
      else if (part.length > 2 && c === '^' && part.slice(-1) === '^') n = h('ins', { class: 'mk', title: 'Written above the line' }, part.slice(1, -1));
      else if (part.indexOf('<doubtful:') === 0) n = h('span', { class: 'chip doubt', title: 'The reader was not sure of this passage as written' }, part.slice(1, -1));
      else if (/: check\]$/.test(part)) n = h('span', { class: 'chip differ', title: 'The readings disagree here. Check the page.' }, part);
      else if (TOKEN.test(part) && part.length === (part.match(TOKEN) || [''])[0].length) n = h('span', { class: 'chip mark' }, part);
      else n = document.createTextNode(part);
      frag.appendChild(n);
    });
    return frag;
  }
  function senseSegments(text, quotes) {
    var spans = [];
    (quotes || []).forEach(function (q) { var nq = norm(q), i = nq ? text.indexOf(nq) : -1; if (i >= 0) spans.push([i, i + nq.length]); });
    spans.sort(function (a, b) { return a[0] - b[0]; });
    var out = [], pos = 0;
    spans.forEach(function (s) { if (s[0] < pos) return; if (s[0] > pos) out.push({ t: text.slice(pos, s[0]) }); out.push({ t: text.slice(s[0], s[1]), s: true }); pos = s[1]; });
    if (pos < text.length) out.push({ t: text.slice(pos) });
    return out;
  }
  function englishBlock(paras, quotes) {
    var box = h('div', { class: 'card english', 'data-english': '1' });
    (paras && paras.length ? paras : ['(no English was produced)']).forEach(function (p) {
      var isNote = /^\[(margin|footer|header)\b/i.test(p);
      var el = h('p', { class: isNote ? 'note' : '' });
      senseSegments(p, quotes).forEach(function (seg) {
        if (seg.s) el.appendChild(h('span', { class: 'sense', title: 'The sense check found this sentence may not make sense' }, inline(seg.t)));
        else el.appendChild(inline(seg.t));
      });
      box.appendChild(el);
    });
    return box;
  }
  function legend() {
    return h('div', { class: 'legend' },
      h('span', null, h('del', { class: 'mk' }, 'crossed out'), 'on the page'), h('span', null, h('ins', { class: 'mk' }, 'written above'), 'the line'),
      h('span', null, h('span', { class: 'chip differ' }, '[a or b: check]'), 'the readings disagree'), h('span', null, h('span', { class: 'chip doubt' }, 'doubtful: …'), 'the reader was unsure'),
      h('span', null, h('span', { class: 'sense' }, 'underlined'), 'may not make sense'));
  }
  function reduced() { return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
  function findIn(root, needle) {
    var low = needle.toLowerCase(), w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      var node = w.currentNode, i = node.nodeValue.toLowerCase().indexOf(low);
      if (i >= 0) { var r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + needle.length); var m = document.createElement('mark'); m.className = 'flash'; r.surroundContents(m); return m; }
    }
    return null;
  }
  function flashText(root, needle) {
    var n = norm(needle), m = null;
    [n, n.slice(0, 30), n.slice(0, 14)].some(function (t) { if (t.length >= 3) m = findIn(root, t); return !!m; });
    var target = m || root;
    target.scrollIntoView({ block: 'center', behavior: reduced() ? 'auto' : 'smooth' });
    if (!m) { root.classList.add('flash'); setTimeout(function () { root.classList.remove('flash'); }, 1500); return; }
    setTimeout(function () { var p = m.parentNode; if (!p) return; while (m.firstChild) p.insertBefore(m.firstChild, m); p.removeChild(m); p.normalize(); }, 2000);
  }

  /* ---------- shell and routing ---------- */
  function route() { var p = (location.hash || '#/new').replace(/^#\/?/, '').split('/'); return { name: p[0] || 'new', id: p[1], target: p[2] }; }
  function render() {
    stopTimer();
    if (route().name === 'handling') { document.title = 'How your papers are handled'; return put(app, h('div', { class: 'login wide' }, handlingView())); }
    document.title = S.pub.site_name;
    if (!S.me) return put(app, loginView());
    var r = route(), view = h('div', { class: 'wrap', id: 'view' });
    function nav(name, label) { return h('a', { href: '#/' + name, 'aria-current': (r.name === name || (name === 'history' && r.name === 'job')) ? 'page' : null }, label); }
    put(app, h('div', { class: 'shell' },
      h('aside', { class: 'rail' }, h('div', { class: 'brand' }, S.pub.site_name, h('small', null, 'a reading aid for court papers')),
        h('nav', { class: 'nav', 'aria-label': 'Main' }, h('h4', null, 'Read'), nav('new', 'New document'), h('h4', null, 'Reference'), nav('glossary', 'Term glossary'), h('h4', null, 'Manage'), nav('history', 'History'), nav('usage', 'Usage')),
        h('div', { class: 'foot' }, h('span', null, STAMP, ' A person reads every page.'), h('a', { href: '#/handling' }, 'How your papers are handled'), h('span', null, S.me.user, ' · ', h('a', { href: '#/new', onclick: signOut }, 'Sign out')))),
      h('main', null, view)));
    var v = { new: newView, history: historyView, glossary: glossaryView, usage: usageView, job: function () { return jobView(r.id, r.target); } }[r.name] || newView;
    put(view, v());
  }
  function signOut(e) { e.preventDefault(); api('POST', '/logout', {}).then(function () { S.me = null; render(); }); }
  window.addEventListener('hashchange', function () { if (S.me) render(); });

  function boot() {
    api('GET', '/public').then(function (d) { S.pub = d; }).catch(function () {});
    return api('GET', '/me').then(function (d) { S.me = d; render(); }).catch(function () { S.me = null; render(); });
  }

  /* ---------- sign in ---------- */
  function loginView() {
    var name = h('input', { type: 'text', id: 'ln', autocomplete: 'username', autocapitalize: 'none', spellcheck: 'false' });
    var code = h('input', { type: 'password', id: 'lc', autocomplete: 'current-password' });
    var err = h('p', { class: 'small', role: 'alert' });
    return h('div', { class: 'login' }, h('div', { class: 'card' }, h('h1', null, S.pub.site_name),
      h('p', { class: 'sub' }, 'Sign in with the name and access code you were given.'),
      h('form', { onsubmit: function (e) {
        e.preventDefault(); err.textContent = '';
        api('POST', '/login', { name: name.value, code: code.value }).then(boot).catch(function (x) { err.textContent = x.message; });
      } }, field('Name', 'ln', name), field('Access code', 'lc', code), h('button', { class: 'btn primary', type: 'submit' }, 'Sign in'), err),
      h('p', { class: 'small' }, STAMP), h('p', { class: 'small' }, h('a', { href: '#/handling' }, 'How your papers are handled'))));
  }
  function handlingView() {
    var p = S.pub, li = function (t) { return h('li', null, t); };
    return h('div', { class: 'card' }, h('h1', null, 'How your papers are handled'), h('p', { class: 'sub' }, 'A plain statement of what this site does with what you upload. It is not a legal agreement.'),
      h('ul', { class: 'reasons' },
        li('You upload page photos or a PDF. They are kept on this site\'s server under a random job number, and only the person who uploaded them can open them through the site.'),
        li('To read them, each page picture, and later the text read from it, is sent to Google\'s Gemini service (' + p.reading + '). Google handles it under the terms of the account this site uses.'),
        li('Before you upload you confirm that nothing in the pages identifies a minor or the victim of a sexual offence. Do not upload such pages.'),
        li('A job and all its files are deleted automatically ' + Math.round(p.retention_hours) + ' hours after the reading ends, or at once when you delete the job. An upload you never start is deleted after 6 hours.'),
        li('There is no backup of your papers. A small usage record (who, when, how many pages, an estimated cost) is kept; it holds no text and no file names.'),
        li('The person who runs this server can read files on it while they exist.'),
        li('What comes back is a machine draft. It is not a certified translation, and a person who reads the language must check every page against the original.')),
      p.contact ? h('p', null, 'Questions about your papers: ', p.contact) : null, h('p', null, h('a', { href: '#/new' }, 'Back')));
  }

  /* ---------- new document ---------- */
  var EXT = /\.(pdf|jpe?g|png|webp)$/i;
  function newView() {
    var me = S.me, f = S.form, caps = me.caps, lim = me.limits;
    var list = h('ul', { class: 'files' }), cost = h('p', { class: 'small', 'aria-live': 'polite' }), msg = h('p', { class: 'small', role: 'status' });
    var input = h('input', { type: 'file', id: 'fp', multiple: true, hidden: true, accept: 'image/jpeg,image/png,image/webp' + (caps.pdf ? ',application/pdf' : '') });
    var drop = h('div', { class: 'drop' }, h('strong', null, 'Drop page photos or a PDF here'),
      h('p', { class: 'small' }, 'JPEG, PNG or WebP' + (caps.pdf ? ' or PDF' : ' (PDF is not available on this server)'), '. Up to ', lim.max_pages, ' pages and ', lim.max_file_mb, ' MB a file.'),
      h('button', { class: 'btn', type: 'button', onclick: function () { input.click(); } }, 'Choose files'), input);
    var go = h('button', { class: 'btn primary', type: 'button' }, 'Upload and see the estimate');
    var demoBtn = h('button', { class: 'btn', type: 'button' }, 'Try the demo (invented pages, free)');

    function addFiles(fl) {
      Array.prototype.forEach.call(fl, function (file) {
        if (!EXT.test(file.name) && !/^(image\/(jpeg|png|webp)|application\/pdf)$/.test(file.type)) return toast(file.name + ' is not a PDF, JPEG, PNG or WebP file.');
        if (/pdf$/i.test(file.type) || /\.pdf$/i.test(file.name)) { if (!caps.pdf) return toast('This server cannot read PDFs. Upload the pages as photos.'); }
        if (file.size > lim.max_file_mb * 1048576) return toast(file.name + ' is larger than ' + lim.max_file_mb + ' MB.');
        S.files.push(file);
      });
      drawList();
    }
    function drawList() {
      clear(list);
      S.files.forEach(function (file, i) {
        var isImg = /^image\//.test(file.type);
        var thumb = isImg ? h('img', { alt: '', src: URL.createObjectURL(file) }) : h('div', { class: 'thumb' }, 'PDF');
        list.appendChild(h('li', null, thumb, h('div', { class: 'nm' }, h('div', { class: 'nm' }, file.name), h('span', { class: 'small' }, bytes(file.size))),
          h('div', { class: 'row' },
            h('button', { class: 'btn small', type: 'button', 'aria-label': 'Move up', disabled: i === 0, onclick: function () { S.files.splice(i - 1, 0, S.files.splice(i, 1)[0]); drawList(); } }, '↑'),
            h('button', { class: 'btn small', type: 'button', 'aria-label': 'Move down', disabled: i === S.files.length - 1, onclick: function () { S.files.splice(i + 1, 0, S.files.splice(i, 1)[0]); drawList(); } }, '↓'),
            h('button', { class: 'btn small', type: 'button', 'aria-label': 'Remove', onclick: function () { S.files.splice(i, 1); drawList(); } }, '×'))));
      });
      var imgs = S.files.filter(function (x) { return /^image\//.test(x.type); }).length, pdfs = S.files.length - imgs;
      groupRow.hidden = imgs < 2;
      if (!S.files.length) cost.textContent = 'Nothing chosen yet.';
      else {
        cost.textContent = imgs + ' page image' + (imgs === 1 ? '' : 's') + (pdfs ? ' and ' + pdfs + ' PDF file' + (pdfs === 1 ? '' : 's') + ' (their pages are counted after the upload)' : '') +
          '. Reading costs about Rs ' + lim.per_page_low_inr + ' a page for a short handwritten page and up to Rs ' + lim.per_page_high_inr + ' for a full page of small print, by the pipeline\'s own estimate; the real bill has run 1.5 to 2 times higher. You see the estimate for these files before anything is read.';
      }
    }
    ['dragenter', 'dragover'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('over'); }); });
    ['dragleave', 'drop'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('over'); }); });
    drop.addEventListener('drop', function (e) { addFiles(e.dataTransfer.files); });
    input.addEventListener('change', function () { addFiles(input.files); input.value = ''; });

    var label = h('input', { type: 'text', id: 'f-label', value: f.label, maxlength: '80', placeholder: 'For example: Notice, 3 pages', oninput: function () { f.label = label.value; } });
    var lang = h('select', { id: 'f-lang', onchange: function () { f.language = lang.value; } }, caps.languages.map(function (l) { return h('option', { value: l, selected: l === f.language }, l); }));
    function radio(value, text, hint) { return h('label', { class: 'check' }, h('input', { type: 'radio', name: 'ptype', value: value, checked: f.page_type === value, onchange: function () { f.page_type = value; } }), h('span', null, text, h('br'), h('span', { class: 'small' }, hint))); }
    var known = h('textarea', { id: 'f-known', placeholder: 'One name per line', oninput: function () { f.known = known.value; } }); known.value = f.known;
    var group = h('input', { type: 'checkbox', id: 'f-group', checked: f.grouped, onchange: function () { f.grouped = group.checked; } });
    var groupRow = h('label', { class: 'check', hidden: true }, group, h('span', null, 'These images are the pages of one document, in the order shown. Their English is joined, and a sentence that runs over a page break is kept whole.'));
    var gate = h('input', { type: 'checkbox', id: 'f-gate', checked: f.gate, onchange: function () { f.gate = gate.checked; } });

    go.addEventListener('click', function () {
      if (!S.files.length) return toast('Choose at least one file.');
      if (!gate.checked) return toast('Tick the confirmation first.');
      go.disabled = demoBtn.disabled = true; var made = null;
      api('POST', '/jobs', { label: f.label, language: f.language, page_type: f.page_type, grouped: f.grouped, known_names: f.known.split('\n').map(norm).filter(Boolean), gate_confirmed: true }).then(function (d) {
        made = d.job.id;
        return S.files.reduce(function (p, file, i) {
          return p.then(function () { msg.textContent = 'Uploading ' + (i + 1) + ' of ' + S.files.length + ': ' + file.name; return api('PUT', '/jobs/' + made + '/files?name=' + encodeURIComponent(file.name), file); });
        }, Promise.resolve());
      }).then(function () { S.files = []; location.hash = '#/job/' + made; }).catch(function (e) {
        msg.textContent = e.message; go.disabled = demoBtn.disabled = false;
        if (made) api('DELETE', '/jobs/' + made).catch(function () {});
      });
    });
    demoBtn.addEventListener('click', function () {
      go.disabled = demoBtn.disabled = true;
      api('POST', '/demo', {}).then(function (d) { location.hash = '#/job/' + d.job.id; }).catch(function (e) { msg.textContent = e.message; go.disabled = demoBtn.disabled = false; });
    });
    drawList();
    return h('div', { class: 'stack' },
      h('div', null, h('h1', null, 'Read a document'), h('p', { class: 'sub' }, 'Upload photos or a PDF of Assamese, Kannada or Hindi court, police or government papers. You get the English beside the page, the places to read first, and a Word file. Every page still needs a person who reads the language.')),
      !caps.real && !caps.stub ? banner('warn', 'Reading real pages is switched off: this server has no model key. The demo still works.') : null,
      caps.stub ? banner('warn', 'This server is in test mode: readings are invented text, no model is called.') : null,
      h('div', { class: 'grid2' },
        h('div', { class: 'stack' }, h('div', { class: 'card' }, drop, list, h('div', { class: 'field' }), groupRow, cost)),
        h('div', { class: 'card' },
          field('Name for this job (optional)', 'f-label', label),
          field('Language of the papers', 'f-lang', lang, 'Most testing so far was on Assamese.'),
          h('div', { class: 'field' }, h('label', null, 'The pages are'), radio('typed', 'Typed or printed', 'Can reach green when everything checks out.'), radio('handwritten', 'Handwritten', 'Never green: a person must read every date, number and name.'),
            radio('unsure', 'Not sure', 'Treated as handwritten, the stricter way.')),
          h('details', null, h('summary', null, 'Names you already know are right (optional)'), h('div', { class: 'field' }, known, h('span', { class: 'small' }, 'A name in the reading that is close to one of these but not the same is flagged. Nothing is ever changed.'))),
          h('label', { class: 'check' }, gate, h('span', null, me.gate_text)),
          h('p', { class: 'small' }, 'Pages are sent to Google\'s Gemini service for reading. Your files are deleted ', Math.round(lim.retention_hours), ' hours after the job ends, or when you delete them.'),
          h('div', { class: 'row' }, go, demoBtn), msg)));
  }

  /* ---------- one job ---------- */
  function jobView(id, target) {
    var box = h('div', { class: 'stack' }, h('p', { class: 'small' }, h('span', { class: 'spinner' }), 'Loading…'));
    function load() {
      return api('GET', '/jobs/' + id).then(function (d) {
        var st = d.job.status;
        if (st === 'done' || st === 'failed' || st === 'cancelled') return api('GET', '/jobs/' + id + '/result').then(function (r) { paint(r.job, d.progress, r.result, r.caps); });
        paint(d.job, d.progress, null);
        if (st === 'queued' || st === 'running') S.timer = setTimeout(load, 1500);
      }).catch(function (e) { put(box, [h('h1', null, 'Job not found'), banner('error', e.message), h('a', { class: 'btn', href: '#/history' }, 'Back to History')]); });
    }
    function paint(job, prog, result, caps) {
      var p = { draft: draftPanel, queued: progressPanel, running: progressPanel }[job.status];
      if (p) return put(box, p(job, prog, load));
      if (job.status === 'done' && result) return put(box, resultPanel(job, result, caps, target, load));
      put(box, failedPanel(job, load));
    }
    load();
    return box;
  }
  function head(job, extra) {
    return h('div', { class: 'row between' }, h('div', null, h('h1', null, job.label || 'Untitled job'),
      h('p', { class: 'sub' }, job.language, ' · ', job.page_type === 'typed' ? 'typed' : (job.page_type === 'unsure' ? 'not sure (read as handwritten)' : 'handwritten'), ' · ', job.n_pages, ' page', job.n_pages === 1 ? '' : 's', job.demo ? ' · demo with invented text' : '')), extra);
  }
  function delBtn(job, then) {
    return h('button', { class: 'btn danger small', type: 'button', onclick: function () {
      if (!confirm('Delete this job and all its files now? This cannot be undone.')) return;
      api('DELETE', '/jobs/' + job.id).then(function () { location.hash = '#/history'; }).catch(function (e) { toast(e.message); });
    } }, 'Delete job');
  }
  function draftPanel(job, prog, reload) {
    var msg = h('p', { class: 'small', role: 'alert' }), me = S.me;
    var start = h('button', { class: 'btn primary', type: 'button', onclick: function () {
      start.disabled = true;
      api('POST', '/jobs/' + job.id + '/start', {}).then(reload).catch(function (e) { msg.textContent = e.message; start.disabled = false; });
    } }, 'Start reading');
    return [head(job), h('div', { class: 'card' }, h('h2', null, 'Ready to read'),
      h('div', { class: 'scroll' }, h('table', { class: 'tbl' }, h('thead', null, h('tr', null, ['File', 'Pages', 'Size'].map(function (x) { return h('th', null, x); }))),
        h('tbody', null, job.files.map(function (f) { return h('tr', null, h('td', null, f.name), h('td', null, f.pages), h('td', null, bytes(f.size))); })))),
      h('p', null, h('b', null, job.n_pages, ' page', job.n_pages === 1 ? '' : 's'), ' · estimated ', h('b', null, inr(job.estimate.low) + ' to ' + inr(job.estimate.high)), ' by the pipeline\'s own figures: the low end if the pages are short, the high end if they are full of small print. The real bill has run 1.5 to 2 times higher.'),
      h('p', { class: 'small' }, 'This job may spend up to ', inr(Math.min(me.room.allowed, job.n_pages * 14 + 4)), ' by that estimate (the most you may start now is ', inr(me.room.allowed), '). The reading stops by itself before it passes that, and you can continue it.'),
      h('div', { class: 'row' }, start, delBtn(job)), msg)];
  }
  function progressPanel(job, prog, reload) {
    var bar = h('i'); bar.style.width = ((prog && prog.percent) || 0) + '%';
    var stop = h('button', { class: 'btn small', type: 'button', onclick: function () { stop.disabled = true; api('POST', '/jobs/' + job.id + '/cancel', {}).then(reload).catch(function (e) { toast(e.message); }); } }, 'Stop');
    return [head(job), h('div', { class: 'card' }, h('p', null, h('span', { class: 'spinner' }), h('b', null, job.status === 'queued' ? 'Waiting for its turn' : (prog && prog.stage) || 'Starting')),
      h('div', { class: 'bar', role: 'progressbar', 'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-valuenow': String((prog && prog.percent) || 0) }, bar),
      h('p', { class: 'small' }, prog ? prog.calls + ' reading step' + (prog.calls === 1 ? '' : 's') + ' done · about ' + inr(prog.estimated_cost_inr) + ' so far (an estimate)' : ''),
      h('p', { class: 'small' }, 'You can leave this page. The reading carries on, and the job is under History.'), h('div', { class: 'row' }, stop))];
  }
  function failedPanel(job, reload) {
    var retry = h('button', { class: 'btn primary', type: 'button', onclick: function () { retry.disabled = true; api('POST', '/jobs/' + job.id + '/resume', {}).then(reload).catch(function (e) { toast(e.message); retry.disabled = false; }); } }, 'Retry');
    return [head(job), banner(job.status === 'cancelled' ? 'warn' : 'error', job.status === 'cancelled' ? 'This job was stopped. Readings that finished are kept and are not paid for again if you retry.' : (job.error || 'The reading did not finish.')),
      h('div', { class: 'row' }, retry, delBtn(job))];
  }

  /* ---------- the result ---------- */
  function resultPanel(job, res, caps, target, reload) {
    var tabsData = [];
    res.documents.forEach(function (d) { if (d.light) tabsData.push({ id: d.id, kind: 'doc', light: d.light, label: res.documents.length > 1 ? d.display : 'Whole document', data: d }); });
    res.pages.forEach(function (p) { tabsData.push({ id: p.id, kind: 'page', light: p.light, label: tabsData.some(function (t) { return t.kind === 'doc'; }) || res.pages.length > 1 ? 'Page ' + p.n + (res.documents.length > 1 ? ' of ' + p.doc : '') : 'Page 1', data: p }); });
    var cur = tabsData.filter(function (t) { return t.id === target; })[0] || tabsData[0];
    var panel = h('div', { class: 'stack' }), tabsEl = h('div', { class: 'tabs', role: 'tablist' });
    function drawTabs() {
      put(tabsEl, tabsData.map(function (t) {
        return h('button', { class: 'tab', role: 'tab', type: 'button', 'aria-selected': t === cur ? 'true' : 'false', onclick: function () { cur = t; history.replaceState(null, '', '#/job/' + job.id + '/' + t.id); drawTabs(); drawPanel(); } },
          h('span', { class: 'dot ' + t.light }), t.label);
      }));
    }
    function drawPanel() { put(panel, cur ? (cur.kind === 'doc' ? docPanel(job, res, cur.data, caps, tabsData, function (id) { cur = tabsData.filter(function (t) { return t.id === id; })[0]; history.replaceState(null, '', '#/job/' + job.id + '/' + id); drawTabs(); drawPanel(); window.scrollTo(0, 0); }) : pagePanel(job, res, cur.data, caps)) : h('p', null, 'There is no result.')); }
    drawTabs(); drawPanel();
    var del = new Date(job.delete_after);
    return h('div', { class: 'stack' }, head(job, h('div', { class: 'row' }, pill(res.light), h('span', { class: 'stamp' }, STAMP))),
      job.stopped_by_budget ? h('div', { class: 'banner warn' }, h('p', null, 'The reading stopped early at its budget. Some pages may be missing or red.'),
        h('button', { class: 'btn small', type: 'button', onclick: function () { api('POST', '/jobs/' + job.id + '/resume', {}).then(reload).catch(function (e) { toast(e.message); }); } }, 'Continue with more budget')) : null,
      job.sense_unrun ? h('div', { class: 'banner warn' }, h('p', null, 'The sense check did not run for part of this job, so nothing has looked for sentences that do not make sense there. You can try it again; readings that finished are not paid for twice.'),
        h('button', { class: 'btn small', type: 'button', onclick: function () { api('POST', '/jobs/' + job.id + '/resume', {}).then(reload).catch(function (e) { toast(e.message); }); } }, 'Try the sense check again')) : null,
      h('p', { class: 'small' }, 'The light is a reading order, never permission to skip a page: read the red pages first, then amber. A handwritten page is never green. Files are deleted ', isNaN(del) ? '' : 'on ' + fmt(job.delete_after), '. ', h('a', { href: '#/history' }, 'History'), ' · ', delBtn(job)),
      tabsEl, panel);
  }
  function reasonsBlock(reasons, light, task) {
    if (!reasons || !reasons.length) return h('p', { class: 'small' }, task || '');
    return h('details', null, h('summary', null, 'Why ' + light + ': ' + reasons.length + ' reason' + (reasons.length === 1 ? '' : 's')),
      h('ul', { class: 'reasons' }, reasons.map(function (r) { return h('li', { class: r.level }, (r.level === 'red' ? 'Red: ' : '') + r.text); })), task ? h('p', { class: 'small' }, task) : null);
  }
  function firstBox(items, getRoot) {
    if (!items || !items.length) return h('div', { class: 'banner' }, h('p', null, 'Nothing was flagged on this page. A person still reads all of it.'));
    var shown = 6, list = h('ol'), more = h('button', { class: 'btn small more', type: 'button' }, '');
    function draw() {
      clear(list);
      items.slice(0, shown).forEach(function (it) {
        list.appendChild(h('li', { class: 'sev-' + it.sev }, h('button', { class: 't', type: 'button', onclick: function () { flashText(getRoot(), it.find); } }, it.title), h('span', { class: 'd' }, it.detail)));
      });
      more.hidden = items.length <= 6; more.textContent = shown >= items.length ? 'Show fewer' : 'Show all ' + items.length;
    }
    more.addEventListener('click', function () { shown = shown >= items.length ? 6 : items.length; draw(); });
    draw();
    return h('div', { class: 'first' }, h('h2', null, 'Read these first'), h('p', { class: 'small' }, 'Each line is a place where the readings disagree, something is crossed out or stamped on the page, the reader was unsure, or the English may not make sense. Click one to find it in the English. This is a reading order, not a verdict.'), list, more);
  }
  function actions(job, res, item, caps, isPage) {
    var r = item.report || {};
    return h('div', { class: 'row' },
      caps && caps.word ? h('a', { class: 'btn primary', href: '/api/jobs/' + job.id + '/word/' + item.id, download: '' }, 'Word file (English)') : null,
      r.html ? h('a', { class: 'btn', href: '/api/jobs/' + job.id + '/report/' + item.id + (r.pdf ? '?format=pdf' : ''), target: '_blank', rel: 'noopener' }, r.pdf ? 'Full report (PDF)' : 'Full report') : null,
      isPage && item.marksheet ? h('a', { class: 'btn', href: '/api/jobs/' + job.id + '/marksheet/' + item.id, target: '_blank', rel: 'noopener' }, 'Marking sheet') : null);
  }
  function reviewedRow(job, item, isDoc) {
    var rv = (job.reviews || {})[item.id], info = h('span', { class: 'small' });
    var cb = h('input', { type: 'checkbox', id: 'rv-' + item.id, checked: !!rv });
    function say(r) { info.textContent = r ? 'Marked as read by ' + r.by + ', ' + fmt(r.at) + '. This records who looked; it does not say the page is correct.' : ''; }
    cb.addEventListener('change', function () {
      api('POST', '/jobs/' + job.id + '/review', { target: item.id, read: cb.checked }).then(function (d) { job.reviews = d.reviews; say(d.reviews[item.id]); }).catch(function (e) { toast(e.message); cb.checked = !cb.checked; });
    });
    say(rv);
    return h('div', { class: 'reviewed' }, cb, h('label', { for: 'rv-' + item.id, class: 'check' }, isDoc ? 'I have read the whole translation against the original pages.' : 'I have read this page against the original.'), info);
  }
  function glossaryTable(rows) {
    if (!rows || !rows.length) return null;
    return h('details', null, h('summary', null, 'Glossary notes (' + rows.length + ')'), h('p', { class: 'small' }, 'Words with a settled legal meaning. Notes only: they never change the translation.'),
      h('div', { class: 'scroll' }, h('table', { class: 'tbl' }, h('thead', null, h('tr', null, ['Word as read', 'Normally means', 'Note'].map(function (x) { return h('th', null, x); }))),
        h('tbody', null, rows.map(function (g) { return h('tr', null, h('td', { class: 'as', lang: 'as' }, g.word), h('td', null, g.english), h('td', null, g.note)); })))));
  }
  function mustTable(rows) {
    if (!rows || !rows.length) return null;
    return h('details', null, h('summary', null, 'Must-check list (' + rows.length + ')'), h('p', { class: 'small' }, 'Dates, amounts, numbers, names and land units found in the readings. A person confirms each against the page, including the ones the readings agree on.'),
      h('div', { class: 'scroll' }, h('table', { class: 'tbl' }, h('thead', null, h('tr', null, ['Kind', 'Value', 'Readings'].map(function (x) { return h('th', null, x); }))),
        h('tbody', null, rows.map(function (m) { return h('tr', null, h('td', null, cap(m.type)), h('td', null, m.status === 'DISAGREE' ? (m.a || 'not found') + '  |  ' + (m.b || 'not found') : String(m.a)), h('td', null, m.status === 'DISAGREE' ? 'disagree' : 'agree: still confirm')); })))));
  }
  function pagePanel(job, res, p, caps) {
    var quotes = p.read_first.filter(function (i) { return i.kind === 'sense'; }).map(function (i) { return i.quote; });
    var eng = englishBlock(p.paras, quotes);
    var img = p.image ? h('figure', { class: 'scan' }, h('a', { href: '/api/jobs/' + job.id + '/image/' + p.id, target: '_blank', rel: 'noopener' }, h('img', { src: '/api/jobs/' + job.id + '/image/' + p.id, alt: 'The page as it was read: ' + p.label })),
      h('figcaption', null, p.label, p.orientation === 'turned' ? ' (turned upright before reading)' : '', ' · click for the full picture')) : h('div', { class: 'noimg' }, 'No picture of this page was kept.');
    return h('div', { class: 'stack' },
      h('div', { class: 'row between' }, h('div', { class: 'row' }, pill(p.light), h('b', null, p.label), p.agreement != null ? h('span', { class: 'small' }, 'the two readings agree on ' + p.agreement + '% of the letters') : null), actions(job, res, p, caps, true)),
      reasonsBlock(p.reasons, p.light, p.person_task),
      (p.notices || []).map(function (n) { return banner('warn', n); }),
      firstBox(p.read_first, function () { return eng; }),
      h('div', { class: 'grid2' }, img, h('div', { class: 'stack' }, h('div', null, h('h2', null, 'English to read'), eng, legend()))),
      h('div', { class: 'card' }, glossaryTable(p.glossary), mustTable(p.must_check),
        h('details', null, h('summary', null, 'What each reading said (' + p.readings.length + ')'), h('p', { class: 'small' }, 'The English above is the first reading, with every value the readings disagree on shown as both. These are the readings it came from.'),
          h('div', { class: 'stack' }, p.readings.map(function (r) { return h('div', null, h('h3', null, r.name), h('pre', { class: 'reading' }, r.english || '(nothing)')); })))),
      reviewedRow(job, p, false));
  }
  function docPanel(job, res, d, caps, tabsData, goto) {
    var quotes = d.read_first.filter(function (i) { return i.kind === 'sense'; }).map(function (i) { return i.quote; });
    var eng = englishBlock(d.paras, quotes);
    var thumbs = d.pages.map(function (pid) {
      var p = res.pages.filter(function (x) { return x.id === pid; })[0];
      return p ? h('button', { class: 'tab', type: 'button', onclick: function () { goto(pid); } }, h('span', { class: 'dot ' + p.light }), 'Page ' + p.n + ' ›') : null;
    });
    var names = d.names && (d.names.only_in_view_1.length || d.names.only_in_view_2.length) ? h('details', null, h('summary', null, 'Names in only one of the two translations'), h('p', { class: 'small' }, 'Check each against the original-script word.'),
      h('div', { class: 'grid2 even' }, h('div', null, h('h3', null, 'Translation 1 only'), h('ul', null, d.names.only_in_view_1.map(function (x) { return h('li', null, x); }))), h('div', null, h('h3', null, 'Translation 2 only'), h('ul', null, d.names.only_in_view_2.map(function (x) { return h('li', null, x); }))))) : null;
    var joins = d.joins && d.joins.length ? h('details', null, h('summary', null, 'How the pages were joined (' + d.joins.length + ')'), h('p', { class: 'small' }, 'Check that nothing was joined by mistake.'),
      h('div', { class: 'scroll' }, h('table', { class: 'tbl' }, h('thead', null, h('tr', null, ['Page', 'What was done', 'Previous page ended', 'This page starts'].map(function (x) { return h('th', null, x); }))),
        h('tbody', null, d.joins.map(function (j) { return h('tr', null, h('td', null, j.page), h('td', null, j.action), h('td', { class: 'as', lang: 'as' }, j.previous_page_ends || ''), h('td', { class: 'as', lang: 'as' }, j.this_page_starts || j.line || '')); }))))) : null;
    var refs = d.references && Object.keys(d.references).length ? h('details', null, h('summary', null, 'Clause, rule, section and order numbers'), (d.reference_flags || []).length ? h('ul', null, d.reference_flags.map(function (f) { return h('li', null, f); })) : null,
      h('p', null, Object.keys(d.references).map(function (k) { return k + ' ×' + d.references[k]; }).join('; '))) : null;
    var second = d.english_2 ? h('details', null, h('summary', null, 'The second translation, for comparison'), h('p', { class: 'small' }, 'Translation 1 is the one to read: it was fixed in advance and the tool never chooses between the two.'), englishBlock(d.english_2 ? d.english_2.split(/\n\s*\n/).map(norm) : [], [])) : null;
    return h('div', { class: 'stack' },
      h('div', { class: 'row between' }, h('div', { class: 'row' }, pill(d.light), h('b', null, d.display), h('span', { class: 'small' }, d.pages.length + ' pages joined')), actions(job, res, d, caps, false)),
      reasonsBlock(d.reasons, d.light, d.person_task),
      (d.notices || []).map(function (n) { return banner('warn', n); }),
      firstBox(d.read_first, function () { return eng; }),
      h('div', null, h('h2', null, 'English to read'), h('p', { class: 'small' }, d.mode ? cap(d.mode) + '.' : ''), eng, legend()),
      h('div', { class: 'row' }, h('span', { class: 'small' }, 'Check the pages against the English:'), thumbs),
      h('div', { class: 'card' }, names, joins, refs, glossaryTable(d.glossary), mustTable(d.must_check), second),
      reviewedRow(job, { id: d.id }, true));
  }

  /* ---------- history, glossary, usage ---------- */
  function historyView() {
    var box = h('div', null, h('p', { class: 'small' }, 'Loading…'));
    api('GET', '/jobs').then(function (d) {
      if (!d.jobs.length) return put(box, h('div', { class: 'empty' }, 'Nothing here yet. Start with ', h('a', { href: '#/new' }, 'a new document'), '.'));
      put(box, h('div', { class: 'card scroll' }, h('table', { class: 'tbl' }, h('thead', null, h('tr', null, ['Job', 'Started', 'Pages', 'Lights', 'Status', 'Estimated cost', 'Read by a person', ''].map(function (x) { return h('th', null, x); }))),
        h('tbody', null, d.jobs.map(function (j) {
          var lc = j.light_counts || {}, n = Object.keys(j.reviews || {}).length;
          return h('tr', null, h('td', null, h('a', { href: '#/job/' + j.id }, j.label || 'Untitled'), j.demo ? h('span', { class: 'small' }, ' (demo)') : null), h('td', null, fmt(j.created)), h('td', null, j.n_pages),
            h('td', null, ['red', 'amber', 'green'].map(function (k) { return lc[k] ? h('span', { class: 'pill ' + k }, lc[k] + ' ' + k) : null; })),
            h('td', null, j.status === 'done' ? 'Done' : cap(j.status)), h('td', null, j.demo ? 'free' : inr(j.spent_inr)), h('td', null, n ? n + ' marked' : '–'),
            h('td', null, h('button', { class: 'btn danger small', type: 'button', disabled: j.status === 'queued' || j.status === 'running', onclick: function () {
              if (!confirm('Delete this job and all its files now?')) return;
              api('DELETE', '/jobs/' + j.id).then(function () { render(); }).catch(function (e) { toast(e.message); });
            } }, 'Delete')));
        })))), h('p', { class: 'small' }, 'Each job and its files are deleted automatically ', Math.round(S.me.limits.retention_hours), ' hours after it finishes.'));
    }).catch(function (e) { put(box, banner('error', e.message)); });
    return h('div', { class: 'stack' }, h('div', null, h('h1', null, 'History'), h('p', { class: 'sub' }, 'Your jobs, with the lights each page got and who marked what as read.')), box);
  }
  function glossaryView() {
    var q = h('input', { type: 'text', id: 'gq', placeholder: 'Word or English', 'aria-label': 'Search the glossary' }), kind = h('select', { id: 'gk', 'aria-label': 'Type' }), body = h('tbody'), count = h('p', { class: 'small' });
    function draw() {
      var rows = S.glossary.rows, s = norm(q.value).toLowerCase(), k = kind.value;
      var hit = rows.filter(function (r) { return (!k || r.kind === k) && (!s || (r.word + ' ' + r.english + ' ' + r.note + ' ' + r.variants.join(' ')).toLowerCase().indexOf(s) >= 0); });
      count.textContent = hit.length + ' of ' + rows.length + ' entries';
      put(body, hit.map(function (r) {
        return h('tr', null, h('td', { class: 'as', lang: 'as' }, r.word), h('td', null, r.english), h('td', null, h('span', { class: 'kind ' + r.kind }, r.kind)),
          h('td', null, r.note, r.avoid.length ? h('div', { class: 'small' }, 'Avoid: ' + r.avoid.join(', ')) : null, h('div', { class: 'small' }, r.group + ' · ' + r.id)));
      }));
    }
    var out = h('div', { class: 'stack' }, h('div', null, h('h1', null, 'Term glossary'), h('p', { class: 'sub' }, 'Words with a settled legal meaning. The reading pipeline shows a note beside the English when it meets one. A note never changes the translation.')),
      h('div', { class: 'row' }, h('div', { class: 'field' }, h('label', { for: 'gq' }, 'Search'), q), h('div', { class: 'field' }, h('label', { for: 'gk' }, 'Type'), kind)), count,
      h('div', { class: 'card scroll' }, h('table', { class: 'tbl' }, h('thead', null, h('tr', null, ['Word', 'English', 'Type', 'Note'].map(function (x) { return h('th', null, x); }))), body)), h('p', { class: 'small', id: 'gnote' }));
    (S.glossary ? Promise.resolve(S.glossary) : api('GET', '/glossary')).then(function (d) {
      S.glossary = d;
      var kinds = {}; d.rows.forEach(function (r) { kinds[r.kind] = 1; });
      put(kind, [h('option', { value: '' }, 'All')].concat(Object.keys(kinds).sort().map(function (x) { return h('option', { value: x }, x); })));
      q.addEventListener('input', draw); kind.addEventListener('change', draw);
      out.querySelector('#gnote').textContent = d.note; draw();
    }).catch(function (e) { count.textContent = e.message; });
    return out;
  }
  function usageView() {
    var box = h('div', null, h('p', { class: 'small' }, 'Loading…'));
    api('GET', '/usage').then(function (d) {
      function stat(label, value, sub) { return h('div', { class: 'card' }, h('div', { class: 'small' }, label), h('div', { class: 'stat' }, h('b', null, value)), h('div', { class: 'small' }, sub)); }
      put(box, h('div', { class: 'stack' }, h('div', { class: 'grid2 even' }, stat('Today (you)', inr(d.today_inr), 'limit ' + inr(d.caps.daily) + ' a day'), stat('This month (you)', inr(d.month_inr), d.pages_month + ' pages read')),
        h('div', { class: 'grid2 even' }, stat('This month (whole site)', inr(d.site_month_inr), 'limit ' + inr(d.caps.monthly)), stat('You may start now', inr(d.room.allowed), 'one job at most ' + inr(d.caps.job))),
        h('p', { class: 'small' }, d.note),
        h('div', { class: 'card scroll' }, h('table', { class: 'tbl' }, h('thead', null, h('tr', null, ['Job', 'Started', 'Pages', 'Status', 'Estimated cost'].map(function (x) { return h('th', null, x); }))),
          h('tbody', null, d.jobs.map(function (j) { return h('tr', null, h('td', null, h('a', { href: '#/job/' + j.id }, j.label || 'Untitled')), h('td', null, fmt(j.created)), h('td', null, j.pages), h('td', null, cap(j.status)), h('td', null, j.demo ? 'free' : inr(j.spent_inr))); }))))));
    }).catch(function (e) { put(box, banner('error', e.message)); });
    return h('div', { class: 'stack' }, h('div', null, h('h1', null, 'Usage'), h('p', { class: 'sub' }, 'What reading has cost, by the pipeline\'s own estimate, against the limits set for this site.')), box);
  }

  boot();
})();
