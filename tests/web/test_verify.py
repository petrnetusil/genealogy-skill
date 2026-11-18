"""Test of the post-deployment check (template/web/scripts/verify.mjs): recognises the family gate, Netlify team
protection and a website without a gate.

From the repository root:
  python3 -I tests/web/test_verify.py skills/genealogy
A local server mimics the website's responses (family gate 401, Netlify login, public page 200); verify.mjs gets its
address via --url, so it never contacts Netlify. Needs Node.js.
"""
import os, shutil, subprocess, sys, tempfile, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

SKILL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy")
TEMPLATE = os.path.join(SKILL, "template", "web")
GATE = open(os.path.join(TEMPLATE, "login.template.html"), encoding="utf-8").read()
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{'' if ok else '  ' + str(detail)[:700]}", flush=True)


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split("?")[0]
        if p.startswith("/gate"):
            self.reply(401, GATE)
        elif p.startswith("/netlify401"):
            self.reply(401, "<html><title>Login Redirect</title><body>Netlify</body></html>")
        elif p.startswith("/netlify"):   # team protection: redirect to the Netlify login
            self.send_response(302)
            self.send_header("Location", "https://app.netlify.com/login?redirect=1")
            self.end_headers()
        elif p.startswith("/cf429"):
            self.reply(429, "error code: 1027")
        elif p.startswith("/cfchallenge"):   # Cloudflare verification page (not our gate)
            self.reply(403, "<html><title>Just a moment...</title><body>cf-chl challenge-platform</body></html>")
        elif p.startswith("/public"):
            self.reply(200, "<html><title>Family tree</title><body>The Novak family tree</body></html>")
        else:
            self.reply(404, "nothing")

    def reply(self, code, text):
        b = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


s = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=s.serve_forever, daemon=True).start()
A = f"http://127.0.0.1:{s.server_address[1]}"

tmp = tempfile.mkdtemp(prefix="verify_web_")
try:
    web = os.path.join(tmp, "web")
    os.makedirs(os.path.join(web, "scripts"))
    for f in ("verify.mjs", "npx.mjs"):   # npx.mjs: running npx without a shell (imported by verify.mjs)
        shutil.copy(os.path.join(TEMPLATE, "scripts", f), os.path.join(web, "scripts", f))

    def verify(path, gate=True, cloudflare=None):
        edge = os.path.join(web, "netlify", "edge-functions", "gate.js")
        cf = os.path.join(web, "cloudflare", "worker.js")
        if cloudflare is None and os.path.exists(cf):
            os.remove(cf)
        elif cloudflare is not None:
            os.makedirs(os.path.dirname(cf), exist_ok=True)
            open(cf, "w").write("const OPEN = %s;" % cloudflare)
            gate = False
        if gate:
            os.makedirs(os.path.dirname(edge), exist_ok=True)
            open(edge, "w").write("// gate")
        elif os.path.exists(edge):
            os.remove(edge)
        r = subprocess.run(["node", "scripts/verify.mjs", "--url", A + path], cwd=web, capture_output=True, text=True,
                           timeout=60)
        return r.returncode, r.stdout + r.stderr

    code, out = verify("/gate")
    check("family gate: fine (code 0)", code == 0 and "family question" in out, out)

    for path in ("/netlify", "/netlify401"):
        code, out = verify(path)
        check(f"Netlify team protection ({path}): error (code 1)", code == 1, out)
        check(f"Netlify team protection ({path}): explains sso_login and the path in the administration",
              "sso_login" in out and "Visitor access" in out, out)

    code, out = verify("/public")
    check("gate in the project, but the website is public: error", code == 1 and "without the family question" in out, out)

    code, out = verify("/public", gate=False)
    check("website without sign-in (no question in the settings): information only, code 0", code == 0 and "without signing in" in out, out)

    code, out = verify("/missing")
    check("unexpected response (404): error with the status code", code == 1 and "404" in out, out)

    code, out = verify("/public", cloudflare="false")
    check("Cloudflare: gate in the project, but the website is public: error", code == 1 and "without the family question" in out, out)

    code, out = verify("/public", cloudflare="true")
    check("Cloudflare: open website – information only, code 0", code == 0 and "without signing in" in out, out)

    code, out = verify("/cf429", cloudflare="false")
    check("Cloudflare 429: explains the daily limit", code == 1 and "limit" in out, out)

    code, out = verify("/cfchallenge", cloudflare="false")
    check("Cloudflare verification page: explains it is not the gate", code == 1 and "verification" in out, out)

    # without --url and without .netlify/state.json: verifies nothing, but does not stop the deployment
    r = subprocess.run(["node", "scripts/verify.mjs"], cwd=web, capture_output=True, text=True, timeout=60)
    check("not linked to Netlify: only a note, code 0", r.returncode == 0 and "private window" in r.stdout,
          r.stdout + r.stderr)
finally:
    s.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(results)} of {len(results)} passed")
sys.exit(0 if all(results) else 1)
