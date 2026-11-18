"""Test of storing images from the browser in the cache (tools/cache.py save / find) – eBadatelna and FamilySearch.

From the repository root:
  python3 -I tests/polite/test_browser_images.py skills/genealogy/tools
The cache is in a temporary folder (GENEALOGY_IMAGES). Downloads nothing, does not need ImageMagick.
Contract with the browser snippets (reference/portals.md, reference/countries/…): the JSON file holds
{"url": <image URL>, "data": "data:image/…;base64,…", "w": …, "h": …}.
"""
import base64, json, os, shutil, subprocess, sys, tempfile

TOOLS = os.path.abspath(sys.argv[1])
CACHE = os.path.join(TOOLS, "cache.py")
JPG = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 40 + b"\xff\xd9"
ARK = "3:1:3Q9M-CS54-T34P-Y"
FS_DIST = f"https://www.familysearch.org/service/records/storage/deepzoomcloud/dz/v1/{ARK}/$dist"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'OK ' if ok else 'FAIL'}] {name} {'' if ok else detail}", flush=True)


tmp = tempfile.mkdtemp(prefix="cache_browser_")
env = dict(os.environ, GENEALOGY_IMAGES=os.path.join(tmp, "cache"), POLITE_STATE=os.path.join(tmp, "state"))


def cache(*a):
    return subprocess.run([sys.executable, "-I", "-X", "utf8", CACHE, *a], cwd=tmp, env=env,
                          capture_output=True, text=True)


def json_from_browser(url, data=JPG):
    p = os.path.join(tmp, "image.json")
    d = {"w": 4000, "h": 3000, "url": url, "data": "data:image/jpeg;base64," + base64.b64encode(data).decode()}
    with open(p, "w") as f:
        json.dump(json.dumps(d), f)   # browser_evaluate with filename stores the result as a JSON string
    return p


try:
    # eBadatelna (existing behaviour)
    r = cache("save", json_from_browser("https://ebadatelna.soapraha.cz/d/11269/40"))
    check("eBadatelna: save", r.returncode == 0 and "saved:" in r.stdout, r.stdout + r.stderr)
    r = cache("find", "https://ebadatelna.soapraha.cz/d/11269/40")
    check("eBadatelna: find", r.returncode == 0 and r.stdout.strip().endswith(".jpg"), r.stdout + r.stderr)

    # FamilySearch: stored by the image's ARK
    r = cache("save", json_from_browser(FS_DIST), "work/fs.jpg")
    check("FamilySearch: save", r.returncode == 0 and "saved:" in r.stdout, r.stdout + r.stderr)
    check("FamilySearch: copy into the project", os.path.exists(os.path.join(tmp, "work", "fs.jpg")))
    stored = [os.path.join(d, f) for d, _, fs in os.walk(env["GENEALOGY_IMAGES"]) for f in fs if "familysearch" in d]
    check("FamilySearch: file name without colons (Windows)", bool(stored) and not any(":" in os.path.basename(p) for p in stored),
          stored)
    check("FamilySearch: json deleted after saving", not os.path.exists(os.path.join(tmp, "image.json")))

    # find: the same image under the $dist URL and under the ark permalink
    for url in (FS_DIST, f"https://www.familysearch.org/ark:/61903/{ARK}?i=5&cc=1554443"):
        r = cache("find", url)
        check(f"FamilySearch: find {url[:60]}…", r.returncode == 0 and r.stdout.strip().endswith(".jpg"),
              r.stdout + r.stderr)
    r = cache("find", "https://www.familysearch.org/ark:/61903/3:1:XXXX-YYYY-ZZZ")
    check("FamilySearch: another image is not found", r.returncode == 1, r.stdout + r.stderr)

    # neither a truncated image nor a foreign URL is stored
    r = cache("save", json_from_browser("https://www.familysearch.org/ark:/61903/3:1:AAAA-BBBB-CCC", JPG[:500]))
    check("FamilySearch: truncated image refused", r.returncode != 0, r.stdout + r.stderr)
    r = cache("save", json_from_browser("https://example.org/picture.jpg"))
    check("foreign URL refused", r.returncode != 0, r.stdout + r.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(results)} of {len(results)} right")
sys.exit(0 if all(results) else 1)
