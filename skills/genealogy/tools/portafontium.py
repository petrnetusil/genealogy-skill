#!/usr/bin/env python3
"""Registers of SOA Plzeň (Czech regional archive, west Bohemia) on the Porta fontium portal (portafontium.eu) without
a browser.

Usage (from the project root `python3 -I tools/portafontium.py …`, on Windows `python -I -X utf8 tools/portafontium.py …`):
  portafontium.py parish <parish>            -> books of the parish: book | villages | years and kinds (* births,
                                                oo marriages, + deaths, i index) | description
                                                <parish> = part of the URL of the Roman Catholic parish, e.g. "dolni-bela"
                                                (https://www.portafontium.eu/contents/register/soap-pn/cirkev-rimskokatolicka/dolni-bela);
  portafontium.py village <village>          -> books with the village in the description, grouped by parish (also
                                                historical names of the village; drop villages of the same name in
                                                other parishes by the villages column)
  portafontium.py info <book>                -> description of the book (reference code, kind, cover text…) and number
                                                of images; <book> = part of the book URL, e.g. "dolni-bela-17"
  portafontium.py image <book> <image> <output.jpg> [preview] [x0,y0,x1,y1]
                                             -> the image at full resolution (IIIF, one request); "preview" = 1/4;
                                                x0,y0,x1,y1 = crop only (fractions 0..1)
  portafontium.py link <book> <image>        -> permalink to the image (field "link" in records.json)
  portafontium.py volume <book>              -> write the volume into data/volumes.json (key pf_<book>)
Image = the sequence number of the thumbnail in the portal's viewer (1, 2, 3…). Book pages are cached in work/.cache_pf/.
Be considerate to the server: download only images you read.
"""
import html, http.client, json, os, re, ssl, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
import cache  # noqa: E402 – shared image cache (tools/cache.py): crop and preview from the stored image
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://www.portafontium.eu"
ARCHIV = "soap-pn"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "work", ".cache_pf")
UA = {"User-Agent": polite.UA}   # without a browser-like User-Agent the portal returns 403
PAUSE = 0.5   # s before every request – consideration for the server even when called in a loop

# The portal's server sends only its own certificate without the intermediate one (browsers and curl find it, Python
# does not → CERTIFICATE_VERIFY_FAILED). The intermediate certificate GEANT TLS RSA 1 (issued by HARICA TLS RSA Root CA
# 2021, valid until 2039, SHA-256 5B:67:8D:C4:…:A5:FB:8C:79, from http://crt.harica.gr/HARICA-GEANT-TLS-R1.cer) is added
# only as a chain link: without PARTIAL_CHAIN it does not become a trust anchor, verification must still end at a
# system root certificate.
GEANT_TLS_RSA_1 = """
-----BEGIN CERTIFICATE-----
MIIGBTCCA+2gAwIBAgIQFNV782kiKCGaVWf6kWUbIjANBgkqhkiG9w0BAQsFADBs
MQswCQYDVQQGEwJHUjE3MDUGA1UECgwuSGVsbGVuaWMgQWNhZGVtaWMgYW5kIFJl
c2VhcmNoIEluc3RpdHV0aW9ucyBDQTEkMCIGA1UEAwwbSEFSSUNBIFRMUyBSU0Eg
Um9vdCBDQSAyMDIxMB4XDTI1MDEwMzExMTUwMFoXDTM5MTIzMTExMTQ1OVowYDEL
MAkGA1UEBhMCR1IxNzA1BgNVBAoMLkhlbGxlbmljIEFjYWRlbWljIGFuZCBSZXNl
YXJjaCBJbnN0aXR1dGlvbnMgQ0ExGDAWBgNVBAMMD0dFQU5UIFRMUyBSU0EgMTCC
AaIwDQYJKoZIhvcNAQEBBQADggGPADCCAYoCggGBAKEEaZSzEzznAPk8IEa17GSG
yJzPTj4cwRY7/vcq2BPT5+IRGxQtaCdgLXIEl2cdPdIkj2eyakFmgMjAtyeju8V8
dRayQCD/bWjJ7thDlowgLljQaXirxnYbT8bzRHAhCZqBakYgi5KWw9dANLyDHGpX
UdY259ab0lWEaFE5Uu6IzQSMJOAy4l/Twym8GUiy0qMDEBFSlm31C9BXpdHKKAlh
vIjMiKoDeTWl5vZaLB2MMRGY1yW2ftPgIP0/MkX1uFITlvHmmMTngxplH1nybEIJ
FiwHg1KiLk1TprcZgeO2gxE5Lz3wTFWrsUlAzrh5xWmscWkjNi/4BpeuiT5+NExF
czboLnXOfjuci/7bsnPi1/aZN/iKNbJRnngFoLaKVMmqCS7Xo34f+BITatryQZFE
u2oDKExQGlxDBCfYMLgLucX/onpLzUSgeQITNLx6i5tGGbUYH+9Dy3GI66L/5tPj
qzlOsydki8ZYGE5SBJeWCZ2IrhUe0WzZ2b6Zhk6JAQIDAQABo4IBLTCCASkwEgYD
VR0TAQH/BAgwBgEB/wIBADAfBgNVHSMEGDAWgBQKSCOmYKSSCjPqk1vFV+olTb0S
7jBNBggrBgEFBQcBAQRBMD8wPQYIKwYBBQUHMAKGMWh0dHA6Ly9jcnQuaGFyaWNh
LmdyL0hBUklDQS1UTFMtUm9vdC0yMDIxLVJTQS5jZXIwEQYDVR0gBAowCDAGBgRV
HSAAMB0GA1UdJQQWMBQGCCsGAQUFBwMCBggrBgEFBQcDATBCBgNVHR8EOzA5MDeg
NaAzhjFodHRwOi8vY3JsLmhhcmljYS5nci9IQVJJQ0EtVExTLVJvb3QtMjAyMS1S
U0EuY3JsMB0GA1UdDgQWBBSGAXI/jKlw4jEGUxbOAV9becg8OzAOBgNVHQ8BAf8E
BAMCAYYwDQYJKoZIhvcNAQELBQADggIBABkssjQzYrOo4GMsKegaChP16yNe6Sck
cWBymM455R2rMeuQ3zlxUNOEt+KUfgueOA2urp4j6TlPbs/XxpwuN3I1f09Luk5b
+ZgRXM7obE6ZLTerVQWKoTShyl34R2XlK8pEy7+67Ht4lcJzt+K6K5gEuoPSGQDP
ef+fUfmXrFcgBMcMbtfDb9dubFKNZZxo5nAXiqhFMOIyByag3H+tOTuH8zuId9pH
RDsUpAIHJ9/W2WBfLcKav7IKRlNBRD/sPBy903J9WHPKwl8kQSDA+aa7XCYk7bJt
Eyf+7GM9F5cZ7+YyknXqnv/rtQEkTKZdQo5Us18VFe9qqj94tXbLdk7PejJYNB4O
Zlli44Ld7rtqfFlUych7gIxFOmiyxMQQYrYmUi+74lEZvfoNhuref0CupuKpz6O3
dLv6kO9T10uNdDBoBQTkge3UzHafTIe3R2o3ujXKUGPwyc9m7/FETyKLUCwSU/5O
AVOeBCU8QtkKKjM8AmbpKpe3pHWcyq3R7B3LmIALkMPTydyDfxen65IDqREbVq8N
xjhkJThUz40JqOlN6uqKqeDISj/IoucYwsqW24AlO7ZzNmohQmMi8ep23H4hBSh0
GBTe2XvkuzaNf92syK8l2HzO+13GLCjzYLTPvXTO9UpK8DGyfGZOuamuwbAnbNpE
3RfjV9IaUQGJ
-----END CERTIFICATE-----
"""
SSL_CTX = ssl.create_default_context()
SSL_CTX.verify_flags &= ~getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
SSL_CTX.load_verify_locations(cadata=GEANT_TLS_RSA_1)


def get(url, binary=False):
    url = url if url.startswith("http") else BASE + url
    err = None
    wait = 0
    for attempt in range(4):
        time.sleep(wait or PAUSE)
        wait = 2 * (attempt + 1)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120, context=SSL_CTX) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                sys.exit(f"Porta fontium: page not found (404): {url}")
            if e.code == 429:   # too many requests – wait (per Retry-After) and try again
                ra = e.headers.get("Retry-After", "")
                wait = min(int(ra), 120) if ra.isdigit() else 30 * (attempt + 1)
                err = e
                continue
            if e.code < 500:   # retrying does not fix a 4xx
                sys.exit(f"Porta fontium refused the request ({e.code}): {url}")
            err = e
        except (OSError, http.client.HTTPException) as e:   # also a truncated transfer (IncompleteRead)
            err = e
    sys.exit(f"Porta fontium does not answer ({err}): {url}")


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def book_page(book):
    book = book.strip("/").split("/")[-1]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, book + ".html")
    if os.path.exists(path):
        return book, open(path, encoding="utf-8").read()
    page = get(f"/register/{ARCHIV}/{book}")
    if "data-iip-path" in page:   # cache only a real book page with images
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
    return book, page


def info(book):
    book, page = book_page(book)
    fields = {}
    for m in re.finditer(r'<div class="field-label">(.*?)</div>\s*<div class="field-items">(.*?)</div>\s*</div>', page, re.S):
        lab, val = text(m.group(1)).rstrip(":"), text(m.group(2))
        if val and lab not in fields:
            fields[lab] = val
    scans = re.findall(r'data-iip-path="([^"]+)"', page)
    # a link belongs to the image whose thumbnail it wraps (<a href="/iipimage/…"><img data-iip-path="…">) – not by
    # order, otherwise another link on the page would shift the pairing and the citation would point to a neighbour
    pairs = dict((s, a) for a, s in re.findall(
        r'<a\s[^>]*?href="(/iipimage/\d+/[^"]+)"[^>]*>\s*<img\s[^>]*?data-iip-path="([^"]+)"', page))
    links = [pairs.get(s, "") for s in scans]
    return book, fields, scans, links


def scan(book, n):
    book, fields, scans, links = info(book)
    if not str(n).isdigit():
        sys.exit(f"the image number must be a whole number from 1 (given \"{n}\")")
    n = int(n)
    if not 1 <= n <= len(scans):
        sys.exit(f"{book}: image {n} does not exist (the book has {len(scans)} images)")
    path, link = scans[n - 1], links[n - 1]
    stem = os.path.splitext(os.path.basename(path))[0]
    if not link or link.rsplit("/", 1)[-1] != stem:   # the link must carry the same file name as the image
        sys.exit(f"{book}: the link for image {n} ({stem}) could not be found – the portal probably changed the page. "
                 "Do not cite a link, report it (notes_for_skill.md).")
    return book, fields, path, link


def image(book, n, out, preview=False, crop=None):
    book, _, path, link = scan(book, n)
    if crop:
        x0, y0, x1, y1 = crop
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            sys.exit("the crop x0,y0,x1,y1 must be fractions 0–1 with x0 < x1, y0 < y1")
    iiif = f"/fcgi-bin/iipsrv.fcgi?IIIF={urllib.parse.quote(path)}"
    # after the first download the whole image is in the shared cache (brake polite.py, tools/cache.py) – crop and preview from it
    stored = cache.find_url(BASE + iiif + "/full/full/0/default.jpg") if (crop or preview) else None
    if stored and cache.derive(stored, out, crop, 4 if preview else 1):
        print("from the cache, no download:", stored)
    else:
        region = "full" if not crop else "pct:" + ",".join(
            f"{v * 100:.3f}" for v in (crop[0], crop[1], crop[2] - crop[0], crop[3] - crop[1]))
        data = get(f"{iiif}/{region}/{'pct:25' if preview else 'full'}/0/default.jpg", binary=True)
        if not data.startswith(b"\xff\xd8"):
            sys.exit("Porta fontium did not return a JPEG image (try again later)")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
    print(out, f"{os.path.getsize(out) // 1024} kB", "link:", BASE + link)


def parish(slug):
    slug = slug.strip("/").split("/")[-1]
    # "Mýto" → "myto", "Dolní Bělá" → "dolni-bela" (the parish URL on the portal has no diacritics)
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode().lower().replace(" ", "-")
    url = f"/contents/register/{ARCHIV}/cirkev-rimskokatolicka/{slug}"
    out, n = [], 0
    while True:   # the list of books has 40 per page
        page = get(url + (f"?page={n}" if n else ""))
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
            m = re.search(r'href="/register/[^/]+/([^"]+)"[^>]*>([^<]+)</a>', row)
            if not m:
                continue
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            out.append((m.group(1), [c for c in cells if c and c != ">"]))
        n += 1
        if f'{slug}?page={n}"' not in page:
            return out


def village(name):
    """Books whose description contains the village (also historical and similar names) – the portal's register search by place."""
    url = "/searching/register?search_api_views_fulltext_1=" + urllib.parse.quote(name.strip())
    out, n = [], 0
    while True:   # results 40 per page
        page = get(url + (f"&page={n}" if n else ""))
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
            m = re.search(r'href="/register/[^/]+/([^"]+)"', row)
            if not m:
                continue
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            out.append((m.group(1), [c for c in cells if c and c != ">"]))
        n += 1
        if not re.search(rf"[?&](?:amp;)?page={n}\b", page) or n > 50:
            return out


def _year(s):
    m = re.search(r"\d{4}", s)
    return int(m.group()) if m else 9999


def print_village(books):
    """Books grouped by parish (or office), parishes and books by start year – a village moving between parishes shows."""
    groups = {}
    for k, c in books:   # c = archive | book title | villages | years and kinds | description
        name = re.sub(r"\s+\S*\d+\w*$", "", c[1]) if len(c) > 1 else k
        groups.setdefault((name, re.sub(r"-\d+\w*$", "", k)), []).append((k, c[2:]))
    for (name, slug), kn in sorted(groups.items(), key=lambda g: min(_year(" ".join(c)) for _, c in g[1])):
        print(f"{name} (parish {slug})")
        for k, c in sorted(kn, key=lambda x: _year(x[1][1] if len(x[1]) > 1 else "")):
            print(" ", k, "|", " | ".join(shorten(x, 160) for x in c))
        print()
    print("Note: the portal also finds historical and similar names – drop villages of the same name in other parishes "
          "by the villages column.\nA village may have belonged to different parishes in different years (see the "
          "years); books of district offices are civil registers.")


def shorten(s, n=300):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " …"


def volume(book):
    book, fields, scans, _ = info(book)
    path = os.path.join(ROOT, "data", "volumes.json")
    d = json.load(open(path, encoding="utf-8-sig")) if os.path.exists(path) else {}
    # field labels are the portal's Czech ones: Signatura = reference code, Místo = place, Text desky = cover text, Typ = kind
    sig = fields.get("Signatura", book)
    desc = "; ".join(x for x in (fields.get("Místo", ""), fields.get("Text desky", "")) if x)
    d[f"pf_{book}"] = {"archive": "SOA Plzeň – Sbírka matrik západních Čech", "portal": "Porta fontium",
                       "title": f"{sig}, {fields.get('Typ', '')}".strip(", "), "description": desc[:300],
                       "images": len(scans), "url": f"{BASE}/register/{ARCHIV}/{book}"}
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"pf_{book} ->", d[f"pf_{book}"]["title"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "parish" and len(a) > 1:
        books = parish(a[1])
        if not books:
            sys.exit(f"Parish \"{a[1]}\" not found or it has no books – check the URL part (e.g. dolni-bela). "
                     f"Parishes of the same name have a district suffix (plana-ps, radnice-ro): the right address is shown by "
                     f"portafontium.py village \"{a[1]}\".")
        for k, c in books:
            print(k, "|", " | ".join(shorten(x) for x in c[1:]))
    elif a[0] == "village" and len(a) > 1:
        books = village(" ".join(a[1:]))
        if not books:
            sys.exit(f"Village \"{' '.join(a[1:])}\" not found in the book descriptions – try another form of the name "
                     "(Stajanovice × Stojanovice, the German name) or a neighbouring village.")
        print_village(books)
    elif a[0] == "info" and len(a) > 1:
        k, f, s, _ = info(a[1])
        for lab, val in f.items():
            print(f"{lab}: {val}")
        print("images:", len(s))
    elif a[0] == "image" and len(a) > 3:
        rest = a[4:]
        crop = None
        for x in rest:
            if "," in x:
                try:
                    crop = tuple(float(v) for v in x.split(","))
                except ValueError:
                    crop = ()
                if len(crop) != 4:   # a bad crop must not silently download the whole page
                    sys.exit(f"give the crop \"{x}\" as four numbers x0,y0,x1,y1 (fractions 0–1)")
        image(a[1], a[2], a[3], "preview" in rest, crop)
    elif a[0] == "link" and len(a) > 2:
        print(BASE + scan(a[1], a[2])[3])
    elif a[0] == "volume" and len(a) > 1:
        volume(a[1])
    else:
        sys.exit(__doc__)
