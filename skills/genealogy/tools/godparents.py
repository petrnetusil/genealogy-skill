#!/usr/bin/env python3
"""Network of godparents and witnesses: who recurs in several records (godparents were often relatives – a lead to
further ancestors).

Adapted from srameko/rodokmen-skill@5f25edb (srameko, MIT), modified for the project
(paths from the project root, Kekulé numbers of the people from data/people.py next to each record, surname filter,
help).

Usage:
  python3 -I tools/godparents.py               -> listing + work/godparents.md
  python3 -I tools/godparents.py Dubois        -> only surnames starting like "Dubois" (also the female form),
                                                  even with a single occurrence
  python3 -I tools/godparents.py --min 3       -> only surnames in >= 3 records (default 2)
From every `summary` in data/records.json it takes the part from a role word (Godparent/Godfather/Godmother/Sponsor/
Witness/Best man/Midwife – also the Latin, German, French, Dutch and Czech register words, e.g. patrinus, Pate,
parrain, peter, getuige, kmotr, svědek) to the end of the sentence and pulls out names "Given Surname".
Slavic female surname forms are folded to the male form (-ová -> -, -á -> -ý) so that men and women of one family meet.
For each record it shows which people of the tree cite it (data/people.py, field r).
Writes nothing into data/.
"""
import json, os, re, sys
from collections import defaultdict
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[1:]
if argv and argv[0] in ("-h", "--help"):
    print(__doc__)
    sys.exit(0)
MIN = 2
if "--min" in argv:
    i = argv.index("--min")
    try:
        MIN = int(argv[i + 1])
    except (IndexError, ValueError):
        sys.exit("--min needs a number, e.g. --min 3")
    del argv[i:i + 2]
FILTER = argv[0] if argv else ""
try:
    with open(os.path.join(ROOT, "data", "records.json"), encoding="utf-8-sig") as fh:
        R = json.load(fh)
except (OSError, ValueError) as e:
    sys.exit(f"Cannot read data/records.json ({e}).")
R = R if isinstance(R, list) else list(R.values())
PEOPLE = defaultdict(list)   # record key -> Kekulé numbers of the people citing it
try:
    ns = {}
    exec(open(os.path.join(ROOT, "data", "people.py"), encoding="utf-8-sig").read(), ns)
    for k, o in ns["P"].items():
        for r in o.get("r", []):
            PEOPLE[r].append(k)
except (OSError, KeyError, SyntaxError):
    pass
UPPER = "A-ZÀ-ÖØ-ÞĀ-ŽČĎĚŇŘŠŤŮŽ"
LOWER = "a-zß-öø-ÿā-žčďěňřšťůž'"
name_re = re.compile(rf"\b([{UPPER}][{LOWER}]+)\s+(?:(?:née|nee|born|geb\.|roz\.)\s+)?([{UPPER}][{LOWER}]+)")
ROLE_WORDS = (r"god\w*|sponsor\w*|witness\w*|best man|midwi\w*|patrin\w*|matrin\w*|testis|testes|"
              r"pat(?:e|in|en)\b|taufpat\w*|trauzeug\w*|hebamme|parrain|marraine|témoin\w*|sage-femme|"
              r"peter|meter|getuige\w*|vroedvrouw|kmotr\w*|svěd\w*|družb\w*|porodní bab\w*")
role = re.compile(rf"\b({ROLE_WORDS})[^.]*", re.S | re.I)
GIVEN = set("Josef Jan Václav Tomáš Vojtěch Jakub Matěj František Jiří Martin Ludmila Anna Marie Marianna Kateřina Barbora "
            "Dorota Alžběta Rozálie Rosalie Magdalena Karel Antonín Ondřej Pavel Petr Matouš Šimon Vít Lukáš Mikuláš "
            "Kristián Adam Eva Terezie Veronika Johana Josefa Františka Markéta Ignác Bernard Augustin Leopold Filip Prokop "
            "Bartoloměj Řehoř Štěpán Emanuel Wenzel Joseph Johann Jiřík Voršila Apolena Salomena Lidmila Juliana "
            "John James William Thomas George Henry Charles Mary Elizabeth Margaret Catherine Sarah Ann "
            "Pierre Jean Jacques Louis François Marie Jeanne Catherine Anne Françoise Joseph Charles "
            "Pieter Jan Jozef Petrus Joannes Maria Anna Catharina Elisabeth Johanna Cornelis Hendrik Willem "
            "Johannes Josephus Franciscus Jacobus Henricus Carolus Antonius Maria Theresia Barbara Margaretha".split())
NOT_NAMES = {"Horní", "Dolní", "Nový", "Nové", "Malá", "Velká", "Svatý", "Panna", "Čteno", "Ověřeno", "Hrabě", "Pan",
             "Paní", "Saint", "Sint", "Upper", "Lower", "New", "Old", "Great", "Little", "Read", "Checked", "Count",
             "Lord", "Lady", "Mr", "Mrs", "Sir", "Our", "Holy", "The", "Both", "Parish"}


def base(s):
    for a, b in (("ová", ""), ("á", "ý")):
        if s.endswith(a) and len(s) > 4:
            return s[: -len(a)] + b
    return s


hits = defaultdict(list)
for z in R:
    if not isinstance(z, dict) or "key" not in z:
        continue
    for m in role.finditer(z.get("summary", "")):
        part = m.group(0)[len(m.group(1)):]   # names only after the role word (otherwise it would merge with a name)
        for g, s in name_re.findall(part):
            if g in NOT_NAMES or s in NOT_NAMES or s in GIVEN:
                continue
            hits[base(s)].append((z["key"], f"{g} {s}", m.group(1).lower()[:6]))
for s in [s for s in hits if s + "a" in hits]:   # Bláhová -> "Bláh": join with the male "Bláha"
    hits[s + "a"] += hits.pop(s)
if FILTER:
    f = base(FILTER)[:max(3, len(base(FILTER)) - 1)].lower()
    rows = [(s, v) for s, v in hits.items() if s.lower().startswith(f)]
else:
    rows = [(s, v) for s, v in hits.items() if len({k for k, _, _ in v}) >= MIN]
rows.sort(key=lambda x: (-len({k for k, _, _ in x[1]}), x[0]))


def people(k):
    c = PEOPLE.get(k)
    return f" [people {', '.join(map(str, sorted(c)))}]" if c else ""


out = ["# Godparents and witnesses (tools/godparents.py)" + (f" – \"{FILTER}\"" if FILTER else ""), "",
       "Recurring godparents/witnesses were often relatives (parents' siblings, brothers-in-law). Numbers in [ ] = "
       "Kekulé numbers of the people citing the record (data/people.py).", ""]
for s, v in rows:
    out.append(f"## {s} – {len({k for k, _, _ in v})} records")
    out += [f"- {who} ({r}) – `{k}`{people(k)}" for k, who, r in v]
    out.append("")
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
with open(os.path.join(ROOT, "work", "godparents.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(out) + "\n")
print(f"{len(rows)} surnames{'' if FILTER else f' in >= {MIN} records'}; written to work/godparents.md")
for s, v in rows[:40]:
    print(f"  {s}: {len({k for k, _, _ in v})} records –", ", ".join(sorted({k.split('_')[0] for k, _, _ in v})))
