"""Test of the image cache (tools/cache.py through the brake tools/polite.py): only whole images are stored.

From the repository root (local server on 127.0.0.2 – localhost is not braked; on macOS an alias on lo0 or Docker):
  python3 -I skills/genealogy/tools/polite.py tests/polite/test_cache.py skills/genealogy/tools
The cache and the brake state are in a temporary folder (GENEALOGY_IMAGES, POLITE_STATE). Downloads nothing from
the internet. The first part (end markers in memory) runs anywhere.
"""
import os, socket, subprocess, sys, tempfile, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

TOOLS = os.path.abspath(sys.argv[1])
sys.path.insert(0, TOOLS)
import cache  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 40 + b"\xff\xd9"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 3000 + b"\x00\x00\x00\x00IEND\xaeB`\x82"
GIF = b"GIF89a" + b"\x01" * 3000 + b";"
WEBP = b"RIFF" + (3000 + 4).to_bytes(4, "little") + b"WEBP" + b"\x00" * 3000
HITS = {}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_GET(self):
        p = self.path.split("?")[0]
        HITS[p] = HITS.get(p, 0) + 1
        body = {"/whole.jpg": JPG, "/short.jpg": JPG[:2000], "/length.jpg": JPG, "/old.jpg": JPG}[p]
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        if p == "/length.jpg":
            self.send_header("Content-Length", str(len(body) + 500))   # the server promised more than it sent
        elif p != "/short.jpg":   # truncated without a length: the connection closes in the middle
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'OK ' if ok else 'FAIL'}] {name} {detail}", flush=True)


# 1) end check in memory
for name, data in (("JPEG", JPG), ("PNG", PNG), ("GIF", GIF), ("WebP", WEBP)):
    check(f"{name} whole", cache.is_complete(data))
    check(f"{name} truncated", not cache.is_complete(data[:len(data) // 2]))
check("JPEG with padding after the end", cache.is_complete(JPG + b"\x00" * 100))
check("Content-Length does not match", not cache.is_complete(JPG, len(JPG) + 1))
check("HTML is not an image", not cache.is_complete(b"<html>blocked</html>"))

# 2) through the brake with a local server
s = ThreadingHTTPServer(("127.0.0.2", 0), H)
threading.Thread(target=s.serve_forever, daemon=True).start()
A = f"http://127.0.0.2:{s.server_address[1]}"
tmp = tempfile.mkdtemp(prefix="cache_test_")
env = {**os.environ, "GENEALOGY_IMAGES": os.path.join(tmp, "images"), "POLITE_STATE": os.path.join(tmp, "state")}
CLIENT = os.path.join(tmp, "client.py")
with open(CLIENT, "w", encoding="utf-8") as f:
    f.write(f"import sys; sys.path.insert(0, {TOOLS!r}); import polite\n"
            "import http.client, urllib.request\n"
            "for u in sys.argv[1:]:\n"
            "    try:\n        n = len(urllib.request.urlopen(u, timeout=10).read())\n"
            "    except http.client.IncompleteRead:\n        n = 'IncompleteRead'\n"
            "    print(u.rsplit('/', 1)[-1], n, flush=True)\n")

# a truncated image stored by an older version – must be deleted and downloaded again
os.environ["GENEALOGY_IMAGES"] = env["GENEALOGY_IMAGES"]
cache.ROOT = env["GENEALOGY_IMAGES"]
old = cache.path_for(cache.url_key(A + "/old.jpg")) + ".jpg"
os.makedirs(os.path.dirname(old), exist_ok=True)
open(old, "wb").write(JPG[:2000])

for round_ in (1, 2):
    r = subprocess.run([sys.executable, "-I", CLIENT] + [A + p for p in ("/whole.jpg", "/short.jpg", "/length.jpg",
                                                                         "/old.jpg")],
                       env=env, capture_output=True, text=True, timeout=120)
    if r.returncode:
        print(r.stdout, r.stderr)
check("whole image: from the archive only once", HITS.get("/whole.jpg") == 1, HITS)
check("truncated without length: not stored, downloaded again", HITS.get("/short.jpg") == 2)
check("length does not match: not stored", HITS.get("/length.jpg") == 2)
check("truncated stored earlier: deleted and downloaded again (then from disk)", HITS.get("/old.jpg") == 1
      and cache.is_complete_file(old))
s.shutdown()

print(f"\n{sum(results)} of {len(results)} right")
sys.exit(0 if all(results) else 1)
