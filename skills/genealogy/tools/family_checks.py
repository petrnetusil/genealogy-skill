#!/usr/bin/env python3
"""Additional family checks. tools/check.py shows their results as warnings.

  a) a record cited for a child names the parents (2k / 2k+1), but the parent does not have it in their `r` –
     based on the translation (`translation` in data/transcripts.json), baptisms only (kind B); the parent is
     looked up in the translation by given name + beginning of the surname;
  b) a fact with a year after the person's death (e.g. "farmer 1790" for someone † 1773) – except facts about the
     burial, widow/widower, children;
  c) living people in the research log: a person without a death, born after 1925, whose name appears in a log row
     together with a full date of birth (day, month, year) – the log goes on the website;
  d) the same ancestor twice: two numbers with the same name and the same birth year, not linked in SAME.

Standalone: python3 -I tools/family_checks.py   (prints all warnings)
No network, writes nothing to data/.
"""
import json
import os
import re
import runpy
import sys
import unicodedata

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:   # python3 -I does not put the script's folder on sys.path
    sys.path.insert(0, TOOLS)
from evidence_check import find_dates  # noqa: E402

ROOT = os.path.abspath(os.path.join(TOOLS, ".."))
DATA = os.path.join(ROOT, "data")
YEAR = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-2][0-9])(?!\d)")
UNKNOWN_NAME = re.compile(r"\bunknown\b|\bnot (?:named|recorded|stated)\b", re.I)


def ascii_lower(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def year_of(f, symbol):
    for x in f:
        x = x.strip()
        if x.startswith(symbol) or (symbol == "†" and x.lower().startswith("(burial)")):
            m = YEAR.search(x)
            if m:
                return int(m.group(1))
    return None


def name_parts(n):
    n = re.sub(r"\(.*?\)", "", n or "").strip()
    return [c for c in re.split(r"[\s,]+", n) if c and c[0].isupper()]


def warnings():
    ns = runpy.run_path(os.path.join(DATA, "people.py"))
    P, SAME = ns["P"], ns.get("SAME", {})
    recs = {z["key"]: z for z in json.load(open(os.path.join(DATA, "records.json"), encoding="utf-8-sig"))}
    tr_path = os.path.join(DATA, "transcripts.json")
    transcripts = json.load(open(tr_path, encoding="utf-8-sig")) if os.path.exists(tr_path) else {}
    out = []

    # a) child's baptism names the parent, the parent does not cite it
    for k, p in P.items():
        if not isinstance(k, int):
            continue
        for key in p.get("r", []):
            z = recs.get(key)
            if not z or z.get("kind") != "B":
                continue
            text = ascii_lower((transcripts.get(key) or {}).get("translation", ""))
            for r in (2 * k, 2 * k + 1):
                rp = P.get(r)
                if not rp or rp.get("st") == "unk" or key in rp.get("r", []):
                    continue
                c = name_parts(rp.get("n"))
                if len(c) < 2:
                    continue
                given, surname = ascii_lower(c[0]), ascii_lower(c[-1])[:5]
                if len(surname) >= 4 and re.search(r"\b" + re.escape(given) + r"\w*\s+(?:\w+\s+)?" + re.escape(surname), text):
                    out.append(f"family: baptism \"{key}\" of person {k} names parent {r} ({rp.get('n')}), "
                               "but the parent does not have it in `r`")

    # b) fact with a year after death
    for k, p in P.items():
        f = p.get("f", [])
        d = year_of(f, "†")
        if not d:
            continue
        for x in f:
            xs = x.strip()
            if xs[:1] in "†×*" or xs.lower().startswith("(burial)") or re.search(
                    r"widow|surviv|after (?:his|her|their) death|†|buri|\bdied\b|\bsons?\b|daughter|child|"
                    r"grand(?:son|daughter|child)|marri|wedding|bequest|\bwill\b|record|register|\bentry\b|"
                    r"\bstate[sd]\b|according|\bc\.|about|~|\?", xs, re.I):
                continue
            years = [int(y) for y in YEAR.findall(xs)]
            if years and min(years) > d + 1:
                out.append(f"family: person {k} ({p.get('n')}) † {d}, but fact \"{xs[:80]}\" has a later year")

    # c) living people in the log with a full date of birth
    log = os.path.join(DATA, "research_log.md")
    rows = open(log, encoding="utf-8-sig").read().split("\n") if os.path.exists(log) else []
    for k, p in P.items():
        y = p.get("y") or ""
        m = re.match(r"\*\s*(\d{4})$", y.strip())
        if not m or int(m.group(1)) <= 1925:
            continue
        c = name_parts(p.get("n"))
        if len(c) < 2:
            continue
        born = int(m.group(1))
        for i, row in enumerate(rows):
            if c[0] in row and c[-1][:5] in row and any(dd and yy == born for _, _, yy, _, dd in find_dates(row)):
                out.append(f"PRIVACY: research log (row {i + 1}) gives the full date of birth of living person {k} "
                           f"({p.get('n')}) – the log goes on the website; shorten it to the year")
                break

    # d) the same ancestor twice
    same = set(SAME) | set(SAME.values())
    seen = {}
    for k, p in P.items():
        if k in same or p.get("st") == "unk":
            continue
        yv = p.get("y", "") or ""
        b = year_of(p.get("f", []), "*") or (int(YEAR.search(yv).group(1)) if YEAR.search(yv) else None)
        n = ascii_lower(re.sub(r"\(.*?\)", "", p.get("n") or "")).strip()
        if not b or not n or UNKNOWN_NAME.search(n):
            continue
        key = (n, b)
        if key in seen:
            out.append(f"family: people {seen[key]} and {k} have the same name \"{p.get('n')}\" and year {b} – "
                       "is it the same ancestor (SAME)?")
        else:
            seen[key] = k
    return out


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    u = warnings()
    for x in u:
        print("warning:", x)
    print(f"{len(u)} warnings")
