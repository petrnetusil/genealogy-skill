#!/usr/bin/env python3
"""Checks that stories are backed by sources and that ancestors' dates fit together (tools/check.py also calls it
and shows the clear-cut findings as warnings).

Usage (from the project root):
  python3 -I tools/evidence_check.py                    -> listing + work/evidence_check.md
  python3 -I tools/evidence_check.py --output <file.md>
  python3 -I tools/evidence_check.py --certain-only     -> chronology: only certain conflicts

What it checks
A) Sources in data/story*.md and data/curiosities.md
   1. every chapter (## …) has at least one non-empty "Sources:" line,
   2. paragraphs with a year that are not followed by a "Sources:" line before the next chapter (claim without source),
   3. links /source/<key>/ must exist in data/records.json, /person/<slug>/ in web/src/data/site.json (read only),
   4. causal / participation claims ("because of", "fell in", "died of cholera") in a block whose "Sources:" line
      has no link to a record or primary source (only interpretation / literature) – warning only.
   Item 4 follows tools/dolozeni.py from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted to this
   format ("Sources:" after the paragraph instead of [[source:…]] inside the sentence).
B) Chronology in data/people.py (Ahnentafel numbering: father 2k, mother 2k+1)
   - child born more than ~1 year before the parents' marriage,
   - child born more than 10 months after the father's death / after the mother's death,
   - mother younger than 14 or older than 50 at the birth (father younger than 15 or older than 75),
   - marriage after one's own death or before birth, death before birth.
   Idea from web/src/lib/navaznost.js in zbysekvoda/rodokmen-plus@096315a (MIT; originally mplisek/rodokmen-skill,
   tools/chronologie.py, MIT). A year without a day = the whole year; "c." / "~" = ±3 years; "before X" = (−∞, X];
   "after X" = [X, ∞). A conflict is CERTAIN only when it holds for every possible date in the intervals and both
   people are doc/fam; otherwise it is UNCERTAIN.
Writes nothing to data/. No network.

The module also provides the shared date parser used by other tools (find_dates, first_date, full_date):
canonical "12 Mar 1873", also "Mar 1873", "1873", and the old numeric "12. 3. 1873", "12.03.1873", "12/03/1873"
(day/month/year), "3. 1873", "2/1847" (month/year).
"""
import datetime as dt
import json
import os
import re
import runpy
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA = os.path.join(ROOT, "data")
OUTPUT = os.path.join(ROOT, "work", "evidence_check.md")
if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- shared date parsing
_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_RE = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
            r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?(?![^\W\d_])")
YEAR_RE = r"(?:1[0-9]{3}|20[0-9]{2})"
DATE_RE = re.compile(
    rf"(?<![\d/.])(?:"
    rf"(?P<d1>\d{{1,2}})\.?\s+(?P<m1>{MONTH_RE})\s*(?P<y1>{YEAR_RE})"          # 12 Mar 1873
    rf"|(?P<m2>{MONTH_RE})\s*(?P<y2>{YEAR_RE})"                                 # Mar 1873
    rf"|(?P<d3>\d{{1,2}})\s*[./]\s*(?P<m3>\d{{1,2}})\s*[./]\s*(?P<y3>{YEAR_RE})"  # 12. 3. 1873, 12/03/1873
    rf"|(?P<m4>\d{{1,2}})\s*[./]\s*(?P<y4>{YEAR_RE})"                           # 3. 1873, 2/1847
    rf"|(?P<y5>{YEAR_RE})"                                                      # 1873
    rf")(?!\d)", re.I)


def _month(word):
    return _MONTHS.index(word.lower().rstrip(".")[:3]) + 1


def _parts(m):
    """Regex match of DATE_RE -> (year, month or None, day or None); None when the numbers are not a valid date."""
    g = m.groupdict()
    if g["y1"]:
        y, mo, d = int(g["y1"]), _month(g["m1"]), int(g["d1"])
    elif g["y2"]:
        y, mo, d = int(g["y2"]), _month(g["m2"]), None
    elif g["y3"]:
        y, mo, d = int(g["y3"]), int(g["m3"]), int(g["d3"])
    elif g["y4"]:
        y, mo, d = int(g["y4"]), int(g["m4"]), None
    else:
        y, mo, d = int(g["y5"]), None, None
    if mo is not None and not 1 <= mo <= 12:
        return None
    if d is not None:
        try:
            dt.date(y, mo, d)
        except ValueError:
            return None
    return y, mo, d


def find_dates(text):
    """All dates in a text: [(start, end, year, month or None, day or None)]."""
    out = []
    for m in DATE_RE.finditer(text or ""):
        p = _parts(m)
        if p:
            out.append((m.start(), m.end(), *p))
    return out


def date_at(text, pos=0):
    """Date starting exactly at text[pos:] -> (end, year, month, day) or None."""
    m = DATE_RE.match(text or "", pos)
    p = _parts(m) if m else None
    return (m.end(), *p) if p else None


def first_date(text):
    """First date in a text -> (year, month, day) (month/day may be None) or None."""
    d = find_dates(text)
    return d[0][2:] if d else None


def full_date(text):
    """First complete date (day, month and year) in a text as datetime.date, or None."""
    for _, _, y, mo, d in find_dates(text):
        if d:
            return dt.date(y, mo, d)
    return None


# ---------------------------------------------------------------- A) sources in stories
YEAR = re.compile(r"(?<![\d/.])(1[0-9]{3}|20[0-2][0-9])(?![\d])")
SOURCES = re.compile(r"^\s*(\*\*)?Sources?(\*\*)?\s*:", re.I)
LINK_SOURCE = re.compile(r"/source/([^/\s)\]]+)/?")
LINK_PERSON = re.compile(r"/person/([^/\s)\]]+)/?")
EPIDEMIC = (r"(?:cholera|typhus|typhoid|smallpox|dysentery|plague|influenza|flu|epidemic|diphtheria|"
            r"scarlet\s+fever|tuberculosis|consumption)")
TRIGGERS = re.compile(r"(?<![^\W\d_])(?:because\s+of|due\s+to|as\s+a\s+result\s+of|in\s+consequence\s+of|"
                      r"took\s+part|participated|fought|fell\s+(?:in|at)|killed\s+in\s+action|"
                      r"died\s+(?:\w+\s+)?(?:of|from)\s+(?:the\s+)?" + EPIDEMIC + r")(?![^\W\d_])", re.I)
PRIMARY = re.compile(r"/source/|(?<![^\W\d_])(?:regist\w*|parish\w*|chronicl\w*|record\w*|entr(?:y|ies)|"
                     r"military\s+record\w*|service\s+record\w*|death\s+certificat\w*|certificat\w*|obituar\w*|"
                     r"census\w*|tax\s+roll\w*|cadastr\w*|land\s+regist\w*|diar(?:y|ies)|index\w*|volume|"
                     r"image|img\.|archiv\w*)", re.I)
SENTENCES = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÀ-ÖØ-Þ\[\"“(])")


def strip_comments(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    if text.startswith("---"):                      # frontmatter (title, lead)
        end = text.find("\n---", 3)
        if end > 0:
            text = text[end + 4:]
    return text


def short(s, n=110):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def check_stories():
    files = sorted(f for f in os.listdir(DATA) if re.match(r"story.*\.md$", f)) + ["curiosities.md"]
    try:
        records = {z["key"] for z in json.load(open(os.path.join(DATA, "records.json"), encoding="utf-8-sig"))}
    except Exception:
        records = None
    try:
        site = json.load(open(os.path.join(ROOT, "web", "src", "data", "site.json"), encoding="utf-8"))
        slugs = {p.get("slug") for p in site.get("people", {}).values()} | set(site.get("aliases", {}) or {})
    except Exception:
        slugs = None
    res = {"no_sources": [], "year_no_source": [], "links": [], "causal": [], "stat": []}
    for f in files:
        path = os.path.join(DATA, f)
        if not os.path.exists(path):
            continue
        text = strip_comments(open(path, encoding="utf-8-sig").read())
        chapters, n_sources = 0, 0
        heading, has_sources, block = "(intro)", False, []

        def close_block(source_line):
            nonlocal block
            if source_line is None:
                for par in block:
                    years = YEAR.findall(par)
                    if years:
                        res["year_no_source"].append((f, heading, ", ".join(dict.fromkeys(years)), short(par)))
            elif not PRIMARY.search(source_line):
                for par in block:
                    for sentence in SENTENCES.split(par):
                        if TRIGGERS.search(sentence):
                            res["causal"].append((f, heading, short(sentence, 150), short(source_line, 90)))
            block = []

        def close_chapter():
            if heading != "(intro)" and not has_sources:
                res["no_sources"].append((f, heading))

        for par in re.split(r"\n\s*\n", text):
            o = par.strip()
            if not o:
                continue
            lines = o.split("\n")
            # a heading may start the paragraph
            while lines and lines[0].startswith("#"):
                if lines[0].startswith("## "):
                    close_block(None)
                    close_chapter()
                    heading, has_sources = lines[0][3:].strip(), False
                    chapters += 1
                lines = lines[1:]
            if not lines:
                continue
            o = "\n".join(lines)
            for key in LINK_SOURCE.findall(o):
                if records is not None and key not in records:
                    res["links"].append((f, heading, f"/source/{key}/ – key is not in data/records.json"))
            for slug in LINK_PERSON.findall(o):
                if slugs is not None and slug not in slugs:
                    res["links"].append((f, heading, f"/person/{slug}/ – slug is not in web/src/data/site.json"))
            if SOURCES.match(o):
                content = SOURCES.sub("", o, count=1).strip()
                if len(content) < 8:
                    res["no_sources"].append((f, heading + " (empty Sources: line)"))
                has_sources = True
                n_sources += 1
                close_block(content)
            else:
                block.append(o)
        close_block(None)
        close_chapter()
        res["stat"].append((f, chapters, n_sources))
    return res


# ---------------------------------------------------------------- B) chronology
YEAR_DAYS = 365.25
MONTHS_AFTER_FATHER = 304            # ~10 months
INF = 10 ** 9


def day(y, m=1, d=1):
    return dt.date(y, m, d).toordinal()


def month_end(y, m):
    return (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).toordinal()


def interval(text):
    """'12 Mar 1873 Hořice', 'before Feb 1847', 'c. 1815', '(burial) 20 Mar 1773', old '12. 3. 1873'
    -> (lo, hi, approx, text) or None."""
    t = text.strip()
    t = re.sub(r"^\((?:burial|buried|baptism|baptised|baptized|bapt\.?)\)\s*", "", t, flags=re.I)
    approx = "(?)" in t or "?" in t[:25]
    before = after = False
    m0 = re.match(r"(before|not\s+later\s+than|by|after|not\s+earlier\s+than|~|c\.|ca\.?|circa|about|abt\.?|around)\s*",
                  t, re.I)
    if m0:
        w = re.sub(r"\s+", " ", m0.group(1).lower())
        before = w in ("before", "not later than", "by")
        after = w in ("after", "not earlier than")
        approx = approx or not (before or after)
        t = t[m0.end():]
    p = date_at(t)
    if not p:
        return None
    end, y, mo, d = p
    try:
        if d:
            lo = hi = day(y, mo, d)
        elif mo:
            lo, hi = day(y, mo, 1), month_end(y, mo)
        else:
            lo, hi = day(y), day(y, 12, 31)
    except ValueError:
        return None
    # range "1720–1725"
    r = re.match(r"\s*[–-]\s*(1[0-9]{3})(?!\d)", t[end:])
    if r and not d and not mo:
        hi = day(int(r.group(1)), 12, 31)
        approx = True
    if approx and not d:
        lo, hi = lo - 3 * 365, hi + 3 * 365
    if before:
        lo = -INF
    if after:
        hi = INF
    return (lo, hi, approx or before or after, short(text, 40))


def facts(p, symbol):
    out = []
    for f in p.get("f", []) or []:
        s = f.strip()
        if s.startswith(symbol):
            iv = interval(s[1:])
            if iv:
                out.append((iv, s))
    return out


def from_years_field(y, part):
    """Fallback from the y field ('1850–1910', 'c. 1720–1785', '* 1931', '1680 – before 1740'); always uncertain."""
    if not y:
        return None
    y = y.strip()
    if y.startswith("*"):
        return interval(y[1:]) if part == "b" else None
    circa = bool(re.match(r"(c\.|ca\.?|circa|about|~)", y, re.I))
    parts = re.split(r"\s*[–-]\s*", re.sub(r"^(c\.|ca\.?|circa|about|~)\s*", "", y, flags=re.I), maxsplit=1)
    if len(parts) != 2:
        return None
    t = parts[0] if part == "b" else parts[1]
    if not t.strip() or t.strip() == "?":
        return None
    iv = interval(("c. " if circa else "") + t)
    return (iv[0], iv[1], True, short(y, 40) + " (y field)") if iv else None


def surname_stem(name):
    s = re.sub(r"\(.*?\)", "", name or "").strip()
    words = [w for w in s.split() if w[:1].isupper()]
    if len(words) < 2:
        return None
    w = words[-1].lower()
    w = re.sub(r"(ová|á|ovou|ou)$", "", w)   # Czech feminine surname endings (Nováková → novák)
    return w[:4] if len(w) >= 3 else None


def check_chronology(certain_only=False):
    ns = runpy.run_path(os.path.join(DATA, "people.py"))
    P = ns["P"]
    uncertain_st = {"prob", "mh", "unk"}

    def events(k):
        p = P[k]
        b = facts(p, "*")
        d = facts(p, "†")
        b = b[0][0] if b else from_years_field(p.get("y"), "b")
        d = d[0][0] if d else (None if "*" in (p.get("y") or "")[:1] else from_years_field(p.get("y"), "d"))
        return b, d

    U = {k: events(k) for k in P if P[k].get("st") != "unk"}
    out = []

    def add(rule, k, text, ivs, people):
        certain = not any(iv[2] for iv in ivs) and not any(P[o].get("st") in uncertain_st for o in people)
        if certain_only and not certain:
            return
        out.append(("CERTAIN" if certain else "uncertain", rule, k, text,
                    ", ".join(f"{o} {P[o].get('st')}" for o in people)))

    def nm(k):
        return f"{P[k].get('n')} ({k})"

    def years_between(a, b):
        return (b - a) / YEAR_DAYS

    for k, p in sorted(P.items()):
        if k not in U:
            continue
        b, d = U[k]
        marriages = facts(p, "×")
        if b and d and d[1] < b[0]:
            add("death before birth", k, f"{nm(k)}: † {d[3]} is earlier than * {b[3]}", [b, d], [k])
        for m, s in marriages:
            if d and m[0] > d[1]:
                add("marriage after death", k, f"{nm(k)}: {short(s, 60)} is after † {d[3]}", [m, d], [k])
            if b and m[1] < b[0]:
                add("marriage before birth", k, f"{nm(k)}: {short(s, 60)} is earlier than * {b[3]}", [m, b], [k])
            elif b and b[0] > -INF and m[1] < INF and years_between(b[0], m[1]) < 14:
                add("marriage as a child", k,
                    f"{nm(k)}: at {short(s, 50)} at most {years_between(b[0], m[1]):.0f} years old (* {b[3]})", [m, b], [k])

        # child k – parents 2k, 2k+1
        if not b:
            continue
        fa, mo = 2 * k, 2 * k + 1
        for r, is_father in ((fa, True), (mo, False)):
            if r not in U:
                continue
            rb, rd = U[r]
            if rd and rd[1] < INF and b[0] > rd[1] + (MONTHS_AFTER_FATHER if is_father else 1):
                add("born after the death of the " + ("father (> 10 months)" if is_father else "mother"), k,
                    f"{nm(k)} * {b[3]}, but {'father' if is_father else 'mother'} {nm(r)} † {rd[3]}", [b, rd], [k, r])
            if rb and rb[0] > -INF:
                if b[1] < rb[0]:
                    add("parent younger than child", k, f"{nm(r)} * {rb[3]} after the child {nm(k)} * {b[3]}", [b, rb], [k, r])
                    continue
                age_max = years_between(rb[0], b[1]) if b[1] < INF else 999
                age_min = years_between(rb[1], b[0]) if rb[1] < INF and b[0] > -INF else -999
                low, high = (14, 50) if not is_father else (15, 75)
                who = "father" if is_father else "mother"
                if age_max < low:
                    add(f"{who} younger than {low}", k,
                        f"{nm(r)} * {rb[3]} – at the birth of the child {nm(k)} (* {b[3]}) at most {age_max:.0f} years old",
                        [b, rb], [k, r])
                elif age_min > high:
                    add(f"{who} older than {high}", k,
                        f"{nm(r)} * {rb[3]} – at the birth of the child {nm(k)} (* {b[3]}) at least {age_min:.0f} years old",
                        [b, rb], [k, r])

        # parents' marriage – a × fact of the father or mother that names the other partner
        if fa in P and mo in P:
            sm, sf = surname_stem(P[mo].get("n")), surname_stem(P[fa].get("n"))
            sn = [(m, s) for m, s in facts(P[fa], "×") if sm and sm in s.lower()]
            sn += [(m, s) for m, s in facts(P[mo], "×") if sf and sf in s.lower()]
            notes = (p.get("note") or "") + " " + " ".join(p.get("f") or [])
            if sn and not re.search(r"illegitim|legitimi[sz]", notes, re.I):   # illegitimate / legitimised child – known
                m, s = min(sn, key=lambda x: x[0][1])
                if m[0] > -INF and b[1] < m[0] - YEAR_DAYS:
                    add("born > 1 year before the parents' marriage", k,
                        f"{nm(k)} * {b[3]}, parents' marriage {short(s, 60)} ({years_between(b[1], m[0]):.1f} years later)",
                        [b, m], [k, fa, mo])
    return out


# ---------------------------------------------------------------- output
def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        sys.exit(__doc__.strip())
    output = OUTPUT
    if "--output" in args:
        output = os.path.abspath(args[args.index("--output") + 1])
    certain_only = "--certain-only" in args

    A = check_stories()
    B = check_chronology(certain_only)
    today = dt.date.today().strftime("%d %b %Y").lstrip("0")
    L = [f"# Evidence and chronology check ({today})", "",
         "Created by `tools/evidence_check.py` (writes nothing to `data/`). "
         "These are **warnings to review**, not errors – a person decides about each one.", ""]
    L += ["## A) Sources in stories and curiosities", "",
          "| File | Chapters (##) | \"Sources:\" lines |", "|---|---|---|"]
    L += [f"| data/{f} | {k} | {z} |" for f, k, z in A["stat"]]
    L += ["", f"### A1. Chapters without a \"Sources:\" line ({len(A['no_sources'])})", ""]
    L += [f"- data/{f} – \"{n}\"" for f, n in A["no_sources"]] or ["- none"]
    L += ["", f"### A2. Paragraphs with a year not followed by \"Sources:\" before the end of the chapter "
          f"({len(A['year_no_source'])})", ""]
    L += [f"- data/{f} – \"{n}\" – years {r}: \"{t}\"" for f, n, r, t in A["year_no_source"]] or ["- none"]
    L += ["", f"### A3. Links that lead nowhere ({len(A['links'])})", ""]
    L += [f"- data/{f} – \"{n}\": {t}" for f, n, t in A["links"]] or ["- none"]
    L += ["", f"### A4. Causal / participation claims whose \"Sources:\" have no record or primary source "
          f"({len(A['causal'])})", "",
          "(after `dolozeni.py` from rodokmen-plus; \"died of cholera\", \"because of\", \"fell in\" – either add a "
          "primary source, or rewrite as context: \"in those years…\")", ""]
    L += [f"- data/{f} – \"{n}\": \"{v}\" ← Sources: {z}" for f, n, v, z in A["causal"]] or ["- none"]

    certain = [x for x in B if x[0] == "CERTAIN"]
    L += ["", "## B) Chronology of ancestors (data/people.py)", "",
          f"In total {len(B)} warnings, **{len(certain)} of them certain** (exact dates, people doc/fam). "
          "Uncertain = estimated year (c., ~, before, after, y field) or person prob/mh – the conflict is only possible.", ""]
    rules = {}
    for x in B:
        rules.setdefault(x[1], []).append(x)
    for rule, xs in sorted(rules.items(), key=lambda kv: (-sum(1 for x in kv[1] if x[0] == "CERTAIN"), kv[0])):
        L += [f"### {rule} ({len(xs)}; certain {sum(1 for x in xs if x[0] == 'CERTAIN')})", "",
              "| Certainty | Ahnentafel | What does not fit | People (status) |", "|---|---|---|---|"]
        L += [f"| {j} | {k} | {t} | {o} |" for j, _, k, t, o in sorted(xs, key=lambda x: (x[0] != "CERTAIN", x[2]))]
        L.append("")
    if not B:
        L.append("- no conflicts")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    open(output, "w", encoding="utf-8").write("\n".join(L) + "\n")

    print(f"A) chapters without Sources: {len(A['no_sources'])}, paragraphs with a year without a source: "
          f"{len(A['year_no_source'])}, broken links: {len(A['links'])}, causal claims without a primary source: "
          f"{len(A['causal'])}")
    print(f"B) chronology: {len(B)} warnings, {len(certain)} certain")
    for j, rule, k, t, o in sorted(B, key=lambda x: (x[0] != "CERTAIN", x[2]))[:15]:
        print(f"   [{j}] {rule}: {t}")
    print(f"Result: {os.path.relpath(output, ROOT)}")


def warnings():
    """For tools/check.py: a list of short warnings (story sources + certain chronology conflicts)."""
    out = []
    v = check_stories()
    for f, heading in v["no_sources"]:
        out.append(f"{f}, chapter \"{heading}\": missing \"Sources:\" line")
    for f, heading, years, par in v["year_no_source"]:
        out.append(f"{f}, \"{heading}\": paragraph with a year ({years}) without \"Sources:\" – {par}")
    for f, heading, what in v["links"]:
        out.append(f"{f}, \"{heading}\": {what}")
    for f, heading, sentence, source in v["causal"]:
        out.append(f"{f}, \"{heading}\": claim \"{sentence}\" has only interpretation in its Sources ({source}) – "
                   "add a primary source")
    for certainty, rule, k, text, people in check_chronology(certain_only=True):
        out.append(f"chronology ({rule}): {text}")
    return out


if __name__ == "__main__":
    main()
