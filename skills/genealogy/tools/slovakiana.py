#!/usr/bin/env python3
"""Census sheets 1930 and 1940 from Slovakiana (Slovak National Archives, slovakiana.sk) without a browser.

Usage (from the project root):
  slovakiana.py search "Village" [--year 1930] [--district "Nové Mesto nad Váhom"] [--all] [--pages N]
        -> index of the village's sheets: year | house number | box/sheet | id | link to the Slovakiana viewer.
           Also saves work/slovakiana/<village>[_<year>].md and .json (index for later, no further requests).
           The search is full-text – the tool keeps only sheets whose village matches exactly (--all: all results).
           --pages N: only the first N pages of 200 results (quick test; the index is then incomplete).
  slovakiana.py sheet <cair-id>
        -> description of the sheet (village, street and house number, box, sheet, date, owner, rights) and image URLs
  slovakiana.py image <cair-id> <side> <output.jpg>
        -> one side of the sheet (1 = front, 2 = back) as a JPEG for reading; the original goes into the shared cache
           (tools/cache.py)
  slovakiana.py download <cair-id> [<cair-id> …] [--output work/slovakiana]
        -> originals of both sides of the sheet (JPEG 2000, .jp2) plus a .jpg for reading (ImageMagick with JP2 or
           sips on macOS).
           CURRENTLY BLOCKED (since 16 Nov 2026): the brake tools/polite.py does not let scripts reach
           content.slovakiana.sk (robots.txt "Disallow: /") – open the sheet image in the browser. Applies to the
           command "image" too.
           At most 10 sheets at a time: the image server content.slovakiana.sk has "Disallow: /" in robots.txt and the
           sheets are flagged downloadable: false. Download only sheets you really read (the ancestors' house), not
           the whole village. Files already downloaded are skipped.

Politeness: Slovakiana asks for "Crawl-delay: 10" in robots.txt, so the brake (tools/polite.py) lets one request per
10 s through to slovakiana.sk – images included. A sheet is 4 requests (about 40 s). On a 429/503/403 response the
site is stopped for all processes (30 min and longer, longer per Retry-After) and the tool exits with code 3. When the
server reports in its headers that requests are running out (RateLimit-Remaining), the brake waits for the reset.
Work around nothing.

Sheets from 1940 are blackened (personal data) and Slovakiana gives no images for them – they are in the index for
completeness. The house number follows the slash in the street field ("-, -/68" = house no. 68; "-/-" = no number).

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: brake tools/polite.py (request and image
1 per 10 s for *.slovakiana.sk), cache through our cache.py (find_url/save_url), the project's User-Agent.
Originally taken over and adapted from a fork (MIT licence, © Jozef Izso / jozefizso, version 0.10.0):
  https://github.com/jozefizso/rodokmen-skill/blob/0fd808fe3833abe2b6f9ee956e2f302963d169e5/skills/rodokmen/tools/slovakiana.py
Differences: runs only inside a project (data/STATUS.md), image originals through the shared cache (cache.py), the
command `image` (one side into a given .jpg, as with the other archive tools). Slovakiana's IIIF server
(imageserver-proxy) returned 502 when checked on 8 Nov 2026, so the JP2 original is used as in the fork.
"""
import json, os, re, shutil, subprocess, sys, unicodedata, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # noqa: E402 – shared rate limit for archive websites (polite.py)
import cache   # noqa: E402 – shared image cache (cache.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

API = "https://wcm.slovakiana.sk"
VIEWER = "https://slovakiana.sk/scitacie-harky/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(os.path.join(ROOT, "data", "STATUS.md")):   # run from the skill folder: writes would go into the skill
    sys.exit(f"{os.path.basename(__file__)}: {ROOT} is not a project folder (data/STATUS.md is missing). "
             f"Run the project copy from the project root: python3 -I tools/{os.path.basename(__file__)} …")
OUTPUT = os.path.join(ROOT, "work", "slovakiana")
PAGE = 200            # results per search request (fewer requests = less load)
MAX_SHEETS = 10       # download: at most sheets per run
UA = polite.UA
ID_RE = re.compile(r"cair-[a-z0-9]+")


def get(url, binary=False):
    """One request (the brake waits and watches 429/503 itself). Not repeated – a retry would only load the server."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://slovakiana.sk/",
                                               "Accept": "*/*" if binary else "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sys.exit(f"Slovakiana does not know {url} (HTTP 404). Check the id (cair-…).")
        if e.code == 502:   # on 8 Nov 2026 the image server content.… returned 502 randomly for about half of the requests
            sys.exit(f"Slovakiana did not deliver the file just now (HTTP 502, the server is often unstable): {url}. Run the "
                     "command again in a few minutes (what has been downloaded is in the cache), or open the sheet in the browser.")
        sys.exit(f"Slovakiana refused the request (HTTP {e.code}): {url}. Try again later or open the sheet in the browser.")
    except OSError as e:
        sys.exit(f"Slovakiana did not answer ({type(e).__name__}: {str(e)[:100]}). Try again later.")
    return data if binary else json.loads(data.decode("utf-8"))


def no_diacritics(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if not unicodedata.combining(c)).lower().strip()


def house_number(street):
    """"-, -/68" -> "68", "Hlavná, 12/345" -> "345 (Hlavná 12)", "-, -/-" -> ""."""
    street = (street or "").strip()
    m = re.match(r"(.*?),\s*([^/]*)/(.*)$", street)
    if not m:
        return street if street not in ("-", "") else ""
    name, orient, conscription = (x.strip() for x in m.groups())
    conscription = "" if conscription == "-" else conscription
    street_txt = " ".join(x for x in (name, orient) if x and x != "-")
    return f"{conscription} ({street_txt})" if street_txt and conscription else conscription or street_txt


def box_sheet(name):
    m = re.search(r"hárok\s+(\d+)/(\d+)", name or "")   # Slovak portal text: "hárok" = sheet
    return (m.group(1), m.group(2)) if m else ("", "")


def district(x):
    """District from the category; some sheets lack the category, then from the name ("…, Brezová (Rožňava)")."""
    k = next((c["name"] for c in x.get("categories") or [] if c.get("level") == 1), "")
    m = re.search(r"\(([^()]+)\)\s*$", x.get("name") or "")
    return k or (m.group(1).strip() if m else "")


def row(x):
    bx, sh = box_sheet(x.get("name"))
    street = (x.get("censusSheetStreet") or [""])[0]
    return {"id": x["key"], "year": x.get("displayOriginDate", ""), "village": x.get("municipality", ""),
            "district": district(x), "house_number": house_number(street), "street": street, "box": bx, "sheet": sh,
            "blackened": bool(x.get("blackened")), "images": bool(x.get("hasImages")), "title": x.get("name", ""),
            "link": VIEWER + x["key"]}


def _order(r):
    c = re.match(r"\d+", r["house_number"])
    return (r["year"], int(c.group(0)) if c else 10 ** 9, r["house_number"], int(r["box"] or 0), int(r["sheet"] or 0))


def search(village, year=None, district_=None, everything=False, pages=None):
    results, page, total = [], 0, None
    while True:
        q = urllib.parse.urlencode({"searchText": village, "size": PAGE, "page": page})
        d = get(f"{API}/censussheet/search?{q}")
        total = d.get("totalCount", total)
        results += d.get("results", [])
        print(f"  page {page + 1}: {len(results)} of {total}", file=sys.stderr)
        if not d.get("hasMoreResults") or not d.get("results") or (pages and page + 1 >= pages):
            break
        page += 1
    rows = [row(x) for x in results]
    if not everything:
        rows = [r for r in rows if no_diacritics(r["village"]) == no_diacritics(village)]
    if year:
        rows = [r for r in rows if r["year"] == str(year)]
    if district_:
        rows = [r for r in rows if no_diacritics(district_) in no_diacritics(r["district"])]
    rows = sorted({r["id"]: r for r in rows}.values(), key=_order)
    if not rows:
        others = sorted({f"{x.get('municipality')} ({district(x)})" for x in results})[:15]
        print(f"No sheet for the village \"{village}\"{f' from {year}' if year else ''}." +
              (f" The search found other villages: {', '.join(others)} (give the exact name as Slovakiana writes it, "
               "or --all)." if others else " Try the Slovak name of the village (Slovakiana has names from 1930 and today's)."))
        return
    districts = sorted({r["district"] for r in rows})
    if len(districts) > 1 and not district_:
        print(f"Note: a village of this name exists in several districts ({', '.join(districts)}). Choose --district.",
              file=sys.stderr)
    os.makedirs(OUTPUT, exist_ok=True)
    name = re.sub(r"[^a-z0-9]+", "_", no_diacritics(village)).strip("_") + (f"_{year}" if year else "")
    with open(os.path.join(OUTPUT, name + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    md = [f"# Census sheets – {village}{f' ({year})' if year else ''}", "",
          f"Source: Slovakiana (Slovak National Archives), search \"{village}\", {len(rows)} sheets.", "",
          "| year | house number | box/sheet | district | id | note |", "|---|---|---|---|---|---|"]
    for r in rows:
        note = "blackened, no image" if r["blackened"] else ("" if r["images"] else "no image")
        md.append(f"| {r['year']} | {r['house_number'] or '–'} | {r['box']}/{r['sheet']} | {r['district']} | "
                  f"[{r['id']}]({r['link']}) | {note} |")
    with open(os.path.join(OUTPUT, name + ".md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("year | house number | box/sheet | district | id | link")
    for r in rows:
        note = " (blackened)" if r["blackened"] else ""
        print(f"{r['year']} | {r['house_number'] or '–'} | {r['box']}/{r['sheet']} | {r['district']} | "
              f"{r['id']}{note} | {r['link']}")
    print(f"\n{len(rows)} sheets. Index: {os.path.relpath(os.path.join(OUTPUT, name + '.md'))} (and .json).")


def describe(cair):
    d = get(f"{API}/culturalobject/{cair}")
    attr = {a["name"]: ", ".join(a.get("values", [])) for a in d.get("attributes", [])}
    return d, attr


def images(d):
    """URLs of the originals (JP2) of all digital objects of the sheet, in the order of the sides."""
    out = []
    for do in d.get("digitalObjects") or []:
        content = get(f"{API}/digitalobject/{do['id']}")
        for c in content.get("content", []):
            if c.get("type") == "IMAGES":
                for img in c.get("images", []):
                    full = img.get("full") or {}
                    if full.get("fileUrl"):
                        out.append({"url": full["fileUrl"], "size": full.get("fileSize"),
                                    "width": img.get("width"), "height": img.get("height")})
    return out


def sheet(cair):
    d, attr = describe(cair)
    print(f"{d.get('name')}\n  id: {cair}  link: {VIEWER}{cair}")
    for k in ("Municipality", "Street", "Box number", "Number of census sheet", "Date", "Owner", "Object's rights"):
        if attr.get(k):
            print(f"  {k}: {attr[k]}" + (f"  (house number: {house_number(attr[k])})" if k == "Street" else ""))
    if d.get("originDateNote"):
        print(f"  census day: {d['originDateNote']}")
    if d.get("blackened") or not d.get("hasImages"):
        print("  images: Slovakiana does not publish them for this sheet (blackened or without images).")
        return
    for i, s in enumerate(images(d), 1):
        print(f"  side {i}: {s['width']}×{s['height']} px, {round((s['size'] or 0) / 1024 ** 2, 1)} MB  {s['url']}")


def to_jpg(jp2):
    """.jp2 -> .jpg for reading. Returns the path or None (when no program can do it)."""
    jpg = os.path.splitext(jp2)[0] + ".jpg"
    if os.path.exists(jpg):
        return jpg
    m = shutil.which("magick")
    if m and "JP2" in subprocess.run([m, "-list", "format"], capture_output=True, text=True).stdout:
        command = [m, jp2, "-quality", "90", jpg]
    elif shutil.which("sips"):   # macOS: always handles JPEG 2000
        command = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "90", jp2, "--out", jpg]
    else:
        return None
    p = subprocess.run(command, capture_output=True, text=True)
    return jpg if p.returncode == 0 and os.path.exists(jpg) else None


def original(s):
    """The original of a side (JP2) from the cache, otherwise from Slovakiana."""
    stored = cache.find_url(s["url"])
    if stored:
        return open(stored, "rb").read()
    data = get(s["url"], binary=True)   # the brake usually stores the image in the cache already, otherwise here
    if not cache.find_url(s["url"]):
        cache.save_url(s["url"], data, s.get("size"))
    return data


def image(cair, side, out):
    if not side.isdigit():
        sys.exit("The side must be a number (1 = front, 2 = back).")
    d, attr = describe(cair)
    if d.get("blackened") or not d.get("hasImages"):
        sys.exit(f"{cair}: Slovakiana does not publish images of this sheet (blackened or without images).")
    sides = images(d)
    n = int(side)
    if not 1 <= n <= len(sides):
        sys.exit(f"{cair}: side {n} does not exist (the sheet has {len(sides)} sides).")
    s = sides[n - 1]
    data = original(s)
    if s["size"] and len(data) != s["size"]:
        sys.exit(f"The downloaded file has {len(data)} B instead of {s['size']} B – the connection broke. Try again later.")
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    jp2 = os.path.splitext(out)[0] + ".jp2"
    with open(jp2, "wb") as f:
        f.write(data)
    jpg = to_jpg(jp2)
    if not jpg:
        sys.exit(f"The original is saved as {jp2}, but JPEG 2000 cannot be converted to .jpg here (ImageMagick with JP2 "
                 "or sips is missing).")
    os.remove(jp2)
    if jpg != out:
        os.replace(jpg, out)
    print(out, f"{os.path.getsize(out) // 1024} kB", "link:", VIEWER + cair,
          f"({d.get('name')}, house {house_number(attr.get('Street')) or '–'})")


def download(ids, output):
    if len(ids) > MAX_SHEETS:
        sys.exit(f"At most {MAX_SHEETS} sheets at a time (given {len(ids)}). Slovakiana's image server does not allow bulk "
                 "downloading (robots.txt) – choose the sheets of houses you really read, open the others in the browser.")
    os.makedirs(output, exist_ok=True)
    no_jpg = False
    for cair in ids:
        d, attr = describe(cair)
        print(f"{cair}: {d.get('name')} (house {house_number(attr.get('Street')) or '–'})")
        if d.get("blackened") or not d.get("hasImages"):
            print("  Slovakiana does not publish images of this sheet (blackened or without images) – skipping.")
            continue
        for i, s in enumerate(images(d), 1):
            target = os.path.join(output, f"{cair}_{i}_{os.path.basename(urllib.parse.urlsplit(s['url']).path)}")
            if os.path.exists(target) and (not s["size"] or os.path.getsize(target) == s["size"]):
                print(f"  side {i}: already downloaded {os.path.relpath(target)}")
            else:
                data = original(s)
                if s["size"] and len(data) != s["size"]:
                    sys.exit(f"  side {i}: the downloaded file has {len(data)} B instead of {s['size']} B – the "
                             "connection broke. Run the command again later.")
                tmp = target + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, target)
                print(f"  side {i}: {os.path.relpath(target)} ({round(len(data) / 1024 ** 2, 1)} MB)")
            jpg = to_jpg(target)
            if jpg:
                print(f"           for reading: {os.path.relpath(jpg)}")
            else:
                no_jpg = True
        info = {"id": cair, "title": d.get("name"), "link": VIEWER + cair, "attributes": attr,
                "census_day": d.get("originDateNote")}
        with open(os.path.join(output, f"{cair}.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(info, f, ensure_ascii=False, indent=1)
    if no_jpg:
        print("\nJPEG 2000 (.jp2) cannot be converted to .jpg: ImageMagick here has no JP2 support. Install it "
              "(macOS: brew reinstall imagemagick, Windows: ImageMagick from winget has it) or OpenJPEG (opj_decompress).")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    command, rest = argv[1], argv[2:]

    def option(name, default=None):
        if name in rest:
            i = rest.index(name)
            if i + 1 >= len(rest):
                sys.exit(f"Missing value after {name}.")
            value = rest[i + 1]
            del rest[i:i + 2]
            return value
        return default

    if command == "search":
        year, district_, pages = option("--year"), option("--district"), option("--pages")
        if pages is not None and not (pages.isdigit() and int(pages) > 0):
            sys.exit("--pages must be a positive number.")
        everything = "--all" in rest
        rest = [a for a in rest if a != "--all"]
        if len(rest) != 1:
            sys.exit('Usage: slovakiana.py search "Village" [--year 1930] [--district "District"] [--all] [--pages N]')
        search(rest[0], year, district_, everything, int(pages) if pages else None)
    elif command == "sheet":
        if len(rest) != 1 or not ID_RE.fullmatch(rest[0]):
            sys.exit("Usage: slovakiana.py sheet <cair-id> (e.g. cair-ko1e3on from the link slovakiana.sk/scitacie-harky/…)")
        sheet(rest[0])
    elif command == "image":
        if len(rest) != 3 or not ID_RE.search(rest[0]):
            sys.exit("Usage: slovakiana.py image <cair-id|link> <side> <output.jpg>")
        image(ID_RE.search(rest[0]).group(0), rest[1], rest[2])
    elif command == "download":
        output = option("--output", OUTPUT)
        ids = [ID_RE.search(a).group(0) for a in rest if ID_RE.search(a)]   # also accepts whole links
        if not ids or len(ids) != len(rest):
            sys.exit("Usage: slovakiana.py download <cair-id|link> [… at most 10] [--output folder]")
        download(list(dict.fromkeys(ids)), output)
    else:
        sys.exit(f"Unknown command {command}. Run slovakiana.py --help.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
