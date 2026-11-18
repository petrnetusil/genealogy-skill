#!/usr/bin/env python3
"""Arolsen Archives (collections.arolsen-archives.org): prisoners and victims of Nazism, forced labour, displacement – no browser.

Dachau, Mauthausen, Auschwitz (part), Buchenwald, Flossenbürg, Theresienstadt (Terezín), Gestapo, forced labourers, DPs
(displaced persons) after the war and more – over 30 million person records (camp card files, transport lists, ITS
correspondence).

Usage (from the project root):
  arolsen.py consent    -> the user (not Claude!) confirms once every 30 days the declaration the portal shows on entry
                           (sensitive data, personal responsibility; in Claude Code `!python3 -I tools/arolsen.py consent`).
                           Without consent the tool downloads nothing.
  arolsen.py search "Surname Given-name [year]" [filters] [--max N] [--from N] [--details] [--lang en|de]
        -> persons: id | surname | given name | maiden name | born | place of birth | prisoner no. | nationality |
           archive section | link
           Words are combined with "and" (each must be in the record); add the year of birth as another word
           ("Novák Josef 1905"). Phonetic variants are searched too. Sorted by surname; by default N = 40 are shown,
           the portal returns 1000 records at a time (`--from 1000` = the next thousand).
        Filters (narrow the result, optional, can be combined):
           --birthplace Praha       (contains)         --maiden Nováková   (maiden name contains)
           --number 103258          (prisoner number)  --nationality Czech (exact name from the portal only, e.g.
                                                                            Czech, Czechoslovakian, Polish)
           --religion Jewish        (exact name from the portal only)
        --details prints all filled-in fields of each person (father, mother, religion, occupation, place of
        incarceration, date of death, last residence…)
  arolsen.py card <id> <output.jpg>
        -> downloads the image of the index card / document (further images get the suffix _2, _3…) and prints the
           link into the archive
The database stores dates of birth as month/day/year – the tool converts them to "12 Mar 1905".
NOTE: a matching name is not an identification. Names are often misspelled (Novák/Nowak/Novak); check the date and
place of birth on the card and with the family. Data on victims is sensitive – on the website only with the family's
consent (reference/privacy.md). The terms of use of the collection are at https://arolsen-archives.org (data only for
personal, scientific and genealogical purposes). Do not crawl the database in bulk.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: network through our brake
tools/polite.py, a request is not repeated after an error (project rule – the brake watches 429/503 itself);
card through our cache.py (find_url/save_url).
Originally taken over and adapted from a fork (MIT licence, © srameko):
  https://github.com/srameko/rodokmen-skill/blob/5f25edb9a201f8ac03b79293bbcb79b5109d022e/skills/rodokmen/tools/arolsen.py
  (variant: https://github.com/hnizdiljan/rodokmen-skill/blob/d172316bc190d0f44894fa67115505729d587c6a/skills/rodokmen/tools/arolsen.py)
"""
import http.cookiejar, json, os, random, re, string, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # noqa: E402 – shared rate limit for archive websites (polite.py)
import cache   # noqa: E402 – shared image cache (cache.py)
import consent  # noqa: E402 – consent to the entry terms of the online archive (tools/consent.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

CONSENT_KEY, CONSENT_PORTAL, CONSENT_COMMAND = "arolsen", "Arolsen Archives (online archive)", "tools/arolsen.py consent"
CONSENT_TEXT = ("Welcome to the Online Archive of the Arolsen Archives! Our Data Protection Rules and Terms of Use were established by the "
                 "International Commission as the governing body of the Arolsen Archives and do not correspond to German or other national "
                 "archival law. Please note that this portal on persons persecuted by the National Socialists includes sensitive personal data "
                 "on identified or identifiable persons. As a user of this portal, you are obliged to observe applicable data protection law "
                 "and to respect the legitimate concerns of third parties or victims. The Arolsen Archives cannot be held responsible for "
                 "third-party publications that appear as a result of the use made of the collections. Some of the documents held by the "
                 "Arolsen Archives are copies. Other archives hold the originals and the rights of use. Before publishing documents from our "
                 "archives, please always take note of our Terms of Use and, if necessary, obtain the rights from third parties.\n\n"
                 "Declaration of consent: I hereby declare my consent to using sensitive personal data in accordance with applicable national "
                 "laws and provisions. I am aware that any violation of these laws and/or provisions may result in criminal charges.")
CONSENT_URL = "https://arolsen-archives.org/en/materials/terms-of-use/ (data protection rules: https://aroa.to/data-processing-rules)"
API = "https://collections-server.arolsen-archives.org/ITS-WS.asmx/"
WEB = "https://collections.arolsen-archives.org/"
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))   # the server keeps the query in the session
_op.addheaders = [("User-Agent", polite.UA)]


def post(method, data):
    err = None
    for attempt in range(1):   # one attempt (project rule: never retry)
        try:
            req = urllib.request.Request(API + method, data=json.dumps(data).encode(),
                                         headers={"Content-Type": "application/json; charset=utf-8", "Origin": WEB.rstrip("/"), "Referer": WEB})
            with _op.open(req, timeout=90) as r:
                return json.load(r)["d"]
        except (OSError, ValueError, KeyError) as e:   # also an invalid response (HTML error page, JSON without "d")
            err = e
            if getattr(e, "code", 0) in (400, 403, 404):
                break
            time.sleep(3 * (attempt + 1))
    sys.exit(f"Arolsen did not answer properly ({type(err).__name__}: {str(err)[:100]}). Try again later or search on collections.arolsen-archives.org.")


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def date(s):
    """MM/DD/YYYY from the database -> "12 Mar 1905" (the project's date format)."""
    m = re.fullmatch(r"(\d\d)/(\d\d)/(\d{4})", s or "")
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{int(m.group(2))} {MONTHS[int(m.group(1)) - 1]} {m.group(3)}"
    return s or ""


FIELDS = {"Father": "father", "Mother": "mother", "Religion": "religion", "Nationality": "nationality", "Occupaton": "occupation",
          "Place_of_incarceration": "place of incarceration", "Date_of_decease": "death", "Last_residence": "last residence",
          "Last_residence_country": "country", "Last_residence_district": "district", "Last_residence_province": "province",
          "Last_residence_town": "town", "Last_residence_part_of_town": "part of town", "Last_residence_street": "street",
          "Last_residence_house_number": "house number", "Signature": "archive section"}


def load_tag(uid, lang, kind, value):
    """Id of a filter item (nationality, religion) by its exact name on the portal."""
    tags = post("GetTagList", {"uniqueId": uid, "lang": lang, "type": kind, "filter": {}, "top": "", "orderBy": "t1.value", "filterType": "person"})
    matches = [t for t in tags if (t.get("desc") or "").strip().lower() == value.strip().lower()]
    if not matches:
        offer = ", ".join(f"{t['desc']} ({t['count']})" for t in tags[:25])
        sys.exit(f"The value \"{value}\" is not in the filter. This search has e.g.: {offer}")
    return matches[0]["id"]


def search(query, maxn, lang, filters=None, start=0, details=False):
    filters = filters or {}
    uid = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
    post("BuildQueryGlobalForAngular", {"uniqueId": uid, "lang": lang, "archiveIds": [], "strSearch": query, "synSearch": True})
    used = False
    grid = [{"Field": field, "Operator": op, "Value": filters[k]} for k, (field, op) in
            {"birthplace": ("PlaceBirth", "contains"), "maiden": ("MaidenName", "contains"), "number": ("PrisonerNumber", "eq")}.items() if k in filters]
    if grid:
        post("BuildGridFilter", {"uniqueId": uid, "lang": lang, "type": "person", "filter": {"Operator": "and", "Field": "", "Filters": grid, "Value": ""}})
        used = True
    cb = {}
    for key, kind in (("nationality", "per_nationality"), ("religion", "per_religion")):
        if key in filters:
            cb[kind] = [load_tag(uid, lang, kind, filters[key])]
    if cb:
        post("BuildFilter", {"uniqueId": uid, "lang": lang, "searchType": "person", "filter": cb})
        used = True
    total = post("GetCount", {"uniqueId": uid, "lang": lang, "searchType": "person", "useFilter": used})
    rows = post("GetPersonList", {"uniqueId": uid, "lang": lang, "rowNum": start, "orderBy": "LastName", "orderType": "asc"})
    for r in rows[:maxn]:
        print(" | ".join([str(r["ObjId"]), r.get("LastName") or "-", r.get("FirstName") or "-", r.get("MaidenName") or "-", date(r.get("Dob")) or "-",
                          r.get("PlaceBirth") or "-", r.get("PrisonerNumber") or "-", r.get("Nationality") or "-",
                          (r.get("Signature") or "")[:70], f"{WEB}{lang}/document/{r['ObjId']}"]))
        if details:
            extra = [f"{FIELDS[k]}: {date(v) if k == 'Date_of_decease' else v}" for k, v in r.items()
                     if k in FIELDS and v not in ("", None) and k not in ("Signature", "Nationality")]
            if extra:
                print("    " + "; ".join(extra))
    if not rows:
        print("Nothing found (try another spelling, the surname only, or without the year / filters)." if not start
              else "There is nothing beyond this offset.", file=sys.stderr)
    else:
        if len(rows) > maxn:
            print(f"… loaded {len(rows)} of {total} records, shown {maxn}; --max {len(rows)} shows more, a year, given "
                  "name or filter narrows the search", file=sys.stderr)
        try:
            more = int(re.sub(r"\D", "", str(total)) or 0) > start + len(rows)
        except ValueError:
            more = False
        if more:
            print(f"… {total} records in total, loaded {len(rows)} (from {start}); next thousand: --from {start + len(rows)}, "
                  "a year, given name or filter narrows the search", file=sys.stderr)


def _download_image(url):
    req = urllib.request.Request(url, headers={"Referer": WEB, "User-Agent": polite.UA})
    with _op.open(req, timeout=90) as r:
        if urllib.parse.urlsplit(r.geturl()).hostname != "collections-server.arolsen-archives.org":
            sys.exit(f"Redirect to an unexpected server: {r.geturl()[:80]}")
        if not (r.headers.get("Content-Type") or "").startswith("image/"):
            sys.exit(f"The server did not return an image ({r.headers.get('Content-Type')}).")
        return r.read()


def card(objid, out):
    if not objid.isdigit():
        sys.exit("id is the number in the first column of the `search` output.")
    images = post("GetFileByObj", {"objId": int(objid), "lang": "en"})
    if not images:
        sys.exit("The record has no image (only an entry in the card file).")
    base, ext = os.path.splitext(out)
    for i, o in enumerate(images, 1):
        url = (o.get("image") or "").replace("\\\\", "//").replace("\\", "/")
        if urllib.parse.urlsplit(url).hostname != "collections-server.arolsen-archives.org":
            sys.exit(f"Unexpected image server: {url[:80]}")
        target = out if i == 1 else f"{base}_{i}{ext}"
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        stored = cache.find_url(url)
        data = open(stored, "rb").read() if stored else _download_image(url)
        if not stored and not cache.find_url(url):
            cache.save_url(url, data)
        with open(target, "wb") as fh:
            fh.write(data)
        print(target, "|", o.get("title", ""), "|", WEB + o.get("relatedLink", ""))
        time.sleep(0.5)


if __name__ == "__main__":
    a = sys.argv[1:]
    maxn, lang, start, details, filters = 40, "en", 0, False, {}
    if "--details" in a:
        a.remove("--details")
        details = True
    FILTERS = {"--birthplace": "birthplace", "--maiden": "maiden", "--number": "number", "--nationality": "nationality",
               "--religion": "religion"}
    for opt in ("--max", "--from", "--lang", *FILTERS):
        if opt in a:
            i = a.index(opt)
            if i + 1 >= len(a) or a[i + 1].startswith("--") or not a[i + 1].strip() \
                    or (opt in ("--max", "--from") and not (a[i + 1].isascii() and a[i + 1].isdigit())) or (opt == "--max" and int(a[i + 1]) < 1) \
                    or (opt == "--lang" and a[i + 1] not in ("en", "de")):
                sys.exit(f"{opt}: missing or invalid value (--max a positive number, --from a number, --lang en|de, "
                         "other filters text).")
            if opt == "--max":
                maxn = int(a[i + 1])
            elif opt == "--from":
                start = int(a[i + 1])
            elif opt == "--lang":
                lang = a[i + 1]
            else:
                filters[FILTERS[opt]] = a[i + 1]
            del a[i:i + 2]
    if not a:
        sys.exit(__doc__)
    if a[0] == "consent" and len(a) == 1:
        consent.confirm(CONSENT_KEY, CONSENT_PORTAL, CONSENT_TEXT, CONSENT_URL, CONSENT_COMMAND)
    elif a[0] == "search" and len(a) == 2 and a[1].strip():
        consent.require(CONSENT_KEY, CONSENT_PORTAL, CONSENT_TEXT, CONSENT_COMMAND)
        search(a[1], maxn, lang, filters, start, details)
    elif a[0] == "card" and len(a) == 3:
        consent.require(CONSENT_KEY, CONSENT_PORTAL, CONSENT_TEXT, CONSENT_COMMAND)
        card(a[1], a[2])
    else:
        sys.exit(__doc__)
