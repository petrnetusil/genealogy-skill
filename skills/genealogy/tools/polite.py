#!/usr/bin/env python3
"""Network brake against being blocked by an archive: one shared request limit for all processes on one computer.

Archives block an IP address after a series of fast requests (e.g. the Czech archives MZA and ZA Opava). The tools
in tools/ load the brake themselves (`import polite`). Run your own scripts, curl and shell scripts through the wrapper:

  python3 -I tools/polite.py work/my_script.py [arguments]   -> Python script (urllib, requests…)
  python3 -I tools/polite.py - <<'EOF' … EOF                 -> Python code from stdin (heredoc), also -c "code"
  python3 -I tools/polite.py curl [curl arguments]           -> curl with the same limit (without -A it identifies
                                                                itself like the tools)
  python3 -I tools/polite.py bash work/script.sh [arguments] -> shell script; every curl inside goes through the brake
  python3 -I tools/polite.py status                          -> limits and stopped sites
  python3 -I tools/polite.py unblock [site]                  -> lift a stop (only when you know why it happened)
  python3 -I tools/polite.py stop <site|url> [reason]        -> record a stop by hand (the archive refused the browser:
                                                                403/429/503) – it stops scripts and tools as well

Rules (for each site separately, shared by all processes and projects on the computer – they share one IP address):
  - requests (pages, searches, API) at most 1 per 2 s (some sites slower, see `status`: ZA Opava and digi.nacr.cz
    1 per 4 s, Porta fontium 1 per 10 s including images), images and tiles at most 10 per second;
    the frequency is limited, not concurrency (threads downloading tiles are fine),
  - after a 429/503 response (403 too for a request), after a "you have been blocked" page or after 3 failed
    connections in a row the site is stopped for all processes and the tool exits at once (code 3). Nothing is
    retried, nothing is worked around. A stop lasts 30 minutes, 2 hours at the second refusal by that site within
    24 h, 8 hours at the third and every further one; if the server asks for a longer pause in Retry-After
    (seconds or an HTTP date), the stop lasts that long.
  - when the server reports that requests are running out (RateLimit-Remaining / X-RateLimit-Remaining 0–1, also the
    form `RateLimit: r=0;t=30`), or sends Retry-After with a normal response, the next request and image to that site
    waits for the reset (at most one hour), for all processes (applies to urllib/requests and to polite.py curl).
  - curl, python and bash started from Python (subprocess) go through the brake as well.
  - Sites that do not allow scripts at all (browser only) are listed by `status`. Czech examples: MZA Brno (mza.cz)
    allows scripts only for the book search (…/actapublica/matrika/hledani…, 1 request per 4 s), book details and
    images only in the browser – any other MZA address ends the tool at once (code 3); the domain actapublica.eu
    does not belong to MZA – no scripts there either. SOA Třeboň (digi.ceskearchivy.cz), SOA Praha (soapraha.cz,
    eBadatelna) and ZA Opava (archives.cz) refuse the tools since November 2026: browser only.
    FamilySearch (familysearch.org) is browser only as well (its terms of use forbid automated access).
localhost, your own website (Netlify, Cloudflare), GitHub, npm and PyPI are not braked. In a browser (Playwright,
Claude in Chrome) the brake does not apply – keep at least 5–10 s between pages there, no parallel requests and no
loops over whole volumes (SKILL.md, "Being gentle with archives").
State lives in ~/.cache/genealogy_polite/ (Windows %LOCALAPPDATA%\\genealogy_polite), only small JSON files;
the environment variable POLITE_STATE sets another folder.
"""
import http.client, io, json, os, re, shutil, socket, subprocess, sys, tempfile, threading, time
from urllib.parse import urlsplit

REQUEST_GAP, IMAGE_GAP = 2.0, 0.1    # default gap in seconds
LIMITS = {                           # end of the host name: (request, image)
    "archives.cz": (4.0, 0.3),       # ZA Opava (digi.archives.cz, images.archives.cz) – blocks for 30 min, images 403 after ~6 scans
    "nominatim.openstreetmap.org": (1.1, 1.1),   # Nominatim usage policy: at most 1 request per second
    "mza.cz": (4.0, 4.0),            # MZA Brno – scripts only for the book search (FORBIDDEN below), blocks fast catalogue requests too
    "digi.nacr.cz": (4.0, 4.0),      # Czech National Archives (Prague police registrations) – throttles by IP after a few fast cards
    "aron.vychodoceskearchivy.cz": (2.0, 2.0),   # ARON: the whole scan (2–4 MB) in one request; tiles imgx.… stay at 0.1 s
    "portafontium.eu": (10.0, 10.0), # SOA Plzeň – robots.txt "Crawl-delay: 10" (an IIIF image is a single request)
    # Slovakiana (Slovak National Archives, censuses 1930/1940): robots.txt "Crawl-delay: 10" – web, API wcm.… and
    # images content.… (after zbysekvoda/rodokmen-plus@096315a, MIT)
    "slovakiana.sk": (10.0, 10.0),
    # --- added in the English fork: conservative defaults for big international hosts ---------------------------
    "arch.be": (3.0, 1.0),           # State Archives of Belgium (search.arch.be) – no published limit, be gentle
    "matricula-online.eu": (3.0, 1.0),   # Matricula (data./img.data.matricula-online.eu) – images via matricula_dl.sh
}
FORBIDDEN = {                        # end of the host name: (paths allowed to scripts, message for everything else)
    suffix: (re.compile(r"/actapublica/matrika/hledani"),
             "MZA does not allow downloading by script since 2 Nov 2026. Scripts may only use the book search "
             "(https://www.mza.cz/actapublica/matrika/hledani?typ=obec&search_by_obec=<village>&page=<n>); book "
             "details and images only in the Acta Publica viewer in a browser – zoom in on the entry and save a "
             "screenshot (reference/countries/czech-republic.md, MZA Brno). Do not work around this (other address, tool, headers).")
    for suffix in ("mza.cz",)
}
FORBIDDEN["actapublica.eu"] = (     # foreign domain with MZA content (MZA, 3 Nov 2026: "not administered by us")
    re.compile(r"(?!)"),
    "actapublica.eu is not an MZA website (MZA does not administer the domain) – do not use it. MZA registers are at "
    "https://www.mza.cz/actapublica (scripts only for the book search, images in the browser; reference/countries/czech-republic.md, "
    "MZA Brno).")
FORBIDDEN["digi.ceskearchivy.cz"] = (   # SOA Třeboň: since 2 Nov 2026 answers the tool (User-Agent "rodokmen") with 403
    re.compile(r"(?!)"),             # nothing for scripts
    "SOA Třeboň refuses this tool since 2 Nov 2026 (HTTP 403) – do not use your own scripts for it. Read the "
    "registers in the browser at digi.ceskearchivy.cz: zoom in on the entry and save a screenshot "
    "(reference/countries/czech-republic.md, SOA Třeboň). Do not work around this (other User-Agent, tool, headers).")
FORBIDDEN["soapraha.cz"] = (        # SOA Praha (eBadatelna): since 2 Nov 2026 robots.txt "User-agent: rodokmen / Disallow: /", 403
    re.compile(r"(?!)"),             # nothing for scripts
    "SOA Praha (eBadatelna) forbids this tool since 2 Nov 2026 (robots.txt, HTTP 403) – do not use ebadatelna.py "
    "downloads or your own scripts. Read the registers in the eBadatelna viewer: crop the entry from the image the "
    "browser has loaded, or take a screenshot (reference/countries/czech-republic.md, SOA Praha). Do not work around this (other "
    "User-Agent, tool, headers).")
FORBIDDEN["content.slovakiana.sk"] = (  # Slovakiana image server: robots.txt "Disallow: /" (found 16 Nov 2026)
    re.compile(r"(?!)"),             # nothing for scripts; search and metadata on www.slovakiana.sk remain
    "Slovakiana does not allow scripts on its image server content.slovakiana.sk (robots.txt \"Disallow: /\"). "
    "Scripts only for search and descriptions (slovakiana.py); open the sheet image in the browser and save a crop / "
    "screenshot. Do not work around this (other User-Agent, tool, headers).")
FORBIDDEN["archives.cz"] = (        # ZA Opava: robots.txt "Disallow: /", since 11/2026 images 403/404 for scripts, browser only
    re.compile(r"(?!)"),             # nothing for scripts
    "ZA Opava (digi.archives.cz, images.archives.cz) does not let tools in since November 2026 (robots.txt, images "
    "HTTP 403/404) – do not use soal_zoomify.py or your own scripts. Save the image from the image viewer: Playwright "
    "(a snippet assembles the tiles the browser has loaded into the whole image), otherwise a screenshot of the "
    "zoomed-in entry (reference/countries/czech-republic.md, ZA Opava). Do not work around this (other User-Agent, tool, headers).")
# --- added in the English fork --------------------------------------------------------------------------------
FORBIDDEN["familysearch.org"] = (   # FamilySearch: terms of use forbid automated access; the user is logged in in a browser
    re.compile(r"(?!)"),             # nothing for scripts
    "FamilySearch (familysearch.org) is browser only: its terms of use forbid scripts and automated downloading. Use "
    "the logged-in browser (Playwright or Claude in Chrome), at least 5–10 s between pages; save images with the "
    "snippet in reference/portals.md and store them with `cache.py save`. Do not work around this (other "
    "User-Agent, tool, headers).")
EXEMPT = ("localhost", "127.0.0.1", "::1", "0.0.0.0", "netlify.app", "netlify.com", "workers.dev", "cloudflare.com",
          "github.com", "githubusercontent.com", "npmjs.org", "pypi.org", "pythonhosted.org")
# How polite.py curl (and the tools) identify themselves. "rodokmen" stays in the name on purpose: this is a fork of
# the rodokmen skill, and archives that set rules for that User-Agent (robots.txt) must keep seeing it.
UA = "Mozilla/5.0 (genealogy; rodokmen)"
BLOCK_TIMES = (30 * 60, 2 * 3600, 8 * 3600)   # stop after the 1st, 2nd and 3rd (and every further) refusal within WINDOW
WINDOW = 24 * 3600
BAN_TEXT = {"archives.cz": re.compile(rb"zablokov[a\xc3\xa1]n|byl[a ]+zablokov|blocked", re.I)}   # Czech "blocked" page
IMAGE_RE = re.compile(r"\.(jpe?g|png|gif|webp|tiff?|jp2|bmp)(\?|$)|_files/|/tilegroup|/ximage/|zoomify|iipsrv|"
                      r"isrv8\.cgi|/iiif/|/tile|/image/|/thumb|//img\.|/referencedfiles/", re.I)   # ARON: whole scan
STATE_DIR = os.environ.get("POLITE_STATE") or os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache"), "genealogy_polite")
EXIT_CODE = 3
_dir_ = []
_dir_lock = threading.Lock()


def state_dir():
    """Folder for the state. When it is not writable (Claude Code sandbox), the system temp folder is tried; when that
    fails too, the brake only works inside this process (None)."""
    with _dir_lock:   # first request from several threads at once: test only once (on Windows the files would clash)
        return _state_dir_unlocked()


def _state_dir_unlocked():
    if not _dir_:
        for d in dict.fromkeys([STATE_DIR, os.path.join(tempfile.gettempdir(), "genealogy_polite")]):
            try:
                os.makedirs(d, exist_ok=True)
                t = os.path.join(d, f".test_{os.getpid()}_{threading.get_ident()}")
                open(t, "w").close()
                os.remove(t)
                _dir_.append(d)
                break
            except OSError:
                continue
        else:
            _dir_.append(None)
            print(f"polite: neither {STATE_DIR} nor the temp folder is writable – the brake applies to this process "
                  "only, not to others. Run downloads one at a time.", file=sys.stderr)
    return _dir_[0]


class Stopped(SystemExit):
    """The site is stopped. Inherits from SystemExit so that `except Exception` / `except OSError` loops cannot swallow it."""


def _group(host):
    host = (host or "").lower().strip("[]").rstrip(".")
    if not host or any(host == v or host.endswith("." + v) for v in EXEMPT):
        return None, None
    for suffix, lim in LIMITS.items():
        if host == suffix or host.endswith("." + suffix):
            return suffix, lim
    return host, (REQUEST_GAP, IMAGE_GAP)


def is_image(url):
    return bool(IMAGE_RE.search(url or ""))


class _Lock:
    """File lock shared by all processes (flock, msvcrt on Windows)."""
    _threads = threading.Lock()

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self._threads.acquire()
        self.f = None
        if self.path.startswith("memory:"):
            return self
        try:
            self.f = open(self.path, "a+b")
        except OSError:
            self._threads.release()
            raise
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    self.f.seek(0)
                    msvcrt.locking(self.f.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        else:
            import fcntl
            fcntl.flock(self.f.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            if self.f and os.name == "nt":
                import msvcrt
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
            if self.f:
                self.f.close()
        finally:
            self._threads.release()


def _path(group):
    d = state_dir()
    return os.path.join(d, re.sub(r"[^a-z0-9.-]", "_", group) + ".json") if d else "memory:" + group


_memory = {}


def _load(path):
    if path.startswith("memory:"):
        return dict(_memory.get(path, {}))
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(path, data):
    if path.startswith("memory:"):
        _memory[path] = dict(data)
        return
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f)
    os.replace(tmp, path)   # atomic – concurrent processes never read a half-written file


def _time(t):
    lt = time.localtime(t)
    return time.strftime("%H:%M", lt) if lt[:3] == time.localtime()[:3] else time.strftime("%d %b %H:%M", lt)


def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _message(group, st):
    until, n = _time(st["stop"]), st.get("nth", 1)
    return (f"polite: {group} is stopped until {until} ({st.get('reason', '')}"
            f"{f', {_ordinal(n)} refusal within 24 h' if n > 1 else ''}). The archive is signalling that we are a burden.\n"
            f"Do not try again earlier and do not work around it (other tool, browser, other method). Do other work meanwhile.\n"
            f"Tell the user what happened. Status: python3 -I tools/polite.py status")


_announced = set()


def _announce(group, st):
    if group not in _announced:   # only once from download threads
        _announced.add(group)
        print(_message(group, st), file=sys.stderr)


def check_forbidden(host, url):
    """Site that does not allow scripts (FORBIDDEN): a path other than the allowed one -> message and Stopped (no stop)."""
    host = (host or "").lower().strip("[]").rstrip(".")
    for suffix, (allowed, message) in FORBIDDEN.items():
        if host == suffix or host.endswith("." + suffix):
            path = urlsplit(url).path if "://" in url else url.split("?")[0]
            if not allowed.match(path or "/"):
                print(f"polite: {message}", file=sys.stderr)
                raise Stopped(EXIT_CODE)


def wait(url_or_host, image=None):
    """Before a request: wait for a free slot (reserved under the lock, the wait happens outside it).
    Stopped site -> Stopped."""
    host = urlsplit(url_or_host).hostname if "://" in url_or_host else url_or_host
    if "://" in url_or_host:
        check_forbidden(host, url_or_host)
    group, lim = _group(host)
    if not group:
        return
    if image is None:
        image = is_image(url_or_host)
    key = "next_image" if image else "next_request"
    path = _path(group)
    with _Lock(path + ".lock"):
        st = _load(path)
        now = time.time()
        if st.get("stop", 0) > now:
            _announce(group, st)
            raise Stopped(EXIT_CODE)
        slot = max(now, st.get(key, 0))
        st[key] = slot + lim[1 if image else 0]
        st.pop("stop", None)
        _save(path, st)
    if slot > now:
        time.sleep(slot - now)


def stop(host, reason, at_least=0):
    """Stop the site for all processes (duration from BLOCK_TIMES, at least `at_least` s – Retry-After) and exit (Stopped)."""
    group, _ = _group(host)
    if not group:
        return
    path = _path(group)
    with _Lock(path + ".lock"):
        st = _load(path)
        now = time.time()
        if st.get("stop", 0) <= now:   # site already stopped = answer to a concurrent request, not a new refusal
            refusals = [t for t in st.get("refusals", []) if t > now - WINDOW] + [now]
            st.update(stop=now + max(BLOCK_TIMES[min(len(refusals), len(BLOCK_TIMES)) - 1], at_least), reason=reason,
                      when=time.strftime("%Y-%m-%d %H:%M"), refusals=refusals, nth=len(refusals))
            _save(path, st)
    _announce(group, st)
    raise Stopped(EXIT_CODE)


_failures = {}


def _connection_failed(host, e):
    group, _ = _group(host)
    if not group:
        return
    _failures[group] = _failures.get(group, 0) + 1
    if _failures[group] >= 3:
        stop(host, f"3 failed connections in a row ({type(e).__name__}) – the archive does not answer or has blocked us")


# Retry-After and RateLimit-* after zbysekvoda/rodokmen-plus@096315a tools/slusne.py (Zbyšek Voda, MIT; originally
# jozefizso/rodokmen-skill@38850a5), adapted: writes into our per-site state (next_request/next_image, stop).
def seconds(value, now=None):
    """Retry-After / RateLimit-Reset as seconds from now: number of seconds, epoch time or HTTP date. Unparsable -> 0."""
    value = str(value or "").strip()
    now = now or time.time()
    if re.fullmatch(r"\d+(\.\d+)?", value):
        n = float(value)
        return max(0.0, n - now) if n > 1e9 else n   # large number = point in time (epoch), small = number of seconds
    try:
        from email.utils import parsedate_to_datetime
        return max(0.0, parsedate_to_datetime(value).timestamp() - now)
    except (TypeError, ValueError, IndexError, OverflowError):
        return 0.0


def slow_down(host, secs):
    """The server wants a pause: the next request and image to the site only after `secs` (at most one hour), for all processes."""
    group, _ = _group(host)
    if not group or not secs or secs <= 0:
        return
    until = time.time() + min(secs, 3600)
    path = _path(group)
    try:
        with _Lock(path + ".lock"):
            st = _load(path)
            for key in ("next_request", "next_image"):
                st[key] = max(st.get(key, 0), until)
            _save(path, st)
    except OSError:
        return
    print(f"polite: {group} asks for a pause – next request not before {_time(until)} ({min(secs, 3600):.0f} s).",
          file=sys.stderr)


def rate_limit_headers(host, header):
    """RateLimit-* (IETF draft) and X-RateLimit-*: 0–1 requests left -> wait for the reset. Retry-After with a normal
    response -> wait. header: function name -> value or None."""
    pause = seconds(header("Retry-After"))
    left = header("RateLimit-Remaining") or header("X-RateLimit-Remaining")
    if not left:
        m = re.search(r"\br=(\d+)", header("RateLimit") or "")   # newer form: RateLimit: "default";r=0;t=30
        left = m and m.group(1)
    if left and str(left).strip().isdigit() and int(left) <= 1:
        reset = header("RateLimit-Reset") or header("X-RateLimit-Reset")
        if not reset:
            m = re.search(r"\bt=(\d+)", header("RateLimit") or "")
            reset = m and m.group(1)
        pause = max(pause, seconds(reset) or 60)
    slow_down(host, pause)


def _no_headers(name):
    return None


def check_response(host, status, image, body=None, header=None):
    """After a response: 429/503 (403 too for a request) and a "blocked" page -> stop (at least as long as Retry-After
    asks); otherwise Retry-After / RateLimit-* headers -> pause. header: function name -> value (r.getheader) or None."""
    group, _ = _group(host)
    if not group:
        return
    header = header or _no_headers
    _failures.pop(group, None)
    if status in (429, 503) or (status == 403 and not image):
        ra = header("Retry-After")
        stop(host, f"HTTP {status}" + (f", Retry-After {ra}" if ra else ""), seconds(ra))
    pattern = BAN_TEXT.get(group)
    if pattern and body and pattern.search(body):
        stop(host, "the page reports a block")
    rate_limit_headers(host, header)


# --- brake for http.client: covers urllib, requests and your own scripts without changes ---------------------------
def _host(conn):
    return getattr(conn, "_tunnel_host", None) or conn.host


try:   # shared image cache (tools/cache.py); without it the brake still works, just without the savings
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cache as _cache
except Exception:   # noqa: BLE001 – project without cache.py
    _cache = None
finally:
    sys.path.pop(0)


def _full_url(conn, url):
    if "://" in url:
        return url
    https = isinstance(conn, getattr(http.client, "HTTPSConnection", ()))
    port = getattr(conn, "_tunnel_port", None) or conn.port
    default = 443 if https else 80
    return f"{'https' if https else 'http'}://{_host(conn)}{'' if not port or port == default else f':{port}'}{url}"


def count_image(host, size, from_disk=True):
    """Statistics for `polite.py status`: an image taken from the cache instead of the archive (from_disk=True), or
    downloaded from the archive and stored in the cache (from_disk=False). Also called by ebadatelna.py and cache.py
    (images from the browser)."""
    group, _ = _group(host)
    if not group:
        return
    count, mb = ("from_cache", "saved_mb") if from_disk else ("downloaded", "downloaded_mb")
    path = _path(group)
    try:
        with _Lock(path + ".lock"):
            st = _load(path)
            st[count] = st.get(count, 0) + 1
            st[mb] = round(st.get(mb, 0) + size / 1024 ** 2, 2)
            st.setdefault("counted_since", time.strftime("%Y-%m-%d"))
            _save(path, st)
    except OSError:
        pass


_count_image = count_image


class _File:   # "socket" for a response from the cache
    def __init__(self, data):
        self.data = data

    def makefile(self, *a, **k):
        return io.BytesIO(self.data)


def _response_from_disk(path):
    data = open(path, "rb").read()
    ctype = {".jpg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".tif": "image/tiff",
             ".webp": "image/webp"}.get(os.path.splitext(path)[1], "application/octet-stream")
    head = (f"HTTP/1.1 200 OK\r\nContent-Type: {ctype}\r\nContent-Length: {len(data)}\r\n"
            "X-Genealogy-Cache: hit\r\n\r\n").encode()
    r = http.client.HTTPResponse(_File(head + data), method="GET")
    r.begin()
    return r, len(data)


def _enable():
    C = http.client.HTTPConnection
    if getattr(C, "_polite", False):
        return
    put, get, connect = C.putrequest, C.getresponse, C.connect
    putheader, endheaders, send = C.putheader, C.endheaders, C.send
    DIRECT = (C, getattr(http.client, "HTTPSConnection", C))   # response from disk only for urllib (not urllib3 etc.)

    def putrequest(self, method, url, *a, **k):
        self._polite_img = is_image(url)
        self._polite_disk = self._polite_store = None
        check_forbidden(_host(self), url)
        if _cache and method == "GET" and self._polite_img and _group(_host(self))[0]:
            full = _full_url(self, url)
            stored = _cache.find_url(full) if type(self) in DIRECT else None
            if stored:   # from the cache: nothing goes to the archive, not even the brake's wait
                self._polite_disk = stored
                return None
            self._polite_store = full
        wait(_host(self), self._polite_img)
        return put(self, method, url, *a, **k)

    def putheader_(self, *a, **k):
        return None if getattr(self, "_polite_disk", None) else putheader(self, *a, **k)

    def endheaders_(self, *a, **k):
        return None if getattr(self, "_polite_disk", None) else endheaders(self, *a, **k)

    def send_(self, data, *a, **k):
        return None if getattr(self, "_polite_disk", None) else send(self, data, *a, **k)

    def connect_(self):
        if getattr(self, "_polite_disk", None):
            return None
        try:
            return connect(self)
        except (ConnectionRefusedError, ConnectionResetError, TimeoutError, socket.timeout) as e:
            _connection_failed(_host(self), e)
            raise

    def getresponse(self):
        stored = getattr(self, "_polite_disk", None)
        if stored:
            self._polite_disk = None
            r, size = _response_from_disk(stored)
            _count_image(_host(self), size)
            return r
        try:
            r = get(self)
        except (TimeoutError, socket.timeout) as e:   # connected, but no response came (the archive "hangs")
            _connection_failed(_host(self), e)
            raise
        host, img = _host(self), getattr(self, "_polite_img", False)
        body = None
        group, _ = _group(host)
        if group in BAN_TEXT and r.status == 200 and "html" in (r.getheader("Content-Type") or ""):
            body = r.read()             # read and put back, so the caller gets the whole body
            r.fp, r.length, r.chunked, r.will_close = io.BytesIO(body), len(body), False, True
        check_response(host, r.status, img, body, r.getheader)
        full = getattr(self, "_polite_store", None)
        if full and r.status == 200 and not r.getheader("Content-Encoding"):
            length = r.getheader("Content-Length")
            data = r.read()             # store the image and return it whole to the caller
            r.fp, r.length, r.chunked, r.will_close = io.BytesIO(data), len(data), False, True
            length = int(length) if length and length.strip().isdigit() else None
            if _cache.save_url(full, data, length):   # only a complete image (length, end marker)
                count_image(host, len(data), from_disk=False)
        return r

    C.putrequest, C.getresponse, C.connect, C._polite = putrequest, getresponse, connect_, True
    C.putheader, C.endheaders, C.send = putheader_, endheaders_, send_


# --- brake for subprocesses: curl, python and bash started from Python (they do not inherit the http.client patch) ---
_direct = threading.local()   # calls of the real curl and bash made by this brake are not rewritten


def _rewrite(argv):
    name = os.path.basename(str(argv[0])).lower()
    name = name[:-4] if name.endswith(".exe") else name
    me = [sys.executable, "-I", "-X", "utf8", os.path.abspath(__file__)]
    if name == "curl":
        return me + ["curl", *argv[1:]]
    if name in ("bash", "sh") and len(argv) > 1:
        return me + ["bash", *argv[1:]]
    if re.fullmatch(r"python[\d.]*|pythonw[\d.]*|py", name):
        i = 1
        while i < len(argv):
            a = str(argv[i])
            if a in ("-X", "-W"):
                i += 2
                continue
            if a == "-m":
                return argv
            if a in ("-c", "-") or not a.startswith("-"):
                break
            i += 1
        if i < len(argv) and os.path.basename(str(argv[i])) != "polite.py":
            return argv[:i] + [os.path.abspath(__file__)] + argv[i:]
    return argv


def _guard_subprocesses():
    P = subprocess.Popen
    if getattr(P, "_polite", False):
        return
    init = P.__init__

    def init_(self, args, *a, **k):
        if isinstance(args, (list, tuple)) and args and not k.get("shell") and not getattr(_direct, "yes", False):
            args = _rewrite(list(args))
        init(self, args, *a, **k)

    P.__init__, P._polite = init_, True


def _unrewritten(fn, *a, **k):
    _direct.yes = True
    try:
        return fn(*a, **k)
    finally:
        _direct.yes = False


_enable()
_guard_subprocesses()


def install():
    """For tools taken over from rodokmen-plus (`slusne.instaluj()` there): our brake is already on at import."""
    _enable()


# --- wrapper for scripts, curl and bash ---------------------------------------------------------------------------
def _find_curl():
    """A curl that can be started, and whether it supports %{stderr} (since 7.63). On Windows after the Git curl also
    the system curl.exe – Smart App Control blocks starting curl from Git (WinError 4551)."""
    candidates = [os.environ.get("POLITE_CURL"), shutil.which("curl")]
    if os.name == "nt":
        candidates.append(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe"))
    errors = []
    for c in dict.fromkeys(k for k in candidates if k):
        try:
            v = _unrewritten(subprocess.run, [c, "--version"], capture_output=True, text=True).stdout
        except OSError as e:
            errors.append(f"{c}: {e}")
            continue
        m = re.match(r"curl (\d+)\.(\d+)", v)
        return c, bool(m) and (int(m.group(1)), int(m.group(2))) >= (7, 63)
    sys.exit("polite: curl cannot be started" + (" (" + "; ".join(errors) + ")" if errors else " – it is not installed") +
             ". On Windows this helps in .claude/settings.json → \"env\": {\"POLITE_CURL\": \"C:\\\\Windows\\\\System32\\\\curl.exe\"}.")


def _bash_path():
    """bash to run a script; on Windows not C:\\Windows\\System32\\bash.exe (that is WSL, another system) but Git Bash."""
    if os.name != "nt":
        return shutil.which("bash") or "bash"
    for d in os.environ.get("PATH", "").split(os.pathsep):
        b = os.path.join(d, "bash.exe")
        if os.path.isfile(b) and "system32" not in b.lower() and "windowsapps" not in b.lower():
            return b
    git = shutil.which("git")
    if git:
        for b in (os.path.join(os.path.dirname(os.path.dirname(git)), "bin", "bash.exe"),
                  os.path.join(os.path.dirname(git), "bash.exe")):
            if os.path.isfile(b):
                return b
    return "bash"


# curl options that take a value (which is then not a URL); short ones can be combined ("-sSLo file")
_CURL_VALUE = {"--output", "--header", "--user-agent", "--data", "--data-raw", "--data-binary", "--data-urlencode",
               "--data-ascii", "--json", "--referer", "--user", "--proxy", "--write-out", "--cookie", "--cookie-jar",
               "--request", "--upload-file", "--form", "--form-string", "--max-time", "--range", "--config",
               "--connect-timeout", "--retry", "--retry-delay", "--retry-max-time", "--limit-rate", "--continue-at",
               "--output-dir", "--resolve", "--connect-to", "--cacert", "--capath", "--cert", "--key", "--dump-header",
               "--speed-limit", "--speed-time", "--max-filesize", "--max-redirs", "--time-cond", "--interface",
               "--proto", "--proto-redir", "--stderr", "--trace", "--trace-ascii", "--etag-save", "--etag-compare"}
_CURL_SHORT = set("oHAdeuxwbcXTFmrKCDEYyz")
_BARE_HOST = re.compile(r"(?i)^[a-z0-9-]+(\.[a-z0-9-]+)+\.?(:\d+)?([/?#].*)?$")   # www.mza.cz/… without https://


def _curl_urls(args):
    """URLs in a curl command: [(index, URL for the brake)]; a URL without a scheme gets http:// (as curl treats it)."""
    out, i = [], 0
    while i < len(args):
        a = args[i]
        if a == "--url" and i + 1 < len(args):
            u = args[i + 1]
            out.append((i + 1, u if "://" in u else "http://" + u))
            i += 2
            continue
        if a.startswith("--url="):
            u = a[6:]
            out.append((i, u if "://" in u else "http://" + u))
        elif a.startswith("--"):
            if a in _CURL_VALUE:
                i += 1
        elif a.startswith("-") and len(a) > 1:
            k = a[1:]
            for j, c in enumerate(k):
                if c in _CURL_SHORT:
                    if j == len(k) - 1:
                        i += 1   # the value is the next argument
                    break        # otherwise the value is attached ("-ofile")
        elif re.match(r"(?i)https?://", a):
            out.append((i, a))
        elif _BARE_HOST.match(a):
            out.append((i, "http://" + a))
        i += 1
    return out


def _curl(args):
    real, has_stderr = _find_curl()
    if not any(a in ("-A", "--user-agent") or a.startswith("--user-agent=") or re.match(r"(?i)\s*user-agent\s*:", a)
               for a in args):
        args = ["-A", UA, *args]   # identify like the tools; some archives refuse the default "curl/…" (403)
    urls = [u for _, u in _curl_urls(args)]
    if len(urls) > 1:   # curl would send them right after each other, the brake could neither wait nor stop
        print("polite: one curl = one URL. Download several images one after another (each through the brake).",
              file=sys.stderr)
        return 2
    globoff = any(a in ("-g", "--globoff") or (re.match(r"-[a-zA-Z]+$", a) and "g" in a) for a in args)
    if urls and not globoff and re.search(r"[\[\]{}]", urls[0]):   # range [1-200] / {a,b} = many requests at once
        print("polite: ranges [..] and {..} in a URL are not allowed (curl would fetch them all at once). Download the "
              "images one after another, or if the bracket is literally part of the URL, add -g.", file=sys.stderr)
        return 2
    for u in urls:
        wait(u)
    # own -w: the brake joins it with its marker (curl only uses the last -w); not for -w @file and old curl without marker
    marker = "%{stderr}\n@@polite %{http_code} %{url_effective}\n"
    w_pos = [i for i, a in enumerate(args) if a in ("-w", "--write-out") or a.startswith("--write-out=")]
    own = None
    if w_pos:
        i = w_pos[-1]
        own = args[i][len("--write-out="):] if args[i].startswith("--write-out=") else (args[i + 1] if i + 1 < len(args) else "")
        if not own.startswith("@"):
            args = [a for j, a in enumerate(args) if j not in w_pos and not (j - 1 in w_pos and not args[j - 1].startswith("--write-out="))]
    if not has_stderr or (own or "").startswith("@"):
        extra = []
    else:
        extra = ["-w", (own or "") + marker]
    # Response headers (Retry-After, RateLimit-*): read the caller's own -D <file>, otherwise add a temporary one.
    # Leave "-D -" (to stdout) alone – a second -D would override it; then only the status code is judged.
    header_file, temporary = None, False
    for i, a in enumerate(args[:-1]):
        if a in ("-D", "--dump-header"):
            header_file = None if args[i + 1] == "-" else args[i + 1]
            break
    else:
        fd, header_file = tempfile.mkstemp(prefix="polite_headers_")
        os.close(fd)
        temporary = True
        extra += ["-D", header_file]
    try:
        p = _unrewritten(subprocess.run, [real, *args, *extra], stderr=subprocess.PIPE)
        header = _headers_from_file(header_file) if header_file else _no_headers
    finally:
        if temporary:
            try:
                os.remove(header_file)
            except OSError:
                pass
    err = p.stderr.decode("utf-8", "replace").replace("\r\n", "\n")   # curl on Windows writes \r\n to stderr
    codes = re.findall(r"^@@polite (\d+) (\S*)$", err, re.M)
    sys.stderr.write(re.sub(r"\n?@@polite \d+ \S*\n", "", err))
    for code, url in codes:
        check_response(urlsplit(url).hostname, int(code), is_image(url), header=header)
    if p.returncode in (7, 28, 35, 56) and urls:   # could not connect / timeout / connection reset
        _connection_failed(urlsplit(urls[0]).hostname, ConnectionError(f"curl exit code {p.returncode}"))
    return p.returncode


def _headers_from_file(path):
    """Headers of the last response from a curl -D file (with -L it holds several responses) -> function name -> value."""
    try:
        with open(path, encoding="latin-1") as f:
            lines = f.read().splitlines()
    except OSError:
        lines = []
    headers = {}
    for line in lines:
        if line.startswith("HTTP/"):   # start of another response – only the headers of the last one count
            headers = {}
        elif ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return lambda name: headers.get(name.lower())


def _posix(p):
    """Path for Git Bash: C:\\Users\\x → /c/Users/x (unchanged outside Windows)."""
    if os.name != "nt":
        return p
    p = p.replace("\\", "/")
    return "/" + p[0].lower() + p[2:] if re.match(r"[A-Za-z]:", p) else p


def _bash(args):
    shim = tempfile.mkdtemp(prefix="polite_")
    try:
        me = os.path.abspath(__file__)
        with open(os.path.join(shim, "curl"), "w", encoding="utf-8", newline="\n") as f:
            py, me_ = sys.executable.replace("\\", "/"), me.replace("\\", "/")   # Git Bash: forward slashes
            f.write(f'#!/bin/sh\nexec "{py}" -I -X utf8 "{me_}" curl "$@"\n')
        os.chmod(os.path.join(shim, "curl"), 0o755)
        # Git\bin\bash.exe (the only bash from PowerShell) rebuilds PATH and the real curl would come before the shim.
        # BASH_ENV is read by every non-interactive bash (also a nested `bash -c`) afterwards, so it puts the shim first again.
        with open(os.path.join(shim, "env.sh"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f'PATH="{_posix(shim)}:$PATH"; export PATH\n')
        try:
            real = _find_curl()[0]   # the real curl that can be started (the shim is first in PATH)
        except SystemExit:
            real = ""                # the script may not need curl; if it does, the shim prints the message
        env = dict(os.environ, POLITE_CURL=real,
                   PATH=shim + os.pathsep + os.environ.get("PATH", ""), BASH_ENV=_posix(os.path.join(shim, "env.sh")))
        return _unrewritten(subprocess.run, [_bash_path(), *args], env=env).returncode
    finally:
        shutil.rmtree(shim, ignore_errors=True)


def _script(args):
    import runpy
    if args[0] in ("-", "-c"):   # code from stdin (heredoc) or from the argument
        code = sys.stdin.read() if args[0] == "-" else (args[1] if len(args) > 1 else "")
        sys.argv = [args[0], *args[2 if args[0] == "-c" else 1:]]
        exec(compile(code, "<stdin>" if args[0] == "-" else "<string>", "exec"), {"__name__": "__main__"})
        return 0
    if args[0] == "-m":
        sys.argv = args[1:]
        runpy.run_module(args[1], run_name="__main__", alter_sys=True)
    else:
        sys.argv = list(args)
        sys.path.insert(0, os.path.dirname(os.path.abspath(args[0])))
        runpy.run_path(args[0], run_name="__main__")
    return 0


def _status():
    print(f"Limits: request 1 per {REQUEST_GAP:g} s, image 1 per {IMAGE_GAP:g} s; separately: " +
          ", ".join(f"{k} {v[0]:g}/{v[1]:g} s" for k, v in LIMITS.items()))
    print("No scripts allowed (browser only): " + ", ".join(FORBIDDEN) +
          " (for MZA scripts may use the book search, see --help)")
    d = state_dir()
    print("State:", d or "only in process memory (the folder is not writable)")
    nothing, now = True, time.time()
    for f in sorted(os.listdir(d)) if d else []:
        if f.endswith(".json"):
            st = _load(os.path.join(d, f))
            refusals = [t for t in st.get("refusals", []) if t > now - WINDOW]
            if st.get("stop", 0) > now:
                nothing = False
                print(f"  STOPPED {f[:-5]} until {_time(st['stop'])} – {st.get('reason', '')} (since {st.get('when', '?')}, "
                      f"{_ordinal(st.get('nth', 1))} refusal within 24 h)")
            elif refusals:
                nxt = BLOCK_TIMES[min(len(refusals) + 1, len(BLOCK_TIMES)) - 1]
                length = f"{nxt // 60} min" if nxt < 3600 else f"{nxt // 3600} h"
                print(f"  {f[:-5]}: refusals within 24 h: {len(refusals)} (last {_time(refusals[-1])}), "
                      f"the next stop would last {length}")
    if nothing:
        print("  no site is stopped")
    cache_stats(d)


def cache_stats(d):
    """How many images were downloaded from the archive and how often they were taken from disk instead (tools/cache.py)."""
    sites = [(f[:-5], _load(os.path.join(d, f))) for f in sorted(os.listdir(d)) if f.endswith(".json")] if d else []
    sites = [(w, st) for w, st in sites if st.get("from_cache") or st.get("downloaded")]
    if not sites:
        return
    since = min(st.get("counted_since", "?") for _, st in sites)
    print(f"Image cache (tools/cache.py), counted since {since}:")
    sd = sc = md = mc = 0
    for w, st in sites:
        dl, c, m1, m2 = st.get("downloaded", 0), st.get("from_cache", 0), st.get("downloaded_mb", 0), st.get("saved_mb", 0)
        sd, sc, md, mc = sd + dl, sc + c, md + m1, mc + m2
        print(f"  {w}: from the archive {dl}× ({_mb(m1)}), from disk {c}× ({_mb(m2)}){_share(dl, c)}")
    if len(sites) > 1:
        print(f"  total: from the archive {sd}× ({_mb(md)}), from disk {sc}× ({_mb(mc)}){_share(sd, sc)}")


def _mb(m):
    return f"{m:.0f} MB" if m >= 10 else f"{m:.1f} MB"


def _share(dl, c):
    """Share of image requests the archive did not get thanks to the cache."""
    return f" – {100 * c / (dl + c):.0f} % of downloads saved" if dl + c else ""


def _unblock(site=None):
    d = state_dir()
    for f in os.listdir(d) if d else []:
        if f.endswith(".json") and (not site or f[:-5] in (site, _group(site)[0])):
            path = os.path.join(d, f)
            with _Lock(path + ".lock"):
                st = _load(path)
                if st.pop("stop", None):
                    print("unblocked:", f[:-5])
                    st["refusals"] = st.get("refusals", [])[:-1]   # it was our mistake – does not count towards longer stops
                _save(path, st)


def main(argv):
    for s in (sys.stdout, sys.stderr):   # UTF-8 messages on Windows too without -X utf8 (e.g. from curl() in ahmp_search.sh)
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):   # code from stdin ("polite.py -") is UTF-8, not cp1250 on Windows
        sys.stdin.reconfigure(encoding="utf-8-sig")
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "--status":
        cmd = "status"
    if cmd == "status":
        return _status()
    if cmd == "unblock":
        return _unblock(rest[0] if rest else None)
    if cmd == "stop":   # a refusal the brake cannot see itself (browser) – same stop as for scripts
        if not rest:
            sys.exit("polite.py stop <site or URL> [reason], e.g. stop ebadatelna.soapraha.cz \"HTTP 403 in the browser\"")
        site = urlsplit(rest[0] if "//" in rest[0] else "//" + rest[0]).hostname
        if not _group(site)[0]:
            sys.exit(f"polite: {rest[0]} is not watched by the brake (own website, localhost…) – nothing to stop")
        stop(site, "by hand: " + (" ".join(rest[1:]) or "the archive refused the browser"))
    if cmd == "curl":
        return _curl(rest)
    if cmd in ("bash", "sh"):
        return _bash(rest)
    if re.match(r"(python3?|py)(\.exe)?$", os.path.basename(cmd)):   # "polite.py python3 x.py" = "polite.py x.py"
        cmd, rest = rest[0], rest[1:]
        if cmd == "-I" and rest:
            cmd, rest = rest[0], rest[1:]
    return _script([cmd, *rest])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
