import json, sys, collections
SP = "/tmp/claude-0/-home-user-recourse-sci-pool/33686f69-1895-5643-b31d-21bed3d4a6ee/scratchpad/"
ADV = ("OVERRULES", "DISAGREES", "DOUBTS_REFERS")
clean = {p["no"]: p for p in json.load(open(SP + "ovr/pairs_clean.json"))}
for name in sys.argv[1:]:
    res = [r for r in json.load(open(SP + f"ovr/{name}.json")) if r["no"] in clean]
    n = len(res)
    C = collections.Counter(r["label"] for r in res)
    adv = [r for r in res if r["label"] in ADV]
    eligible = [r for r in adv if r["eligible"]]
    expl = [r for r in res if r["label"] == "OVERRULES"]
    mention = [r for r in res if r["label"] is not None]
    print(f"== {name}: {n} pairs (suspect matches removed)")
    print(f"   citing judgment names the case (mention found): {len(mention)} ({len(mention)/n:.0%})")
    print(f"   read as overrules/disagrees/doubts: {len(adv)} ({len(adv)/n:.0%});  of which court/headnote voice and confident: {len(eligible)}")
    print(f"   read as an explicit overruling: {len(expl)} ({len(expl)/n:.0%})")
    print("   labels:", dict(C))
