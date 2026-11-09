"""run_e2e.py with the harbouring entries trimmed to a variant: VARIANT=none (no harbouring entry), v1 (version 1's seven groups), v2 (as built). Usage: VARIANT=v1 python3 run_variant.py <config> <questions module> <out>"""
import os, sys, runpy
sys.path.insert(0, "/home/user/recourse")
import statute_aliases as A
v = os.environ.get("VARIANT", "v2")
if v == "none":
    A._COMPILED[:] = [e for e in A._COMPILED if not e["id"].startswith("bns_2")]
elif v == "v1":
    for e in A._COMPILED:
        if e["id"] == "bns_249_harbour":
            e["groups"] = e["groups"][:7]
print("VARIANT", v, [(e["id"], len(e["groups"])) for e in A._COMPILED], flush=True)
sys.argv = ["run_e2e.py"] + sys.argv[1:]
runpy.run_path("/home/user/recourse-sci-pool/review_results/2026-11-03_retrieval_misses/run_e2e.py", run_name="__main__")
