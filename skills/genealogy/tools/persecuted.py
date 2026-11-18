#!/usr/bin/env python3
"""Database of politically and racially persecuted persons (Terezín Memorial, pamatnik-terezin.cz/databaze) without a browser.

Czech prisoners in the concentration camps Buchenwald, Dachau, Flossenbürg (and sub-camps), Mauthausen, Ravensbrück,
in the Terezín ghetto, the internment camp, the Small Fortress Terezín, Pankrác prison and others (completeness
differs by camp).

Usage (from the project root):
  persecuted.py consent  -> the user (not Claude!) confirms once every 30 days responsible handling of sensitive data
                            (in Claude Code `!python3 -I tools/persecuted.py consent`). Without consent nothing is downloaded.
  persecuted.py search [--surname S] [--given G] [--born "15. 3. 1910"] [--place P] [--number N] [--pages N]
        -> surname | given name | born | place of birth | database (camp) | link; N pages of 20 records (default 2).
           --born uses the portal's date format "D. M. YYYY". Try the surname with and without diacritics
           (Novák / Novak – the camps wrote it differently). A value means "starts with".
  persecuted.py detail <link|slug>
        -> all fields: residence, handed over by, transports, imprisonment, prisoner numbers, where the original is kept
The data comes from contemporary documents (often from the Czech National Archives) – check the date and place of
birth with the family and in the parish register. Sensitive – on the website only with the family's consent
(reference/privacy.md).

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: network through our brake
tools/polite.py, a request is not repeated after an error (project rule – the brake watches 429/503 itself).
Originally taken over and adapted from a fork (MIT licence, © hnizdiljan):
  https://github.com/hnizdiljan/rodokmen-skill/blob/d172316bc190d0f44894fa67115505729d587c6a/skills/rodokmen/tools/vezni.py
"""
import os, html, http.cookiejar, json, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # noqa: E402 – shared rate limit for archive websites (polite.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

import consent  # noqa: E402 – consent to the terms (tools/consent.py)

BASE = "https://www.pamatnik-terezin.cz"
CONSENT_KEY, CONSENT_PORTAL, CONSENT_COMMAND = ("pamatnik_terezin", "Database of prisoners (Terezín Memorial)",
                                                "tools/persecuted.py consent")
CONSENT_TEXT = ("The Terezín Memorial's database of politically and racially persecuted persons contains sensitive "
                "personal data of prisoners of Nazi camps and prisons (birth, residence, imprisonment, prisoner numbers, "
                "death). I use the data only for personal and genealogical research, with respect for the victims and the "
                "bereaved, and I will publish it only with the family's consent. (Notice of the tool; the Terezín "
                "Memorial's terms of use apply.)")
CONSENT_URL = "https://www.pamatnik-terezin.cz/databaze"
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
_op.addheaders = [("User-Agent", polite.UA)]
FIELDS = {"--surname": "s1", "--given": "s2", "--born": "s3", "--place": "s4", "--number": "s7"}   # portal form fields


def get(url, data=None, ajax=False):
    err = None
    for attempt in range(1):   # one attempt (project rule: never retry)
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None,
                                         headers={"X-Requested-With": "XMLHttpRequest"} if ajax else {})
            with _op.open(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except OSError as e:
            err = e
            if getattr(e, "code", 0) in (403, 404):
                break
            time.sleep(2 * (attempt + 1))
    sys.exit(f"The portal did not answer ({type(err).__name__}: {str(err)[:100]}). Try again later or search in the browser.")


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def search(fields, pages):
    form = get(BASE + "/databaze")
    f = re.search(r'<form method="post" action="">.*?</form>', form, re.S)
    if not f:
        sys.exit("The portal has changed the page (the search form was not found). Search in the browser.")
    data = dict(re.findall(r'name="(db_\d+)" value="(\d)"', f.group(0)))   # all databases (camps) switched on
    data.update({f"s{i}": "" for i in range(1, 11)})
    data.update(fields)
    n, total = 0, None
    for p in range(1, pages + 1):
        j = json.loads(get(BASE + "/databaze", {"ax": "searchBasic", "p": str(p), "o0": "0", "o1": "0", **data}, ajax=True))
        if j.get("err") == "no_result":
            break   # nothing found – the message is printed below
        if j.get("err"):
            sys.exit("The portal returned an error: " + text(str(j["err"]))[:200])
        res = j["results"]
        total = total or re.search(r"Záznamů:\s*([\d\s\xa0]+)", res)   # Czech page text: "records:"
        rows = re.findall(r'<div id="i\d+" class="tr trd">(.*?)</a></div>\s*</div>', res, re.S)
        for r in rows:
            cells = {c: text(v) for c, v in re.findall(r'<div class="td (\w+)">(.*?)</div>', r, re.S)}
            link = re.search(r'href="(/vezen/[^"]+)"', r)
            print(" | ".join([cells.get("fmn", ""), cells.get("gvn", ""), cells.get("brd", "") or "-", cells.get("pln", "") or "-",
                              (re.findall(r'<div class="td dbn">(.*?)</div>', r, re.S) or [""])[0].strip(),
                              BASE + link.group(1) if link else "-"]))
            n += 1
        if not rows or f"page_{p + 1}" not in res:
            break
        time.sleep(0.7)
    if n == 0:
        print("Nothing found (try the surname without diacritics, the surname only, or a shorter prefix).", file=sys.stderr)
    elif total and n < int(re.sub(r"\D", "", total.group(1)) or 0):
        print(f"… {total.group(1).strip()} records in total, shown {n}; narrow down by given name and year, --pages gives more",
              file=sys.stderr)


def detail(arg):
    url = arg if arg.startswith("http") else f"{BASE}/vezen/{arg.strip('/').split('/')[-1]}"
    if not url.startswith(BASE + "/vezen/"):
        sys.exit("The link must be from the Terezín Memorial website (…/vezen/…).")
    page = get(url)
    t = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S))
    i = t.find("Databáze českých vězňů")   # Czech page headings: "Database of Czech prisoners", "Name"
    if i < 0:
        i = t.find("Jméno")
    k = t.find("Cookies", i)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    print((text(h1.group(1)) + " – " if h1 else "") + t[i:k if k > i else i + 1500].strip())


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a == ["consent"]:
        consent.confirm(CONSENT_KEY, CONSENT_PORTAL, CONSENT_TEXT, CONSENT_URL, CONSENT_COMMAND)
        sys.exit(0)
    if a[0] in ("search", "detail"):
        consent.require(CONSENT_KEY, CONSENT_PORTAL, CONSENT_TEXT, CONSENT_COMMAND)
    if a[0] == "search":
        fields, pages, i = {}, 2, 1
        while i < len(a):
            if a[i] == "--pages" and i + 1 < len(a) and a[i + 1].isdigit() and int(a[i + 1]) >= 1:
                pages, i = int(a[i + 1]), i + 2
            elif a[i] in FIELDS and i + 1 < len(a):
                fields[FIELDS[a[i]]], i = a[i + 1], i + 2
            else:
                sys.exit(__doc__)
        if not fields:
            sys.exit("Give at least --surname (or --given, --born, --place, --number).")
        search(fields, pages)
    elif a[0] == "detail" and len(a) == 2:
        detail(a[1])
    else:
        sys.exit(__doc__)
