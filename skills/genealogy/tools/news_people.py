#!/usr/bin/env python3
"""List of people each website version concerns (expandable list on the "What's new" page).

For each version in web/src/news.json it remembers the state of the data (data/news_state.json: record keys and a
fingerprint of every person). Comparing with the previous version it fills the field "people" in the news:
  [{"k": person number, "new": true/false, "records": [keys of new records the person cites]}]

Usage (from the project root):
  python3 -I tools/news_people.py   – the newest version without a snapshot gets one now; recomputes all versions
Runs automatically in tools/deploy_all.sh before the website data is prepared.

data/news_state.json: {"<version>": {"records": [record keys], "people": {"<k>": fingerprint}, "synthetic": false}}
("synthetic": true marks a snapshot reconstructed afterwards – changed people are then not reported, only new ones).
"""
import hashlib, json, os, sys
if sys.argv[1:2] in (["-h"], ["--help"]):   # help instead of a crash
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "news_state.json")
NEWS = os.path.join(ROOT, "web", "src", "news.json")


def load_people(text):
    ns = {}
    exec(text, ns)
    return ns["P"], ns.get("SAME", {})


def fingerprint(p):
    return hashlib.sha1(json.dumps(p, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def current():
    P, SAME = load_people(open(os.path.join(ROOT, "data", "people.py"), encoding="utf-8-sig").read())
    recs = [z["key"] for z in json.load(open(os.path.join(ROOT, "data", "records.json"), encoding="utf-8-sig"))]
    return P, SAME, recs


def main():
    P, SAME, recs = current()
    state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    if not os.path.exists(NEWS):
        sys.exit("web/src/news.json does not exist – add the first news entry first.")
    news = json.load(open(NEWS, encoding="utf-8"))
    if not news:
        print("web/src/news.json is empty – nothing to do.")
        return
    latest = max(n["version"] for n in news)
    if str(latest) not in state:
        state[str(latest)] = {"records": recs, "people": {str(k): fingerprint(p) for k, p in P.items() if k not in SAME},
                              "synthetic": False}
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"snapshot of version {latest} saved")
    for n in news:
        v = n["version"]
        s1, s0 = state.get(str(v)), state.get(str(v - 1))
        if not s1 or not s0:
            n.pop("people", None)
            continue
        new_recs = set(s1["records"]) - set(s0["records"])
        hash_ok = not s1.get("synthetic") and not s0.get("synthetic")
        people = []
        for ks in s1["people"]:
            k = int(ks)
            if k not in P:
                continue
            is_new = ks not in s0["people"]
            recs_k = [r for r in P[k].get("r", []) if r in new_recs]
            changed = hash_ok and not is_new and s0["people"][ks] != s1["people"][ks]
            if is_new or recs_k or changed:
                people.append({"k": k, "new": is_new, "records": recs_k})
        n["people"] = sorted(people, key=lambda o: o["k"])
    json.dump(news, open(NEWS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("people per version:", {n["version"]: len(n.get("people", [])) for n in news})


if __name__ == "__main__":
    main()
