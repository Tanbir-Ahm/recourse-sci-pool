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
import argparse, base64, difflib, html, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marking sheet __PID__</title>
<style>
:root{--bg:#f4f5f6;--fg:#17212b;--muted:#5b6670;--line:#c9ced3;--card:#fff;--red:#a3271f;--redbg:#f8e0dd;--amber:#8a5a00;--amberbg:#f8ecd0;--green:#17663a}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,"Segoe UI","Noto Sans","Noto Sans Bengali","Noto Sans Kannada","Noto Sans Devanagari",sans-serif;padding:16px}
h1{font-size:1.3rem;margin:0 0 4px} h2{font-size:1.05rem;margin:22px 0 8px} .muted{color:var(--muted);font-size:.88rem}
.banner{background:var(--amberbg);border:1px solid var(--line);border-radius:6px;padding:8px 12px;margin:10px 0;font-size:.9rem}
.wrap{display:grid;grid-template-columns:minmax(0,4fr) minmax(0,8fr);gap:16px;align-items:start}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px;min-width:0}
.sticky{position:sticky;top:8px} img{width:100%;height:auto;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:.88rem} th,td{border:1px solid var(--line);padding:5px 7px;vertical-align:top;text-align:left}
th{background:#eef0f2;font-weight:600;white-space:nowrap} .scroll{overflow-x:auto}
tr.sub td{background:#fbfbf4;border-top:none}tr.dis td:first-child{background:var(--redbg);color:var(--red);font-weight:600} tr.conf td:first-child{background:var(--amberbg);color:var(--amber)}
input,select,button,textarea{font:inherit;font-size:.86rem;padding:3px 5px;max-width:100%} textarea{width:100%;min-height:3.2rem}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px} .txt{white-space:pre-wrap;line-height:1.55}
.zoomwrap{position:relative;line-height:0}.lens{display:none;position:absolute;width:230px;height:230px;border:3px solid #17212b;border-radius:50%;box-shadow:0 2px 10px rgba(0,0,0,.35);background-repeat:no-repeat;background-color:#fff;pointer-events:none;z-index:5}
.dg{font-size:1.55em;font-weight:700;letter-spacing:.05em;background:#fff3b8;padding:0 2px;border-radius:3px}.ln{margin-top:4px;line-height:1.9;font-size:.9rem}.v3{color:var(--red);font-weight:600}
@media (max-width:860px){.wrap,.two{grid-template-columns:minmax(0,1fr)}.sticky{position:static}}
</style></head><body>
<h1>Marking sheet: page __PID__ (group __GROUP__)</h1>
<div class="muted">Reader A: __ANAME__ &middot; Reader B: __BNAME__</div>
<div class="banner"><b>Machine draft, not a certified translation.</b> Close every row below against the page image. <b>Dates and amounts: compare every digit with the page itself</b> (move the pointer over the page for a magnifier); two readings that agree can both be wrong. A row left open is not checked. This file holds the page and its text: keep it private.</div>
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
<h3>Page summary</h3><p>Gist correct: <select id="gist"><option></option><option>yes</option><option>no</option></select> &nbsp; Critical errors: <input id="ncrit" size="3"> &nbsp; Silent critical errors: <input id="nsil" size="3"> &nbsp; Reviewer minutes: <input id="mins" size="4"> &nbsp; Summary is about: <select id="who"><option>both readings (the pipeline)</option><option>__ANAME__</option><option>__BNAME__</option></select></p></div>
</div></div>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s), esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
$('#sum').textContent=D.summary.disagreements+' disagreements to resolve, '+D.summary.to_confirm+' items to confirm, '+D.summary.differing_lines+' differing lines'+(D.summary.possible_dropped_text?'. One reading is much shorter than the other: check for dropped text.':'.');
const DIGIT_TYPES=['date','amount','number','section'];
const big=s=>esc(s).replace(/[\\p{Nd}][\\p{Nd}\\-\\/.,।]*/gu,m=>'<span class="dg">'+m+'</span>');
function digitCell(i){let o='';if(DIGIT_TYPES.includes(i.type)){const a=D.linesA[(i.line_A||0)-1],b=D.linesB[(i.line_B||0)-1];
 if(a!=null)o+='<div class="ln"><b>A:</b> '+big(a)+'</div>';if(b!=null&&b!==a)o+='<div class="ln"><b>B:</b> '+big(b)+'</div>';}
 if(D.hasC&&['date','amount'].includes(i.type))o+='<div class="ln"><b>View 3:</b> <span class="'+(i.C_same?'':'v3')+'">'+esc(i.C==null?'not found':i.C)+'</span>'+(i.C_same?'':' &larr; differs: look at the page')+'</div>';return o;}
let h='<tr><th>Status</th><th>Type</th><th>Reader A</th><th>Reader B</th><th>Line (A/B)</th><th>Value on the page</th><th>Result</th></tr>';
D.items.forEach(i=>{h+='<tr data-c="'+esc(i.C==null?'':i.C)+'" class="'+(i.status==='DISAGREE'?'dis':'conf')+'"><td>'+i.status+'</td><td>'+esc(i.type)+'</td><td>'+esc(i.A)+'</td><td>'+esc(i.B)+'</td><td>'+esc(i.line_A)+' / '+esc(i.line_B)+'</td><td><input size="14"></td><td><select><option></option><option>right in both</option><option>A wrong</option><option>B wrong</option><option>both wrong</option><option>not on the page</option></select></td></tr>';const dc=digitCell(i);if(dc)h+='<tr class="sub"><td></td><td colspan="6">'+dc+'</td></tr>';});
$('#items').innerHTML=h;
const fl=s=>{s=String(s==null?'':s);let o='';for(const c of s){const k=c.codePointAt(0);let d=-1;for(const b of [0x9E6,0x966,0xA66,0xAE6,0xB66,0xBE6,0xC66,0xCE6,0xD66]){if(k>=b&&k<b+10){d=k-b;break;}}
 if(d>=0)o+=d;else if(c==='ৰ')o+='র';else if(c==='ৱ')o+='ব';else if(c==='।'||c==='৷')o+='/';else if(c.trim()===''||k===0x200c||k===0x200d)continue;else o+=c.toLowerCase();}return o;};
document.querySelectorAll('#items tr.dis, #items tr.conf').forEach((tr,idx)=>{const it=D.items[idx],inp=tr.querySelector('input');
 inp.addEventListener('input',()=>{const v=fl(inp.value),a=it.A==null?null:fl(it.A),b=it.B==null?null:fl(it.B),c=it.C==null?null:fl(it.C),bad=v!==''&&v!==a&&v!==b&&v!==c;
  let sp=inp.nextElementSibling;if(!sp||!sp.classList.contains('mm')){sp=document.createElement('div');sp.className='mm';sp.style.cssText='color:#a3271f;font-size:.8rem';inp.after(sp);}
  sp.textContent=bad?'differs from both readings: look at the page again':'';});});
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
 rows.push([]); rows.push(['Check list','Status','Type','Reader A','Reader B','Line A/B','Value on the page','Result','View 3']);
 document.querySelectorAll('#items tr.dis, #items tr.conf').forEach(tr=>{const c=[...tr.children]; rows.push(['',c[0].textContent,c[1].textContent,c[2].textContent,c[3].textContent,c[4].textContent,c[5].querySelector('input').value,c[6].querySelector('select').value,tr.dataset.c||'']);});
 rows.push([]); rows.push(['Page summary','gist correct',$('#gist').value,'critical errors',$('#ncrit').value,'silent critical',$('#nsil').value,'minutes',$('#mins').value,'about',$('#who').value]);
 return rows.map(r=>r.map(q).join(',')).join('\\n');}
$('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(csv());$('#copy').textContent='Copied';}catch(e){window.prompt('Copy this:',csv());}};
$('#dl').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv()],{type:'text/csv'}));a.download=D.pid+'_marks.csv';a.click();};
;(function(){const img=document.getElementById('pg'),lens=document.getElementById('lens'),sel=document.getElementById('zoomsel');if(!img||!lens)return;
 function show(e){const r=img.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,Z=+sel.value;if(x<0||y<0||x>r.width||y>r.height){lens.style.display='none';return;}
  lens.style.display='block';lens.style.backgroundImage='url("'+img.src+'")';lens.style.backgroundSize=(r.width*Z)+'px '+(r.height*Z)+'px';
  lens.style.backgroundPosition=(-(x*Z-115))+'px '+(-(y*Z-115))+'px';lens.style.left=(x-115)+'px';lens.style.top=(y-115)+'px';}
 img.addEventListener('mousemove',show);img.addEventListener('mouseleave',()=>{lens.style.display='none';});})();
</script></body></html>"""


def build(page_id, group, a_text, b_text, a_name, b_name, image_path=None, c_text=None):
    cmp_ = checker.compare(a_text, b_text)
    def english(t):
        return t.split("TRANSLATION", 1)[1].lstrip("*:# \n-") if "TRANSLATION" in t else "(no translation in this output)"
    if image_path:
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
        img = (f'<div class="zoomwrap"><img id="pg" alt="Page {html.escape(page_id)}" src="data:image/{mime};base64,{base64.b64encode(open(image_path, "rb").read()).decode()}"><div class="lens" id="lens"></div></div>'
               '<div class="muted" style="margin-top:6px">Magnifier: move the pointer over the page. Zoom <select id="zoomsel"><option>2</option><option selected>3</option><option>4</option><option>6</option></select> &times;</div>')
    else:
        img = '<div class="muted">No page image was given. Open the original beside this sheet.</div>'
    data = dict(cmp_, pid=page_id, group=group, aname=a_name, bname=b_name, enA=english(a_text), enB=english(b_text),
                linesA=checker.transcription_lines(a_text), linesB=checker.transcription_lines(b_text), hasC=bool(c_text))
    if c_text:                                   # the third (ultra-high detail) reading: what it reads for each date and amount
        third = checker.extract_items(checker.transcription_lines(c_text))
        have = {(i["type"], i["norm"]) for i in third}
        for it in data["items"]:
            same = [i for i in third if i["type"] == it["type"]]
            mine = checker.extract_items([it["A"] or it["B"] or ""])
            it["C_same"] = bool(mine) and all((m["type"], m["norm"]) in have for m in mine)
            near = difflib.get_close_matches(it["A"] or it["B"] or "", [i["value"] for i in same], n=1, cutoff=0.0)
            it["C"] = near[0] if near else None
    page = PAGE
    for k, v in {"__PID__": html.escape(page_id), "__GROUP__": html.escape(group), "__ANAME__": html.escape(a_name), "__BNAME__": html.escape(b_name), "__IMAGE__": img}.items():
        page = page.replace(k, v)
    return page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))


def selftest():
    a = "TRANSCRIPTION\n1. Order dated 15-02-2020; phone 98599-79979.\n2. Closing line.\nTRANSLATION\nThe order is dated 15 February 2020. <script>alert(1)</script>"
    b = "TRANSCRIPTION\n1. Order dated 15-02-2020; phone 98659-79979.\nTRANSLATION\nOrder of 15 February 2020."
    d = tempfile.mkdtemp(); img = os.path.join(d, "x.png"); open(img, "wb").write(b"\x89PNG fake")
    out = build("T01", "A", a, b, "reader-a", "reader-b", img)
    assert "differs from both readings" in out and "Summary is about" in out
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
