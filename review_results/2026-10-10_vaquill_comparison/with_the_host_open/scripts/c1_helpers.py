import re, collections
HDR = re.compile(r"\ACase: [^\n]*\nSection: [^\n]*\n\n")
LONE = re.compile(r"(?m)^[A-H]\s*$")
RUN = re.compile(r"(?mi)^(?:\d{1,4}\s+)?(?:SUPREME COURT REPORTS.*|\[\d{4}\]\s+(?:SUPP\.\s+)?\d+\s+S\.C\.R\.(?:\s+\d+)?)\s*$")
TAGLINE = re.compile(r"(?m)^\[[A-Z_]+\]\s*#*\s*")
def reassemble(df, cid, off):
    d = df[df.case_id == cid].sort_values("chunk_index")
    parts, prev_end = [], None
    for ci, t in zip(d.chunk_index, d.text_original):
        h = HDR.match(t); body = t[h.end():] if h else t
        cs, ce = off.loc[(cid, ci)]
        if prev_end is not None and cs < prev_end: body = body[prev_end - cs:]
        elif prev_end is not None: parts.append("\n\n")
        parts.append(body); prev_end = ce
    return "".join(parts)
def words(t):
    t = TAGLINE.sub("", RUN.sub("", LONE.sub("", t)))
    return re.findall(r"[a-z0-9]+", t.lower())
