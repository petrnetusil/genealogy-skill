"""Test of the title filter in tools/anno.py (ANNO_TITLE, --losses) – offline, the ANNO API is faked.

From the repository root:
  python3 -I tests/anno/test_losses.py skills/genealogy/tools
ANNO filters a title with the parameter selectedFilters=title:<code> (it does not know a title= parameter and returns 0,
checked on 5 Nov 2026); several filters at once combine as "and", so titles are searched one at a time.
"""
import contextlib, io, os, sys

TOOLS = os.path.abspath(sys.argv[1])
sys.path.insert(0, TOOLS)
import anno  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{'' if ok else '  ' + str(detail)[:600]}", flush=True)


CALLS = []


def fake_get(path, params):
    CALLS.append((path, dict(params)))
    if path == "snippet":
        return {"snippetPages": []}
    f = params.get("selectedFilters", "")
    title = f.split(":", 1)[1] if f.startswith("title:") else None
    docs = {None: ["ANNO_ptb19141013", "ANNO_vlv19160812"], "vll": ["ANNO_vll19150301"],
            "vlv": ["ANNO_vlv19160812"], "nvv": ["ANNO_nvv19141210"]}.get(title, [])
    return {"totalHits": len(docs), "textQuery": params["text"], "lastHit": len(docs),
            "documents": [{"docId": d, "displayTitle": d, "totalHitsInDoc": 1, "openUrl": "u"} for d in docs]}


anno.get = fake_get


def run(argv, env=None):
    CALLS.clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        anno.main(argv, env or {})
    return out.getvalue()


out = run(['"Hromadko Wenzel"', "1914", "1919"], {"ANNO_TITLE": "vlv"})
p = CALLS[0][1]
check("ANNO_TITLE sends selectedFilters=title:vlv", p.get("selectedFilters") == "title:vlv", p)
check("ANNO_TITLE does not send the unknown parameter title=", "title" not in p, p)
check("result from the casualty index", "ANNO_vlv19160812" in out, out)

out = run(['"Hromadko Wenzel"', "1914", "1919"], {"ANNO_TITLE": "vll,nvv"})
filters = [v[1].get("selectedFilters") for v in CALLS if v[0] == "complex"]
check("several titles in ANNO_TITLE: each separately", filters == ["title:vll", "title:nvv"], filters)
check("several titles: results of both", "ANNO_vll19150301" in out and "ANNO_nvv19141210" in out, out)

out = run(['"Hromadko Wenzel"', "1914", "1919", "--losses"])
filters = [v[1].get("selectedFilters") for v in CALLS if v[0] == "complex"]
check("--losses searches lists, indexes and the wounded", filters == ["title:vll", "title:vlv", "title:nvv"], filters)
check("--losses: no ordinary newspapers", "ANNO_ptb" not in out and "ANNO_vll19150301" in out, out)

out = run(['"Hromadko Wenzel"', "1914", "1919"])
p = CALLS[0][1]
check("without a filter: no selectedFilters", "selectedFilters" not in p and "ANNO_ptb19141013" in out, p)

print(f"\n{sum(results)} of {len(results)} right")
sys.exit(0 if all(results) else 1)
