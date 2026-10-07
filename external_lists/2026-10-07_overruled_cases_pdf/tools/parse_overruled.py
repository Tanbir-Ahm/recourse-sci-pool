"""Parse the List-of-Overruled-Cases PDF into rows. Reads the PDF as data only. Run with python3 -I."""
import sys, re, json, warnings
warnings.filterwarnings("ignore")
import pymupdf

def parse(pdf):
    doc = pymupdf.open(pdf)
    entries = []   # dict(no, left, right, page)
    for pn in range(len(doc)):
        pg = doc[pn]
        blocks = []
        for b in pg.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            L, R = [], []
            for ln in b["lines"]:
                txt = "".join(sp["text"] for sp in ln["spans"])
                if not txt.strip():
                    continue
                (L if ln["bbox"][0] < 312 else R).append((ln["bbox"], txt))
            for side, lines in ((0, L), (1, R)):
                if lines:
                    x0 = min(b_[0][0] for b_ in lines); y0 = min(b_[0][1] for b_ in lines)
                    blocks.append((x0, y0, 0, 0, "\n".join(t for _, t in lines) + "\n"))
        left = sorted([b for b in blocks if b[0] < 312], key=lambda b: b[1])
        right = sorted([b for b in blocks if b[0] >= 312], key=lambda b: b[1])
        starts = []
        for b in left:
            m = re.match(r'\s*(\d{1,4})\.\s*(.*)', b[4], re.S)
            if m and not (entries and int(m.group(1)) < entries[-1]["no"] - 0 and False):
                starts.append((b, int(m.group(1)), m.group(2)))
            else:
                # continuation of previous left cell
                if entries:
                    entries[-1]["left"] += " " + b[4]
                    entries[-1].setdefault("pages", set()).add(pn + 1)
        # create entries for starts, in order; keep y for pairing right blocks
        prev_last = entries[-1] if entries else None
        newents = []
        for b, no, rest in starts:
            e = {"no": no, "left": rest, "right": "", "page": pn + 1, "y": b[1], "pages": {pn + 1}}
            entries.append(e); newents.append(e)
        for r in right:
            near = [e for e in newents if abs(e["y"] - r[1]) < 16]
            if near:
                near[0]["right"] += (" " if near[0]["right"] else "") + r[4]
            elif prev_last is not None:
                prev_last["right"] += " " + r[4]
    out = []
    for e in entries:
        norm = lambda s: re.sub(r'\s+', ' ', s).strip()
        out.append({"no": e["no"], "page": e["page"], "left": norm(e["left"]), "right": norm(e["right"])})
    return out

if __name__ == "__main__":
    rows = parse(sys.argv[1])
    json.dump(rows, open(sys.argv[2], "w"), ensure_ascii=False, indent=0)
    print(len(rows), "rows")
