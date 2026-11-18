#!/usr/bin/env python3
"""Sieve – a systematic pass through a book without an index in batches of contact sheets, recording the images read
and the hits.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: archives aron, pf, ahmp
(no MZA – it forbids scripts), contact_sheet.py run with -I, exit code 3 when the brake stops a site.
Idea taken from "Síto Jev" of the xsigik fork (changes #21–#24):
  https://github.com/xsigik/rodokmen-skill/blob/9aa2c189892885f579df3043a2da04ed245f23e6/skills/rodokmen/tools/sito.py
  https://github.com/xsigik/rodokmen-skill/blob/9aa2c189892885f579df3043a2da04ed245f23e6/skills/rodokmen/reference/sito_jev.md
Licence: MIT (original © Jakub Valenta, xsigik; changes rodokmen-plus).
Difference: the original sorts the strips with the paid model TypeSafe Jev (OMP only). Here Claude (or a helper)
reads the contact sheets from tools/contact_sheet.py; the safeguards are kept – a fixed range, no gap, continuous
recording, resuming after an interruption, "not found" only for images really read.

Usage (from the project root):
  sieve.py create <search> <archive> <book> <from> <to> [--skip 1,2,240] [--crop x0,y0,x1,y1] [--per N] [--question "…"]
  sieve.py create <search> <archive> <book> --year <volume key> <year> [options]    (range from the volume's orientation)
  sieve.py next <search>                  -> contact sheet of the next unread batch (contact_sheet.py, through cache.py
                                             and polite.py)
  sieve.py done <search> <from> [<to>]    -> images read and finished (also without a hit)
  sieve.py hit <search> <image> "<what>"  -> a candidate to read at full resolution
  sieve.py status <search>                -> coverage, gaps, hits (exit code 1 until the whole range has been read)
archive = a portal with an image tool: aron | pf | ahmp (see the country guide).

Journal: work/sieve/<search>.json. A hit is only a lead – it goes into the data once it has been read on the image
(SKILL.md). A search that found nothing belongs into research_log.md as "sieve: images from–to read, nothing" with
the question.
"""
import json, os, re, subprocess, sys
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DIR = os.path.join(ROOT, "work", "sieve")
ARCHIVES = ("aron", "pf", "ahmp")


def path_of(h):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", h):
        sys.exit("name the search with letters without diacritics, digits, _ and - only (e.g. novak_jan_baptism)")
    return os.path.join(DIR, h + ".json")


def load(h):
    p = path_of(h)
    if not os.path.exists(p):
        sys.exit(f"search \"{h}\" has not been created (sieve.py create …)")
    return json.load(open(p, encoding="utf-8"))


def save(h, d):
    os.makedirs(DIR, exist_ok=True)
    p = path_of(h)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)   # atomic – an interruption never leaves a half-written journal


def numbers(s):
    return sorted({int(x) for x in s.split(",") if x.strip()}) if s else []


def remaining(d):
    finished = set(d["done"]) | set(d["skip"])
    return [n for n in range(d["from"], d["to"] + 1) if n not in finished]


def create(a):
    options, rest, i = {}, [], 0
    while i < len(a):
        if a[i] == "--year" and i + 2 < len(a):
            options["year"] = (a[i + 1], int(a[i + 2])); i += 3
        elif a[i] in ("--skip", "--crop", "--per", "--question") and i + 1 < len(a):
            options[a[i][2:]] = a[i + 1]; i += 2
        else:
            rest.append(a[i]); i += 1
    if len(rest) < 3 or rest[1] not in ARCHIVES:
        sys.exit(__doc__)
    h, archive, book = rest[:3]
    if os.path.exists(path_of(h)):
        sys.exit(f"search \"{h}\" already exists – continue with sieve.py next {h}")
    if "year" in options:
        import contact_sheet
        start, end = contact_sheet.year_range(*options["year"])
    elif len(rest) == 5 and rest[3].isdigit() and rest[4].isdigit():
        start, end = int(rest[3]), int(rest[4])
    else:
        sys.exit("give the range <from> <to>, or --year <volume key> <year>")
    if start < 1 or start > end:
        sys.exit("range: 1 ≤ from ≤ to")
    d = {"archive": archive, "book": book, "from": start, "to": end, "skip": numbers(options.get("skip")),
         "crop": options.get("crop"), "per": int(options.get("per", 6)), "question": options.get("question", ""),
         "done": [], "hits": []}
    save(h, d)
    print(f"{h}: {archive} {book}, images {start}–{end}, {len(remaining(d))} to sieve in batches of {d['per']}")


def next_batch(h):
    d = load(h)
    z = remaining(d)
    if not z:
        print(f"{h}: the range {d['from']}–{d['to']} has been read completely"); return
    batch = [n for n in z if n < z[0] + d["per"]]   # a continuous stretch – the contact sheet skips gaps (skipped) itself
    start, end = batch[0], batch[-1]
    cmd = [sys.executable, "-I", os.path.join(TOOLS, "contact_sheet.py"), d["archive"], d["book"], str(start), str(end),
           "--per", str(d["per"]), "-o", os.path.join(DIR, h)]
    if d.get("crop"):
        cmd += ["--crop", d["crop"]]
    if d.get("question"):
        print(f"question: {d['question']}")
    r = subprocess.run(cmd)
    print(f"after reading: sieve.py done {h} {start} {end}  (hit: sieve.py hit {h} <image> \"…\"); "
          f"{len(z)} images remaining")
    if r.returncode:
        sys.exit(r.returncode)


def done(h, start, end=None):
    d = load(h)
    start, end = int(start), int(end or start)
    if not d["from"] <= start <= end <= d["to"]:
        sys.exit(f"outside the range of the search {d['from']}–{d['to']}")
    d["done"] = sorted(set(d["done"]) | set(range(start, end + 1)))
    save(h, d)
    print(f"{h}: read {len(d['done'])}, remaining {len(remaining(d))}")


def hit(h, n, what):
    d = load(h)
    n = int(n)
    if not d["from"] <= n <= d["to"]:
        sys.exit(f"image {n} is outside the range {d['from']}–{d['to']}")
    d["hits"].append({"image": n, "what": what})
    save(h, d)
    print(f"{h}: hit on image {n} – read it at full resolution before you record anything")


def status(h):
    d = load(h)
    z = remaining(d)
    print(f"{h}: {d['archive']} {d['book']}, images {d['from']}–{d['to']}"
          + (f", skipped {','.join(map(str, d['skip']))}" if d["skip"] else ""))
    if d.get("question"):
        print(f"question: {d['question']}")
    print(f"read {len(d['done'])}, remaining {len(z)}" + (f" (from image {z[0]})" if z else " – complete"))
    for x in d["hits"]:
        print(f"  hit img. {x['image']}: {x['what']}")
    if z:
        sys.exit(1)


def main(a):
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    sys.path.insert(0, TOOLS)
    p, r = a[0], a[1:]
    if p == "create":
        return create(r)
    if p == "next" and len(r) == 1:
        return next_batch(r[0])
    if p == "done" and len(r) in (2, 3):
        return done(*r)
    if p == "hit" and len(r) == 3:
        return hit(*r)
    if p == "status" and len(r) == 1:
        return status(r[0])
    sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
