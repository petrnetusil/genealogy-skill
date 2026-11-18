#!/usr/bin/env python3
# Based on sarsonj/rodokmen-skill PR #126 by Vojtěch Pražák (commit 1c7fe2a; MIT) – logic unchanged, translated to English.
"""Family reconstruction and deciding between candidates – a small database of one "case" in data/cases/<case>.json.

When: (1) you rebuild an ancestor's whole family from the siblings' baptisms (godparents, house, grandparents
complement each other); (2) several people with the same name fit an ancestor's place (18th century: in one village
two couples "Václav × Kateřina" baptise children at the same time).
Procedure like breadth-first search (BFS): write down the candidates, read records for each in layers
(1 = their own baptism, marriage, death; 2 = their children, godparents, witnesses, siblings; 3 = parents, in-laws…)
and after each layer look at where the candidate's people or houses meet what is documented about the ancestor
("anchors").

Usage (from the project root; no network, reads files only):
  cases.py new <case> "goal" [--person N]          creates a case (N = Ahnentafel number of the ancestor, optional)
  cases.py candidate <case> <id> "description"     adds a candidate (short id: A, B, son_of_jan…)
  cases.py state <case> <id> open|excluded|confirmed "reason"
  cases.py record <case> <file.json>               adds a record you have read (object or list of objects, format below)
  cases.py task <case> <candidate|all> <layer> "what to look for" ["where: volume, images"]
  cases.py done <case> <task> "result" [--nothing]  --nothing = searched, found nothing (a result too)
  cases.py overview <case>     candidates, records, what is next (the lowest layer with open tasks)
  cases.py intersect <case>    matches of the candidates' people and houses with anchors and with data/people.py
  cases.py families <case>     children grouped by parents: order, gaps, repeated names, regular godparents
  cases.py list                all cases in the project

Record (work/x.json):
  {"belongs": "anchor" | "<candidate id>" | "?",   anchor = documented about the ancestor; "?" = not known yet whose
   "kind": "B" | "M" | "D" | "O", "date": "3 Mar 1760", "place": "Lhota", "house": "5",
   "source": "a1b2c3d4 img. 10", "key": "<key in data/records.json, if already there>", "note": "…",
   "people": [{"name": "Václav Novák", "role": "father", "house": "5", "place": "Lhota", "note": "farmer"}, …]}
Roles: child, father, mother, groom, bride, groom_father, groom_mother, bride_father, bride_mother, godfather,
godmother, witness, midwife, deceased, husband, wife, parent, other. Write names in the form used in data/people.py
(nominative, the usual modern spelling: Wenceslaus → Václav, Joannes → Jan); uncertain names with "(?)".

Case file keys: case, goal, person (optional), candidates {id: {state, reason, description}},
records [{id, belongs, kind, date, place, house, source, key, note, people [{name, role, house, place, note}]}],
tasks [{id, candidate, layer, what, where, state (pending|done|nothing), result}].

The tool compares names loosely (Latin, German, French, Dutch and English given names, Czech feminine -ová, w/v, cz/č…),
so matches are only SUGGESTIONS: check each one in the record. Evidence decides, not the number of matches.
Only a confirmed candidate goes into data/people.py.
"""
import json, os, re, sys, unicodedata
from collections import defaultdict
for _s in (sys.stdout, sys.stderr):   # UTF-8 output even on Windows without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:   # python3 -I does not put the script's folder on sys.path
    sys.path.insert(0, TOOLS)
from evidence_check import find_dates  # noqa: E402

ROOT = os.getcwd()
FOLDER = os.path.join(ROOT, "data", "cases")   # research state – belongs in git, the website does not read it
ROLES = {"child", "father", "mother", "groom", "bride", "groom_father", "groom_mother", "bride_father", "bride_mother",
         "godfather", "godmother", "witness", "midwife", "deceased", "husband", "wife", "parent", "other"}
STATES = ("open", "excluded", "confirmed")

# Given names: Latin, German, French, Dutch and English forms from registers → one canonical key (lower case, ASCII).
# The keys are only internal identifiers (here the Czech forms); add your own variants as needed.
GIVEN = {
    "vaclav": "wenceslaus wenzel wenzl wentzel venceslaus wenceslai wenceslas",
    "jan": "joannes johannes johann hans joanne joannis john jean johan jehan",
    "katerina": "catharina katharina katharine catherina catherine katrien catharine",
    "ondrej": "andreas andre andreae andrew andries", "jiri": "georgius georg georgii george georges joris",
    "antonin": "antonius anton antoni antoine antoon anthony", "frantisek": "franciscus franz francisci francois frans francis",
    "frantiska": "francisca franziska francoise", "josef": "josephus joseph josephi jozef", "josefa": "josepha josephine",
    "rozalie": "rosalia rozalia rosalie", "anna": "anne", "marie": "maria mary",
    "terezie": "theresia teresia theresa terezia therese", "vavrinec": "laurentius lorenz laurenz laurent lawrence",
    "mikulas": "nicolaus nikolaus nicolai nicolas nicholas klaas", "martin": "martinus", "matej": "matthias mathias matthaeus mathieu matthew",
    "petr": "petrus peter pierre pieter", "pavel": "paulus paul", "tomas": "thomas", "jakub": "jacobus jakob jacob jacques james",
    "vojtech": "adalbertus adalbert", "augustin": "augustinus", "dorota": "dorothea dorothee", "magdalena": "magdalene madeleine",
    "veronika": "veronica veronique", "barbora": "barbara", "alzbeta": "elisabetha elisabeth elizabeth isabelle",
    "ludmila": "ludmilla", "justina": "justine", "judita": "judith", "tobias": "tobiae", "karel": "carolus karl charles",
    "ignac": "ignatius ignaz ignace", "alois": "aloysius aloys", "simon": "simeon", "stepan": "stephanus stephan etienne stephen",
    "vit": "vitus veit", "zuzana": "susanna susana zuzanna suzanne", "eva": "eva", "kristina": "christina christine",
    "jindrich": "henricus heinrich henri hendrik henry", "bartolomej": "bartholomaeus barthelemy", "filip": "philippus philipp philippe",
    "rehor": "gregorius gregor gregoire", "michal": "michael michel michiel", "jakub_": "", "lukas": "lucas luc",
    "marek": "marcus marc", "ludvik": "ludovicus ludwig louis lodewijk lewis", "daniel": "danielus", "adam": "adamus", "eliska": "",
}
_GV = {}
for key, vs in GIVEN.items():
    _GV[key.rstrip("_")] = key.rstrip("_")
    for v in vs.split():
        _GV[v] = key.rstrip("_")


def ascii_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def given_key(s):
    s = re.sub(r"[^a-z ]", " ", ascii_lower(s)).split()
    return _GV.get(s[0], s[0]) if s else ""


def surname_key(s):
    """Loose surname key: Novák, Nowak, Nowák, Nováková, Nováčka → novak; Petráček, Petráčková → petrak."""
    s = re.sub(r"[^a-z]", "", ascii_lower(s))
    s = s.replace("sch", "s").replace("cz", "c").replace("w", "v").replace("y", "i").replace("ia", "a")
    s = s.replace("tz", "c").replace("ch", "#").replace("c", "k").replace("#", "ch")
    for end in ("ovich", "ova", "ovi", "ove", "a"):     # feminine form and endings → stem
        if len(s) > 4 and s.endswith(end):
            s = s[: -len(end)]
            break
    if s.endswith("ek"):                                # mobile e: Javůrek / Javůrková, Doleček / Dolečková
        s = s[:-2] + "k"
    s = re.sub(r"(.)\1+", r"\1", s)
    return s


def person_key(name):
    parts = [c for c in re.sub(r"\(\?\)|\[.*?\]|†|\+", " ", name).split() if c]
    if not parts:
        return None
    if len(parts) == 1:
        return (given_key(parts[0]), "")
    return (given_key(parts[0]), surname_key(parts[-1]))


def house_key(place, house):
    if not house:
        return None
    return (surname_key(place or "")[:4], re.sub(r"\D", "", str(house)))


def path_of(case):
    if not re.fullmatch(r"[a-z0-9_]+", case):
        sys.exit("ERROR: case name only lower-case letters without diacritics, digits and _ (e.g. vaclav_512)")
    return os.path.join(FOLDER, case + ".json")


def load(case):
    c = path_of(case)
    if not os.path.exists(c):
        sys.exit(f"ERROR: case {case} does not exist ({c}); create it: cases.py new {case} \"goal\"")
    with open(c, encoding="utf-8") as f:
        return json.load(f)


def save(case, d):
    os.makedirs(FOLDER, exist_ok=True)
    tmp = path_of(case) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path_of(case))


def new_id(items, letter):
    n = max([int(x["id"][1:]) for x in items if re.fullmatch(letter + r"\d+", x.get("id", ""))] + [0])
    return f"{letter}{n + 1}"


def ancestors():
    """People from data/people.py (P and SIDE) as {key: [description]} – for matches with the family tree."""
    p = os.path.join(ROOT, "data", "people.py")
    out = defaultdict(list)
    if not os.path.exists(p):
        return out
    ns = {}
    try:
        exec(open(p, encoding="utf-8-sig").read(), ns)
    except Exception as e:
        print(f"warning: data/people.py cannot be loaded ({e}), skipping matches with the family tree")
        return out
    for k, o in ns.get("P", {}).items():
        kl = person_key(o.get("n", ""))
        if kl and kl[1]:
            out[kl].append((year(o.get("y", "") + " " + " ".join(o.get("f", [])[:1])), f"no. {k} {o.get('n')}"))
    for o in ns.get("SIDE", []):
        kl = person_key(re.sub(r"\(.*?\)", "", o.get("n", "")))
        if kl and kl[1]:
            out[kl].append((year(o.get("n", "") + " " + o.get("t", "")), f"relative of no. {o.get('k')}: {o.get('n')}"))
    return out


CONTEMPORARY = 80   # difference in years up to which a person from the tree counts as a possible match (otherwise a namesake)


def contemporaries(tree, kl, r):
    return [t for y, t in tree.get(kl, []) if not (y and r and abs(y - r) > CONTEMPORARY)]


def describe_record(z):
    return f"{z['id']} {z.get('kind', '?')} {z.get('date', '')} {z.get('place', '')}" + \
           (f" no. {z['house']}" if z.get("house") else "") + (f" ({z['source']})" if z.get("source") else "")


# ---------------------------------------------------------------- commands
def cmd_new(a):
    if len(a) < 2:
        sys.exit("usage: cases.py new <case> \"goal\" [--person N]")
    case, goal = a[0], a[1]
    if os.path.exists(path_of(case)):
        sys.exit(f"ERROR: case {case} already exists")
    d = {"case": case, "goal": goal, "candidates": {}, "records": [], "tasks": []}
    if "--person" in a:
        d["person"] = int(a[a.index("--person") + 1])
    save(case, d)
    print(f"created: {path_of(case)}\nNext: anchors (documented records about the ancestor) via `record` with "
          f"\"belongs\": \"anchor\", then candidates (`candidate`) and layer-1 tasks (`task`).")


def cmd_candidate(a):
    if len(a) < 3:
        sys.exit("usage: cases.py candidate <case> <id> \"description\"")
    d = load(a[0])
    if not re.fullmatch(r"[A-Za-z0-9_]+", a[1]) or a[1] in ("anchor", "all"):
        sys.exit("ERROR: candidate id only letters, digits and _ (not \"anchor\" or \"all\")")
    d["candidates"].setdefault(a[1], {"state": "open", "reason": ""})["description"] = a[2]
    save(a[0], d)
    print(f"candidate {a[1]}: {a[2]}")


def cmd_state(a):
    if len(a) < 4 or a[2] not in STATES:
        sys.exit("usage: cases.py state <case> <id> open|excluded|confirmed \"reason\"")
    d = load(a[0])
    if a[1] not in d["candidates"]:
        sys.exit(f"ERROR: candidate {a[1]} is not in the case ({', '.join(d['candidates'])})")
    d["candidates"][a[1]].update(state=a[2], reason=a[3])
    if a[2] == "confirmed":
        others = [k for k, v in d["candidates"].items() if k != a[1] and v["state"] == "confirmed"]
        if others:
            print(f"WARNING: {', '.join(others)} is confirmed too – only one should be confirmed")
    save(a[0], d)
    print(f"{a[1]}: {a[2]} – {a[3]}")
    if a[2] == "confirmed":
        print("Now write it into data/people.py (st=\"doc\" only if a record states the link directly, otherwise \"prob\" "
              "with a note why) and into the research log. Candidates left open should have a reason in the log why "
              "they were dropped.")


def cmd_record(a):
    if len(a) < 2:
        sys.exit("usage: cases.py record <case> <file.json>")
    d = load(a[0])
    with open(a[1], encoding="utf-8-sig") as f:
        data = json.load(f)
    for z in data if isinstance(data, list) else [data]:
        belongs = z.get("belongs", "?")
        if belongs not in ("anchor", "?") and belongs not in d["candidates"]:
            sys.exit(f"ERROR: \"belongs\": \"{belongs}\" – the candidate does not exist (create it with `candidate`)")
        if not z.get("people"):
            sys.exit("ERROR: record without \"people\" – list everyone in the record with their role "
                     "(godparents and witnesses are the most valuable)")
        for o in z["people"]:
            if o.get("role") not in ROLES:
                print(f"warning: role \"{o.get('role')}\" of {o.get('name')} is not in the list ({', '.join(sorted(ROLES))})")
        dup = [x["id"] for x in d["records"] if x.get("source") and x.get("source") == z.get("source")
               and x.get("date") == z.get("date")]
        if dup:
            print(f"warning: {', '.join(dup)} already has the same source and date – are you adding it twice?")
        z["id"] = new_id(d["records"], "z")
        z["belongs"] = belongs
        d["records"].append(z)
        print(f"recorded {describe_record(z)} → {belongs}, {len(z['people'])} people")
    save(a[0], d)


def cmd_task(a):
    if len(a) < 4:
        sys.exit("usage: cases.py task <case> <candidate|all> <layer> \"what to look for\" [\"where\"]")
    d = load(a[0])
    if a[1] != "all" and a[1] not in d["candidates"]:
        sys.exit(f"ERROR: candidate {a[1]} is not in the case")
    u = {"id": new_id(d["tasks"], "u"), "candidate": a[1], "layer": int(a[2]), "what": a[3],
         "where": a[4] if len(a) > 4 else "", "state": "pending", "result": ""}
    d["tasks"].append(u)
    save(a[0], d)
    print(f"task {u['id']} (layer {u['layer']}, {u['candidate']}): {u['what']}")


def cmd_done(a):
    if len(a) < 3:
        sys.exit("usage: cases.py done <case> <task> \"result\" [--nothing]")
    d = load(a[0])
    for u in d["tasks"]:
        if u["id"] == a[1]:
            u.update(state="nothing" if "--nothing" in a else "done", result=a[2])
            save(a[0], d)
            print(f"{u['id']}: {u['state']} – {a[2]}")
            return
    sys.exit(f"ERROR: task {a[1]} is not in the case")


def open_candidates(d):
    return [k for k, v in d["candidates"].items() if v["state"] == "open"]


def cmd_overview(a):
    d = load(a[0])
    print(f"CASE {d['case']}: {d['goal']}" + (f" (ancestor no. {d['person']})" if d.get("person") else ""))
    anchors = [z for z in d["records"] if z["belongs"] == "anchor"]
    print(f"\nAnchors (documented about the ancestor): {len(anchors)}")
    for z in anchors:
        print(f"  {describe_record(z)}" + (f" – {z['note']}" if z.get("note") else ""))
    print("\nCandidates:")
    for k, v in d["candidates"].items():
        zz = [z for z in d["records"] if z["belongs"] == k]
        print(f"  [{v['state']}] {k}: {v.get('description', '')}" + (f" – {v['reason']}" if v.get("reason") else ""))
        for z in zz:
            print(f"      {describe_record(z)}" + (f" – {z['note']}" if z.get("note") else ""))
    unassigned = [z for z in d["records"] if z["belongs"] == "?"]
    if unassigned:
        print(f"\nRecords not assigned (?): {len(unassigned)}")
        for z in unassigned:
            print(f"  {describe_record(z)}" + (f" – {z['note']}" if z.get("note") else ""))
    op = open_candidates(d)
    confirmed = [k for k, v in d["candidates"].items() if v["state"] == "confirmed"]
    if confirmed:
        print(f"\nDECIDED: {', '.join(confirmed)}. Remaining tasks only rebuild the family.")
    pending = [u for u in d["tasks"] if u["state"] == "pending" and (u["candidate"] == "all" or u["candidate"] in op or confirmed)]
    if pending:
        v = min(u["layer"] for u in pending)
        print(f"\nNEXT – layer {v} (breadth first: finish the layer for all open candidates before going deeper):")
        for u in pending:
            if u["layer"] == v:
                print(f"  {u['id']} [{u['candidate']}] {u['what']}" + (f" – {u['where']}" if u["where"] else ""))
        later = sorted({u["layer"] for u in pending if u["layer"] > v})
        if later:
            print(f"  (layers {', '.join(map(str, later))} are waiting too)")
    elif len(op) > 1:
        top = max([u["layer"] for u in d["tasks"]] + [0])
        print(f"\nLayer {top} is done and candidates {', '.join(op)} are still open. Run `intersect`; if it does not "
              f"decide, add layer-{top + 1} tasks: children and their godparents, marriage witnesses, siblings, death "
              f"with age, the bride's family – the same kinds of records for every candidate, so the comparison is fair.")
    elif len(op) == 1 and not confirmed:
        print(f"\nOnly one open candidate is left ({op[0]}). Before confirming: does it have at least one direct match "
              f"with an anchor (`intersect`)? Excluding the others is not enough – there may be someone we have not found.")
    finished = [u for u in d["tasks"] if u["state"] != "pending"]
    if finished:
        print(f"\nFinished tasks: {len(finished)}")
        for u in finished:
            print(f"  {u['id']} l{u['layer']} [{u['candidate']}] {u['what']} → {u['state']}: {u['result']}")


def record_people(z):
    for o in z.get("people", []):
        kl = person_key(o.get("name", ""))
        if kl:
            yield kl, o, house_key(o.get("place") or z.get("place"), o.get("house") or (z.get("house") if o.get("role") in (
                "father", "mother", "child", "deceased", "groom") else ""))


def cmd_intersect(a):
    d = load(a[0])
    tree = ancestors()
    anchor_p, anchor_h = defaultdict(list), defaultdict(list)
    for z in d["records"]:
        if z["belongs"] == "anchor":
            for kl, o, hk in record_people(z):
                if kl[1]:
                    anchor_p[kl].append(f"{o.get('role')} in {z['id']}")
                if hk:
                    anchor_h[hk].append(f"{o.get('name')} ({o.get('role')}) in {z['id']}")
    print(f"INTERSECTION – case {d['case']}. Matches are based on loose name comparison: check each one in the record.\n")
    found = {}   # candidate -> {(type, key): [lines]}
    for k, v in d["candidates"].items():
        found[k] = defaultdict(list)
        for z in (z for z in d["records"] if z["belongs"] == k):
            r = year(z.get("date", ""))
            for kl, o, hk in record_people(z):
                who = f"{o.get('name')} ({o.get('role')} in {z['id']}, {z.get('date', '')})"
                if kl[1] and kl in anchor_p:
                    found[k][("person", kl)].append(f"PERSON   {who} ~ anchors: {'; '.join(anchor_p[kl])}")
                sr = contemporaries(tree, kl, r) if kl[1] else []
                if sr:
                    found[k][("tree", kl)].append(f"TREE     {who} ~ {'; '.join(sr[:3])}")
                if hk and hk in anchor_h:
                    found[k][("house", hk)].append(f"HOUSE    no. {hk[1]}: {who} ~ anchors: {'; '.join(anchor_h[hk])}")
    op = open_candidates(d)
    common = set.intersection(*(set(found[k]) for k in op)) if len(op) > 1 else set()
    for k, v in d["candidates"].items():
        n = sum(1 for z in d["records"] if z["belongs"] == k)
        print(f"[{v['state']}] {k}: {v.get('description', '')}  ({n} records)")
        own = [kl for kl in found[k] if kl not in common]
        for kl in own:
            for line in found[k][kl]:
                print("   " + line)
        if not own:
            print("   no own match" + (" – no records yet" if not n else ""))
    if common:
        print("\nDOES NOT DISTINGUISH (match for all open candidates – usually the candidate or the whole village): " +
              ", ".join(f"{t} {' '.join(x for x in kl if x)}" for t, kl in sorted(common)))
    if len(op) > 1:
        print("\nOwn matches: " + ", ".join(f"{k} {len([x for x in found[k] if x not in common])}" for k in op))
        print("Evidence decides, not the count: a matching house or godparent is a clue, a direct \"son of X\" is proof.")


def cmd_families(a):
    d = load(a[0])
    couples = defaultdict(list)
    for z in d["records"]:
        if z.get("kind") != "B":
            continue
        role = defaultdict(list)
        for o in z.get("people", []):
            role[o.get("role")].append(o)
        if not role.get("child"):
            continue
        fa = role["father"][0]["name"] if role.get("father") else "father not named"
        mo = role["mother"][0]["name"] if role.get("mother") else "?"
        key = (person_key(fa) or ("", ""), given_key(mo), z["belongs"])
        couples[key].append((z, role, fa, mo))
    if not couples:
        print("No baptisms (kind B with role child) – record the siblings' baptisms with the `record` command.")
        return
    couple_godparents = {}
    for key, kids in sorted(couples.items(), key=lambda x: year(x[1][0][0].get("date", ""))):
        kids.sort(key=lambda x: full_day(x[0].get("date", "")) or (year(x[0].get("date", "")), 0, 0))
        z0, _, fa, mo = kids[0]
        print(f"\n{fa} × {mo}: {len(kids)} children  (belongs: {', '.join(sorted({x[0]['belongs'] for x in kids}))})")
        names, previous, gp, last_day = {}, None, defaultdict(int), None
        for z, role, _, _ in kids:
            r = year(z.get("date", ""))
            child = role["child"][0]["name"]
            gg = [o["name"] for x in ("godfather", "godmother") for o in role.get(x, [])]
            # regular godparents: in the 18th century the same people alternate as godparent and witness – count both
            for o in gg + [o["name"] for o in role.get("witness", [])]:
                gp[person_key(o)] += 1
            notes = []
            gk = given_key(child)
            if gk in names:
                notes.append(f"the name was already given to a child of {names[gk]} – that child probably died")
            names[gk] = z.get("date", "")
            dd = full_day(z.get("date", ""))
            if dd and last_day:
                days = day_count(dd) - day_count(last_day)
                if 2 < days < 270:
                    notes.append(f"only {max(1, round(days / 30.44))} month(s) after the previous child – one mother cannot manage that: two "
                                 "couples of the same name, or a misread date (month/year is often in the column header)")
                elif 0 <= days <= 2:
                    notes.append("same day as the previous child – twins?")
            last_day = dd or last_day
            if previous and r and r - previous >= 4:
                notes.append(f"gap of {r - previous} years – a child is missing, or recorded elsewhere")
            previous = r or previous
            print(f"  {z.get('date', ''):<14} {child:<22} no. {z.get('house') or '–':<5} godparents: {', '.join(gg) or '–'}"
                  f"  [{z['id']}]" + (f"  ← {'; '.join(notes)}" if notes else ""))
        regular = [k for k, n in gp.items() if n >= 2 and k]
        couple_godparents[key] = set(gp)
        if regular:
            print(f"  regular godparents: {', '.join(' '.join(x for x in k if x) for k in regular)}")
    # godparents shared by two couples – the families knew each other / were related
    kl = list(couple_godparents)
    for i in range(len(kl)):
        for j in range(i + 1, len(kl)):
            sp = {k for k in couple_godparents[kl[i]] & couple_godparents[kl[j]] if k and k[1]}
            if sp:
                print(f"\nCommon godparent of couples {couples[kl[i]][0][2]} × {couples[kl[i]][0][3]} and {couples[kl[j]][0][2]} × "
                      f"{couples[kl[j]][0][3]}: {', '.join(' '.join(k) for k in sp)}")
    same = defaultdict(list)
    for kl in couples:
        same[kl[:2]].append(kl[2])
    for kl, where in same.items():
        if len(where) > 1:
            print(f"\nCouple {couples[(*kl, where[0])][0][2]} × {couples[(*kl, where[0])][0][3]} has children under: "
                  f"{', '.join(where)}. Whether it is one couple or several of the same name, decide by the house and "
                  "godparents above.")
    if any(kl[2] == "?" for kl in couples):
        print("\nAssign children with \"belongs\": \"?\" to a candidate once you decide (edit the case file).")


def full_day(date):
    """"18 Jan 1764" (or old "18. 1. 1764") → (1764, 1, 18); incomplete date → None."""
    for _, _, y, m, d in find_dates(date or ""):
        if d:
            return (y, m, d)
    return None


def day_count(d):
    """Approximate number of days since year 0 – enough for the gap between births."""
    return int(d[0] * 365 + d[0] // 4 + (d[1] - 1) * 30.44 + d[2])


def year(date):
    m = re.search(r"\d{4}", date or "")
    return int(m.group()) if m else 0


def cmd_list(a):
    if not os.path.isdir(FOLDER):
        print("No cases (data/cases/ does not exist).")
        return
    for f in sorted(os.listdir(FOLDER)):
        if f.endswith(".json"):
            try:
                d = json.load(open(os.path.join(FOLDER, f), encoding="utf-8"))
                op = open_candidates(d)
                pending = sum(1 for u in d.get("tasks", []) if u["state"] == "pending")
                print(f"{d['case']}: {d['goal']} – candidates {len(d['candidates'])} (open {len(op)}), "
                      f"records {len(d['records'])}, pending tasks {pending}")
            except (ValueError, KeyError):
                pass   # another file in the folder (working notes), not a case


COMMANDS = {"new": cmd_new, "candidate": cmd_candidate, "state": cmd_state, "record": cmd_record, "task": cmd_task,
            "done": cmd_done, "overview": cmd_overview, "intersect": cmd_intersect, "families": cmd_families, "list": cmd_list}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 2)
    COMMANDS[sys.argv[1]](sys.argv[2:])
