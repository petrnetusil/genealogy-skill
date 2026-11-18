"""Cloudflare deployment test: the export builds the gate (web/cloudflare/worker.js) and wrangler.jsonc, the gate lets only the family in.

Creates a sample project in a temporary folder, runs the export with a question and for an open website, and tries
the gate in Node with a mocked env.ASSETS (Cloudflare static assets). Never contacts Cloudflare. Needs Node.js.
From the repository root:
  python3 -I tests/web/test_cloudflare.py skills/genealogy
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile

SKILL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{'' if ok else '  ' + str(detail)[:800]}", flush=True)


def jsonc(path):
    return json.loads("".join(r for r in open(path, encoding="utf-8") if not r.lstrip().startswith("//")))


def export(project, gate, cloudflare=None, *args):
    path = os.path.join(project, "data", "website.json")
    cfg = json.load(open(path, encoding="utf-8"))
    cfg["gate"] = gate
    cfg.pop("cloudflare", None)
    if cloudflare is not None:
        cfg["cloudflare"] = cloudflare
    json.dump(cfg, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(project, "tools", "export_web.py"), *args],
                          capture_output=True, text=True, cwd=project)


# Mocked Cloudflare: env.ASSETS returns files from dist/ and, like Cloudflare (html_handling auto-trailing-slash),
# redirects /login.html to /login. Prints the results of the requests as JSON.
TRIAL = r"""
import worker from %s;
const LOGIN = '<html><script>document.cookie = \'genealogy=\' + hash</script></html>';
const ASSETS = { async fetch(req) {
  const p = new URL(req.url ?? req).pathname;
  if (p === '/login.html') return new Response(null, { status: 307, headers: { location: '/login' } });
  if (p === '/login') return new Response(LOGIN, { headers: { 'content-type': 'text/html' } });
  if (p === '/nothing') return new Response('404 page', { status: 404 });
  return new Response('content ' + p, { headers: { 'content-type': 'text/html' } });
} };
const results = {};
for (const [key, path, cookie] of %s) {
  const req = new Request('https://genealogy.account.workers.dev' + path, { headers: cookie ? { cookie } : {} });
  const res = await worker.fetch(req, { ASSETS });
  results[key] = { status: res.status, text: await res.text(), robots: res.headers.get('x-robots-tag'),
                   cache: res.headers.get('cache-control'), location: res.headers.get('location') };
}
console.log(JSON.stringify(results));
"""


def attempt(worker, requests):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "trial.mjs")
        url = "file://" + os.path.abspath(worker).replace(os.sep, "/")
        open(p, "w", encoding="utf-8").write(TRIAL % (json.dumps(url), json.dumps(requests)))
        r = subprocess.run(["node", p], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except ValueError:
            return {"error": r.stderr[-800:]}


tmp = tempfile.mkdtemp()
try:
    project = os.path.join(tmp, "project")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(SKILL, "tools", "new_project.py"), project, "--sample"],
                       capture_output=True, text=True)
    check("sample project created", r.returncode == 0, r.stderr)
    web = os.path.join(project, "web")
    worker = os.path.join(web, "cloudflare", "worker.js")
    wrangler = os.path.join(web, "wrangler.jsonc")

    # --- with a family question ---
    r = export(project, {"question": "Trade?", "answer": "blacksmith"})
    check("with a question: export ran", r.returncode == 0, r.stderr)
    digest = hashlib.sha256("genealogy:blacksmith".encode()).hexdigest()
    content = open(worker, encoding="utf-8").read() if os.path.exists(worker) else ""
    check("gate cloudflare/worker.js with the answer fingerprint", digest in content and "{{" not in content, content[:300])

    cfg = {}
    try:
        cfg = jsonc(wrangler)
    except (OSError, ValueError) as e:
        cfg = {"error": str(e)}
    a = cfg.get("assets") or {}
    check("wrangler.jsonc: default name genealogy, gate as main", cfg.get("name") == "genealogy" and cfg.get("main") == "cloudflare/worker.js", cfg)
    check("wrangler.jsonc: files from dist/ via ASSETS", a.get("directory") == "./dist" and a.get("binding") == "ASSETS", a)
    check("wrangler.jsonc: the gate runs before every file (run_worker_first)", a.get("run_worker_first") is True, a)
    check("wrangler.jsonc: missing page = 404.html", a.get("not_found_handling") == "404-page", a)
    check("wrangler.jsonc: workers.dev yes, preview URLs no", cfg.get("workers_dev") is True and cfg.get("preview_urls") is False, cfg)
    check("wrangler.jsonc: compatibility_date", re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cfg.get("compatibility_date", ""))), cfg)

    c = f"genealogy={digest}"
    v = attempt(worker, [["none", "/", None], ["wrong", "/", "genealogy=abc"], ["good", "/", c],
                         ["more", "/person/jan/", "other=1; " + c + "; next=2"], ["image", "/img/x.jpg", None],
                         ["image_ok", "/img/x.jpg", c], ["login", "/login", None],
                         ["login_html", "/login.html", None], ["nothing", "/nothing", c]])
    check("node: the gate runs", "error" not in v, v.get("error"))
    if "error" not in v:
        check("no cookie: 401 with the login page", v["none"]["status"] == 401 and "genealogy=" in v["none"]["text"], v["none"])
        check("no cookie: noindex and no-store", v["none"]["robots"] == "noindex, nofollow" and "no-store" in (v["none"]["cache"] or ""), v["none"])
        check("wrong cookie: 401", v["wrong"]["status"] == 401, v["wrong"])
        check("right cookie: website page", v["good"]["status"] == 200 and v["good"]["text"] == "content /", v["good"])
        check("right cookie: noindex", v["good"]["robots"] == "noindex, nofollow", v["good"])
        check("cookie among other cookies", v["more"]["status"] == 200, v["more"])
        check("image without cookie: 401 (not the file)", v["image"]["status"] == 401 and "content" not in v["image"]["text"], v["image"])
        check("image with cookie: the file", v["image_ok"]["text"] == "content /img/x.jpg", v["image_ok"])
        check("login page available without cookie", v["login"]["status"] == 200 and "genealogy=" in v["login"]["text"], v["login"])
        check("/login.html without cookie passes (Cloudflare redirect)", v["login_html"]["status"] in (200, 307, 308), v["login_html"])
        check("missing page with cookie: 404", v["nothing"]["status"] == 404, v["nothing"])

    # --- subdomain name (cloudflare.subdomain) ---
    r = export(project, {"question": "Trade?", "answer": "blacksmith"}, {"subdomain": "novak-family"})
    cfg = jsonc(wrangler) if r.returncode == 0 and os.path.exists(wrangler) else {}
    check("a valid cloudflare.subdomain passes, the worker is still called genealogy", cfg.get("name") == "genealogy", (r.stderr, cfg))
    r = export(project, {"question": "Trade?", "answer": "blacksmith"}, {"subdomain": "Novák.Family"})
    check("invalid name: export ends with a clear error", r.returncode != 0 and "cloudflare" in (r.stdout + r.stderr).lower(), (r.returncode, r.stdout[-300:], r.stderr[-300:]))

    # --- answer without Latin letters or digits (Cyrillic, symbols) ---
    r = export(project, {"question": "Where?", "answer": "Москва"}, None, "--deploy")
    out = r.stdout + r.stderr
    check("Cyrillic answer: deployment refused with an explanation (Latin letters)", r.returncode != 0 and "Latin" in out, out[-300:])

    # --- open website ---
    r = export(project, {"open": True})
    check("open website: export ran", r.returncode == 0, r.stderr)
    v = attempt(worker, [["none", "/", None], ["image", "/img/x.jpg", None]])
    check("open website: page and image without cookie", v.get("none", {}).get("status") == 200 and v.get("image", {}).get("text") == "content /img/x.jpg", v)

    # --- checking a free name (--check-free): Cloudflare DNS over DoH, mocked here by a local server ---
    import threading
    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    QUERIES = []

    class Doh(BaseHTTPRequestHandler):
        def do_GET(self):
            name = parse_qs(urlparse(self.path).query).get("name", [""])[0]
            QUERIES.append(name)
            taken = name.endswith(".novak-family.workers.dev")
            b = json.dumps({"Status": 0, "Answer": [{"data": "104.21.12.93"}]} if taken else {"Status": 3}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/dns-json")
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Doh)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = dict(os.environ, GENEALOGY_DOH=f"http://127.0.0.1:{srv.server_address[1]}/dns-query")

    def check_free(*names):
        r = subprocess.run(["node", "scripts/deploy_cloudflare.mjs", "--check-free", *names], cwd=web, env=env,
                           capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout + r.stderr

    code, out = check_free("novak-family")
    check("--check-free: recognises a taken name (code 1)", code == 1 and "taken" in out, out)
    check("--check-free: asks for *.name.workers.dev", any(d.endswith(".novak-family.workers.dev") for d in QUERIES), QUERIES)
    code, out = check_free("novak-family-holice")
    check("--check-free: free name (code 0)", code == 0 and "free" in out, out)
    code, out = check_free("novak-family", "novak-line")
    check("--check-free: several names – prints each", "novak-family" in out and "novak-line" in out and code == 0, out)
    code, out = check_free("Novák.Family")
    check("--check-free: refuses an invalid name", code == 2 and "cannot be used" in out, out)
    srv.shutdown()
    r = subprocess.run(["node", "scripts/deploy_cloudflare.mjs", "--trial"], cwd=web, capture_output=True, text=True, timeout=60)
    check("unknown option: ends at once (code 2), deploys nothing", r.returncode == 2 and "wrangler" not in r.stdout.lower(), r.stdout + r.stderr)

    # --- scripts and git ---
    pkg = json.load(open(os.path.join(web, "package.json"), encoding="utf-8"))
    s = pkg["scripts"].get("deploy-cloudflare", "")
    check("package.json: deploy-cloudflare (data --deploy, build, deployment, check)",
          "--deploy" in s and "build" in s and "cloudflare" in s, s)
    gi = open(os.path.join(project, ".gitignore"), encoding="utf-8").read()
    check(".gitignore: generated gate, wrangler.jsonc and .wrangler/",
          all(x in gi for x in ("web/cloudflare/worker.js", "web/wrangler.jsonc", "web/.wrangler/")), gi[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(results)} of {len(results)} passed")
sys.exit(0 if all(results) else 1)
