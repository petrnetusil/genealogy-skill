#!/usr/bin/env python3
"""Registers and archival records of SOA Praha (Czech regional archive in Prague; eBadatelna, ebadatelna.soapraha.cz)
without a browser and without logging in.

CURRENTLY DISABLED: since 2 Nov 2026 the archive forbids this tool (robots.txt "User-agent: rodokmen / Disallow: /",
HTTP 403) and the brake tools/polite.py therefore stops it. Only link and a-link (no network) and image / a-image with
images the browser has stored in the cache (crop and preview without network) work. Read the registers in the browser
(reference/countries/czech-republic.md, SOA Praha). The tool stays in case the archive allows access again.

Usage (from the project root):
  ebadatelna.py search "Village"          -> places from the portal's autocomplete (full name "Village - obec X - okres Y");
                                            the portal has no numeric place ids, give the full name to "registers"
  ebadatelna.py registers <"Village"|"full name">
                                         -> registers of the place: matrikaId | book | kind | years | parish | images
                                            (with several places of the same name it lists the options – give the
                                            full name with the district)
  ebadatelna.py info <matrikaId>          -> book, parish (creator), district, kinds and years, content, places, number of images
  ebadatelna.py image <matrikaId> <image> <output.jpg> [preview] [x0,y0,x1,y1]
                                         -> the image in full resolution (the portal gives the whole image in one
                                            request, no tiles); "preview" = 1/4 resolution; x0,y0,x1,y1 = crop as
                                            fractions of width/height (0–1), e.g. 0.5,0,1,0.5 = top right quarter
  ebadatelna.py link <matrikaId> <image>  -> permalink to the image (field "link" in data/records.json)
  ebadatelna.py volume <matrikaId>        -> write the volume into data/volumes.json (key ebad_<matrikaId>)
  ebadatelna.py a-info <archivalieId>     -> the same for archival records (urbaria, land books …)
  ebadatelna.py a-image <archivalieId> <image> <output.jpg> [preview] [x0,y0,x1,y1]
  ebadatelna.py a-link <archivalieId> <image>
  ebadatelna.py a-volume <archivalieId>   -> key ebad_a_<archivalieId>
Permalinks: register https://ebadatelna.soapraha.cz/d/<matrikaId>/<image>,
            archival record https://ebadatelna.soapraha.cz/a/<archivalieId>/<image>
Images are numbered from 1 (as in the portal's viewer). Crop and preview need ImageMagick (magick).
Kinds in the output: B = baptisms/births, M = marriages, D = deaths/burials, suffix i = index; idx = has an index.
The portal has daily maintenance around 4:44 (about 2 minutes). Be considerate to the server: download only images you read.
"""
import glob, html, http.client, http.cookiejar, json, os, re, shutil, subprocess, sys, tempfile, time, unicodedata
import urllib.error, urllib.parse, urllib.request
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
import cache  # noqa: E402 – shared image cache (tools/cache.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://ebadatelna.soapraha.cz"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cj = http.cookiejar.CookieJar()
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))
_op.addheaders = [("User-Agent", polite.UA), ("Accept-Language", "cs")]
NOT_FOUND = "neexistující stránku"   # Czech portal text: "a non-existent page"
PAUSE = 0.5   # s before every request – consideration for the server even when called in a loop


class Error(Exception):
    pass


def maintenance():
    t = time.localtime()
    return " This is probably the portal's daily maintenance (around 4:44, ~2 min) – try again in a few minutes." \
        if (t.tm_hour, t.tm_min) >= (4, 40) and (t.tm_hour, t.tm_min) <= (4, 52) else ""


def get(path, referer=None, binary=False, data=None, ajax_base=None):
    """GET/POST with retries (2, 4, 8 s; longer on HTTP 429). Returns (content, final URL)."""
    url = path if path.startswith("http") else BASE + path
    wait = 0
    for attempt in range(4):
        time.sleep(wait or PAUSE)
        wait = 2 ** (attempt + 1)
        req = urllib.request.Request(url, data=data)
        if referer:
            req.add_header("Referer", referer)
        if data is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
        if ajax_base:
            req.add_header("Wicket-Ajax", "true")
            req.add_header("Wicket-Ajax-BaseURL", ajax_base)
            req.add_header("X-Requested-With", "XMLHttpRequest")
        try:
            with _op.open(req, timeout=90) as r:
                d = r.read()
                return (d if binary else d.decode("utf-8", "replace")), r.geturl()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:   # too many requests – wait (per Retry-After) and try again
                ra = e.headers.get("Retry-After", "")
                wait = min(int(ra), 120) if ra.isdigit() else 30 * (attempt + 1)
            elif e.code < 500 or attempt == 3:
                raise Error(f"the portal returned HTTP error {e.code} ({url}).{maintenance()}")
        except (OSError, http.client.HTTPException) as e:   # also a truncated transfer (IncompleteRead)
            if attempt == 3:
                raise Error(f"the portal does not answer ({e}).{maintenance() or ' Try again in a while.'}")


def text(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def years(s):
    s = s.replace(" - ", "–").strip()
    return "" if s in ("---", "") else s


def no_diacritics(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


# ---------- description of a book / archival record ----------

def rows(page):
    """Pairs label -> values from the tables "tableMatrikaBasicInfoRow"."""
    out = {}
    for row in page.split('class="tableMatrikaBasicInfoRow"')[1:]:
        cols = [text(c) for c in re.findall(r'<div class="tableMatrikaBasicInfoColumn[^"]*">\s*<div[^>]*>(.*?)</div>',
                                            row, re.S)]
        if cols and cols[0] and cols[0] not in out:
            out[cols[0]] = cols[1:]
    return out


def places(page):
    return [text(x).split(" / ")[0] for x in re.findall(r'<div class="obecCastLabel">(.*?)</div>', page, re.S)]


def load_page(path, what):
    page, url = get(path)
    if NOT_FOUND in page:
        raise Error(f"{what} not found – check the number.")
    if "obecCastLabel" not in page and "tableMatrikaBasicInfo" not in page:
        raise Error(f"page {url} does not have the expected content (portal maintenance?).{maintenance()}")
    return page


def info(mid):
    page = load_page(f"/pages/MatrikaPage/matrikaId/{mid}", f"register {mid}")
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.S)
    r = rows(page)
    creator = re.search(r'class="puvodceLink"[^>]*>(.*?)</div>', page, re.S)
    kinds = []
    for k, v in r.items():   # row labels of the Czech / English portal: births, marriages, deaths
        for pref, code in (("Naroz", "B"), ("Odda", "M"), ("Zem", "D"), ("Birth", "B"), ("Marr", "M"), ("Death", "D")):
            if k.startswith(pref):
                if v and years(v[0]):
                    kinds.append(f"{code} {years(v[0])}")
                if len(v) > 1 and years(v[1]):
                    kinds.append(f"{code}i {years(v[1])}")
    content = re.search(r'tableMatrikaDescriptionHeader1">\s*<span>(.*?)</span>.*?tableMatrikaDescriptionHeader1">\s*'
                        r'<span>(.*?)</span>', page, re.S)
    sn = next((v[0] for k, v in r.items() if k.startswith(("Počet snímků", "Number of scans")) and v), "")
    district = next((v[0] for k, v in r.items() if k.startswith(("Okres", "District")) and v), "")
    return {"book": text(h1.group(1)) if h1 else f"register {mid}", "creator": text(creator.group(1)) if creator else "",
            "district": district, "kinds": kinds, "content": text(content.group(2)) if content else "",
            "places": places(page), "images": int(sn) if sn.isdigit() else None,
            "url": f"{BASE}/pages/MatrikaPage/matrikaId/{mid}"}


def a_info(aid):
    page = load_page(f"/pages/ArchivaliePage/archivalieId/{aid}", f"archival record {aid}")
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.S)
    r = rows(page)
    fields = {k: v[0] for k, v in r.items() if v and v[0] and v[0] != "---"}   # labels as on the (Czech) portal
    desc = re.search(r"<span>Popis archiválie</span>.*?<span>(.*?)</span>", page, re.S)
    sn = fields.get("Snímky", fields.get("Scans", ""))
    return {"title": text(h1.group(1)) if h1 else f"archival record {aid}", "fields": fields,
            "description": text(desc.group(1)) if desc and text(desc.group(1)) != "---" else "",
            "places": places(page), "images": int(sn) if sn.isdigit() else None,
            "url": f"{BASE}/pages/ArchivaliePage/archivalieId/{aid}"}


# ---------- searching places and registers ----------

def _search_page():
    get("/pages/IndexPage")   # starts a session (cookie) and the Czech locale; without it the portal finds nothing
    page, url = get("/pages/SearchMatrikaPage")
    m = re.search(r"var availableTags1 = (\[.*?\]);", page, re.S)
    if not m:
        raise Error(f"list of places not found on the search page (portal maintenance?).{maintenance()}")
    return json.loads(m.group(1)), page, url


def _match(tag, token):
    t = no_diacritics(tag)
    name, _, rest = t.partition(" - ")
    village = rest.split(" - ")[0].removeprefix("obec ")   # "obec" = municipality (portal text)
    return any(re.search(r"(^|\s)" + re.escape(token), w) for w in (name, village))


def search(name, tags=None):
    tags = tags or _search_page()[0]
    token = no_diacritics(name.strip())
    return list(dict.fromkeys(t for t in tags if _match(t, token)))


def _pick_place(arg, tags):
    s, a = arg.strip().lower(), no_diacritics(arg.strip())
    # first exactly, with diacritics: "Příbram" and "Přibram" are two different autocomplete items
    exact = [t for t in tags if t.lower() == s] or [t for t in tags if no_diacritics(t) == a] or \
            [t for t in tags if t.lower().partition(" - ")[0] == s] or \
            [t for t in tags if no_diacritics(t).partition(" - ")[0] == a]
    candidates = list(dict.fromkeys(exact)) or search(arg, tags)   # the autocomplete has duplicate items too
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise Error(f"place \"{arg}\" is not in eBadatelna (try another form of the name, e.g. without \"Dolní\", "
                    f"or `search`).")
    raise Error(f"\"{arg}\" matches several places – give the full name in quotes:\n  " + "\n  ".join(candidates[:40])
                + ("\n  …" if len(candidates) > 40 else ""))


def _ajax(link, page_url, base, data=None):
    xml, _ = get(urllib.parse.urljoin(page_url, link), referer=page_url, ajax_base=base,
                 data=urllib.parse.urlencode(data).encode() if data is not None else None)
    if "<ajax-response>" not in xml:
        raise Error("the portal returned no search results (session expired or maintenance?)." + maintenance())
    return "".join(re.findall(r"<!\[CDATA\[(.*?)\]\]>", xml, re.S)), xml


def _handler(xml, name):
    m = re.search(r'"u":"([^"]*-' + re.escape(name) + r')"', xml)
    return m.group(1) if m else None


def registers(arg):
    if arg.isdigit():
        raise Error("eBadatelna has no numeric place ids – give the village name (or the full name from `search`).")
    tags, page, url = _search_page()
    place = _pick_place(arg, tags)
    base = re.search(r'Wicket\.Ajax\.baseUrl="([^"]*)"', page)
    button = _handler(page, "searchForm-searchButton")
    if not base or not button:
        raise Error("the search form has changed – the tool needs updating.")
    content, xml = _ajax(button, url, base.group(1), {"searchType": "1", "keywordBox:searchTokenIn": "radio0",
                                                      "keywordBox:searchToken": place, "dateYearFrom": "1000",
                                                      "dateYearTo": "2100", "searchButton": "1"})
    total = re.search(r"nalezeno (\d+)", content)   # Czech portal text: "found N"
    total = int(total.group(1)) if total else 0
    out = {}

    def collect(content):
        new = 0
        for m in re.finditer(r'<tr name="dataLink"[^>]*matrikaId/(\d+)"[^>]*>(.*?)</tr>', content, re.S):
            if m.group(1) not in out:
                out[m.group(1)] = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(2), re.S)]
                new += 1
        return new

    collect(content)
    if len(out) < total:   # more than 50 results: 100 per page and keep paging
        h = _handler(xml, "resultsOnPagePanel-resultsOnPage")
        if h:
            content, xml = _ajax(h, url, base.group(1), {"tableContainer:resultsOnPagePanel:resultsOnPage": "100"})
            collect(content)
        while len(out) < total:
            h = _handler(xml, "pagination-results-nextPageUrl")
            if not h:
                break
            content, xml = _ajax(h, url, base.group(1))
            if not collect(content):
                break
    return place, total, out


def register_line(mid, c):
    # columns: book | creator type | district | number of places | places | B | M | D | index B | index M | index D | images
    c = c + [""] * (12 - len(c))
    kinds, yrs = [], []
    for code, v in zip(("B", "M", "D", "Bi", "Mi", "Di"), c[5:11]):
        if years(v):
            yrs.append(f"{code} {years(v)}")
            if code[0] not in kinds:
                kinds.append(code[0])
    if any(years(v) for v in c[8:11]):
        kinds.append("idx")
    parish = re.sub(r"\s+\d+\w*$", "", c[0])
    if c[1] and not c[1].startswith("Římskokatol"):   # creator type other than Roman Catholic (portal text)
        parish += f" ({c[1]})"
    return f"{mid} | {c[0]} | {'+'.join(kinds) or '?'} | {', '.join(yrs) or '?'} | {parish}, district {c[2]} | {c[11]} images"


# ---------- images ----------

def magick():
    m = (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
         or (os.name != "nt" and shutil.which("convert")))   # ImageMagick 6 has no magick; on Windows convert.exe is a different program
    if not m:
        raise Error("ImageMagick (magick) is missing – it is needed for the preview, the crop and the image size.")
    return m


def dimensions(path):
    try:
        m = magick()
    except Error:   # without ImageMagick the whole image is saved, only the size is not printed
        return "?"
    r = subprocess.run([m, path + "[0]", "-format", "%wx%h", "info:"], capture_output=True, text=True)
    return r.stdout.strip() or "?"


def link(kind, xid, n):
    return f"{BASE}/{kind}/{xid}/{n}"


def image(kind, xid, n, out, options):
    if not str(n).isdigit() or int(n) < 1:
        raise Error(f"the image number must be a whole number from 1 (given \"{n}\").")
    preview = "preview" in options
    crop = next((v for v in options if v != "preview"), None)
    if crop:
        try:
            x0, y0, x1, y1 = (float(v) for v in crop.split(","))
            assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
        except (ValueError, AssertionError):
            raise Error(f"the crop \"{crop}\" must be x0,y0,x1,y1 as fractions 0–1 (x0<x1, y0<y1), e.g. 0,0,0.5,0.5.")
    ref = link(kind, xid, n)
    # the archive forbids the tool (robots.txt): the image only from the cache, where the browser stored it (reference/countries/czech-republic.md)
    stored = cache.path_for(cache.ebadatelna_key(kind, xid, n))
    if not os.path.exists(stored):
        raise Error(f"image {ref} is not stored yet – open it in the browser and save it with the snippet from "
                    "reference/countries/czech-republic.md (SOA Praha), then repeat this command. The archive forbids downloading by tool.")
    print("from the cache, no download:", stored)
    with open(stored, "rb") as f:
        data = f.read()
    if not (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"):
        raise Error(f"the stored image {stored} is damaged – delete it and save it again from the browser.")
    d = os.path.dirname(os.path.abspath(out))
    os.makedirs(d, exist_ok=True)
    jpeg_out = os.path.splitext(out)[1].lower() in (".jpg", ".jpeg")
    if not preview and not crop and data[:3] == b"\xff\xd8\xff" and jpeg_out:
        with open(out, "wb") as f:   # the original file unchanged (no re-encoding)
            f.write(data)
    else:
        with tempfile.TemporaryDirectory(prefix="ebad_") as tmp:
            src_f = os.path.join(tmp, "image.jpg" if data[:3] == b"\xff\xd8\xff" else "image.png")
            with open(src_f, "wb") as f:
                f.write(data)
            cmd = [magick(), src_f]
            if crop:
                wh = dimensions(src_f)
                if not re.fullmatch(r"\d+x\d+", wh):
                    raise Error("ImageMagick could not read the image (damaged transfer?) – try again.")
                w, h = (int(v) for v in wh.split("x"))
                cw, ch = round((x1 - x0) * w), round((y1 - y0) * h)
                cmd += ["-crop", f"{cw}x{ch}+{round(x0 * w)}+{round(y0 * h)}", "+repage"]
            if preview:
                cmd += ["-resize", "25%"]
            r = subprocess.run(cmd + ["-quality", "92", out], capture_output=True, text=True)
            if r.returncode:
                raise Error(f"ImageMagick failed: {r.stderr.strip()[:300]}")
    print(out, dimensions(out), "link:", ref)


# ---------- volumes.json ----------

def write_volume(key, entry):
    path = os.path.join(ROOT, "data", "volumes.json")
    d = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    d[key] = entry
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"{key} -> {entry['title']}")


def shorten(s, n=300):
    return s if len(s) <= n else s[:n - 1].rsplit(", ", 1)[0] + " …"


def volume(mid):
    i = info(mid)
    write_volume(f"ebad_{mid}", {
        "archive": "SOA Praha – Sbírka matrik", "portal": "eBadatelna",
        "title": ", ".join([i["book"]] + i["kinds"]), "description": shorten(", ".join(i["places"])),
        "images": i["images"], "url": i["url"]})


def a_volume(aid):
    i = a_info(aid)
    p = i["fields"]   # Czech portal labels: place of storage, archival fonds, dating, inventory number, reference code
    archive = "SOA Praha" if p.get("Místo uložení", "Státní oblastní archiv v Praze") == "Státní oblastní archiv v Praze" \
        else p["Místo uložení"]
    if p.get("Archivní fond"):
        archive += " – " + p["Archivní fond"]
    dating = years(p.get("Datace od do", "")) or p.get("Datace rok", "")
    title = i["title"] + (f", {dating}" if dating and dating not in i["title"] else "") + \
        (f", inv. no. {p['Inventární číslo']}" if p.get("Inventární číslo") else "") + \
        (f", ref. {p['Signatura']}" if p.get("Signatura") else "")
    desc = " ".join(x for x in (i["description"], "Places: " + ", ".join(i["places"]) if i["places"] else "") if x)
    write_volume(f"ebad_a_{aid}", {"archive": archive, "portal": "eBadatelna", "title": title,
                                   "description": shorten(desc), "images": i["images"], "url": i["url"]})


def main(a):
    if not a or a[0] not in COMMANDS or len(a) < COMMANDS[a[0]]:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd in ("info", "volume", "image", "link", "a-info", "a-volume", "a-image", "a-link") and not a[1].isdigit():
        raise Error(f"the id must be a number (given \"{a[1]}\").")
    if cmd == "search":
        results = search(a[1])
        if not results:
            raise Error(f"nothing found for \"{a[1]}\" – try a shorter form of the name or the name without an attribute.")
        for t in results:
            print(t)
    elif cmd == "registers":
        place, total, out = registers(a[1])
        print(f"# {place}: {total} books")
        for mid, c in out.items():
            print(register_line(mid, c))
    elif cmd == "info":
        i = info(a[1])
        print(i["book"])
        print("parish (creator):", i["creator"], "| district:", i["district"])
        print("kinds and years:", ", ".join(i["kinds"]) or "?")
        print("images:", i["images"])
        if i["content"] and i["content"] != "---":
            print("content:", i["content"])
        print("places:", ", ".join(i["places"]))
        print("link:", i["url"])
    elif cmd in ("image", "a-image"):
        image("d" if cmd == "image" else "a", a[1], a[2], a[3], a[4:])
    elif cmd in ("link", "a-link"):
        if not a[2].isdigit() or int(a[2]) < 1:
            raise Error(f"the image number must be a whole number from 1 (given \"{a[2]}\").")
        print(link("d" if cmd == "link" else "a", a[1], a[2]))
    elif cmd == "volume":
        volume(a[1])
    elif cmd == "a-info":
        i = a_info(a[1])
        print(i["title"])
        for k, v in i["fields"].items():
            print(f"{k}: {v}")
        if i["description"]:
            print("description:", i["description"])
        print("places:", ", ".join(i["places"]))
        print("link:", i["url"])
    elif cmd == "a-volume":
        a_volume(a[1])


COMMANDS = {"search": 2, "registers": 2, "info": 2, "image": 4, "link": 3, "volume": 2,
            "a-info": 2, "a-image": 4, "a-link": 3, "a-volume": 2}

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Error as e:
        sys.exit(f"Error: {e}")
    except KeyboardInterrupt:
        sys.exit("interrupted")
