#!/usr/bin/env python3
"""Overview of searched register books: what has been searched for in which book and what was found.

Adapted from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), modified for the project
(idea originally vlastimilvasek/rodokmen-skill, MIT).

Usage (from the project root):
  python3 -I tools/searched_books.py                  -> overview of all books (number of searches, log rows, records)
  python3 -I tools/searched_books.py Dubois           -> only searches and records mentioning the surname (detailed)
  python3 -I tools/searched_books.py --book 617       -> one book in detail (volume key, call number or ARON apu)
  python3 -I tools/searched_books.py --detailed       -> all books in detail (long)
  … --data <folder>                                   -> another data folder (default data/)
The output goes to the screen and to work/searched_books.md (nothing is written into data/).

It combines the existing evidence, nothing is filled in by hand:
  data/volumes.json     books (volume title with call number, portal, number of images, description with places),
  data/records.json     records found in the book (field "volume" = volume key),
  data/research_log.md  searches (table | # | date | source | range | searched | result | citation |) – also the
                        unsuccessful ones. (The Czech column names of older logs – datum, zdroj, rozsah, hledáno,
                        výsledek, citace – are understood too.)
A log row belongs to a book when its source/range/citation columns contain the volume key (e.g. an ARON apu
"1a0b2337") or the call number ("123", "45-6", "DGS 1234567", "book 12345"). For a call number without a hyphen
(e.g. "123") the row must also mention a place from the volume's description, and numbers after "img.", "p.", "fol.",
"no." (and the Czech "sn.", "str.", "č.") are not taken as a call number.
Log rows not matched to any book are counted at the end (listed when a surname is given).
A book searched for one person does not mean another person is not in it – it only covers the range and the
searched names in the columns.
"""
import json, os, re, sys
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND = {"B": "Births/Baptisms", "M": "Marriages", "D": "Deaths/Burials", "X": "Mixed (B/M/D in one book)",
        "?": "Other / undetermined"}
DESC_KIND = (("BIRTHS", "B"), ("BAPTISMS", "B"), ("MARRIAGES", "M"), ("DEATHS", "D"), ("BURIALS", "D"),
             ("NAROZENÝCH", "B"), ("POKŘTĚNÝCH", "B"), ("ODDANÝCH", "M"), ("ZEMŘELÝCH", "D"),
             ("TAUFEN", "B"), ("TRAUUNGEN", "M"), ("STERBEFÄLLE", "D"),
             ("BAPTÊMES", "B"), ("MARIAGES", "M"), ("SÉPULTURES", "D"), ("DOPEN", "B"), ("HUWELIJKEN", "M"),
             ("BEGRAVENISSEN", "D"))
GENERIC = {"Sbírka", "Východočeského", "Státní", "Roman", "Catholic", "Slovakia", "Church", "Synagogue", "Taufen",
           "Index", "Sčítání", "Hradec", "Králové", "Archive", "Archives", "State", "Regional", "Collection",
           "Register", "Registers", "Parish", "Births", "Baptisms", "Marriages", "Deaths", "Burials", "Census",
           "Rijksarchief", "Archives"}   # words from the description that are not the parish's place
NOT_BEFORE = r"(?:img|image|p|pp|page|fol|no|entry|sn|str|č|pag|list|s|zápis|zápisy|čp)\.?\s*$"   # numbers after these are no call number
COLUMNS = {"datum": "date", "zdroj": "source", "rozsah": "range", "hledáno": "searched", "výsledek": "result",
           "citace": "citation"}   # older Czech research logs


def research_log(path):
    """Rows of the research_log.md table as dicts keyed by the header."""
    if not os.path.exists(path):
        return []
    head, out = None, []
    for r in open(path, encoding="utf-8-sig"):
        if not r.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        if head is None:
            head = [COLUMNS.get(c.lower(), c.lower()) for c in cells]
        elif not all(set(c) <= set("-: ") for c in cells):
            out.append(dict(zip(head, cells)))
    return out


def call_numbers(s):
    """Call numbers of the volume as the log writes them: "123", "45-6", "DGS 1234567", "book 12345"."""
    t = s.get("title", "")
    out = []
    m = re.search(r"(?:sign|sig|call no|shelfmark)\.?:?\s*([\w-]+)", t, re.I)
    if m:
        out.append(m.group(1))
    out += ["DGS " + x for x in re.findall(r"DGS\s*(\d+)", t)]
    out += re.findall(r"(?:book|kniha)\s+\d+", t)
    return out


def places(s):
    words = re.findall(r"[A-ZÀ-ÖØ-ÞČĎĚŇŘŠŤŮŽ][a-zß-öø-ÿčďěňřšťůž]{2,}", s.get("description", "") + " " + s.get("title", ""))
    return {w[:5].lower() for w in words if w not in GENERIC}


def belongs(row_text, key, sigs, places_):
    low = row_text.lower()
    if len(key) >= 6 and key.lower() in low:
        return True
    for sig in sigs:
        for m in re.finditer(r"(?<![\w-])" + re.escape(sig) + r"(?![\w-]|[.,]\d)", row_text):
            if re.search(NOT_BEFORE, row_text[:m.start()], re.I):
                continue
            if "-" in sig or " " in sig or len(sig) >= 4:
                return True
            if any(p in low for p in places_):   # short numeric call number: a place from the description must be in the row
                return True
    return False


def volume_kind(s, recs):
    kinds = {d for word, d in DESC_KIND if word in s.get("description", "").upper()}
    if not kinds:
        kinds = {z.get("kind") for z in recs if z.get("kind") in ("B", "M", "D")}
    return kinds.pop() if len(kinds) == 1 else ("X" if kinds else "?")


def short(t, n):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[:n - 1] + "…"


def main():
    argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    data = os.path.join(ROOT, "data")
    book = None
    detailed = "--detailed" in argv
    argv = [a for a in argv if a != "--detailed"]
    for opt in ("--data", "--book"):
        if opt in argv:
            i = argv.index(opt)
            if i + 1 >= len(argv):
                sys.exit(f"{opt} needs a value")
            if opt == "--data":
                data = argv[i + 1]
            else:
                book = argv[i + 1]
            del argv[i:i + 2]
    term = argv[0].lower() if argv else ""
    detailed = detailed or bool(term) or bool(book)

    def jload(name, default):
        p = os.path.join(data, name)
        return json.load(open(p, encoding="utf-8-sig")) if os.path.exists(p) else default

    volumes = jload("volumes.json", {})
    recs_all = jload("records.json", [])
    log = research_log(os.path.join(data, "research_log.md"))
    texts = [" | ".join(r.get(k, "") for k in ("source", "range", "citation")) for r in log]
    used, books = set(), {}
    for key, s in volumes.items():
        sigs, pl = call_numbers(s), places(s)
        if book and book.lower() not in [key.lower(), *(x.lower() for x in sigs)] and not (len(book) >= 8 and book.lower() in s.get("url", "").lower()):
            continue
        recs = [z for z in recs_all if z.get("volume") == key]
        hits = []
        for i, r in enumerate(log):
            if belongs(texts[i], key, sigs, pl):
                hits.append(r)
                used.add(i)
        if term:
            recs = [z for z in recs if term in json.dumps(z, ensure_ascii=False).lower()]
            hits = [r for r in hits if term in " ".join(r.values()).lower()]
        if recs or hits:
            books.setdefault(volume_kind(s, recs), []).append((key, s, sigs, recs, hits))

    heading = "# Searched register books" + (f" – \"{argv[0]}\"" if term else "") + (f" – book {book}" if book else "")
    L = [heading, "", "Computed from data/volumes.json, data/records.json and data/research_log.md (tools/searched_books.py). "
         "Log rows are matched to a book by call number / volume key – check doubtful ones.", ""]
    count = 0
    for kind in sorted(books, key=lambda d: "BMDX?".find(d)):
        L += [f"## {KIND.get(kind, kind)} ({kind})", ""]
        if detailed:
            for key, s, sigs, recs, hits in books[kind]:
                count += 1
                L += [f"### {s.get('title', key)} [`{key}`]",
                      f"{s.get('portal', '')}, {s.get('images', '?')} images – {short(s.get('description', ''), 160)}", ""]
                for r in hits:
                    L.append(f"- log #{r.get('#', '?')} ({r.get('date', '')}): {short(r.get('source', ''), 220)}; "
                             f"searched: {short(r.get('searched', '') or r.get('range', ''), 80)} → "
                             f"{short(r.get('result', ''), 220)}")
                for z in recs:
                    L.append(f"- record `{z.get('key')}`: {z.get('title', '')} (img. {z.get('image', '?')}, {z.get('date', '')})")
                L.append("")
        else:
            L += ["| book | portal | images | searches (log rows) | records found |", "|---|---|---|---|---|"]
            for key, s, sigs, recs, hits in books[kind]:
                count += 1
                nums = ", ".join(r.get("#", "?") for r in hits) or "—"
                z = f"{len(recs)}: " + ", ".join(f"img. {x.get('image', '?')}" for x in recs[:8]) + ("…" if len(recs) > 8 else "") if recs else "—"
                name = f"call no. {sigs[0]}" if sigs else short(s.get("title", key), 50)
                place = short(re.sub(r"^.*?(?:matrika|register) [A-ZÁČĚÍŘŠÚŮÝŽ, ]+,\s*", "", s.get("description", "")), 45)
                L.append(f"| {name} {place} [`{key}`] | {s.get('portal', '')} | {s.get('images', '')} | "
                         f"{len(hits)}× (#{nums}) | {z} |")
            L.append("")
    rest = [r for i, r in enumerate(log) if i not in used and (not term or term in " ".join(r.values()).lower())]
    if rest and not book:
        L += [f"## Log rows without a matched book ({len(rest)})", "",
              "Searches outside volumes.json (web, other sources) or a book written differently from its call number.", ""]
        if detailed:
            L += [f"- #{r.get('#', '?')} {short(r.get('source', ''), 160)} → {short(r.get('result', ''), 160)}" for r in rest]
        else:
            L.append("Row numbers: " + ", ".join(r.get("#", "?") for r in rest))
        L.append("")
    if not count and not rest:
        L.append("Nothing found.")
    L.append(f"Books: {count}, log rows: {len(log)}, of which matched to a book: {len(used)}.")
    text = "\n".join(L)
    print(text)
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    with open(os.path.join(ROOT, "work", "searched_books.md"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
