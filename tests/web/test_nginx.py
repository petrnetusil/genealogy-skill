"""Test of nginx.conf, which tools/export_web.py builds from the template (deployment via Docker/CapRover).

Creates a sample project in a temporary folder, runs the export with a question and for an open website, and checks
the map $cookie_genealogy: exactly one `default` (nginx refuses two `default`s, #61). If Docker is available,
it also checks the configuration with nginx itself (`nginx -t` in the image from web/Dockerfile).
From the repository root:
  python3 -I tests/web/test_nginx.py skills/genealogy
"""
import json, os, re, shutil, subprocess, sys, tempfile

SKILL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{'' if ok else '  ' + str(detail)[:800]}", flush=True)


def gate_map(conf):
    m = re.search(r"map \$cookie_genealogy \$genealogy_ok \{(.*?)\n\}", conf, re.S)
    return m.group(1) if m else ""


def export(project, gate):
    path = os.path.join(project, "data", "website.json")
    cfg = json.load(open(path, encoding="utf-8"))
    cfg["gate"] = gate
    json.dump(cfg, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(project, "tools", "export_web.py")],
                       capture_output=True, text=True, cwd=project)
    conf = os.path.join(project, "web", "nginx.conf")
    return r, (open(conf, encoding="utf-8").read() if os.path.exists(conf) else "")


def docker_image(project):
    for line in open(os.path.join(project, "web", "Dockerfile"), encoding="utf-8"):
        if line.startswith("FROM nginx"):
            return line.split()[1]


def nginx_t(conf, image):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "default.conf")
        open(p, "w", encoding="utf-8").write(conf)
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{p}:/etc/nginx/conf.d/default.conf:ro", image, "nginx", "-t"],
                           capture_output=True, text=True)
        return r.returncode == 0, r.stderr[-400:]


tmp = tempfile.mkdtemp()
try:
    project = os.path.join(tmp, "project")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(SKILL, "tools", "new_project.py"), project, "--sample"],
                       capture_output=True, text=True)
    check("sample project created", r.returncode == 0, r.stderr)

    r, with_question = export(project, {"question": "Trade?", "answer": "blacksmith"})
    m = gate_map(with_question)
    check("with a question: export ran", r.returncode == 0, r.stderr)
    check("with a question: map has default 0 and the fingerprint", m.count("default") == 1 and "default 0;" in m and re.search(r'"[0-9a-f]{64}" 1;', m), m)
    check("with a question: map_hash_bucket_size for the 64-character fingerprint", "map_hash_bucket_size 128;" in with_question, with_question[:300])

    r, open_site = export(project, {"open": True})
    m = gate_map(open_site)
    check("open website: export ran", r.returncode == 0, r.stderr)
    check("open website: exactly one default in the map, and it is 1", m.count("default") == 1 and "default 1;" in m, m)
    check("open website: no fingerprint in the map", not re.search(r'"[0-9a-f]{64}"', m), m)

    image = docker_image(project)
    check("Dockerfile: nginx:stable-alpine", image == "nginx:stable-alpine", image)
    if shutil.which("docker") and subprocess.run(["docker", "info"], capture_output=True).returncode == 0:
        for name, conf in (("with a question", with_question), ("open website", open_site)):
            ok, err = nginx_t(conf, image)
            check(f"nginx -t ({image}): {name}", ok, err)
    else:
        print("[–] Docker not available, nginx -t skipped")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(results)} of {len(results)} passed")
sys.exit(0 if all(results) else 1)
