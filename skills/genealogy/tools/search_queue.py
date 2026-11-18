#!/usr/bin/env python3
"""Search queue: ancestors missing at least one parent, sorted by the cheapest next step.

Adapted from srameko/rodokmen-skill@5f25edb (srameko, MIT), modified for the project
(paths from the project root, SAME – a person recorded under two numbers is searched only once, "unk" persons are
skipped, line filter and help).

Usage:
  python3 -I tools/search_queue.py                  -> listing + work/search_queue.md
  python3 -I tools/search_queue.py --line 8         -> only line 8–15 (the eight great-grandparent lines,
                                                       names in data/people.py LINES)
  python3 -I tools/search_queue.py --all            -> include closed lines
  python3 -I tools/search_queue.py --rich-from 1784 -> year from which registers are richer (default 1784)
Points (higher = earlier):
  +3  the parent's name is already in the data ("son of Jan Novák" in the facts / note – just find the baptism
      or write it down)
  +2  born in or after the --rich-from year (default 1784: in the Habsburg lands the Josephine registers give house,
      parents and grandparents; set your country's year when registers become detailed)  /  +1 born 1750 or later
  +2  house number known (no. 47),  +1 birth place known
  +1  status doc (the person is documented by a register record)
  −5  line closed by the user – not listed without --all
Closed lines: key "queue_closed_lines": [line numbers 8–15] in `data/website.json` (written only by the user).
If only one parent is missing (e.g. the mother), the person is queued as well. Writes nothing into data/.
"""
import json, os, re, sys
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[1:]
if argv and argv[0] in ("-h", "--help"):
    print(__doc__)
    sys.exit(0)


def load(path):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8-sig") as fh:
            return fh.read()
    except OSError as e:
        sys.exit(f"Cannot read {path} ({e.strerror}).")


def option(name, default=None):
    if name not in argv:
        return default
    i = argv.index(name)
    if i + 1 >= len(argv):
        sys.exit(f"{name} needs a number.")
    try:
        return int(argv[i + 1])
    except ValueError:
        sys.exit(f"{name} needs a number, not {argv[i + 1]!r}.")


ns = {}
exec(load("data/people.py"), ns)
P, LINES, SAME = ns["P"], ns.get("LINES", {}), ns.get("SAME", {})
try:
    CLOSED = {int(x) for x in json.loads(load("data/website.json")).get("queue_closed_lines", [])}
except (ValueError, TypeError):
    sys.exit('data/website.json: "queue_closed_lines" must be a list of line numbers, e.g. [12, 13].')
except SystemExit:
    CLOSED = set()   # website.json need not exist
show_all = "--all" in argv
only_line = option("--line")
RICH_FROM = option("--rich-from", 1784)
UPPER = "A-ZÀ-ÖØ-ÞĀ-ŽČĎĚŇŘŠŤŮŽ"
# Date before the year: "12 Mar 1873", "Mar 1873", "c. 1873", "before 1873", old "12. 3. 1873", "12/03/1873".
DATE = (r"(?:(?:c\.|ca\.|about|before|after|~)\s*)?"
        r"(?:\d{1,2}\s+[A-Z][a-z]{2}\.?\s+|[A-Z][a-z]{2}\.?\s+|\d{1,2}\.\s*\d{1,2}\.\s*|\d{1,2}[./]\d{1,2}[./])?")


def line_of(k):
    return k >> (k.bit_length() - 4) if k >= 8 else None


def birth_year(o):
    t = (o.get("y", "") + " " + " ".join(o.get("f", [])))
    m = re.search(rf"\*\s*{DATE}(1[5-9]\d\d)", t) or \
        re.search(r"(?:c\.\s*)?(1[5-9]\d\d)", o.get("y", ""))
    return int(m.group(1)) if m else None


def known(k):
    return k in P or k in SAME


parent_re = re.compile(rf"\b(?:son|daughter|child) of\s+(?:the\s+)?(?:late\s+|†\s*)?(?:[a-z]+\s+)?"
                       rf"([{UPPER}]\w+\s+[{UPPER}]\w+)")
place_re = re.compile(rf"^\*\s*{DATE}\d{{4}}\s+[{UPPER}]")   # "* 1852 Village", "* 12 Mar 1852 Village"
house_re = re.compile(r"\bno\.\s*\d+|čp\.\s*\d+")
rows = []
for k, o in P.items():
    if k < 2 or k in SAME or o.get("st") == "unk" or (known(2 * k) and known(2 * k + 1)):
        continue   # SAME: the parents are under the other number; unk = only a placeholder; both parents known
    ln = line_of(k)
    if only_line and ln != only_line:
        continue
    facts = o.get("f", [])
    t = " ".join(facts) + " " + o.get("note", "")
    pts, why = 0, []
    if not known(2 * k) and not known(2 * k + 1):
        why.append("both parents missing")
    else:
        why.append(("father" if not known(2 * k) else "mother") + " missing")
    m = parent_re.search(t)
    if m:
        pts += 3; why.append("parent in data: " + m.group(0))
    y = birth_year(o)
    if y and y >= RICH_FROM: pts += 2; why.append(f"from {RICH_FROM}")
    elif y and y >= 1750: pts += 1
    if house_re.search(t): pts += 2; why.append("house")
    if any(place_re.match(x) for x in facts): pts += 1
    if o.get("st") == "doc": pts += 1
    if ln in CLOSED:
        pts -= 5
        if not show_all: continue
    rows.append((pts, k, o["n"], y or "", LINES.get(ln, ("?",))[0] if ln else "", "; ".join(why)))
rows.sort(key=lambda x: (-x[0], -(x[3] or 0)))
out = ["# Search queue (tools/search_queue.py)" + (f" – line {only_line}" if only_line else ""), "",
       "| points | no. | person | * | line | why |", "|---|---|---|---|---|---|"]
out += [f"| {b} | {k} | {n} | {y} | {r} | {d} |" for b, k, n, y, r, d in rows]
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
with open(os.path.join(ROOT, "work", "search_queue.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(out) + "\n")
print(f"{len(rows)} people at the edge (closed lines {'included' if show_all else 'skipped'}); written to work/search_queue.md")
for b, k, n, y, r, d in rows[:25]:
    print(f"  {b:>2} pts | {k:>6} | {n} (* {y}) | {r} | {d}")
