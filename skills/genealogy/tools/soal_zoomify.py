#!/usr/bin/env python3
"""A register image in Zoomify format (SOA Litoměřice, Czech regional archive) at full resolution – no browser, no cookies.

ZA Opava (images.archives.cz) does not let tools in since November 2026 (robots.txt, images HTTP 403/404) – save
images from there in the image viewer (reference/countries/czech-republic.md, ZA Opava; best with Playwright).

Usage (from the project root):
  soal_zoomify.py <path or URL> <reduction> <output.jpg>
    (at the end of October 2026 SOA Litoměřice changed the paths to …/CZ-214000010/NAD-<number>/dao/images/… –
    give the full URL)
    path      = older SOA Litoměřice URLs: the part of the image URL after "…/CZ-214000010/matriky/"; take it once
                from the browser: open the image in the digital reading room and find in the network traffic the request
                https://images.soalitomerice.cz/ximage/matriky/zoomify/cz/archives/CZ-214000010/matriky/<path>/ImageProperties.xml
                (further images of the same book have the same path, only the image number differs)
    URL       = the full image URL starting with https:// (with or without "/ImageProperties.xml" at the end), e.g.
                https://images.soalitomerice.cz/ximage/matriky/zoomify/cz/archives/CZ-214000010/NAD-<number>/dao/images/<folder>/<uuid>.jpg
    reduction = 0 full resolution (for reading and cropping), 1 half (for orientation), 2 quarter
NOTE: the application digi.soalitomerice.cz blocks access for 30 minutes after ~100 fast requests. Use the browser
only to find the book and the image path, then download images one at a time with this tool.
"""
import glob, math, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
import concurrent.futures as cf
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://images.soalitomerice.cz/ximage/matriky/zoomify/cz/archives/CZ-214000010/matriky/"
HOSTS = ("images.soalitomerice.cz",)   # only the archive's image server (images are processed by ImageMagick); not ZA Opava (above)


def magick():
    """Path to ImageMagick; when it is missing, exit right away (before downloading) with a clear message."""
    m = (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
         or (os.name != "nt" and shutil.which("convert")))   # ImageMagick 6 has no magick; on Windows convert.exe is a different program
    if not m:
        sys.exit("ImageMagick is missing (command magick). Install it (macOS: brew install imagemagick, "
                 "Windows: winget install ImageMagick.ImageMagick and restart Claude Code) and run the tool again.")
    return m


def get(url):
    err = None
    for _ in range(3):
        try:
            return urllib.request.urlopen(url, timeout=30).read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503):   # the archive refuses – do not retry, stop the site in the brake (images too)
                host = urllib.parse.urlsplit(url).hostname
                polite.stop(host, f"HTTP {e.code} for an image")
                sys.exit(f"The archive refused the image (HTTP {e.code}) – site {host} is stopped in the brake. Leave it for "
                         "today and try another time; images you need now should be saved by the user in the browser.")
            if e.code == 404:   # do not retry: wrong path, or the archive refuses the tool (the browser loads the image)
                sys.exit(f"Image not found (HTTP 404): {url[:160]}\nCheck that it is the full image URL from the browser "
                         "(paths change, the .JPG extension too). If the browser loads it and the tool does not, the archive "
                         "refuses the tool – stop and save the image from the browser (reference/countries/czech-republic.md).")
            time.sleep(1)
            err = e
        except Exception as e:
            time.sleep(1)
            err = e
    raise err


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    arg = sys.argv[1].strip().removesuffix("/ImageProperties.xml").strip("/")
    base = arg if arg.startswith("http") else BASE + arg
    if urllib.parse.urlsplit(base).hostname in ("images.archives.cz", "digi.archives.cz"):
        sys.exit("ZA Opava does not let tools in since November 2026 (robots.txt, images HTTP 403/404). Save the image "
                 "from the image viewer – Playwright assembles the tiles the browser has loaded "
                 "(reference/countries/czech-republic.md, ZA Opava).")
    if urllib.parse.urlsplit(base).scheme != "https" or urllib.parse.urlsplit(base).hostname not in HOSTS:
        sys.exit(f"The URL must be https:// on the archive's server ({', '.join(HOSTS)}), not {base[:80]}")
    red, out = int(sys.argv[2]), sys.argv[3]
    MAGICK = magick()
    x = get(base + "/ImageProperties.xml").decode()
    W, H, T = (int(re.search(fr'{k}="(\d+)"', x).group(1)) for k in ("WIDTH", "HEIGHT", "TILESIZE"))
    dims, w, h = [], W, H   # Zoomify levels from the smallest to full resolution
    while True:
        dims.append((w, h))
        if w <= T and h <= T:
            break
        w, h = (w + 1) // 2, (h + 1) // 2
    dims = dims[::-1]
    counts = [math.ceil(a / T) * math.ceil(b / T) for a, b in dims]
    L = len(dims) - 1 - red
    w, h = dims[L]
    nx, ny = math.ceil(w / T), math.ceil(h / T)
    start = sum(counts[:L])
    d = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(out)))
    try:   # clean up the temp folder also after a network outage or ImageMagick error
        def tile(yx):
            y, xx = yx
            g = (start + y * nx + xx) // 256
            f = os.path.join(d, f"{y:03d}_{xx:03d}.jpg")
            with open(f, "wb") as fh:
                fh.write(get(f"{base}/TileGroup{g}/{L}-{xx}-{y}.jpg"))
        with cf.ThreadPoolExecutor(4) as ex:   # 4 in parallel: several times faster, no more load on the server than 4 browsers
            list(ex.map(tile, [(y, xx) for y in range(ny) for xx in range(nx)]))
        # rows of tiles +append, then the rows stacked -append (montage on ImageMagick 7.1.2 crashes without a font);
        # short names (cwd=d) and row by row: the whole page in one command would exceed the Windows command-line limit
        rows = []
        for y in range(ny):
            rows.append(f"row{y:03d}.miff")   # MIFF keeps the JPEG properties (chroma subsampling)
            subprocess.run([MAGICK, *[f"{y:03d}_{xx:03d}.jpg" for xx in range(nx)], "+append", rows[-1]], check=True, cwd=d)
        subprocess.run([MAGICK, *rows, "-append", "-crop", f"{w}x{h}+0+0", "+repage", "-quality", "88",
                        os.path.abspath(out)], check=True, cwd=d)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print(out, w, h)


if __name__ == "__main__":
    main()
