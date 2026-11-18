#!/usr/bin/env python3
"""Ideas for curiosities: goes through data/people.py and lists things that often make nice "fun facts".

Usage (from the project root): python3 -I tools/ideas.py [project folder]

Looks for: weddings shortly before a birth (and "right on time" births nine months after the wedding), children born
before the wedding, a big age gap between spouses, very young and old marriages, multiple marriages, longevity,
a mother's death shortly after a birth, deaths in years of epidemics and wars, a line in one house for generations,
ancestors appearing more than once, the oldest ancestors, trades in the lines, births at Christmas.

These are only IDEAS from the data – check each one in the record (data are often uncertain) and only then write it
into data/curiosities.md as a short story (see reference/stories.md).
"""
import os, re, sys
if sys.argv[1:2] in (["-h"], ["--help"]):   # help instead of a crash
    sys.exit(__doc__.strip())
from collections import defaultdict
for _s in (sys.stdout, sys.stderr):   # UTF-8 output even on Windows without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:   # python3 -I does not put the script's folder on sys.path
    sys.path.insert(0, TOOLS)
from evidence_check import full_date  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(TOOLS)
# Years of epidemics, famines and wars that often show in Central European registers – adjust for your region.
EPIDEMICS = {1771: "famine", 1772: "famine and typhus", 1805: "typhus", 1831: "cholera", 1832: "cholera", 1836: "cholera",
             1849: "cholera", 1850: "cholera", 1855: "cholera", 1866: "cholera and the Austro-Prussian war",
             1873: "cholera", 1918: "Spanish flu", 1919: "Spanish flu"}


def load():
    ns = {}
    exec(open(os.path.join(ROOT, "data", "people.py"), encoding="utf-8-sig").read(), ns)
    return ns["P"], ns.get("LINES", {}), ns.get("SAME", {})


INEXACT = re.compile(r"^\S\s*(?:\S+\s+)?(?:before|after|between|c\.|ca\.?|circa|about|abt\.?|around|~|"
                     r"not\s+later|not\s+earlier)(?![^\W\d_])", re.I)


def event(p, sym):
    """All dates of an event (* × †) from a person's facts; "† before Jun 1919", "c. 1850" etc. are not exact dates."""
    out = []
    for f in p.get("f", []):
        if f.strip().startswith(sym) and not INEXACT.match(f.strip()):
            d = full_date(f)
            if d:
                out.append((d, f))
    return out


def year_of(p, sym):
    for f in p.get("f", []):
        if f.strip().startswith(sym) and not INEXACT.match(f.strip()):
            m = re.search(r"\d{4}", f)
            if m:
                return int(m.group())
    return None


def line_of(k):
    while k > 15:
        k //= 2
    return k if k >= 8 else None


def main():
    P, LINES, SAME = load()
    real = {k: p for k, p in P.items() if k not in SAME}
    name = lambda k: f"{P[k]['n']} ({k})"
    ideas = defaultdict(list)

    for k, p in real.items():
        births, marr, deaths = event(p, "*"), event(p, "×"), event(p, "†")
        b = births[0][0] if births else None
        # wedding × birth of the child in the direct line (the child of ancestor k is k // 2)
        if k >= 2 and k % 2 == 0 and marr and (k // 2) in P:
            cb = event(P[k // 2], "*")
            wife = P.get(k + 1, {}).get("n", "").split()
            mine = [m for m in marr if wife and wife[-1][:5] in m[1]] or (marr if len(marr) == 1 else [])
            if cb:
                for md, _ in mine:
                    days = (cb[0][0] - md).days
                    if -3650 < days < 0:
                        ideas["Child born before the wedding"].append(f"{name(k // 2)} was born {-days} days BEFORE the wedding of the parents {name(k)} and {name(k + 1)} – legitimised?")
                    elif 0 <= days < 245:
                        ideas["Wedding at the last minute"].append(f"{name(k // 2)} was born {days} days after the wedding of the parents {name(k)} × {name(k + 1)}")
                    elif 255 <= days <= 280:
                        ideas["Right on time (≈ 9 months after the wedding)"].append(f"{name(k // 2)} was born {days} days after the parents' wedding")
        # age at marriage, age gap of the spouses
        if b and marr:
            for md, f in marr:
                age = (md - b).days / 365.25
                if age < 19:
                    ideas["Very young marriage"].append(f"{name(k)} married at {age:.0f} ({f})")
                elif age > 45:
                    ideas["Marriage at a mature age"].append(f"{name(k)} married at {age:.0f} ({f})")
        if k % 2 == 0 and (k + 1) in real and b:
            wb = event(real[k + 1], "*")
            if wb:
                diff = (wb[0][0] - b).days / 365.25
                if abs(diff) >= 12:
                    older = name(k) if diff > 0 else name(k + 1)
                    ideas["Big age gap between spouses"].append(f"{name(k)} × {name(k + 1)}: {abs(diff):.0f} years apart (older: {older})")
        txt = " | ".join(p.get("f", []) + [p.get("note", "")])
        m = re.search(r"[^|]{0,60}\b(widow|second marriage|third marriage|remarried)[^|]{0,80}", txt, re.I)
        if len([f for f in p.get("f", []) if f.strip().startswith("×")]) >= 2 or m:
            ideas["Several marriages / widowhood"].append(f"{name(k)}: " + ("; ".join(f for f in p.get("f", []) if f.strip().startswith("×")) if not m else m.group(0).strip())[:200])
        # longevity, death after a birth, epidemics
        if b and deaths:
            age = (deaths[0][0] - b).days / 365.25
            if age >= 85:
                ideas["Longevity"].append(f"{name(k)} lived to {age:.0f}")
        if k % 2 == 1 and k >= 3 and deaths and (k // 2) in P:
            cb = event(P[k // 2], "*")
            if cb and 0 <= (deaths[0][0] - cb[0][0]).days <= 60:
                ideas["Mother died shortly after a birth"].append(f"{name(k)} died {(deaths[0][0] - cb[0][0]).days} days after the birth of {name(k // 2)}")
        dy = year_of(p, "†")
        if dy in EPIDEMICS:
            ideas["Death in a year of epidemic / war"].append(f"{name(k)} † {dy} – {EPIDEMICS[dy]}? (check the cause in the record)")
        if b and b.month == 12 and b.day in (24, 25):
            ideas["Born at Christmas"].append(f"{name(k)} * {b.day} Dec {b.year}")

    # a line in one house: the same place and house number over generations in the paternal line
    shown = {}
    for k in sorted(real):
        if k % 2 == 1 or (k // 2 in real and k // 2 >= 2 and (k // 2) % 2 == 0):
            continue   # start from the youngest man of the chain
        chain, kk = [], k
        while kk in real:
            houses = re.findall(r"([^\W\d_][\w'’-]+(?: [^\W\d_][\w'’-]+)?) (?:no\.|No\.|nr\.?|n°|čp\.|č\.|N\.)\s*(\d+)",
                                " ".join(real[kk].get("f", [])))
            keys = {}
            for o, n in houses:
                if not o[0].isupper():
                    continue
                keys.setdefault(" ".join(w[:4] for w in o.split()) + f" {n}", f"{o} no. {n}")   # place stem because of inflection
            shown.update({kk2: v for kk2, v in keys.items() if kk2 not in shown})
            chain.append((kk, set(keys)))
            kk *= 2
        for i in range(len(chain)):
            for h in chain[i][1]:
                run = [c[0] for c in chain[i:] if h in c[1]]
                j = i
                while j < len(chain) and h in chain[j][1]:
                    j += 1
                if j - i >= 3 and (i == 0 or h not in chain[i - 1][1]):
                    ideas["A line in one house"].append(f"{shown[h]}: {j - i} generations ({', '.join(name(c) for c in run[: j - i])})")

    for alias, main_k in SAME.items():
        ideas["Ancestor in the tree more than once (relatives married)"].append(f"{name(main_k)} is also ancestor no. {alias}")
    oldest = sorted((y, k) for k, p in real.items() if p.get("st") == "doc" for y in [year_of(p, "*") or year_of(p, "×")] if y)[:3]
    for y, k in oldest:
        ideas["Oldest documented ancestors"].append(f"{name(k)} – {y}")
    trades = defaultdict(set)
    for k, p in real.items():
        for f in p.get("f", []):
            if re.match(r"\s*[*×†]", f) or re.search(r"\d{4}", f):
                continue
            for t in re.split(r"[;,(]", f):
                t = re.sub(r"\s+(in|at|on|of|from|near)\s.*$", "", t.strip())
                if t and t[0].islower() and not re.match(r"(daughter|son|from|of|née|married|later|born|illegitimate|"
                                                          r"widow|widower|resident|lived|living|also)\b", t) and len(t) < 30 \
                        and not re.search(r"\)|^a |^an |no\.|estate|parish|tree|read|found|birth|children|legend|illegible", t):
                    trades[LINES.get(line_of(k), ("?",))[0] if line_of(k) else "root family"].add(t)
    for line, t in sorted(trades.items()):
        ideas["Trades and status in the lines"].append(f"{line}: {', '.join(sorted(t))[:300]}")

    if not ideas:
        print("Nothing yet – add dates of birth, marriage and death to people (facts starting with *, ×, †).")
    for title, items in ideas.items():
        print(f"\n## {title}")
        for i in items[:12]:
            print(" -", i)
    print("\nThese are only ideas from the data. Check each in the record, then write it as a short story into data/curiosities.md.")


if __name__ == "__main__":
    main()
