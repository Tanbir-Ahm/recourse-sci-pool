"""Print one marking sheet (a single self-contained HTML file) for a page, from two readers' outputs.

  python marksheet.py --page-id A01 --group A --image A01.png --a RUN/A01/gemini-4-argon/run1.txt --a-name gemini-4-argon \
                      --b RUN/A01/gemini-3.7-flash/run1.txt --b-name gemini-3.7-flash --out A01_marksheet.html
  python marksheet.py --selftest

The sheet shows the page image beside: the check list (every disagreement first, then every date, amount, number, unit,
section number and name the readers agree on, which still need confirming), the lines where the readings differ, both English
drafts, and the plan's error-logging table (section 8 of OCR_TRANSLATION_TEST_PLAN.md) with Copy-as-CSV.
The file contains the page image and the text, so it is CASE DATA: keep it outside the repository.
Nothing is loaded from the internet. The sheet never marks anything as correct; a person closes every row.
"""
import argparse, base64, html, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marking sheet __PID__</title>
<style>
:root{--bg:#f4f5f6;--fg:#17212b;--muted:#5b6670;--line:#c9ced3;--card:#fff;--red:#a3271f;--redbg:#f8e0dd;--amber:#8a5a00;--amberbg:#f8ecd0;--green:#17663a}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,"Segoe UI","Noto Sans","Noto Sans Bengali","Noto Sans Kannada","Noto Sans Devanagari",sans-serif;padding:16px}
h1{font-size:1.3rem;margin:0 0 4px} h2{font-size:1.05rem;margin:22px 0 8px} .muted{color:var(--muted);font-size:.88rem}
.banner{background:var(--amberbg);border:1px solid var(--line);border-radius:6px;padding:8px 12px;margin:10px 0;font-size:.9rem}
.wrap{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:16px;align-items:start}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px;min-width:0}
.sticky{position:sticky;top:8px} img{width:100%;height:auto;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:.88rem} th,td{border:1px solid var(--line);padding:5px 7px;vertical-align:top;text-align:left}
th{background:#eef0f2;font-weight:600;white-space:nowrap} .scroll{overflow-x:auto}
tr.dis td:first-child{background:var(--redbg);color:var(--red);font-weight:600} tr.conf td:first-child{background:var(--amberbg);color:var(--amber)}
input,select,button,textarea{font:inherit;font-size:.86rem;padding:3px 5px;max-width:100%} textarea{width:100%;min-height:3.2rem}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px} .txt{white-space:pre-wrap;line-height:1.55}
@media (max-width:860px){.wrap,.two{grid-template-columns:minmax(0,1fr)}.sticky{position:static}}
</style></head><body>
<h1>Marking sheet: page __PID__ (group __GROUP__)</h1>
<div class="muted">Reader A: __ANAME__ &middot; Reader B: __BNAME__</div>
<div class="banner"><b>Machine draft, not a certified translation.</b> Close every row below against the page image. A row left open is not checked. This file holds the page and its text: keep it private.</div>
<div class="wrap">
<div class="card sticky" id="imgbox">__IMAGE__</div>
<div>
<div class="card"><h2 style="margin-top:0">1. Check list</h2><div class="muted" id="sum"></div>
<div class="scroll"><table id="items"></table></div></div>
<div class="card"><h2 style="margin-top:0">2. Lines where the two readings differ</h2><div class="scroll"><table id="diffs"></table></div></div>
<div class="card"><h2 style="margin-top:0">3. The two English drafts</h2><div class="two"><div><b>__ANAME__</b><div class="txt" id="enA"></div></div><div><b>__BNAME__</b><div class="txt" id="enB"></div></div></div></div>
<div class="card"><h2 style="margin-top:0">4. Errors found (one row per error)</h2>
<div class="muted">Critical = changes what the evidence says. Moderate = awkward but the meaning survives. Minor = the rest. &ldquo;Warned?&rdquo; = did the tool flag that spot (<code>[unclear]</code> or a disagreement).</div>
<div class="scroll"><table id="errs"><thead><tr><th>Page</th><th>Tool</th><th>Group</th><th>Line</th><th>What the tool said</th><th>What it should say</th><th>Type</th><th>Severity</th><th>Warned?</th><th></th></tr></thead><tbody></tbody></table></div>
<p><button id="add">Add row</button> <button id="copy">Copy as CSV</button> <button id="dl">Download CSV</button></p>
<h3>Page summary</h3><p>Gist correct: <select id="gist"><option></option><option>yes</option><option>no</option></select> &nbsp; Critical errors: <input id="ncrit" size="3"> &nbsp; Silent critical errors: <input id="nsil" size="3"> &nbsp; Reviewer minutes: <input id="mins" size="4"></p></div>
</div></div>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s), esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
$('#sum').textContent=D.summary.disagreements+' disagreements to resolve, '+D.summary.to_confirm+' items to confirm, '+D.summary.differing_lines+' differing lines'+(D.summary.possible_dropped_text?'. One reading is much shorter than the other: check for dropped text.':'.');
let h='<tr><th>Status</th><th>Type</th><th>Reader A</th><th>Reader B</th><th>Line (A/B)</th><th>Value on the page</th><th>Result</th></tr>';
D.items.forEach(i=>{h+='<tr class="'+(i.status==='DISAGREE'?'dis':'conf')+'"><td>'+i.status+'</td><td>'+esc(i.type)+'</td><td>'+esc(i.A)+'</td><td>'+esc(i.B)+'</td><td>'+esc(i.line_A)+' / '+esc(i.line_B)+'</td><td><input size="14"></td><td><select><option></option><option>right in both</option><option>A wrong</option><option>B wrong</option><option>both wrong</option><option>not on the page</option></select></td></tr>';});
$('#items').innerHTML=h;
h='<tr><th>Line A</th><th>Reader A</th><th>Line B</th><th>Reader B</th><th>Similarity</th></tr>';
D.line_diffs.forEach(d=>{h+='<tr><td>'+esc(d.line_A)+'</td><td>'+esc(d.A)+'</td><td>'+esc(d.line_B)+'</td><td>'+esc(d.B)+'</td><td>'+d.similarity+'</td></tr>';});
$('#diffs').innerHTML=h;
$('#enA').textContent=D.enA; $('#enB').textContent=D.enB;
const TYPES=['name','number','date','amount','place','negation','who-did-what','section','omitted','invented'];
function addRow(){const tr=document.createElement('tr');
 tr.innerHTML='<td>'+esc(D.pid)+'</td><td><select>'+[D.aname,D.bname].map(x=>'<option>'+esc(x)+'</option>').join('')+'</select></td><td>'+esc(D.group)+'</td><td><input size="5"></td><td><textarea></textarea></td><td><textarea></textarea></td><td><select>'+TYPES.map(x=>'<option>'+x+'</option>').join('')+'</select></td><td><select><option>Critical</option><option>Moderate</option><option>Minor</option></select></td><td><select><option>no</option><option>yes</option></select></td><td><button>remove</button></td>';
 tr.querySelector('button').onclick=()=>tr.remove(); $('#errs tbody').appendChild(tr);}
$('#add').onclick=addRow;
function csv(){const q=v=>'"'+String(v).replace(/"/g,'""')+'"'; const rows=[['Page','Tool','Group','Line','Tool said','Should say','Type','Severity','Warned']];
 document.querySelectorAll('#errs tbody tr').forEach(tr=>{rows.push([...tr.children].slice(0,9).map(td=>{const f=td.querySelector('input,select,textarea');return f?f.value:td.textContent;}));});
 rows.push([]); rows.push(['Check list','Status','Type','Reader A','Reader B','Line A/B','Value on the page','Result']);
 document.querySelectorAll('#items tr.dis, #items tr.conf').forEach(tr=>{const c=[...tr.children]; rows.push(['',c[0].textContent,c[1].textContent,c[2].textContent,c[3].textContent,c[4].textContent,c[5].querySelector('input').value,c[6].querySelector('select').value]);});
 rows.push([]); rows.push(['Page summary','gist correct',$('#gist').value,'critical errors',$('#ncrit').value,'silent critical',$('#nsil').value,'minutes',$('#mins').value]);
 return rows.map(r=>r.map(q).join(',')).join('\\n');}
$('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(csv());$('#copy').textContent='Copied';}catch(e){window.prompt('Copy this:',csv());}};
$('#dl').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv()],{type:'text/csv'}));a.download=D.pid+'_marks.csv';a.click();};
</script></body></html>"""


def build(page_id, group, a_text, b_text, a_name, b_name, image_path=None):
    cmp_ = checker.compare(a_text, b_text)
    def english(t):
        return t.split("TRANSLATION", 1)[1].lstrip("*:# \n-") if "TRANSLATION" in t else "(no translation in this output)"
    if image_path:
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
        img = f'<img alt="Page {html.escape(page_id)}" src="data:image/{mime};base64,{base64.b64encode(open(image_path, "rb").read()).decode()}">'
    else:
        img = '<div class="muted">No page image was given. Open the original beside this sheet.</div>'
    data = dict(cmp_, pid=page_id, group=group, aname=a_name, bname=b_name, enA=english(a_text), enB=english(b_text))
    page = PAGE
    for k, v in {"__PID__": html.escape(page_id), "__GROUP__": html.escape(group), "__ANAME__": html.escape(a_name), "__BNAME__": html.escape(b_name), "__IMAGE__": img}.items():
        page = page.replace(k, v)
    return page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))


def selftest():
    a = "TRANSCRIPTION\n1. Order dated 15-02-2020; phone 98599-79979.\n2. Closing line.\nTRANSLATION\nThe order is dated 15 February 2020. <script>alert(1)</script>"
    b = "TRANSCRIPTION\n1. Order dated 15-02-2020; phone 98659-79979.\nTRANSLATION\nOrder of 15 February 2020."
    d = tempfile.mkdtemp(); img = os.path.join(d, "x.png"); open(img, "wb").write(b"\x89PNG fake")
    out = build("T01", "A", a, b, "reader-a", "reader-b", img)
    assert "Marking sheet: page T01" in out and "98659-79979" in out and "data:image/png;base64" in out
    assert "<script>alert(1)</script>" not in out, "text from the readers must never be able to run as script"
    assert 'src="http' not in out and 'href="http' not in out and "https://" not in out, "nothing may be loaded from the internet"
    assert out.count("<script>") == 1, "only the sheet's own script"
    print("selftest OK (invented text only)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-id"); ap.add_argument("--group", default="?"); ap.add_argument("--image"); ap.add_argument("--a"); ap.add_argument("--b")
    ap.add_argument("--a-name", default="reader A"); ap.add_argument("--b-name", default="reader B"); ap.add_argument("--out"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: selftest()
    elif a.page_id and a.a and a.b and a.out:
        open(a.out, "w", encoding="utf8").write(build(a.page_id, a.group, open(a.a).read(), open(a.b).read(), a.a_name, a.b_name, a.image)); print("wrote", a.out)
    else: sys.exit(__doc__)
