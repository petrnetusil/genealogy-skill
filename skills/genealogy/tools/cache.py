#!/usr/bin/env python3
"""Shared cache of archive images – every image (scan, tile) is downloaded from the archive only once.

It is filled by the brake tools/polite.py: every image downloaded through the brake (tools, your own scripts, helpers)
is stored by its URL and next time taken from disk without asking the archive. Before storing, only the parts of the
URL that do not change the content are removed (;jsessionid=, PHPSESSID, cache busters like _=1793… or &1793…, utm_…);
unknown parameters stay – better to download again than to return someone else's image. Only a successful response
that really is a whole image is stored: the length from the server matches and the file has an end marker (an
interrupted download is not stored, a truncated stored image is deleted and downloaded again). Porta fontium and
eBadatelna make crops and previews from the stored whole image without the network.

The cache is shared by all projects on the computer: ~/.cache/genealogy_images/ (Windows
%LOCALAPPDATA%\\genealogy_images); the variable GENEALOGY_IMAGES sets another folder. At most 5 GB
(GENEALOGY_IMAGES_GB); the least recently used files are deleted automatically. The whole folder can be deleted at
any time, the tools will download the images again.

Usage (from the project root):
  cache.py status                     -> how much space it takes and how many archive downloads it saved
                                         (details in polite.py status)
  cache.py save <file.json> [output.jpg] [--preview preview.jpg]
                                      -> store an image from the eBadatelna, FamilySearch or ZA Opava viewer (result
                                         of the browser snippet in reference/portals.md (FamilySearch) or
                                         reference/countries/czech-republic.md); then deletes the .json file
  cache.py find <image URL> [--preview preview.jpg]
                                      -> path of the stored image from eBadatelna (/d/… or /a/…), FamilySearch
                                         ($dist URL or /ark:/61903/3:1:…) or ZA Opava (URL
                                         showZoomifySeparate…myImageUuid=…), otherwise exit code 1; also prints the size
                                         (a found image counts as one browser opening saved)
  --preview preview.jpg               -> also a 1600 px wide preview right away (to read the page, without network)

The JSON file for `save` holds {"url": <image URL in the viewer>, "data": "data:image/…;base64,…", "w": <width>,
"h": <height>} and optionally "missing" (tiles the browser did not load); Playwright may store it as a JSON string.

Only what would otherwise really go to the archive again is counted: for tools behind the brake every image returned
from disk, for eBadatelna a hit with `find` (not crops and previews from ebadatelna.py, those would be made from disk
even without the cache).
"""
import base64, glob, hashlib, json, os, re, shutil, subprocess, sys
from urllib.parse import parse_qsl, urlencode, urlsplit

ROOT = os.environ.get("GENEALOGY_IMAGES") or os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache"), "genealogy_images")
LIMIT = float(os.environ.get("GENEALOGY_IMAGES_GB") or 5) * 1024 ** 3
EXTENSIONS = ((b"\xff\xd8\xff", ".jpg"), (b"\x89PNG\r\n\x1a\n", ".png"), (b"GIF8", ".gif"), (b"II*\x00", ".tif"),
              (b"MM\x00*", ".tif"), (b"\x00\x00\x00\x0cjP  ", ".jp2"), (b"\xffO\xffQ", ".j2k"))


def path_for(key):
    """File in the cache; the key is a relative path with "/"."""
    return os.path.join(ROOT, *key.split("/"))


def extension(data):
    """Extension from the first bytes; None = not an image (error page, "blocked" page …)."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return next((p for z, p in EXTENSIONS if data.startswith(z)), None)


def _complete(head, tail, size):
    """Does the image have an end? An interrupted download has the header too, it just lacks the bottom of the image."""
    p = extension(head)
    if p in (".jpg", ".jp2", ".j2k"):   # end marker FF D9 (padding may follow); it cannot appear inside the data
        return b"\xff\xd9" in tail
    if p == ".png":
        return b"IEND" in tail[-64:]
    if p == ".gif":
        return tail.rstrip(b"\x00")[-1:] == b";"
    if p == ".webp":
        return int.from_bytes(head[4:8], "little") + 8 <= size
    return p is not None   # TIFF has no end marker – only the length from the server guards it


def is_complete(data, length=None):
    """Complete image: matches the length from the server (Content-Length), if any, and has an end marker."""
    if length is not None and len(data) != length:
        return False
    return _complete(data[:16], data[-1024:], len(data))


def is_complete_file(path):
    """The same for a stored file (reads only the beginning and the end)."""
    try:
        n = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(16)
            f.seek(max(0, n - 1024))
            return _complete(head, f.read(), n)
    except OSError:
        return False


# --- images by URL (stored by the brake polite.py) ------------------------------------------------------------------
def url_key(url):
    """Key by URL without the parts that do not change the content. Unknown parameters stay."""
    u = urlsplit(url)
    path = re.sub(r";jsessionid=[^/?#;]*", "", u.path, flags=re.I)
    q = []
    for k, v in parse_qsl(u.query, keep_blank_values=True):
        kl = k.lower()
        if kl in ("jsessionid", "phpsessid") or kl.startswith("utm_"):
            continue
        if (kl == "_" and v.isdigit()) or (not v and re.fullmatch(r"\d{10,}", k)):   # cache buster
            continue
        q.append((k, v))
    host = (u.hostname or "").lower()
    port = f":{u.port}" if u.port and u.port not in (80, 443) else ""   # http and https = the same image
    norm = f"{host}{port}{path}?{urlencode(sorted(q))}"
    h = hashlib.sha1(norm.encode()).hexdigest()
    return f"web/{host}/{h[:2]}/{h}"


def find_url(url):
    """Stored image for the URL, or None."""
    k = path_for(url_key(url))
    for _, p in EXTENSIONS + ((None, ".webp"),):
        if os.path.exists(k + p):
            if not is_complete_file(k + p):   # truncated (stored by an older version) – delete and download again
                try:
                    os.remove(k + p)
                except OSError:
                    pass
                return None
            _touch(k + p)
            return k + p
    return None


_saved = [0]


def save_url(url, data, length=None):
    """Store an image downloaded from the URL (only a real and complete image). Returns the path or None."""
    p = extension(data)
    return save(url_key(url) + p, data) if p and is_complete(data, length) else None


# --- shared ---------------------------------------------------------------------------------------------------------
def _touch(p):
    try:
        os.utime(p)   # last used – the cleanup deletes the least recently used
    except OSError:
        pass


def cleanup():
    """Above the limit delete the least recently used files (down to 90 % of the limit)."""
    files = []
    for d, _, fs in os.walk(ROOT):
        for f in fs:
            if ".tmp" not in f:
                p = os.path.join(d, f)
                try:
                    st = os.stat(p)
                    files.append((st.st_mtime, st.st_size, p))
                except OSError:
                    pass
    total = sum(s for _, s, _ in files)
    if total <= LIMIT:
        return
    for _, s, p in sorted(files):
        try:
            os.remove(p)
            total -= s
        except OSError:
            continue
        if total <= LIMIT * 0.9:
            break


def save(key, data):
    """Write bytes into the cache atomically (concurrent downloads of the same image do not clash)."""
    p = path_for(key)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = f"{p}.{os.getpid()}.{id(data)}.tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, p)
    except OSError:   # disk full, sandbox without write access – the cache only saves work, it must not stop it
        return None
    _saved[0] += 1
    if _saved[0] % 200 == 1:   # cleanup only now and then (it walks the whole folder)
        cleanup()
    return p


def _magick():
    return (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
            or (os.name != "nt" and shutil.which("convert")))


def derive(src, out, crop=None, reduce=1):
    """Crop (fractions 0–1) and reduction (1, 2, 4 …) from a stored image without network. True = done."""
    M = _magick()
    if not M:
        return False
    args = [M, src + "[0]"]
    if crop:
        r = subprocess.run([M, src + "[0]", "-format", "%w %h", "info:"], capture_output=True, text=True)
        try:
            W, H = map(int, r.stdout.split())
        except ValueError:
            return False
        x0, y0, x1, y1 = crop
        args += ["-crop", f"{round((x1 - x0) * W)}x{round((y1 - y0) * H)}+{round(x0 * W)}+{round(y0 * H)}", "+repage"]
    if reduce > 1:
        args += ["-resize", f"{100 / reduce:g}%"]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    return subprocess.run(args + ["-quality", "90", out], capture_output=True).returncode == 0


# --- images from the browser (eBadatelna, FamilySearch, ZA Opava) ----------------------------------------------------
EBAD = re.compile(r"ebadatelna\.soapraha\.cz/(d|a)/(\d+)/(\d+)")


EBAD_WEB = "ebadatelna.soapraha.cz"


def _polite():
    """The brake tools/polite.py from the same folder (python -I does not add the script folder to the path)."""
    d = os.path.dirname(os.path.abspath(__file__))
    if d not in sys.path:
        sys.path.insert(0, d)
    import polite
    return polite


def _count_image(host, size, from_disk=True):
    """Statistics for polite.py status (downloaded from the archive / taken from disk). Without the brake nothing is counted."""
    try:
        polite = _polite()
        polite.count_image(host, size, from_disk)
    except Exception:   # noqa: BLE001 – statistics must not stop the work
        pass


def ebadatelna_key(kind, xid, n):
    return f"ebadatelna/{kind}/{xid}/sn{int(n):04d}.jpg"


# FamilySearch: the image is identified by the ARK "3:1:XXXX-XXXX-XXX" – the same in the $dist URL and in the permalink /ark:/61903/3:1:…
FS = re.compile(r"familysearch\.org/.*?\b3:1:([0-9A-Z]{4}-[0-9A-Z-]{4,})")
FS_WEB = "www.familysearch.org"

# ZA Opava: the image is identified by myImageUuid in the image viewer URL (showZoomifySeparate), known without opening it
ZAO = re.compile(r"archives\.cz/da/showZoomifySeparate\?.*?\bmyImageUuid=([0-9A-Fa-f-]{32,36})")
ZAO_WEB = "images.archives.cz"


def from_browser(url):
    """(cache key, site) for an image URL from a browser viewer (eBadatelna, FamilySearch, ZA Opava), otherwise None."""
    m = EBAD.search(url or "")
    if m:
        return ebadatelna_key(*m.groups()), EBAD_WEB
    m = FS.search(url or "")
    if m:
        return f"familysearch/3_1_{m.group(1)}.jpg", FS_WEB   # no colons – Windows does not allow them in file names
    m = ZAO.search(url or "")
    if m:
        return f"zaopava/{m.group(1).replace('-', '').lower()}.jpg", ZAO_WEB
    return None


def _size(p):
    """Width and height of a stored image (ImageMagick), otherwise None."""
    M = _magick()
    r = subprocess.run([M, p + "[0]", "-format", "%w %h", "info:"], capture_output=True, text=True) if M else None
    return tuple(map(int, r.stdout.split())) if r and re.fullmatch(r"\d+ \d+", r.stdout.strip()) else None


def _from_file(path):
    d = json.loads(open(path, encoding="utf-8").read())
    if isinstance(d, str):   # Playwright stores the result as a JSON string
        d = json.loads(d)
    return d


PREVIEW_PX = 1600


def _preview(src, out, width=None):
    """Preview PREVIEW_PX wide (a smaller image is just copied)."""
    if not out:
        return
    if not width:
        M = _magick()
        r = subprocess.run([M, src + "[0]", "-format", "%w", "info:"], capture_output=True, text=True) if M else None
        width = int(r.stdout) if r and r.stdout.strip().isdigit() else PREVIEW_PX
    if derive(src, out, reduce=max(1, int(width) / PREVIEW_PX)):
        print("preview:", out)
    else:
        print("the preview failed (ImageMagick missing?) – the image is stored, make the preview with "
              "ebadatelna.py image … preview")


def main(a):
    for s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    if not a or a[0] in ("-h", "--help"):
        sys.exit(__doc__)
    preview = None
    if "--preview" in a:
        i = a.index("--preview")
        if i + 1 >= len(a):
            sys.exit("--preview needs a file, e.g. --preview work/preview.jpg")
        preview = a[i + 1]
        a = a[:i] + a[i + 2:]
    if a[0] == "status":
        n = s = 0
        for d, _, fs in os.walk(ROOT):
            for f in fs:
                n += 1
                s += os.path.getsize(os.path.join(d, f))
        print(f"{ROOT}: {n} files, {s / 1024 ** 2:.0f} MB of {LIMIT / 1024 ** 3:g} GB "
              "(above the limit the least recently used are deleted automatically)")
        try:
            polite = _polite()
            polite.cache_stats(polite.state_dir())
        except Exception:   # noqa: BLE001
            pass
    elif a[0] == "save" and len(a) > 1:
        d = _from_file(a[1])
        source = from_browser(d.get("url", ""))
        if d.get("missing"):
            sys.exit(f"missing tiles: {d['missing']} – the browser did not load them; run the tile snippet again "
                     "(it only adds the missing ones) and then the assembly")
        if not source or not str(d.get("data", "")).startswith("data:image/"):
            sys.exit("the file is not a result of the snippet for eBadatelna, FamilySearch or ZA Opava (image URL "
                     "or image missing)")
        key, web = source
        again = os.path.exists(path_for(key))   # image already stored – the browser loaded it from the archive needlessly
        data = base64.b64decode(d["data"].split(",", 1)[1])
        if not is_complete(data):
            sys.exit("the image from the browser is not complete (the end of the image is missing) – wait until it "
                     "has loaded and save it again")
        old = _size(path_for(key)) if again and web == ZAO_WEB else None
        if old and d.get("w") and old[0] > int(d["w"]):   # ZA Opava: a lower resolution does not overwrite a higher one
            print(f"the cache already has a larger image ({old[0]} × {old[1]}) – keeping it:", path_for(key))
            os.remove(a[1])
            _preview(path_for(key), preview, old[0])
            return
        p = save(key, data)
        _count_image(web, len(data), from_disk=False)
        if not p:
            sys.exit(f"{ROOT} is not writable")
        os.remove(a[1])
        print("saved:", p, f"({d.get('w')} × {d.get('h')})")
        if again:
            print("note: this image was already in the cache – next time ask first with \"cache.py find <URL>\"")
        if len(a) > 2:
            os.makedirs(os.path.dirname(os.path.abspath(a[2])), exist_ok=True)
            shutil.copyfile(p, a[2])
            print(a[2])
        _preview(p, preview, d.get("w"))
    elif a[0] == "find" and len(a) > 1:
        source = from_browser(a[1])
        p = path_for(source[0]) if source else None
        if not p or not os.path.exists(p):
            sys.exit(1)
        if not is_complete_file(p):   # truncated – delete, the image will be stored again from the browser
            os.remove(p)
            sys.exit(1)
        _touch(p)
        _count_image(source[1], os.path.getsize(p))   # the image need not be opened in the browser again
        r = _size(p)
        print(p, f"({r[0]} × {r[1]})" if r else "")
        _preview(p, preview)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
