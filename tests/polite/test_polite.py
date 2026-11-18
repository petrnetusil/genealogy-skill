"""Regression test of the brake tools/polite.py with local servers on 127.0.0.2 and 127.0.0.3 (localhost is not braked).

From the repository root, through the wrapper (the test itself runs curl), the tested brake is the argument:
  python3 -I skills/genealogy/tools/polite.py tests/polite/test_polite.py skills/genealogy/tools/polite.py
  (Windows: python -I -X utf8 …; run it from Git Bash and from PowerShell – bash from PowerShell is Git\\bin\\bash.exe,
  which rebuilds PATH)
  EXTENDED=0 … – basic tests only (no heredoc, no stop extension, no subprocesses, no repeated thread races)
Talks only to local servers; every test keeps the brake state in its own temporary folder (POLITE_STATE).
Verified on Windows 11 (Python 3.13, Git Bash, PowerShell 7) on 2 Nov 2026 (as slusne.py); on macOS 127.0.0.2 needs
an alias on lo0 (`sudo ifconfig lo0 alias 127.0.0.2 up`, the same for .3, .4 and .5), or run it in Docker.
"""
import os, subprocess, sys, tempfile, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BRAKE = os.path.abspath(sys.argv[1])
TOOLS = os.path.dirname(BRAKE)
PY = [sys.executable, "-I", "-X", "utf8"]
EXIT_CODE = 3
LOG = []
BLOCKED_PAGE = "<html><body>Váš přístup byl zablokován.</body></html>".encode("utf-8")   # Czech "your access was blocked"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        LOG.append((time.time(), self.server.server_address[0], self.path))
        p = self.path.split("?")[0]
        code = {"/limit": 429, "/busy": 503, "/forbidden": 403, "/t/forbidden.jpg": 403}.get(p, 200)
        body = BLOCKED_PAGE if p == "/blocked" else b"ok"
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8" if p == "/blocked" else "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def server(addr):
    s = ThreadingHTTPServer((addr, 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s.server_address[1]


PA, PB = server("127.0.0.2"), server("127.0.0.3")
A, B = f"http://127.0.0.2:{PA}", f"http://127.0.0.3:{PB}"
tmp = tempfile.mkdtemp(prefix="polite_test_")


def write_file(name, text):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return p


CLIENT = write_file("client.py",
                    "import sys, urllib.request, urllib.error\n"
                    "for u in sys.argv[1:]:\n"
                    "    try:\n        r = urllib.request.urlopen(u, timeout=10); st = r.status; r.read()\n"
                    "    except urllib.error.HTTPError as e:\n        st = e.code\n"
                    "    except urllib.error.URLError as e:\n        st = 'connection failed'\n"
                    "    print(u.split('/', 3)[-1], st, flush=True)\n")
# like a tool in tools/: loads the brake itself, runs without the wrapper
TOOL = write_file("tool.py",
                  f"import os as _os, sys as _sys; _sys.path.insert(0, {TOOLS!r}); import polite\n"
                  "import sys, urllib.request\nfor u in sys.argv[1:]:\n    urllib.request.urlopen(u, timeout=10).read()\n")
THREADS = write_file("threads.py",
                     "import sys, urllib.request, concurrent.futures as cf\n"
                     "with cf.ThreadPoolExecutor(8) as ex:\n"
                     "    list(ex.map(lambda u: urllib.request.urlopen(u, timeout=10).read(), sys.argv[1:]))\n")
OPAVA = write_file("opava.py",   # digi.archives.cz redirected to the local server (only in this process)
                   "import socket, sys, urllib.request\n_g = socket.getaddrinfo\n"
                   "socket.getaddrinfo = lambda h, *a, **k: _g('127.0.0.2' if h.endswith('archives.cz') else h, *a, **k)\n"
                   "for u in sys.argv[1:]:\n    print(urllib.request.urlopen(u, timeout=10).status, flush=True)\n")
results = []


def state(name):
    return {**os.environ, "POLITE_STATE": os.path.join(tmp, name)}


def run(args, env, **kw):
    return subprocess.run(PY + [BRAKE] + args, env=env, capture_output=True, text=True, encoding="utf-8", **kw)


def records(since, path=None):
    return [(t, h, p) for t, h, p in LOG if t >= since and (path is None or p.startswith(path))]


def gaps(z):
    return [round(b[0] - a[0], 2) for a, b in zip(z, z[1:])]


def max_per_second(z):
    """Most requests in any 1 s window (at 10 per s and scheduler jitter we expect 10–11)."""
    t = [x[0] for x in z]
    return max(sum(1 for y in t if x <= y < x + 1.0) for x in t) if t else 0


def check(name, ok, detail, info=False):
    if not info:
        results.append(ok)
    mark = ("OK " if ok else "FAIL") if not info else ("yes" if ok else "NO ")
    print(f"[{mark}] {name}: {detail}", flush=True)


def last(text):
    lines = [r for r in text.strip().splitlines() if r.strip()]
    return lines[-1][:110] if lines else ""


# 1) requests to the same site
e = state("s1"); t0 = time.time()
r = run([CLIENT, A + "/api?q=1", A + "/api?q=2", A + "/api?q=3"], e)
z = gaps(records(t0, "/api"))
check("requests to the same site", r.returncode == 0 and len(z) == 2 and all(1.9 <= x <= 2.4 for x in z), f"gaps {z} s")

# 2) tiles
t0 = time.time()
r = run([CLIENT] + [A + f"/t/{i}_0.jpg" for i in range(10)], e)
z = records(t0, "/t/")
total = round(z[-1][0] - z[0][0], 2) if z else -1
check("10 tiles", r.returncode == 0 and len(z) == 10 and 0.8 <= total <= 1.6, f"9 gaps in {total} s")

# 3) msvcrt lock: two processes, then load (6 processes × 20 tiles + 4 processes × 2 requests, 8 threads in one process)
e = state("s3"); t0 = time.time()
p = [subprocess.Popen(PY + [BRAKE, CLIENT, A + f"/api?p={i}a", A + f"/api?p={i}b"], env=e, stdout=subprocess.DEVNULL)
     for i in (1, 2)]
[x.wait() for x in p]
z = gaps(records(t0, "/api"))
check("two processes at once (msvcrt lock)", len(z) == 3 and all(x >= 1.9 for x in z), f"gaps of all 4 requests {z} s")

e = state("s3b"); t0 = time.time()
procs = [subprocess.Popen(PY + [BRAKE, CLIENT] + [A + f"/t/{i}_{j}.jpg" for j in range(20)], env=e,
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8") for i in range(6)]
procs += [subprocess.Popen(PY + [BRAKE, CLIENT, A + f"/api?z={i}a", A + f"/api?z={i}b"], env=e,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8") for i in range(4)]
errors = [(pr.wait(), pr.stderr.read()) for pr in procs]
wrong = [(k, err.strip().splitlines()[-1][:120]) for k, err in errors if k != 0 or "Error" in err]
dl, dt = records(t0, "/t/"), records(t0, "/api?z=")
rd, rq = gaps(dl), gaps(dt)
check("load: 10 processes at once (120 tiles + 8 requests)",
      not wrong and len(dl) == 120 and len(dt) == 8 and max_per_second(dl) <= 12 and min(rq) >= 1.9,
      f"{len(dl)} tiles in {round(dl[-1][0] - dl[0][0], 1)} s, at most {max_per_second(dl)} in one second "
      f"(gap {min(rd)}–{max(rd)} s), requests at least {min(rq)} s apart; process errors: {wrong or 'none'}")
e = state("s3c"); t0 = time.time()
r = run([THREADS] + [A + f"/t/v{i}.jpg" for i in range(40)], e)
dl = records(t0, "/t/v")
check("8 threads in one process, first request from threads (new state folder)",
      r.returncode == 0 and len(dl) == 40 and max_per_second(dl) <= 12 and "applies to this process only" not in r.stderr,
      f"40 tiles in {round(dl[-1][0] - dl[0][0], 1)} s, at most {max_per_second(dl)} per s; {last(r.stderr) or 'no messages'}")

# 4) 429: exit, block for other processes and curl too; not for another site; status and unblock
e = state("s4"); t0 = time.time()
r = run([CLIENT, A + "/limit", A + "/api?after=limit"], e)
check("HTTP 429 ends the tool", r.returncode == EXIT_CODE and not records(t0, "/api"),
      f"code {r.returncode}; {last(r.stderr.splitlines()[0] if r.stderr else '')}")
t1 = time.time()
r2 = run([CLIENT, A + "/api?other=process"], e)
r3 = run(["curl", "-s", A + "/api?curl=1"], e)
r3b = subprocess.run(PY + [TOOL, A + "/api?tool=1"], env=e, capture_output=True, text=True, encoding="utf-8")
check("block applies to another process, curl and a tool with import polite",
      (r2.returncode, r3.returncode, r3b.returncode) == (EXIT_CODE, EXIT_CODE, EXIT_CODE) and not records(t1),
      f"codes {r2.returncode}/{r3.returncode}/{r3b.returncode}, nothing reached the server")
r4 = run([CLIENT, B + "/api?other=site"], e)
check("another site (127.0.0.3) is not stopped", r4.returncode == 0 and "200" in r4.stdout, r4.stdout.strip())
r5 = run(["status"], e)
check("polite.py status", "STOPPED 127.0.0.2" in r5.stdout,
      ([x for x in r5.stdout.splitlines() if "STOPPED" in x] or ["(no STOPPED line)"])[0][:100])
r6 = run(["unblock", "127.0.0.2"], e)
r7 = run([CLIENT, A + "/api?after=unblock"], e)
check("polite.py unblock", r7.returncode == 0, f"{r6.stdout.strip()} → next request code {r7.returncode}")

# 5) 503 and 403
e = state("s5")
r = run([CLIENT, A + "/busy"], e)
check("HTTP 503", r.returncode == EXIT_CODE, f"code {r.returncode}")
e = state("s6")
r = run([CLIENT, A + "/t/forbidden.jpg", A + "/api?after=403image"], e)
r2 = run([CLIENT, B + "/forbidden"], e)
check("403 on an image does not stop, on a request it does", r.returncode == 0 and r2.returncode == EXIT_CODE,
      f"image → code {r.returncode}, request → code {r2.returncode}")

# 6) tool with "import polite" without the wrapper
e = state("s6b"); t0 = time.time()
r = subprocess.run([sys.executable, "-I", "-X", "utf8", TOOL, A + "/api?n=1", A + "/api?n=2"], env=e,
                   capture_output=True, text=True, encoding="utf-8")
z = gaps(records(t0, "/api?n="))
check("tool with import polite brakes even without the wrapper", r.returncode == 0 and z and z[0] >= 1.9, f"gap {z} s")

# 7) bash script: curl inside (also in a nested bash -c) must go through the brake
e = state("s7")
sh = write_file("test.sh", 'curl -s "$1/api?sh=1" -o /dev/null\ncurl -s "$1/api?sh=2" -o /dev/null\n'
                           'bash -c "curl -s \\"$1/api?sh=3\\" -o /dev/null"\necho "curl: $(command -v curl)"\n')
t0 = time.time()
r = run(["bash", sh, A], e)
z = gaps(records(t0, "/api?sh="))
check(f"polite.py bash: curl in the script and in bash -c (PATH from {os.environ.get('CONTEXT', '?')})",
      r.returncode == 0 and len(z) == 2 and all(x >= 1.9 for x in z), f"gaps {z} s, {r.stdout.strip()[-70:]}")
e = state("s7b")
r = run(["curl", "-s", "-o", os.devnull, A + "/limit"], e)
check("polite.py curl and 429", r.returncode == EXIT_CODE, f"code {r.returncode}, stderr {r.stderr.strip()[:70]!r}")
e = state("s7c"); sh2 = write_file("limit.sh", 'curl -s -o /dev/null "$1/limit"\ncurl -s -o /dev/null "$1/api?after=limit"\n')
t0 = time.time()
r = run(["bash", sh2, A], e)
check("polite.py bash: 429 from curl in a script stops further requests", not records(t0, "/api?after="),
      f"code {r.returncode}, second curl {'NOT sent' if not records(t0, '/api?after=') else 'SENT'}")

# 8) archives.cz (ZA Opava) forbids scripts since 11/2026 (FORBIDDEN): nothing may reach the server, exit code 3.
#    (Before that the test checked the 4 s limit and the "blocked" page with status 200 – BAN_TEXT stays in polite.py.)
e = state("s8"); t0 = time.time()
r = run([OPAVA, f"http://digi.archives.cz:{PA}/api?o=1", f"http://digi.archives.cz:{PA}/blocked"], e)
check("archives.cz: forbidden for scripts, nothing sent", r.returncode == EXIT_CODE and not records(t0, "/"),
      f"code {r.returncode}, {last(r.stderr)[:80]}")

# 9) 3 failed connections in a row (closed port on 127.0.0.4)
e = state("s9"); t0 = time.time()
r = run([CLIENT] + [f"http://127.0.0.4:9/api?c={i}" for i in range(4)], e)
check("3 failed connections stop the site", r.returncode == EXIT_CODE and "3 failed connections" in r.stderr,
      f"code {r.returncode} in {round(time.time() - t0, 1)} s")

# 9b) the connection is made but no response comes (an archive at night) – 3 timeouts in a row must stop the site too
import socket  # noqa: E402
SILENT = socket.socket()
SILENT.bind(("127.0.0.5", 0)); SILENT.listen(16)
HELD = []
threading.Thread(target=lambda: [HELD.append(SILENT.accept()) for _ in iter(int, 1)], daemon=True).start()
SLOW = write_file("slow.py",
                  "import sys, urllib.request\n"
                  "for u in sys.argv[1:]:\n"
                  "    try:\n        urllib.request.urlopen(u, timeout=1).read(); st = 'ok'\n"
                  "    except OSError as e:\n        st = type(e).__name__\n"
                  "    print(u.split('/', 3)[-1], st, flush=True)\n")
e = state("s9b"); t0 = time.time()
r = run([SLOW] + [f"http://127.0.0.5:{SILENT.getsockname()[1]}/api?c={i}" for i in range(5)], e)
check("3 response timeouts in a row stop the site", r.returncode == EXIT_CODE and "3 failed connections" in r.stderr,
      f"code {r.returncode} in {round(time.time() - t0, 1)} s, output {r.stdout!r} {r.stderr[-300:]!r}")

# 10) state folder that is not writable → temp folder
e = {**os.environ, "POLITE_STATE": os.path.join(CLIENT, "impossible")}
r = run(["status"], e)
check("unwritable state folder → temp folder", r.returncode == 0 and "genealogy_polite" in r.stdout,
      ([x for x in r.stdout.splitlines() if x.startswith("State")] or ["(no State line)"])[0][:110])

# 11) subprocesses from Python: curl, python and bash go through the brake
EXT = os.environ.get("EXTENDED", "1") != "0"
e = state("s11"); scr = write_file("subprocesses.py",
    "import subprocess, sys\n"
    f"subprocess.run(['curl', '-s', '-o', {os.devnull!r}, '{A}/api?sub=1'])\n"
    f"subprocess.run(['curl', '-s', '-o', {os.devnull!r}, '{A}/api?sub=2'])\n"
    f"subprocess.run([sys.executable, '-I', {CLIENT!r}, '{A}/api?sub=3'])\n"
    f"subprocess.run(['bash', '-c', 'curl -s -o /dev/null {A}/api?sub=4'])\n")
t0 = time.time()
run([scr], e)
z = gaps(records(t0, "/api?sub="))
check("subprocesses curl, python and bash from Python are braked", len(z) == 3 and all(x >= 1.8 for x in z),
      f"gaps {z} s (slots of 2 s, starting the curl process jitters by ~0.1 s)", info=not EXT)

if EXT:
    import json
    # 12) code from stdin and -c
    e = state("s12"); t0 = time.time()
    r = run(["-"], e, input=f"import urllib.request\nfor i in range(2): urllib.request.urlopen('{A}/api?stdin=%d' % i).read()\n")
    r2 = run(["-c", f"import urllib.request; urllib.request.urlopen('{A}/api?c=1').read()"], e)
    z = gaps(records(t0, "/api?"))
    check("polite.py - (heredoc) and -c", r.returncode == 0 and r2.returncode == 0 and len(z) == 2 and all(x >= 1.9 for x in z),
          f"gaps {z} s {last(r.stderr + r2.stderr)}")

    # 13) stop extension: 30 min → 2 h → 8 h (expiry of the stop simulated by editing the state file)
    e = state("s13"); lengths = []
    state_file = os.path.join(tmp, "s13", "127.0.0.2.json")
    for i in range(3):
        if i:
            st = json.load(open(state_file, encoding="utf-8")); st["stop"] = time.time() - 1
            json.dump(st, open(state_file, "w", encoding="utf-8"))
        t0 = time.time()
        r = run([CLIENT, A + "/limit"], e)
        st = json.load(open(state_file, encoding="utf-8"))
        lengths.append(round((st["stop"] - t0) / 60))
    r = run(["status"], e)
    check("stop extension 30 min → 2 h → 8 h", lengths == [30, 120, 480] and "3rd refusal" in r.stdout,
          f"lengths {lengths} min; {([x for x in r.stdout.splitlines() if 'STOPPED' in x] or [''])[0].strip()[:90]}")
    t0 = time.time()
    r = run([CLIENT, A + "/limit"], e)   # a concurrent answer during a stop does not count
    st = json.load(open(state_file, encoding="utf-8"))
    check("a request during a stop adds no refusal", st.get("nth") == 3 and len(st.get("refusals", [])) == 3,
          f"nth {st.get('nth')}, refusals {len(st.get('refusals', []))}, code {r.returncode}")

    # 14) thread race at the first request – five times with a new state folder
    wrong = 0
    for i in range(5):
        r = run([THREADS] + [A + f"/t/r{i}_{j}.jpg" for j in range(16)], state(f"s14_{i}"))
        wrong += "applies to this process only" in r.stderr or r.returncode != 0
    check("first request from 8 threads, 5 repetitions", wrong == 0, f"failures: {wrong} of 5")

print(f"\n{sum(results)} of {len(results)} tests passed")
sys.exit(0 if all(results) else 1)
