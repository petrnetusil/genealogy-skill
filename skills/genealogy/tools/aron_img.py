#!/usr/bin/env python3
"""Download a register image from the ARON portal (Czech regional archive SOA Zámrsk, aron.vychodoceskearchivy.cz).

Usage:
  aron_img.py <apu_id> <image> [level] [output.jpg] [x0,y0,x1,y1]
      level: 0 = full resolution, 1 = half (default), 2 = quarter
      x0,y0,x1,y1: crop only (fractions 0..1 of the whole page)
      Downloads the whole scan in one request (like the download button in ARON) and makes the crop and reduction
      from disk; the scan is stored in the shared cache (tools/cache.py), further crops of the same page do not go
      to the archive. When the scan cannot be downloaded, it falls back to tiles (slower, dozens of requests).
  aron_img.py <apu_id> info          -> volume title and number of images
  aron_img.py <apu_id> link <n>      -> permalink to image n in the ARON viewer (field "link" in records.json)
  aron_img.py <apu_id> volume        -> write the volume into data/volumes.json (key = first 8 characters of apu_id)

Volume descriptions are cached in work/.cache_aron/<apu_id>.json (inside the project folder).
"""
import glob, json, math, os, shutil, ssl, subprocess, sys, tempfile, time, urllib.error, urllib.request
import concurrent.futures as cf
import xml.etree.ElementTree as ET
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
import cache  # noqa: E402 – crop and reduction from the stored scan
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

API = "https://aron.vychodoceskearchivy.cz/api/aron"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "work", ".cache_aron")


def magick():
    """Path to ImageMagick; when it is missing, exit right away (before downloading) with a clear message."""
    m = (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
         or (os.name != "nt" and shutil.which("convert")))   # ImageMagick 6 has no magick; on Windows convert.exe is a different program
    if not m:
        sys.exit("ImageMagick is missing (command magick). Install it (macOS: brew install imagemagick, "
                 "Windows: winget install ImageMagick.ImageMagick and restart Claude Code) and run the tool again.")
    return m


def get(url, binary=False, tries=4):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                data = r.read()
            return data if binary else data.decode("utf-8")
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def volume(apu_id):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, apu_id + ".json")
    if not os.path.exists(path):
        data = get(f"{API}/apu/{apu_id}")
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
        os.replace(tmp, path)  # atomic, safe when several processes fetch the same volume
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def tiles_by_order(vol):
    out = {}
    for dao in vol.get("digitalObjects", []):
        for f in dao["files"]:
            if f["type"] == "TILE":
                out[f["order"]] = f["referencedFile"]
    return out


def fetch_image(dzi_url, level_offset=1, out="page.jpg", crop=None):
    MAGICK = magick()
    dzi = ET.fromstring(get(dzi_url))
    ns = {"d": "http://schemas.microsoft.com/deepzoom/2009"}
    ts = int(dzi.get("TileSize"))
    ov = int(dzi.get("Overlap"))
    size = dzi.find("d:Size", ns)
    W, H = int(size.get("Width")), int(size.get("Height"))
    maxlevel = math.ceil(math.log2(max(W, H)))
    level = maxlevel - level_offset
    scale = 2 ** level_offset
    w, h = math.ceil(W / scale), math.ceil(H / scale)
    cols, rows = math.ceil(w / ts), math.ceil(h / ts)
    c0, r0, c1, r1 = 0, 0, cols - 1, rows - 1
    if crop:
        x0, y0, x1, y1 = crop
        c0, c1 = int(x0 * w // ts), min(cols - 1, int(x1 * w // ts))
        r0, r1 = int(y0 * h // ts), min(rows - 1, int(y1 * h // ts))
    base = dzi_url[: -len(".dzi")] + "_files"
    tmp = tempfile.mkdtemp(prefix="aron_")
    try:
        jobs = []
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                jobs.append((c, r, f"{base}/{level}/{c}_{r}.jpg", os.path.join(tmp, f"{c}_{r}.jpg")))

        def dl(job):
            c, r, url, p = job
            with open(p, "wb") as f:
                f.write(get(url, binary=True, tries=6))
            return job

        # 4 threads: the brake lets 10 images per second through anyway, and more parallel requests break name
        # resolution on macOS (URLError [Errno 8] nodename nor servname) at full resolution
        with cf.ThreadPoolExecutor(4) as ex:
            list(ex.map(dl, jobs))
        # a tile with c > 0 (r > 0) carries `ov` extra pixels on its left (top) edge;
        # crop every tile to its own ts x ts cell, then append rows and columns
        # row by row: one command for the whole page would exceed the Windows command-line limit (32,767 characters)
        row_files = []
        for r in range(r0, r1 + 1):
            args = [MAGICK]
            for c in range(c0, c1 + 1):
                p = os.path.join(tmp, f"{c}_{r}.jpg")
                cw, ch = min(ts, w - c * ts), min(ts, h - r * ts)
                ox, oy = (ov if c > 0 else 0), (ov if r > 0 else 0)
                args += ["(", p, "-crop", f"{cw}x{ch}+{ox}+{oy}", "+repage", ")"]
            row_files.append(os.path.join(tmp, f"row_{r}.miff"))   # MIFF keeps the JPEG properties (chroma subsampling)
            subprocess.run(args + ["+append", row_files[-1]], check=True)
        subprocess.run([MAGICK, *row_files, "-append", "-quality", "88", out], check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # clean up also after a download or magick error
    return out, (W, H)


def scan_url(vol, n):
    """The whole scan of image n (file PUBLISHED) in one request; None when the volume does not have it."""
    for dao in vol.get("digitalObjects", []):
        for f in dao.get("files", []):
            if f.get("type") == "PUBLISHED" and f.get("order") == n:
                return f"{API}/referencedfiles/{f['id']}"
    return None


def fetch_scan(url, level_offset=1, out="page.jpg", crop=None):
    """Download the whole scan and make the crop and reduction from disk. Returns (out, (W, H)), or None (then tiles)."""
    M = magick()
    data = get(url, binary=True)
    if cache.extension(data) != ".jpg" or not cache.is_complete(data):
        return None
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = f"{out}.{os.getpid()}.scan.jpg"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        r = subprocess.run([M, tmp + "[0]", "-format", "%w %h", "info:"], capture_output=True, text=True)
        W, H = map(int, r.stdout.split())
        if level_offset == 0 and not crop:
            os.replace(tmp, out)   # full resolution: the original scan unchanged (no further JPEG re-encoding)
        elif not cache.derive(tmp, out, crop, 2 ** level_offset):
            return None
    except ValueError:
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return out, (W, H)


def no_image(vol, tiles, n):
    """Image n is not in the volume: a clear message instead of KeyError."""
    if not tiles:
        sys.exit(f"Volume \"{vol.get('name', '')}\" has no published images in ARON (scans: 0) – try another volume of "
                 "the parish (often there is a separate index or a duplicate copy), or look it up in the ARON viewer.")
    sys.exit(f"Image {n} is not in the volume – the volume has images {min(tiles)}–{max(tiles)} (aron_img.py <apu_id> info).")


NET_ERRORS = (urllib.error.URLError, ssl.SSLError, ConnectionError, TimeoutError)   # network errors (not local files)


def archive_error(e):
    """Outage on ARON's side (certificate, another page instead of the image, server not answering): message, no traceback."""
    reason = getattr(e, "reason", e)
    if isinstance(reason, ssl.SSLError) or isinstance(e, ET.ParseError):
        sys.exit("ARON: the image server has an invalid certificate or returns another page instead of the image – a "
                 f"problem on the archive's side ({type(reason).__name__}). Try again later; info and link still work, "
                 "volumes can still be planned. Do not switch off certificate checking.")
    if isinstance(e, urllib.error.HTTPError):
        sys.exit(f"ARON returned HTTP error {e.code} – a problem on the archive's side, try again later.")
    sys.exit(f"ARON does not answer ({reason}) – try again later.")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    apu = sys.argv[1]
    try:
        vol = volume(apu)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sys.exit(f"Volume {apu} is not in ARON (HTTP 404) – check the apu_id (the whole id from aron_search.py); "
                     "ARON itself does not publish some volumes found by the search, try another volume of the parish.")
        archive_error(e)
    except NET_ERRORS + (ValueError,) as e:
        archive_error(e)
    tiles = tiles_by_order(vol)
    if sys.argv[2] == "info":
        print(vol["name"], "|", vol.get("description"))
        print("scans:", len(tiles))
        sys.exit(0)
    if sys.argv[2] == "volume":
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "data", "volumes.json")
        vols = json.load(open(path, encoding="utf-8-sig")) if os.path.exists(path) else {}
        fonds, _, rest = vol["name"].partition(": ")
        vols[apu[:8]] = dict(archive=fonds if rest else "", portal="ARON", title=rest or vol["name"],
                             description=(vol.get("description") or "")[:300], images=len(tiles),
                             url=f"https://aron.vychodoceskearchivy.cz/apu/{vol['id']}")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(vols, f, ensure_ascii=False, indent=1)
        print(apu[:8], "->", vols[apu[:8]]["title"])
        sys.exit(0)
    if sys.argv[2] == "link":
        n = int(sys.argv[3])
        dao = (vol.get("digitalObjects") or [{}])[0]
        pub = [f for f in dao.get("files", []) if f["type"] == "PUBLISHED" and f["order"] == n]
        if not pub:
            no_image(vol, tiles, n)
        print(f"https://aron.vychodoceskearchivy.cz/apu/{apu}/dao/{dao['id']}/file/{pub[0]['id']}")
        sys.exit(0)
    n = int(sys.argv[2])
    lo = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    out = sys.argv[4] if len(sys.argv) > 4 else f"{apu[:8]}_{n:04d}.jpg"
    crop = tuple(float(v) for v in sys.argv[5].split(",")) if len(sys.argv) > 5 else None
    if n not in tiles:
        no_image(vol, tiles, n)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    result = None
    if scan_url(vol, n):
        try:
            result = fetch_scan(scan_url(vol, n), lo, out, crop)
        except NET_ERRORS:
            result = None
        if not result:
            print("The whole scan cannot be downloaded – trying tiles (slower).", file=sys.stderr)
    try:
        path, dims = result or fetch_image(tiles[n], lo, out, crop)
    except NET_ERRORS + (ET.ParseError,) as e:
        archive_error(e)
    print(path, "full size", dims)
