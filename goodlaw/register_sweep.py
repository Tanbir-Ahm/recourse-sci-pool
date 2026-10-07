"""A cheap sweep for overrulings the register does not hold yet: later judgments (by default 2016 on, three or more judges) that say an earlier decision is overruled.

Two kinds of evidence, both only proposals for a person (nothing is added to the register by the sweep):
    tag       the law report's case-law list prints "A v. B (citations); C v. D (citations) - overruled" at the top of a judgment (the report editors' words)
    sentence  the judgment's own sentence ("... is hereby overruled", "... does not lay down the correct law")
The sweep needs the local store (corpus.sqlite) and takes about half a minute for the 1,500 judgments of three or more judges since 2016.

    python sci_goodlaw.py register-sweep --corpus corpus.sqlite
"""
import re

from . import cites as C
from . import register as R
from . import textutil as X

_ADVERSE = ("overruled", "partly overruled", "partially overruled", "overruled in part", "overruled to the extent", "held not good law", "held not a good law", "held not correct law", "not good law",
            "not correct law", "held to be per incuriam", "held per incuriam", "per incuriam", "disapproved", "held not binding", "not binding")
_OTHER = ("relied on", "relied upon", "referred to", "followed", "distinguished", "approved", "explained", "clarified", "affirmed", "held inapplicable", "inapplicable", "held not applicable",
          "applied", "considered", "upheld", "doubted", "not followed", "held applicable", "reiterated", "followed and applied", "observed", "discussed", "noted")
_TAG = re.compile(r"\s[–-]\s*(" + "|".join(sorted((re.escape(w) for w in _ADVERSE + _OTHER), key=len, reverse=True)) + r")\b[^;.]{0,60}", re.I)
_OP = re.compile(r"(?:\b(?:is|are|stands?|stood|hereby|accordingly|therefore|also|specifically|expressly|must be|needs to be)\b[^.;]{0,90}\boverrul(?:ed|ing)\b|\bwe\s+(?:\w+\s+){0,3}overrule\b|"
                 r"\bis\s+not\s+good\s+law\b|\bnot\s+lay\s+down\s+(?:the\s+)?(?:correct|good)\s+law\b|\bstand\s+overruled\b)", re.I)
_NEG = re.compile(r"objection|contention|plea|submission|prayer|application|learned|counsel|urged|argued|\bwould\b|\bif\b|\bmay be overruled|needs? to be overruled by|referred|reference", re.I)
_CITE = re.compile(r"\bv\.?\s+\w|\bvs\.?\s+\w|\bsupra\b|\(supra\)|SCC", re.I)


def parse_tags(head):
    """[(name, citations, tag)] from the case-law lists at the top of a judgment. A tag covers the cases printed since the previous tag."""
    start = head.find("Case Law Cited")
    if start < 0:
        start = head.find("Case law Cited")
    region = head[start:] if start >= 0 else head
    out, pos = [], 0
    for m in _TAG.finditer(region):
        seg = region[pos:m.start()]
        pos = m.end()
        if m.group(1).lower() not in _ADVERSE:
            continue
        for part in re.split(r";\s+(?=[A-Z])", seg):
            part = re.sub(r"\s+", " ", part).strip(" .;:-–")
            part = re.sub(r"^.*\[Paras?[^\]]*\](?:\s*\[[^\]]*\])*\s+(?=[A-Z])", "", part)         # the headnote text before the case list ends with '[Para 155][754-C-F]'
            part = re.sub(r"^(?:Case Law Cited\s*)?(?:In the judgment of [^:]{3,80}:\s*)?", "", part)
            cm = re.search(r"\(\s*\d{4}\s*\)|\[\s*\d{4}\s*\]|\bAIR\b|\b\d{4}\s*\(|\bSCC\b", part)
            name = part[:cm.start()].strip(" ,") if cm else part[:120]
            if 6 <= len(name) <= 160 and re.search(r"\sv\.?s?\.?\s|\sversus\s", name + " ", re.I):
                out.append((name, part[len(name):].strip(" ,:"), re.sub(r"\s+", " ", m.group(1)).lower()))
    return out


def operative_sentences(body):
    out = []
    for _, _, s in R.sentences(body):
        if _OP.search(s) and _CITE.search(s) and not _NEG.search(s) and len(s) < 600:
            out.append(re.sub(r"\s+", " ", s))
    return out


def sweep(corpus, reg=None, min_year=2016, min_bench=3, log=print):
    """Proposals: [{kind, doc_key, date, bench, title, overruled_name, overruled_cites, tag_or_sentence, already_in_register}]. `reg` (a Register) marks proposals it already holds."""
    con = corpus.con
    rows = con.execute("select doc_key,title,date,bench_size,year from docs where dup_of is null and year>=? and bench_size>=? order by date", (min_year, min_bench)).fetchall()
    log(f"sweep: {len(rows)} judgments of {min_bench}+ judges since {min_year}")
    props = []
    for k, title, date, bs, yr in rows:
        d = corpus.get(k)
        t = X.flatten(d["text"])
        st = int(d.get("body_start") or 0) or len(t) // 8
        tags = parse_tags(t[:max(st, int(len(t) * 0.35))])
        body_hits = operative_sentences(t[st:])
        for name, cites, tag in tags:
            props.append({"kind": "tag", "doc_key": k, "date": date, "bench": bs, "title": title, "overruled_name": name, "overruled_cites": cites, "evidence": tag})
        if not tags:
            for s in body_hits[:3]:
                props.append({"kind": "sentence", "doc_key": k, "date": date, "bench": bs, "title": title, "overruled_name": None, "overruled_cites": None, "evidence": s[:400]})
    if reg is not None:
        for p in props:
            p["already_in_register"] = _held(reg, p)
    return props


def _held(reg, p):
    """True if the register already has a row for the named decision whose overruling decision is this judgment."""
    if not p.get("overruled_name"):
        return False
    text = p["overruled_name"] + " " + (p.get("overruled_cites") or "")
    for h in reg.scan(text):
        if h["strength"] != "strong":
            continue
        b = h["row"]["overruling"]
        if b.get("doc_key") == p["doc_key"] or (p["title"] and R.Register._names_agree(b.get("name", ""), p["title"].replace(" versus ", " v. "))):
            return True
    return False
