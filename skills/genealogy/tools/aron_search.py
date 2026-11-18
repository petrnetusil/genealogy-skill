#!/usr/bin/env python3
"""Search volumes on the ARON portal (Czech regional archive SOA Zámrsk, fonds "Sbírka matrik Východočeského kraje" =
collection of parish registers of the East Bohemian region).
Usage: aron_search.py "<text in the description, e.g. a village>" [fonds name filter] [max]
  Several words separated by commas must all be in the description: "Vinice,Hořice" = Vinice in the parish of Hořice
  (villages of the same name are common – the results are therefore sorted by parish / first village in the description).
Prints: apu_id | reference code, kind and years | description (villages the volume covers).
Also lists volumes without images (mostly 20th century) – whether a volume is online shows
`aron_img.py <apu_id> info` (scans: 0 = not online)."""
import json, re, sys, time, urllib.request
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

API = "https://aron.vychodoceskearchivy.cz/api/aron"

def post(path, body, tries=3):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    for attempt in range(tries):   # ARON sometimes does not answer (timeout) – retry after a pause
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))

def search(desc, name="Sbírka matrik Východočeského kraje", maxn=500):
    out, offset = [], 0
    while True:
        d = post("/apu/listview?listType=SEARCH", {
            "filters": [{"field": "type", "operation": "EQ", "value": "ARCH_DESC"},
                        {"operation": "FTXF", "field": "name", "value": name},
                        *({"operation": "FTXF", "field": "description", "value": w.strip()}
                          for w in desc.split(",") if w.strip())],
            "sort": [], "offset": offset, "size": 100, "aggregations": []})
        items = d.get("items", [])
        out += items
        offset += len(items)
        if not items or offset >= min(d.get("count", 0), maxn):
            return out, d.get("count")

def place(desc):
    """Sort key: the description without the leading kind of book ("římskokatolická matrika NAROZENÝCH, …" = Roman
    Catholic register of BIRTHS), i.e. starting at the parish / first village. The patterns match ARON's Czech text."""
    parts = (desc or "").split(", ")
    while parts and re.search(r"matrika|index", parts[0]):
        parts.pop(0)
    return re.sub(r"^\(?(farnost|soudní okres) ", "", ", ".join(parts))

if __name__ == "__main__":
    desc = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "Sbírka matrik Východočeského kraje"
    maxn = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    items, cnt = search(desc, name, maxn)
    print("count", cnt)
    for i in sorted(items, key=lambda i: (place(i.get("description")), i["name"])):
        n = i["name"].split(": ", 1)[-1]
        print(i["id"], "|", n.replace("Sbírka matrik Východočeského kraje, ", ""), "|", (i.get("description") or "")[:220])
