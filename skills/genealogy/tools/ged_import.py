#!/usr/bin/env python3
"""Extracts a family tree (GEDCOM .ged from MyHeritage, Geni, FamilySearch…) for the genealogy project.

Usage (from the project root):
  python3 -I tools/ged_import.py documents/tree.ged                   -> list of people (id | name | birth)
  python3 -I tools/ged_import.py documents/tree.ged "Given Surname"   -> ancestors of this person with Kekulé numbers
                                                                         (1 = the person, 2 = father, 3 = mother…), all
                                                                         events, notes and a QUEUE OF RECORDS to look up
  … "Given Surname" --people   -> the same as a skeleton for data/people.py (status "fam", to check and complete)
  … --limits 100,75,30         -> closure periods in years for births, marriages, deaths (default: the Czech ones);
                                  younger records are usually only at the civil registry office, not online

Queue of records: for every ancestor the youngest known event with a place (death, then marriage, then birth) –
death and marriage records give the date and place of birth and the parents, so one searches from the youngest record.
E-mails and addresses from the tree are not printed.
Dates are written in the project's form: "14 Feb 1890", "c. 1850", "before 1900", "between 1850 and 1855".
Encoding: UTF-8; older files with the header "1 CHAR ANSI" (Brother's Keeper) are read as Windows-1250, and Czech
dates of such exports ("SRPEN 1945", "PODZIM 1951", "1926 NEBO 1927", "11.11.1934") become "Aug 1945",
"autumn 1951", "1926 or 1927", "11 Nov 1934".
"""
import datetime, re, sys
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

EVENTS = {"BIRT": "*", "CHR": "* (baptism)", "DEAT": "†", "BURI": "† (burial)", "MARR": "×"}
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
MON = [m.title() for m in MONTHS]   # "Jan" … "Dec" – the project's date form "14 Feb 1890"
# Czech dates from Brother's Keeper ("SRPEN 1945", "PODZIM 1951", "1926 NEBO 1927", "ASI 1930", "11.11.1934")
CZ_MONTHS = {m: i for i, m in enumerate("LEDEN ÚNOR BŘEZEN DUBEN KVĚTEN ČERVEN ČERVENEC SRPEN ZÁŘÍ ŘÍJEN LISTOPAD PROSINEC".split())}
CZ_WORDS = {"JARO": "spring", "LÉTO": "summer", "PODZIM": "autumn", "ZIMA": "winter", "NEBO": "or", "ASI": "c.",
            "OKOLO": "c.", "PŘED": "before", "PO": "after", "MEZI": "between", "A": "and"}


def decode(data):
    """UTF-8; when the file is not UTF-8 and the header says "1 CHAR ANSI" (Brother's Keeper etc.), Windows-1250."""
    # join CONC already in bytes: MyHeritage splits long lines even in the middle of a multi-byte UTF-8 character
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):   # UTF-16 ("1 CHAR UNICODE", older Family Tree Maker, Legacy…)
        data = data.decode("utf-16").encode("utf-8")
    data = re.sub(rb"\r?\n[ \t]*\d+[ \t]+CONC(?: |(?=\r?\n))", b"", data)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    m = re.search(rb"^\s*1\s+CHAR\s+(\S+)", data[:5000], re.M)
    char = m.group(1).decode("ascii", "replace").upper() if m else ""
    if char in ("ANSI", "WINDOWS-1250", "CP1250"):
        return data.decode("cp1250", "replace")
    if char == "ANSEL":
        print("WARNING: the tree is in the ANSEL encoding – accented letters may be broken; export it again in UTF-8.",
              file=sys.stderr)
    return data.decode("utf-8", "replace")


def read(path):
    raw = decode(open(path, "rb").read()).lstrip("﻿")
    recs, cur, stack = {}, None, []
    for line in raw.splitlines():
        m = re.match(r"\s*(\d+)\s+(@[^@]+@\s+)?(\S+)\s?(.*)$", line)
        if not m:
            continue
        lvl, xref, tag, val = int(m.group(1)), (m.group(2) or "").strip(), m.group(3), m.group(4)
        if lvl == 0:
            cur = {"_id": xref, "_type": tag, "_sub": [], "val": val} if xref else None   # val: text of a shared note
            if cur:
                recs[xref] = cur
            stack = [cur]
            continue
        if cur is None:
            continue
        stack = stack[:lvl]
        parent = stack[-1] if stack else cur
        if tag in ("CONC", "CONT") and parent is not None:
            parent["val"] = parent.get("val", "") + ("\n" if tag == "CONT" else "") + val
            stack.append(parent)
            continue
        node = {"tag": tag, "val": val, "_sub": []}
        parent["_sub"].append(node)
        stack.append(node)
    return recs


def sub(node, tag):
    return [n for n in node["_sub"] if n["tag"] == tag]


def first(node, tag, default=""):
    s = sub(node, tag)
    return s[0].get("val", "").strip() if s else default


def date_en(d):
    """'14 FEB 1890' -> '14 Feb 1890', 'ABT 1850' -> 'c. 1850', 'BET 1850 AND 1855' -> 'between 1850 and 1855'."""
    d = d.strip()
    pre = ""
    for k, v in (("ABT", "c. "), ("EST", "c. "), ("CAL", "c. "), ("BEF", "before "), ("AFT", "after "), ("BET", "between ")):
        if d.startswith(k):
            pre, d = v, d[len(k):].strip()
    d = d.replace(" AND ", " and ")
    def one(m):
        day, mon, yr = m.group(1), m.group(2), m.group(3)
        return f"{str(int(day)) + ' ' if day else ''}{MON[MONTHS.index(mon)] + ' ' if mon else ''}{yr}"
    d = re.sub(r"(?:(\d{1,2}) )?(?:(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) )?(\d{3,4})", one, d)
    if re.search(r"[A-ZÁ-Ž]{2,}|\d\.\d", d) and not re.search(r"[a-z]", d):   # only Czech dates, not an English GEDCOM
        d = re.sub(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\b",
                   lambda m: f"{int(m[1])} {MON[int(m[2]) - 1]} {m[3]}" if 1 <= int(m[2]) <= 12 else m[0], d)
        d = re.sub(r"[A-ZÁ-Ž]+", lambda m: MON[CZ_MONTHS[m[0]]] if m[0] in CZ_MONTHS else CZ_WORDS.get(m[0], m[0]), d)
        d = re.sub(r"\b(\d{1,2})\.\s*(?=[A-Z][a-z]{2} )", r"\1 ", d)   # "11. Aug 1945" -> "11 Aug 1945"
    return pre + d


def year(d):
    m = re.search(r"\d{4}", d or "")
    return int(m.group()) if m else None


def name(ind):
    n = first(ind, "NAME").replace("/", "").strip()
    return re.sub(r"\s+", " ", n) or "(no name)"


def events(ind, recs):
    out = []
    for n in ind["_sub"]:
        if n["tag"] in EVENTS:
            d, p = first(n, "DATE"), first(n, "PLAC")
            extra = first(n, "CAUS")
            out.append((n["tag"], date_en(d) if d else "", p, extra))
    for fam_id in [n["val"] for n in sub(ind, "FAMS")]:
        fam = recs.get(fam_id.strip())
        if not fam:
            continue
        spouse = [recs.get(n["val"].strip()) for n in fam["_sub"] if n["tag"] in ("HUSB", "WIFE") and n["val"].strip() != ind["_id"]]
        for m in sub(fam, "MARR"):
            d, p = first(m, "DATE"), first(m, "PLAC")
            out.append(("MARR", date_en(d) if d else "", p, name(spouse[0]) if spouse and spouse[0] else ""))
    return out


def parents(ind, recs):
    for n in sub(ind, "FAMC"):
        fam = recs.get(n["val"].strip())
        if fam:
            h, w = first(fam, "HUSB"), first(fam, "WIFE")
            return recs.get(h), recs.get(w)
    return None, None


def find(recs, query):
    q = query.lower().split()
    hits = [r for r in recs.values() if r["_type"] == "INDI" and all(w in name(r).lower() for w in q)]
    if not hits:
        sys.exit(f"Person \"{query}\" is not in the tree. Run without a name for the list of people.")
    if len(hits) > 1:
        print("Several people match, use the id instead of the name:", file=sys.stderr)
        for h in hits:
            print(f"  {h['_id']} | {name(h)}", file=sys.stderr)
        sys.exit(1)
    return hits[0]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    recs = read(sys.argv[1])
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    as_py = "--people" in sys.argv
    limits = {"death": 30, "marriage": 75, "birth": 100}   # Czech closure periods (years); other countries differ
    if "--limits" in sys.argv:
        i = sys.argv.index("--limits")
        try:
            b, m, d = (int(x) for x in sys.argv[i + 1].split(","))
        except (IndexError, ValueError):
            sys.exit("--limits needs three numbers: births,marriages,deaths – e.g. --limits 100,75,30")
        limits = {"death": d, "marriage": m, "birth": b}
        args = [a for a in args if a != sys.argv[i + 1]]
    if not args:
        for r in recs.values():
            if r["_type"] == "INDI":
                b = next((e for e in events(r, recs) if e[0] == "BIRT"), None)
                print(f"{r['_id']} | {name(r)} | {('* ' + b[1] + ' ' + b[2]).strip() if b and (b[1] or b[2]) else ''}")
        return
    start = recs.get(args[0]) or find(recs, args[0])
    tree, todo = {1: start}, [1]
    while todo:
        k = todo.pop(0)
        f, m = parents(tree[k], recs)
        for kk, p in ((2 * k, f), (2 * k + 1, m)):
            if p:
                linie, j = [], k   # own line below kk: child, grandchild… down to the home person
                while j >= 1:
                    linie.append(tree[j]["_id"])
                    j //= 2
                if p["_id"] in linie:   # error in the tree: a person is their own ancestor → endless loop
                    print(f"WARNING: loop in the tree – {name(p)} is recorded as their own ancestor (an error in the tree, "
                          "check it with the family); not following this branch further.", file=sys.stderr)
                    continue
                tree[kk] = p
                todo.append(kk)
    queue = []
    if as_py:
        print("P = {")
    for k in sorted(tree):
        ind = tree[k]
        ev = events(ind, recs)
        facts = []
        for tag, d, p, extra in ev:
            if tag == "MARR":
                facts.append(" ".join(x for x in ("×", d, p, extra) if x))
            elif d or p:   # cause of death only in the listing, not in the data skeleton (health data)
                facts.append(" ".join(x for x in (EVENTS[tag], d, p) if x) + (f" ({extra})" if extra and not as_py else ""))
        facts += [first(n, "OCCU") or n.get("val", "") for n in sub(ind, "OCCU")]
        notes = [n.get("val", "") for n in sub(ind, "NOTE")]
        notes = [(recs.get(t.strip(), {}).get("val", "") if re.fullmatch(r"\s*@[^@]+@\s*", t) else t) for t in notes]   # shared note @N1@
        notes = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip() for t in notes]
        notes = [n for n in notes if n]
        b = next((year(d) for t, d, p, x in ev if t == "BIRT"), None)
        dd = next((year(d) for t, d, p, x in ev if t == "DEAT"), None)
        y = f"{b}–{dd}" if b and dd else (f"* {b}" if b else (f"† {dd}" if dd else ""))
        if as_py:
            note = " ".join(notes)   # !r = valid Python even for quotes and "\\" in names and notes (people.py is run via exec)
            print(f' {k}: dict(n={name(ind)!r}, y={y!r}, st="fam", f={facts!r}, r=[]' + (f', note={note[:300]!r}' if note else "") + "),")
        else:
            print(f"\n{k} | {name(ind)} | {y}")
            for f in facts:
                print("   ", f)
            for n in notes:
                print("    note:", n.replace("\n", " ")[:600])
        dated = [(t, d, p) for t, d, p, x in ev if p or d]
        for pref in ("DEAT", "BURI", "MARR", "BIRT", "CHR"):
            hit = [e for e in dated if e[0] == pref and e[2]]
            if hit:
                t, d, p = max(hit, key=lambda e: year(e[1]) or 0)
                queue.append((k, name(ind), {"DEAT": "death", "BURI": "death", "MARR": "marriage"}.get(t, "birth"), d, p))
                break
    if as_py:
        print("}")
        return
    print(f"\nQUEUE OF RECORDS (youngest known event with a place; closure periods: births {limits['birth']}, "
          f"marriages {limits['marriage']}, deaths {limits['death']} years):")
    now = datetime.date.today().year
    for k, n, what, d, p in queue:
        y = year(d)
        where = "" if not y else ("  → registers online" if now - y > limits[what]
                                  else "  → so far only at the civil registry office (closure period)")
        print(f"  {k:>4} {n}: {what} {d} {p}".rstrip() + where)


if __name__ == "__main__":
    main()
