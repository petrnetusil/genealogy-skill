#!/usr/bin/env python3
"""Prague police registrations 1850–1914 (Czech National Archives, digi.nacr.cz/prihlasky2) without a browser.

Usage (from the project root):
  prague_police.py <Surname> [Given] [from_year] [to_year]  -> no. | surname | given name | year of birth
The surname is a prefix without diacritics ("Kolar" finds Kolář, Kolár, Kolarik…). Years = the person's year of birth.
Without a browser the site returns only the first 20 results – when there are more, narrow the search by given
name or years.
  prague_police.py card <no.> <output.jpg> <Surname> [Given] [from_year] [to_year]
      -> downloads the card (head of family, wife with place of birth, children, addresses) from the result of the
         same search (also numbers above 20) and prints the citation and permalink (the portal only gives the card
         at 1000 × 1333 px). The tool checks that the searched person is marked on the card – when throttling, the
         portal can return someone else's card; then it exits with an error and saves nothing.
The portal throttles by IP: download cards one at a time (brake: 1 request per 4 s).
Permalink to a card:
  https://digi.nacr.cz/prihlasky2/index.php?action=link&ref=czarch:CZ-100000010:874&karton=<K>&folium=<F>
Covers Prague I–VIII. Smíchov, Vinohrady, Žižkov, Karlín etc. were separate towns until 1922 – no registrations there.
"""
import html, re, sys, time, unicodedata, urllib.parse, urllib.request
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://digi.nacr.cz/prihlasky2/"
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
_op.addheaders = [("User-Agent", polite.UA)]


def get(url, data=None):
    if data:
        data = urllib.parse.urlencode(data).encode()
    for i in range(5):   # the server sometimes does not answer
        try:
            return _op.open(url, data, timeout=40).read().decode("utf-8", "replace")
        except Exception as e:
            print("retry", i + 1, e, file=sys.stderr)
            time.sleep(5 * (i + 1))
    sys.exit("the server does not answer")


def bare(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def check_card(h, number, surname, given, start, end, row):
    """When throttling, the portal can return a card from another search: check the number and the searched person."""
    people = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<div>(.*?)</div>",
              (re.search(r'<div class="seznam_lidi">(.*?</div>)</div>', h, re.S) or re.search("()", "")).group(1))]
    person = re.search(r'<div class="seznam_lidi">.*?<strong>(.*?)</strong>', h, re.S)
    person = html.unescape(re.sub(r"<[^>]+>", "", person.group(1))).strip() if person else ""
    c = re.search(r"záznam č\.\s*(\d+)", h)   # Czech page text: "record no."
    errors = []
    if not c or c.group(1) != str(number):
        errors.append(f"the portal shows record no. {c.group(1) if c else '?'}, not {number}")
    words, year = re.findall(r"[^\s()]+", bare(person)), re.search(r"\((\d{4})\)\s*$", person)
    if not person:
        errors.append("the searched person is not marked on the card")
    else:
        if not any(w.startswith(bare(surname)) for w in words):
            errors.append(f"the marked person \"{person}\" does not have the surname \"{surname}…\"")
        if given and not any(w.startswith(bare(given)) for w in words):
            errors.append(f"the marked person \"{person}\" does not have the given name \"{given}…\"")
        if year and ((start and int(year.group(1)) < int(start)) or (end and int(year.group(1)) > int(end))):
            errors.append(f"year of birth {year.group(1)} is outside {start}–{end}")
        if row and (bare(row[1]) not in bare(person) or row[3] and row[3] not in person
                    or row[2].strip() and bare(row[2].strip()) not in words):
            errors.append(f"the results have \"{row[1]} {row[2]} ({row[3]})\" under no. {number}, the card \"{person}\"")
    if errors:
        sys.exit("The card does NOT MATCH the search – the portal is probably throttling and returned someone else's card. "
                 "Record nothing, try again later (the whole search).\n  " + "\n  ".join(errors) +
                 (f"\n  on the card: {', '.join(people)}" if people else ""))
    return people


def card(session, number, out, checks):
    h = get(f"{BASE}?session={session}&action=image&record={number}")
    m = re.search(r'src="images/((\d+)-(\d+)\.jpg)"', h)
    if not m:
        sys.exit(f"card no. {number} not found (is the number from this search?)")
    people = check_card(h, number, *checks)
    for i in range(5):
        try:
            data = _op.open(BASE + "images/" + m.group(1), timeout=60).read()
            break
        except Exception as e:
            print("retry", i + 1, e, file=sys.stderr)
            time.sleep(5 * (i + 1))
    else:
        sys.exit("the server does not answer")
    if not data.startswith(b"\xff\xd8"):   # when throttling: an error page instead of the image
        sys.exit("the portal did not return the card image (throttling?) – try again later, nothing was saved")
    with open(out, "wb") as f:
        f.write(data)
    k, fo = int(m.group(2)), int(m.group(3))
    print(out, f"– Czech National Archives, Prague Police Headquarters I, conscription, box {k}, image {fo}")
    print("on the card:", ", ".join(people), "(marked = the searched person; still check by reading)")
    print(f"link: {BASE}index.php?action=link&ref=czarch:CZ-100000010:874&karton={k}&folium={fo}")


RX = re.compile(r'record=(\d+)">([^<]*)</a></td>\s*<td class="table_jmeno">([^<]*)</td>\s*<td class="table_rok">([^<]*)<')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    args = sys.argv[1:]
    wanted = None
    if args[0] == "card":
        if len(args) < 4 or not args[1].isdigit():
            sys.exit(__doc__)
        wanted, args = (args[1], args[2]), args[3:]
    a = args + ["", "", ""]
    surname, given, start, end = a[0], a[1], a[2], a[3]
    m = re.search(r"session=([0-9a-f]+)", get(BASE))
    if not m:
        sys.exit("could not open the search (has the website changed?)")
    h = get(BASE + "?session=" + m.group(1),   # the portal's form fields (Czech)
            {"prijmeni": surname, "jmeno": given, "action": "hledani2", "odroku": start, "doroku": end})
    if wanted:
        rows = {r[0]: r for r in RX.findall(h)}
        return card(m.group(1), *wanted, (surname, given, start, end, rows.get(wanted[0])))
    m = re.search(r"záznamů:\s*(\d+)", h)   # Czech page text: "records:"
    n = int(m.group(1)) if m else 0
    print(f"# {surname} {given} {start}–{end}: {n} records")
    for r in RX.findall(h):
        print("\t".join(x.strip() for x in r))
    if n > 20:
        print(f"# only 20 of {n} shown – narrow the search by given name or years of birth")


if __name__ == "__main__":
    main()
