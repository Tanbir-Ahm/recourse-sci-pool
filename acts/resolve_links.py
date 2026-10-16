"""
resolve_links.py -- finds each Act of the Act Directory (Recourse acts_directory.json) on India Code and proposes its link.  Read-only GETs on indiacode.gov.in; needs that host to be reachable
(environment Network access -> Allowed domains).  Written 2026-10-16 after the first stored links proved stale: the old-style handles (www.indiacode.nic.in/handle/123456789/<n>) that search
engines had indexed mean nothing on India Code's new system (123456789/1558 is now a collection called "Form", 123456789/2079 does not exist).

How it finds an Act (nothing here is a guess; a missing or doubled match stops the run for that Act):
  1. every CENTRAL record of the "ACT" collection (about 850), read with the discovery query  dc.identifier.collection:ACT AND dc.identifier.state_name:CENTRAL ;
     a record matches when its title (leading "The" and trailing year ignored) and its Act number and year equal the Directory entry's;
  2. otherwise the archive "stub" for an Act that has been repealed, whose title reads "<Name>, <N> of <YEAR> (Rep., Act <X> of <Y>)" (TADA, the Evidence Act, the IPC, the CrPC, the 1961 Income-tax Act).
The link written is  https://indiacode.gov.in/items/<uuid>  (the item page: title, Act number, year, ministry, the Act's PDF, and the "Section View" button).

It only PROPOSES.  Run it, read the table, then let the Directory's own check decide whether a link counts as checked:
    python acts/resolve_links.py --directory <recourse>/acts_directory.json            # print the table
    python acts/resolve_links.py --directory <recourse>/acts_directory.json --write    # put the links into url (url_alt cleared) and clear url_checked
    cd <recourse> && python act_directory.py check-links --write                        # India Code's own record must match the Act's title, number and year

Also writes (with --catalogue DIR) the metadata of all central Acts, for later steps (which Acts to load next): DIR/central_acts.json.
"""
import argparse
import json
import re
import sys
import time

import requests

API = "https://indiacode.gov.in/server/api/discover/search/objects"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
STUB = re.compile(r"^(?P<name>.+?)[\s,]+(?P<num>\d+)\s+of\s+(?P<year>\d{4})\s*(?:,?\s*\(\s*Rep\.?[\s,]*(?P<by>[^)]*?)\s*\))?\s*$", re.I)


def norm(text):
    t = (text or "").lower().replace("’", "'")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def name_key(text):
    k = norm(re.sub(r"^\s*the\s+", "", text or "", flags=re.I))
    return re.sub(r"\s+\d{4}$", "", k)


def md(item, key):
    v = (item.get("metadata") or {}).get(key)
    return (v[0]["value"] if v else None)


def search(query, page=0, size=100):
    for attempt in range(4):
        try:
            r = requests.get(API, params={"query": query, "dsoType": "item", "size": size, "page": page}, headers=HEADERS, timeout=60)
            r.raise_for_status()
            sr = r.json()["_embedded"]["searchResult"]
            return [o["_embedded"]["indexableObject"] for o in sr["_embedded"]["objects"]], sr["page"]["totalPages"]
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(3)


def central_acts():
    out, page, pages = [], 0, 1
    while page < pages:
        items, pages = search("dc.identifier.collection:ACT AND dc.identifier.state_name:CENTRAL", page)
        out += items
        page += 1
        time.sleep(0.4)
    return out


def stub_for(entry):
    """The archive record of a repealed Act: title 'Name, N of YEAR (Rep., Act X of Y)'."""
    want = re.match(r"\s*(\d+)\s+of\s+(\d{4})", entry["act_no"])
    core = re.sub(r"^\s*the\s+", "", entry["name"], flags=re.I)
    core = re.sub(r",?\s*\d{4}\s*$", "", core)                    # 'Indian Penal Code, 1860' -> 'Indian Penal Code'
    hits, page, pages = [], 0, 1
    while page < pages and page < 5:                                  # a title phrase such as 'Code of Criminal Procedure' is also in dozens of amendment-Act stubs: read a few pages
        items, pages = search(f'dc.title:"{core}" AND dc.title:"Rep."', page)
        for it in items:
            m = STUB.match(it.get("name") or "")
            if m and m.group("by") and name_key(m.group("name")) == name_key(entry["name"]) and (int(m.group("num")), int(m.group("year"))) == (int(want.group(1)), int(want.group(2))):
                hits.append(it)
        page += 1
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--directory", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--catalogue", help="directory to save central_acts.json (metadata of every central Act)")
    args = ap.parse_args()
    data = json.load(open(args.directory, encoding="utf-8"))
    acts = central_acts()
    print(f"{len(acts)} central Acts read from India Code")
    if args.catalogue:
        import os
        os.makedirs(args.catalogue, exist_ok=True)
        slim = [{"uuid": a["uuid"], "handle": a["handle"], "title": a["name"], "act_number": md(a, "dc.identifier.act_number"), "act_year": md(a, "dc.date.act_year"),
                 "act_id": md(a, "dc.identifier.act_id"), "repealed": md(a, "dc.identifier.repealed"), "enacted": md(a, "dc.date.enact_date"), "enforced": md(a, "dc.date.enforcement_date"),
                 "ministry": md(a, "dc.identifier.ministry_name")} for a in acts]
        json.dump(slim, open(os.path.join(args.catalogue, "central_acts.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    problems = 0
    for e in data["acts"]:
        want = re.match(r"\s*(\d+)\s+of\s+(\d{4})", e["act_no"])
        key = (int(want.group(1)), int(want.group(2)))
        hits = [a for a in acts if md(a, "dc.identifier.act_number") and md(a, "dc.date.act_year")
                and (int(md(a, "dc.identifier.act_number")), int(md(a, "dc.date.act_year"))) == key and name_key(a["name"]) == name_key(e["name"])]
        kind = "act"
        if not hits:
            hits, kind = stub_for(e), "repealed-stub"
        if len(hits) != 1:
            problems += 1
            print(f"  !! {e['id']:32s} {len(hits)} candidate(s): {[h['name'] for h in hits]}")
            continue
        h = hits[0]
        url = f"https://indiacode.gov.in/items/{h['uuid']}"
        print(f"  ok {e['id']:32s} {kind:13s} {h['name'][:78]:78s} {url}")
        if args.write:
            e["url"], e["url_alt"], e["url_checked"] = url, None, None
            if "handle" in (e.get("note") or "").lower():          # notes about the stale old-style handles ("lists this Act under two handles", "Handle 12846 is the page ...")
                e.pop("note")
    if args.write and not problems:
        with open(args.directory, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("written:", args.directory)
    elif args.write:
        print("NOT written: fix the candidates marked !! first")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
