"""Test of the version check (tools/version.py) and of the guard against updating a project with an older skill
(new_project.py).

GitHub is imitated by a local server (GENEALOGY_VERSION_URL), the cache is in a temporary folder (GENEALOGY_CACHE) –
no network access.
From the repository root:
  python3 -I tests/version/test_version.py skills/genealogy
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

SKILL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{'' if ok else '  ' + str(detail)[:700]}", flush=True)


STATE = {"tag": "v0.9.0", "requests": 0, "code": 200}


class GH(BaseHTTPRequestHandler):
    def do_GET(self):
        STATE["requests"] += 1
        b = json.dumps({"tag_name": STATE["tag"]}).encode()
        self.send_response(STATE["code"])
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b if STATE["code"] == 200 else b"{}")

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 0), GH)
threading.Thread(target=srv.serve_forever, daemon=True).start()
tmp = tempfile.mkdtemp(prefix="version_")
cache = os.path.join(tmp, "cache")
ENV = dict(os.environ, GENEALOGY_VERSION_URL=f"http://127.0.0.1:{srv.server_address[1]}/latest", GENEALOGY_CACHE=cache)


def fake_skill(version, plugin=False):
    s = os.path.join(tmp, "plugins", "cache", "genealogy-skill", "genealogy", version, "skills", "genealogy") if plugin \
        else os.path.join(tmp, "skills", f"genealogy_{version}")
    os.makedirs(os.path.join(s, "tools"), exist_ok=True)
    shutil.copy(os.path.join(SKILL, "tools", "version.py"), os.path.join(s, "tools", "version.py"))
    open(os.path.join(s, "VERSION"), "w").write(version + "\n")
    return s


def project(version):
    p = os.path.join(tmp, f"project_{version}")
    os.makedirs(p, exist_ok=True)
    open(os.path.join(p, ".skill_version"), "w").write(version + "\n")
    return p


def version(skill, proj=None, env=None):
    args = [sys.executable, "-I", os.path.join(skill, "tools", "version.py")] + ([proj] if proj else [])
    r = subprocess.run(args, capture_output=True, text=True, env=env or ENV, timeout=60)
    return r.returncode, r.stdout + r.stderr


try:
    if not os.path.exists(os.path.join(SKILL, "tools", "version.py")):
        check("tools/version.py exists", False)
        raise SystemExit

    # 1) GitHub newer than the installed skill
    code, out = version(fake_skill("0.8.2", plugin=True), project("0.8.2"))
    check("GitHub newer: exit code 0", code == 0, out)
    check("GitHub newer, plugin: tells the version and advises claude plugin update",
          "0.9.0" in out and "plugin update" in out and "NEW_SKILL_VERSION" in out, out)
    code, out = version(fake_skill("0.8.2"), project("0.8.2"))
    check("GitHub newer, manually copied skill: no claude plugin advice, a new folder from GitHub instead",
          "NEW_SKILL_VERSION" in out and "claude plugin" not in out and "github.com/petrnetusil/genealogy-skill" in out, out)
    check("GitHub newer: does not update the project from GitHub (no git clone)", "clone" not in out, out)
    check("cache written", os.path.exists(os.path.join(cache, "genealogy_version.json")), os.listdir(tmp))

    # 2) within 24 hours GitHub is not asked again
    before = STATE["requests"]
    code, out = version(fake_skill("0.8.2"), project("0.8.2"))
    check("within 24 h: from the cache, no GitHub request", STATE["requests"] == before and "0.9.0" in out, (STATE, out))

    # 3) after 24 hours again
    c = os.path.join(cache, "genealogy_version.json")
    d = json.load(open(c))
    d["time"] = time.time() - 25 * 3600
    json.dump(d, open(c, "w"))
    STATE["tag"] = "v0.10.0"
    code, out = version(fake_skill("0.9.0"), project("0.9.0"))
    check("after 24 h: asks again", STATE["requests"] == before + 1, STATE)
    check("0.10.0 is newer than 0.9.0 (numbers, not text)", "0.10.0" in out and "NEW_SKILL_VERSION" in out, out)

    # 4) GitHub unreachable: nothing crashes, at least the project and the skill are compared
    shutil.rmtree(cache)
    STATE["code"] = 500
    code, out = version(fake_skill("0.9.0"), project("0.8.2"))
    check("GitHub unreachable: code 0 and offers the project update", code == 0 and "UPDATE_PROJECT" in out, out)
    env = dict(ENV, GENEALOGY_VERSION_URL="http://127.0.0.1:9/nothing")
    code, out = version(fake_skill("0.9.0"), project("0.9.0"), env)
    check("no network: code 0, up to date by the local versions", code == 0 and "UP_TO_DATE" in out, out)
    STATE["code"] = 200
    STATE["tag"] = "v0.9.0"

    # 5) skill newer than the project
    shutil.rmtree(cache, ignore_errors=True)
    code, out = version(fake_skill("0.9.0"), project("0.8.2"))
    check("skill newer than the project: offers new_project.py", "UPDATE_PROJECT" in out and "new_project.py" in out, out)

    # 6) project newer than the skill (old copy of the skill)
    code, out = version(fake_skill("0.9.0"), project("0.9.1"))
    check("project newer than the skill: warns, do not update the project",
          "PROJECT_NEWER" in out and "UPDATE_PROJECT" not in out, out)

    # 7) everything the same
    code, out = version(fake_skill("0.9.0"), project("0.9.0"))
    check("everything up to date", "UP_TO_DATE" in out and "NEW_SKILL_VERSION" not in out, out)

    # 8) project without .skill_version (very old) = update
    p = os.path.join(tmp, "project_without")
    os.makedirs(p)
    code, out = version(fake_skill("0.9.0"), p)
    check("project without .skill_version: offers an update", "UPDATE_PROJECT" in out, out)

    # 9) without a project: only skill × GitHub
    code, out = version(fake_skill("0.9.0"))
    check("without a project: only the skill and GitHub", code == 0 and "UP_TO_DATE" in out, out)

    # 10) copy of version.py in the project's tools/: finds the installed skill (plugin registry / ~/.claude/skills),
    #     otherwise does not report UP_TO_DATE
    shutil.rmtree(cache, ignore_errors=True)
    cfg = os.path.join(tmp, "claude_cfg")
    pr = project("0.9.0")
    os.makedirs(os.path.join(pr, "tools"), exist_ok=True)
    shutil.copy(os.path.join(SKILL, "tools", "version.py"), os.path.join(pr, "tools", "version.py"))
    env = dict(ENV, CLAUDE_CONFIG_DIR=cfg)
    copy = os.path.join(pr, "tools", "version.py")

    def from_project():
        r = subprocess.run([sys.executable, "-I", copy, pr], capture_output=True, text=True, env=env, timeout=60)
        return r.stdout + r.stderr

    os.makedirs(cfg, exist_ok=True)
    out = from_project()
    check("copy in the project, skill not found: no UP_TO_DATE", "UP_TO_DATE" not in out and "SKILL_NOT_FOUND" in out, out)

    def plugin(version, scope, project_path=None):
        ip = os.path.join(cfg, "plugins", "cache", "genealogy-skill", "genealogy", version)
        os.makedirs(os.path.join(ip, "skills", "genealogy"), exist_ok=True)
        open(os.path.join(ip, "skills", "genealogy", "VERSION"), "w").write(version + "\n")
        z = {"scope": scope, "installPath": ip, "version": version}
        if project_path:
            z["projectPath"] = project_path
        return z
    reg = {"version": 2, "plugins": {"genealogy@genealogy-skill": [plugin("0.5.0", "local", "/other/project"),
                                                                   plugin("0.8.2", "user")]}}
    json.dump(reg, open(os.path.join(cfg, "plugins", "installed_plugins.json"), "w"))
    out = from_project()
    check("copy in the project: finds the plugin (user scope, not another project) → 0.8.2 < GitHub",
          "0.8.2" in out and "NEW_SKILL_VERSION" in out and "claude plugin" in out, out)
    reg["plugins"]["genealogy@genealogy-skill"].append(plugin("0.9.0", "project", pr))
    json.dump(reg, open(os.path.join(cfg, "plugins", "installed_plugins.json"), "w"))
    out = from_project()
    check("copy in the project: the plugin for this project wins", "Skill (installed): 0.9.0" in out and "UP_TO_DATE" in out, out)
    os.remove(os.path.join(cfg, "plugins", "installed_plugins.json"))
    os.makedirs(os.path.join(cfg, "skills", "genealogy"), exist_ok=True)
    open(os.path.join(cfg, "skills", "genealogy", "VERSION"), "w").write("0.8.2\n")
    out = from_project()
    check("copy in the project: finds the manually copied ~/.claude/skills/genealogy",
          "0.8.2" in out and "NEW_SKILL_VERSION" in out and "claude plugin" not in out, out)
    shutil.rmtree(os.path.join(cfg, "skills"))
    out = from_project()
    check("copy in the project, no registry: finds the plugin folder ~/.claude/plugins/cache/genealogy-skill/genealogy/<v>",
          "Skill (installed): 0.9.0" in out and "UP_TO_DATE" in out, out)

    # 11) new_project.py: an older skill does not update the project
    proj = os.path.join(tmp, "real")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(SKILL, "tools", "new_project.py"), proj],
                       capture_output=True, text=True)
    check("project created", r.returncode == 0, r.stdout[-400:] + r.stderr)
    open(os.path.join(proj, ".skill_version"), "w").write("99.0.0\n")
    exp = os.path.join(proj, "tools", "export_web.py")
    open(exp, "a").write("# own change\n")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(SKILL, "tools", "new_project.py"), proj],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    check("new_project: project newer than the skill → refused (code ≠ 0)", r.returncode != 0 and "99.0.0" in out, out[-400:])
    check("new_project: nothing changed on refusal", open(exp).read().endswith("# own change\n")
          and open(os.path.join(proj, ".skill_version")).read().strip() == "99.0.0", "")
finally:
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(results)} of {len(results)} correct")
sys.exit(0 if all(results) else 1)
