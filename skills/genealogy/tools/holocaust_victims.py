#!/usr/bin/env python3
"""Database of victims of Nazi persecution (holocaust.cz, Terezín Initiative Institute, Czech lands) without a browser.

Usage (from the project root):
  holocaust_victims.py consent  -> the user (not Claude!) confirms once every 30 days the "terms of entry to the database"
                                   the portal shows on entry (the database holds sensitive data; in Claude Code
                                   `!python3 -I tools/holocaust_victims.py consent`). Without consent nothing is downloaded.
  holocaust_victims.py search [--surname S] [--given G] [--residence R] [--birthplace B] [--year Y] [--pages N]
        -> name | birth | fate (transports, death) | link; N pages of 20 victims (default 3).
           Enter surnames also in the female form and with diacritics ("Nováková"); a partial name is searched as a prefix.
  holocaust_victims.py detail <link|number>
        -> last residence before deportation, address in the Protectorate, transports, fate, related documents
This is data on murdered people (Jews from the Czech lands, Roma in a separate database) – name, date of birth,
transports. It is a lead to an ancestor's fate, not a substitute for a parish register. On the family website only with
the family's consent (see `reference/privacy.md`).

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: network through our brake
tools/polite.py, a request is not repeated after an error (project rule – the brake watches 429/503 itself).
Originally taken over and adapted from a fork (MIT licence, © srameko):
  https://github.com/srameko/rodokmen-skill/blob/5f25edb9a201f8ac03b79293bbcb79b5109d022e/skills/rodokmen/tools/obeti.py
  (variant: https://github.com/hnizdiljan/rodokmen-skill/blob/d172316bc190d0f44894fa67115505729d587c6a/skills/rodokmen/tools/obeti.py)
"""
import os, html, http.cookiejar, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # noqa: E402 – shared rate limit for archive websites (polite.py)
import consent  # noqa: E402 – consent to the database's terms of entry (tools/consent.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://www.holocaust.cz/databaze-obeti/"
CONSENT_KEY, CONSENT_PORTAL, CONSENT_COMMAND = ("holocaust_cz", "Database of victims (holocaust.cz)",
                                                "tools/holocaust_victims.py consent")
# The portal's own terms are in Czech: an English translation first, then the original wording as the portal shows it.
CONSENT_TEXT = ("The database of victims of Nazi persecution contains the names and fates of Jews deported from the Czech "
                "lands and of prisoners of the Terezín ghetto from other European countries, and basic information on Roma, "
                "Sinti and other persons who died as prisoners in the so-called \"Gypsy camp I\" in Lety near Písek. Please "
                "note that the database contains sensitive personal data and its purpose is dignified remembrance with "
                "respect for the bereaved. By entering the database the user confirms having read the information about its "
                "content and being fully aware of their personal responsibility for handling the materials and information "
                "found in it.\n\n"
                "Original wording (Czech, as shown by the portal):\n"
                "Databáze obětí nacistického pronásledování obsahuje jména a osudy Židů deportovaných z českých zemí a vězňů "
                "terezínského ghetta z dalších evropských zemí a dále základní informace o Romech, Sintech a dalších osobách, "
                "které zemřely jako vězni v takzvaném „Cikánském táboře I“ v Letech u Písku. Upozorňujeme, že databáze obsahuje "
                "citlivé osobní údaje a jejím účelem je důstojné vzpomínání s respektem vůči pozůstalým. Vstupem do databáze "
                "uživatel potvrzuje, že se seznámil s informacemi o jejím obsahu a je si plně vědom své osobní odpovědnosti za "
                "nakládání s materiály a informacemi, které v ní nalezne.")
CONSENT_URL = "https://www.holocaust.cz/databaze-obeti/help/"
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
_op.addheaders = [("User-Agent", polite.UA)]


def get(url, data=None):
    err = None
    for attempt in range(1):   # one attempt (project rule: never retry)
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
            with _op.open(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except OSError as e:
            err = e
            if getattr(e, "code", 0) in (403, 404):
                break
            time.sleep(2 * (attempt + 1))
    sys.exit(f"The portal did not answer ({type(err).__name__}: {str(err)[:100]}). Try again later.")


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def listing(page):
    out = []
    for block in re.findall(r'<div class="victims-wrapper">(.*?)</div>', page, re.S):
        m = re.search(r'<p>\s*<a href="([^"]+)">(.*?)</a>(.*?)</p>', block, re.S)
        if m:
            rest = [text(x) for x in re.split(r"<br\s*/?>", m.group(3)) if text(x)]
            out.append((text(m.group(2)), " | ".join(rest), m.group(1)))
    return out


def search(fields, pages):
    # form field names and the Czech submit label are the portal's own
    page = get(BASE, {"searchFirstname": fields.get("given", ""), "searchSurname": fields.get("surname", ""),
                      "searchPlaceLast": fields.get("residence", ""), "searchPlaceBirth": fields.get("birthplace", ""),
                      "searchDateBirthDay": "0", "searchDateBirthMonth": "0", "searchDateBirthYear": fields.get("year", ""),
                      "searchTransport": "", "searchSubmit": "Vyhledat v databázi"})
    total = re.search(r"Celkem nalezeno: ([\d\s\xa0]+)", page)   # Czech page text: "found in total"
    n = 0
    for p in range(1, pages + 1):
        for r in listing(page):
            print(" | ".join(r))
            n += 1
        nxt = re.search(r'<a href="(https://www\.holocaust\.cz/databaze-obeti/strana/\d+/)">další</a>', page)   # "next"
        if not nxt or p == pages:
            break
        page = get(nxt.group(1))
        time.sleep(0.5)
    if not total:
        print("The portal returned no results (has the form changed?). Search in the browser.", file=sys.stderr)
    elif n == 0:
        print("Nothing found (try the surname in the female form, without the given name or with fewer details).",
              file=sys.stderr)
    elif n < int(re.sub(r"\D", "", total.group(1)) or 0):
        print(f"… {total.group(1).strip()} found in total, shown {n}; narrow down by given name or year, --pages gives more",
              file=sys.stderr)


def detail(arg):
    if not arg.startswith("http") and not re.fullmatch(r"[0-9a-z-]+", arg):
        sys.exit("Give the link to the victim (from the `search` output) or its number with the name, e.g. 12345-jana-novakova.")
    url = arg if arg.startswith("http") else f"{BASE}obet/{arg}/"
    if not url.startswith(BASE):
        sys.exit("The link must be from the victims database on holocaust.cz.")
    page = get(url)
    name = re.search(r"<h1>(.*?)</h1>", page, re.S)
    w = re.search(r'<div class="wrapper">.*?<p>(.*?)</p>', page, re.S)
    if not name or not w:
        sys.exit("Victim not found (check the link).")
    print(text(name.group(1)))
    for r in re.split(r"<br\s*/?>", w.group(1)):
        if text(r):
            print("  " + text(r))
    for href, title in re.findall(r'<div class="victim-documents">\s*<a href="([^"]+)">.*?<span>(.*?)</span>', page, re.S):
        print(f"  document: {text(title)} | {href}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "consent" and len(a) == 1:
        consent.confirm(CONSENT_KEY, CONSENT_PORTAL, CONSENT_TEXT, CONSENT_URL, CONSENT_COMMAND)
        sys.exit(0)
    if a[0] in ("search", "detail"):
        consent.require(CONSENT_KEY, CONSENT_PORTAL, CONSENT_TEXT, CONSENT_COMMAND)
    if a[0] == "search":
        fields, pages, i = {}, 3, 1
        keys = {"--surname": "surname", "--given": "given", "--residence": "residence", "--birthplace": "birthplace",
                "--year": "year"}
        while i < len(a):
            if a[i] == "--pages" and i + 1 < len(a) and a[i + 1].isdigit() and int(a[i + 1]) >= 1:
                pages, i = int(a[i + 1]), i + 2
            elif a[i] in keys and i + 1 < len(a):
                fields[keys[a[i]]], i = a[i + 1], i + 2
            else:
                sys.exit(__doc__)
        if not fields:
            sys.exit("Give at least --surname (or --given, --residence, --birthplace).")
        if "year" in fields and not re.fullmatch(r"\d{4}", fields["year"]):
            sys.exit("--year needs a four-digit year of birth.")
        search(fields, pages)
    elif a[0] == "detail" and len(a) == 2:
        detail(a[1])
    else:
        sys.exit(__doc__)
