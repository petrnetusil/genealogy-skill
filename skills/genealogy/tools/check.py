#!/usr/bin/env python3
"""Consistency check of the family-tree data. Run it after every larger change and before building the website.

Usage: check.py
Prints ERRORS (break the website or are factually wrong) and WARNINGS (something is missing, to be added).
Exit code 1 if there are errors.
"""
import datetime, json, os, re, sys, unicodedata
if sys.argv[1:2] in (["-h"], ["--help"]):   # help instead of a crash
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):   # UTF-8 output even on Windows without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
# Names of placeholder people (an unnamed parent, e.g. the father of an illegitimate child) – same list as in export_web.py
PLACEHOLDER_NAMES = ("father unknown", "mother unknown", "father not named", "mother not named",
                     "unknown father", "unknown mother")


def jload(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p, encoding="utf-8-sig")) if os.path.exists(p) else default


MONTH = (r"(?i:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
         r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?(?![^\W\d_])")
# A place in a fact: capitalised word(s) after "in/at/from/near/of" or after the date of a */†/× fact
PLACE_RE = re.compile(r"(?:\b(?:in|at|from|near|of)\s+|[*†×]\s*(?:(?:c\.|before|after|about)\s*)?"
                      rf"(?:\d{{1,2}}\.?\s+)?(?:{MONTH}\s*|\d{{1,2}}\.\s*)?\d{{4}}\s+)"
                      r"([^\W\d_][^\W\d_'’-]*(?:\s+[^\W\d_][^\W\d_'’-]*)?)")


def place_words(facts):
    """Words from facts that look like a place (after "in/at/from" or after the date of */†/×): shows whether a
    place is missing in places.json, or only its spelling differs."""
    out = []
    for m in PLACE_RE.finditer(" ".join(facts)):
        words = m.group(1).split()
        if not words[0][0].isupper():
            continue
        out.append(" ".join(words[:1] + [w for w in words[1:2] if w[0].isupper()]))
    return list(dict.fromkeys(out))[:4]


def is_placeholder(p):   # like placeholder() in export_web.py
    n = p.get("n", "")
    return n.lower().startswith(PLACEHOLDER_NAMES) or n in ("", "?")


def main():
    err, warn = [], []
    ns = {}
    try:
        exec(open(os.path.join(DATA, "people.py"), encoding="utf-8-sig").read(), ns)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"ERROR: data/people.py cannot be loaded: {e}")
    P, SIDE, LINES, SAME = ns.get("P", {}), ns.get("SIDE", []), ns.get("LINES", {}), ns.get("SAME", {})
    recs = jload("records.json", [])
    volumes, transcripts, hl = jload("volumes.json", {}), jload("transcripts.json", {}), jload("highlights.json", {})
    keys = [z.get("key") for z in recs]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        err.append(f"records with the same key: {sorted(dup)}")
    keys = set(keys)

    if 1 not in P:
        err.append("person 1 is missing (the root person of the tree)")
    for k, p in P.items():
        if not isinstance(k, int) or k < 1:
            err.append(f"person {k!r}: the number must be a positive integer")
            continue
        if k > 1 and k // 2 not in P and k not in SAME:
            warn.append(f"person {k} ({p.get('n')}): their child {k // 2} is missing in the tree – is the number right?")
        st = p.get("st", "unk")
        if st not in ("doc", "prob", "fam", "mh", "unk"):
            err.append(f"person {k}: unknown status '{st}'")
        for r in p.get("r", []):
            if r not in keys:
                err.append(f"person {k} ({p.get('n')}) cites a non-existent record '{r}'")
        if st == "doc" and not p.get("r"):
            warn.append(f"person {k} ({p.get('n')}) is 'doc' (documented) but cites no record")
    for s in SIDE:
        if s.get("k") not in P:
            err.append(f"side relative '{s.get('n')}' belongs to non-existent person {s.get('k')}")
        for r in s.get("r", []):
            if r not in keys:
                err.append(f"side relative '{s.get('n')}' cites a non-existent record '{r}'")
        if not (s.get("t") or "").strip():
            warn.append(f"side relative '{s.get('n')}' has no text (t) – the website will show only the name")
    for a, c in SAME.items():
        if c not in P:
            err.append(f"SAME: {a} -> {c}, but person {c} does not exist")
        elif is_placeholder(P[c]):
            err.append(f"SAME: {a} -> {c}, but person {c} is a placeholder (no name) – an alias must point to a real person")
    for k in LINES:
        if k not in range(8, 16):
            err.append(f"LINES: line {k} – lines have numbers 8 to 15 (great-grandparents)")
    names = {}
    for k, v in sorted(LINES.items()):
        names.setdefault(str(v[0]).strip().lower(), []).append(k)
    for n, ks in names.items():
        if len(ks) > 1:
            err.append(f"LINES: lines {', '.join(map(str, ks))} have the same name \"{LINES[ks[0]][0]}\" – tell them apart "
                       "(e.g. \"Nováks of Holice\" and \"Nováks of Chrudim\"), otherwise the website cannot distinguish them")
    for d in jload("documents.json", []):
        if isinstance(d, dict) and not (d.get("caption") or "").strip():
            warn.append(f"document {d.get('img')} has no caption – the website will show it without one")
        if isinstance(d, dict) and d.get("img") and not os.path.exists(os.path.join(ROOT, "crops", d["img"] + ".jpg")):
            warn.append(f"document {d.get('img')}: crops/{d['img']}.jpg is missing – it will not show on the website "
                        "(shrink the original from documents/ into crops/, reference/data.md)")
    for i, x in enumerate(ns.get("ISSUES", [])):
        if not (isinstance(x, str) or (isinstance(x, (tuple, list)) and len(x) == 2
                                       and all(isinstance(y, str) for y in x))):
            err.append(f"ISSUES[{i}]: must be a text, or a pair (\"Question\", \"Open: …\"), not {type(x).__name__} "
                       f"{str(x)[:60]} – the website export would crash on it")
    for k, t in transcripts.items():
        if not isinstance(t, dict):
            err.append(f"transcripts.json \"{k}\": must be {{\"orig\": …, \"translation\": …}}")
            continue
        unknown = sorted(set(t) - {"orig", "translation"})
        if unknown:
            warn.append(f"transcripts.json \"{k}\": unknown key {', '.join(unknown)} – the website reads only \"orig\" "
                        "(transcription) and \"translation\", the text will not be shown")
        elif not (t.get("translation") or "").strip():
            warn.append(f"transcripts.json \"{k}\": translation is missing (\"translation\")")

    cited = ({r for p in P.values() for r in p.get("r", [])} | {r for s in SIDE for r in s.get("r", [])}
             | {r for h in ns.get("HYPOTHESES", []) if isinstance(h, dict) for r in h.get("records", [])})
    for z in recs:
        k = z.get("key", "?")
        for f in ("key", "kind", "date", "title", "summary"):
            if not z.get(f):
                err.append(f"record {k}: field '{f}' is missing")
        if z.get("kind") and z["kind"] not in ("B", "M", "D", "C", "O"):
            err.append(f"record {k}: unknown kind '{z['kind']}' (B baptism/birth, M marriage, D death/burial, "
                       "C census, O other)")
        if z.get("volume") and z["volume"] not in volumes:
            err.append(f"record {k}: volume '{z['volume']}' is not in data/volumes.json")
        if z.get("sample"):   # invented record of the sample family – has no image or transcription
            continue
        if not z.get("link") and not volumes.get(z.get("volume", ""), {}).get("url"):
            warn.append(f"record {k}: link to the image is missing (field 'link')")
        if not os.path.exists(os.path.join(ROOT, "crops", k + ".jpg")):
            warn.append(f"record {k}: crop crops/{k}.jpg is missing")
        elif k not in hl:
            warn.append(f"record {k}: highlight box is missing (tools/frame.py)")
        if k not in transcripts:
            warn.append(f"record {k}: transcription and translation are missing in data/transcripts.json")
        if k not in cited:
            warn.append(f"record {k}: no person cites it (add it to 'r' of a person or side relative)")

    known = [k for k in range(8, 16) if P.get(k, {}).get("st") in ("doc", "prob")]
    missing = [f"{k} ({P[k].get('n', '?')})" for k in known if k not in LINES]
    if missing:   # without LINES the website shows neither lines nor colours in the fan chart
        warn.append(f"LINES: line missing for {', '.join(missing)}"
                    " – once you know the great-grandparents (8–15), fill in LINES in data/people.py (reference/data.md)")

    places = jload("places.json", {})
    patterns = []
    for n, e in places.items():
        try:
            patterns += [re.compile(e.get("re") or re.escape(n))] if "lat" in e else []
        except re.error:   # a bad expression is reported by the place check below
            pass
    no_place = [k for k, p in sorted(P.items()) if isinstance(k, int) and p.get("st") == "doc" and p.get("f")
                and not any(rx.search(" ".join(p["f"])) for rx in patterns)]
    if no_place:   # the website map shows only places from data/places.json
        example = ", ".join(f"{k} {P[k].get('n', '?')}" + (f" [{', '.join(s)}]" if (s := place_words(P[k]["f"])) else "")
                            for k in no_place[:3])
        warn.append(f"map: {len(no_place)} documented ancestors have no place from data/places.json in their facts "
                    f"(e.g. {example}) – add their places: tools/places.py add \"Place\", then tools/places.py")

    def stems(s):   # first 4 letters of words without diacritics; text in brackets is ignored
        s = "".join(c for c in unicodedata.normalize("NFD", re.sub(r"\(.*?\)", "", s).lower())
                    if not unicodedata.combining(c))
        return {w[:4] for w in re.findall(r"[a-z]{3,}", s)}

    all_places = []   # all valid place expressions, also without coordinates (patterns above are only places on the map)
    for n, e in places.items():
        try:
            all_places.append(re.compile(e.get("re") or re.escape(n)))
        except re.error:
            pass

    date_head = re.compile(r"×\s*(?:(?:c\.|before|after|about)\s*)?(?:\d{1,2}\.?\s+)?"
                           rf"(?:{MONTH}\s*)?[\s\d.,?/–-]*")

    def without_place(f):   # "× 12 May 1950 Holice Karel Hrubý" → without the place right after the date, name stays
        i = date_head.match(f).end()
        for rx in all_places:
            m = rx.match(f, i)
            if m and m.end() > i:
                return f[:i] + " " + f[re.compile(r"\w*").match(f, m.end()).end():]
        return f

    for k, p in P.items():   # a marriage "× Name" should name the partner at the neighbouring number (k ^ 1, mind SAME)
        marriages = [stems(without_place(f)) for f in p.get("f", []) if isinstance(f, str) and f.startswith("×")]
        marriages = [s for s in marriages if s]
        if not isinstance(k, int) or not marriages:
            continue
        candidates = {k ^ 1} | {a ^ 1 for a, c in SAME.items() if c == k and isinstance(a, int)}
        partners = {sp for sp in {SAME.get(sp, sp) for sp in candidates} if sp in P and not is_placeholder(P[sp])}
        if partners and not any(stems(P[sp].get("n", "")) & s for sp in partners for s in marriages):
            sp = min(partners)
            warn.append(f"person {k} ({p.get('n')}): no marriage (×) names partner {sp} ({P[sp].get('n')})"
                        " – does the marriage belong to this person, is the number right?")

    # House number in a record: after "no.", "nr.", "n°", "house", or the archival "čp.", "č.", "Haus", "N." …,
    # in a "[House] …" field, or right after a place from places.json ("from Holice 23"). A date ("5. 1. 1767",
    # "23 March", "9. 9bris"), an age, a year or a number of the entry, page or image ("entry no. 23") is no house.
    # Month names include German, Latin and Czech forms because transcriptions keep the original language.
    month = (r"january|february|march|april|may|june|july|august|september|october|november|december|"
             r"jänner|januar|feber|februar|märz|mai|juni|juli|oktober|dezember|"
             r"januarii|februarii|martii|aprilis|maii|junii|julii|augusti|septembris|octobris|novembris|decembris|"
             r"ledna|února|března|dubna|května|června|července|srpna|září|října|listopadu|prosince|"
             r"janvier|février|mars|avril|juin|juillet|août|septembre|octobre|novembre|décembre|"
             r"[7-9x]bris|10bris|jan|feb|mar|mär|apr|jun|jul|aug|sept?|okt|oct|nov|dez|dec")
    not_date = rf"(?!\d|\.\s*(?:\d|(?:{month})(?![^\W\d_])))"
    after_no = r"(\d+)" + not_date
    with_prefix = re.compile(r"(?<![^\W\d_])(?:no|nr|nro|n°|n|house|haus|huis|maison|čp|čís|č|dům|domu|domě)\.?\s*"
                             + after_no, re.I)
    house_field = re.compile(r"\[[^\]\n]*(?:house|haus|huis|maison|dům|domu)[^\]\n]*\]([^\n|\[]*)", re.I)
    after_place = re.compile(r"\w*,?\s+(\d{1,3})" + not_date, re.I)   # number right after a place, not a year
    not_house = re.compile(r"(?<![^\W\d_])(?:record\w*|entr(?:y|ies)|page\w*|p|pp|sheet\w*|line|fol|folio|image\w*|"
                           r"img|pag|zápis\w*|záznam\w*|stran\w*|str|list\w*|sním\w*|sn)\.?\s*$", re.I)

    def house_numbers(t):   # each field separately so that a "[House]" field does not spill into further text
        nums = {m.group(1) for m in with_prefix.finditer(t) if not not_house.search(t[max(0, m.start() - 12):m.start()])}
        nums |= {c for v in house_field.findall(t) for c in re.findall(r"(?<!\d)" + after_no, v, re.I)}
        for rx in all_places:   # the place expression is only searched for, never embedded (own flags and groups)
            for m in rx.finditer(t):
                c = after_place.match(t, m.end())
                if c and m.end() > m.start():
                    nums.add(c.group(1))
        return nums
    rec_nums = {z.get("key"): house_numbers(str(z.get("summary", ""))) | house_numbers(str(z.get("title", ""))) for z in recs}
    sample_recs = {z.get("key") for z in recs if z.get("sample")}
    person_recs = {}   # an ancestor twice in the tree (SAME): records of the main person and all aliases
    for k, p in P.items():
        person_recs.setdefault(SAME.get(k, k), set()).update(p.get("r", []))
    for k, p in P.items():   # a house number in the facts should be in a cited record
        cites = person_recs.get(SAME.get(k, k), set())
        if p.get("st") != "doc" or not cites - sample_recs:   # invented sample records have no transcription
            continue
        documented = set().union(*(rec_nums.get(r, set()) | house_numbers(str(transcripts.get(r, {}).get("orig", "")))
                                   | house_numbers(str(transcripts.get(r, {}).get("translation", ""))) for r in cites))
        fs = [f for f in p.get("f", []) if isinstance(f, str)   # "(per online tree)", "(family story)" = source marked
              and not re.search(r"\([^)]*\b(?:tree|told|story|family|memor)", f, re.I)]
        for c in sorted(set(re.findall(r"\bno\.\s*(\d+)", " ".join(fs))) - documented, key=int):
            warn.append(f"person {k} ({p.get('n')}): house no. {c} is in no cited record – verify it, "
                        "or mark the source (tree, family story)")

    for name, e in places.items():
        if "lat" not in e:
            warn.append(f"place {name}: has no coordinates (run tools/places.py)")
        try:
            re.compile(e.get("re") or "")
        except re.error as ex:
            err.append(f"place {name}: bad expression '{e.get('re')}': {ex}")

    cfg = jload("website.json", {})
    # A missing gate question is not reported all the time – deployment checks it (export_web.py --deploy).
    sample_marks = ("(sample", "fictional family", "Novák family tree", "The Nováks")
    if any(u in json.dumps(cfg, ensure_ascii=False) for u in sample_marks) and "Novák" not in P.get(1, {}).get("n", ""):
        warn.append("website.json: still contains sample texts (the Nováks) – set the title, story and contact")

    # Sensitive things that go on the website: ISSUES ("Open questions"), notes and facts of people, side relatives, texts.
    sensitive = re.compile(r"suicid|took (?:his|her|their) own life|hanged (?:him|her)self|shot (?:him|her)self|"
                           r"drowned (?:him|her)self|alcohol|drunk|prison|jail|imprison|criminal|convict|divorc|"
                           r"psychiatr|asylum|mental (?:illness|hospital)|insan|cancer|illegitim|adulter|debt|"
                           r"bankrupt|foreclos|abortion|miscarriage", re.I)

    limit = datetime.date.today().year - 100   # the last ~100 years; old register facts (illegitimate child in the 18th c.) are fine

    def recent(text):   # a date in brackets ("Addendum (3 Nov 2026)") is the date of the note, not of the event
        text = re.sub(r"\(\s*(?:\d{1,2}\.\s*\d{1,2}\.\s*\d{4}|\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}|\d{4}-\d{2}-\d{2})\s*\)",
                      "", text)
        return any(int(y) >= limit for y in re.findall(r"\b(19\d\d|20\d\d)\b", text))

    def negated(text, m):   # "no debts", "without debt", "was not divorced" – the word is negated
        return re.search(r"(?:^|\s)(?:no|without|not|never|wasn't|weren't|had no|has no)\s+(?:\w+\s+)?$",
                         text[max(0, m.start() - 30):m.start()], re.I)
    approved = [s for s in (cfg.get("sensitive_approved") if isinstance(cfg.get("sensitive_approved"), list) else [])
                if isinstance(s, str) and len(s.strip()) >= 3]

    def is_approved(text, m):   # the user allowed it on the website: website.json "sensitive_approved" has a snippet with this word
        for s in approved:
            i = text.find(s)
            while i >= 0:
                if i <= m.start() and m.end() <= i + len(s):
                    return True
                i = text.find(s, i + 1)
        return False
    texts = [("ISSUES", i if isinstance(i, str) else " ".join(map(str, i.values() if isinstance(i, dict) else i)))
             for i in ns.get("ISSUES", []) if isinstance(i, (str, tuple, list, dict))]
    for k, p in P.items():
        text = " ".join(p.get("f", [])) + " " + p.get("note", "")
        years = [int(y) for y in re.findall(r"\b1[5-9]\d\d|20\d\d\b", p.get("y", "") + " " + text)]
        texts.append((f"person {k}", text + (f" {limit}" if years and min(years) >= 1870 or k < 8 else "")))
    texts += [(f"side relative {s.get('n')}", s.get("n", "") + " " + s.get("t", "")) for s in SIDE]
    for f in ("curiosities.md", "story.md"):
        if os.path.exists(os.path.join(DATA, f)):
            content = open(os.path.join(DATA, f), encoding="utf-8-sig").read()
            texts += [(f, par) for par in re.split(r"\n\s*\n|\n(?=#)", content)]   # paragraphs and "## …" sections
    for where, text in texts:
        if not recent(text):
            continue
        m = next((m for m in sensitive.finditer(text) if not is_approved(text, m) and not negated(text, m)), None)
        if m:
            warn.append(f"SENSITIVE ({where}): \"…{text[max(0, m.start() - 40):m.end() + 40].strip()}…\" – goes on the "
                        f"website; ask the user whether it may be there (reference/privacy.md); if yes, "
                        f"add a snippet of the text with that word to website.json \"sensitive_approved\"")

    if not os.path.exists(os.path.join(DATA, "story.md")):
        main_line = min(LINES) if LINES else 8   # without LINES the paternal line (father's father's father)
        name = (LINES[main_line][0] if LINES else
                (P.get(8) or P.get(1) or {}).get("n", "").split()[-1:] or ["paternal"])
        name = name if isinstance(name, str) else name[0]
        n = max((k.bit_length() for k in P if isinstance(k, int) and k >= 8 and k >> (k.bit_length() - 4) == main_line),
                default=0)
        if n >= 6:
            warn.append(f"the {name} line already has {n} generations – time to write the story of the line "
                        f"(data/story.md, reference/stories.md); show a draft to the user in the chat first")

    try:   # story sources and chronology (tools/evidence_check.py; details: python3 -I tools/evidence_check.py)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import evidence_check
        warn.extend(evidence_check.warnings())
        import family_checks          # baptism names the parents, fact after death, living people in the log, ancestor twice
        warn.extend(family_checks.warnings())
    except Exception as ex:
        warn.append(f"evidence check (tools/evidence_check.py, tools/family_checks.py) did not run: {ex}")

    log = os.path.join(DATA, "research_log.md")
    rows = sum(1 for l in open(log, encoding="utf-8-sig") if re.match(r"^\| \d+ \|", l)) if os.path.exists(log) else 0
    print(f"{len(P)} people, {len(recs)} records, {len(volumes)} volumes, {rows} research log rows")
    for e in err:
        print("ERROR:", e)
    for w in warn:
        print("warning:", w)
    if not err and not warn:
        print("All OK.")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
