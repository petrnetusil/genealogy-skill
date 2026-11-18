#!/usr/bin/env python3
"""The brake for `polite.py curl …`: URL without https://, several URLs, ranges [..]/{..}, own -w, browser-only sites.

Downloads nothing: instead of curl a fake script runs (POLITE_CURL) that only records its arguments and, per -w,
prints the status code from FAKE_CODE. The brake state is in a temporary folder (POLITE_STATE).

    python3 -I tests/polite/test_curl.py skills/genealogy/tools/polite.py
"""
import json, os, subprocess, sys, tempfile

POLITE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy/tools/polite.py")
TMP = tempfile.mkdtemp(prefix="test_curl_")
FAKE = os.path.join(TMP, "fakecurl.py")
LOG = os.path.join(TMP, "log")
with open(FAKE, "w", encoding="utf-8") as f:
    f.write(r'''import sys, os, json
a = sys.argv[1:]
if a == ["--version"]:
    print("curl 8.5.0 (fake)"); sys.exit(0)
open(os.environ["FAKE_LOG"], "a", encoding="utf-8").write(json.dumps(a) + "\n")
w = None
for i, x in enumerate(a):
    if x in ("-w", "--write-out"): w = a[i + 1]
url = next((x for x in a if "://" in x), "")
if w:
    w = w.replace("%{http_code}", os.environ.get("FAKE_CODE", "200")).replace("%{url_effective}", url)
    for i, part in enumerate(w.split("%{stderr}")):
        (sys.stdout if i == 0 else sys.stderr).write(part)
''')
if os.name == "nt":
    CURL = os.path.join(TMP, "fakecurl.cmd")
    open(CURL, "w").write(f'@"{sys.executable}" "{FAKE}" %*\n')
else:
    CURL = os.path.join(TMP, "fakecurl")
    open(CURL, "w").write(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n')
    os.chmod(CURL, 0o755)

results = []


def curl(*args, code="200", state="a"):
    open(LOG, "w").close()
    env = dict(os.environ, POLITE_CURL=CURL, POLITE_STATE=os.path.join(TMP, "state_" + state), FAKE_LOG=LOG, FAKE_CODE=code)
    p = subprocess.run([sys.executable, "-I", POLITE, "curl", *args], capture_output=True, text=True, encoding="utf-8",
                       env=env)
    calls = [json.loads(r) for r in open(LOG, encoding="utf-8").read().splitlines()]
    return p.returncode, p.stdout, p.stderr, calls


def check(name, condition, info=""):
    results.append(condition)
    print(f"[{'OK ' if condition else 'FAIL'}] {name} {info}")


k, out, err, v = curl("-s", "www.mza.cz/actapublica/matrika/detail/1")
check("URL without https:// to a forbidden site is stopped", k == 3 and not v and "MZA" in err, f"code {k}")

k, out, err, v = curl("-s", "https://www.familysearch.org/ark:/61903/3:1:XXXX-YYYY-ZZZ")
check("FamilySearch is browser only (added in the English fork)", k == 3 and not v and "FamilySearch" in err, f"code {k}")

k, out, err, v = curl("-s", "-O", "https://img.example.cz/a.jpg", "-O", "https://img.example.cz/b.jpg")
check("two URLs in one curl are refused", k == 2 and not v, f"code {k}")

k, out, err, v = curl("-s", "-O", "https://img.example.cz/img[1-200].jpg")
check("range [1-200] is refused", k == 2 and not v, f"code {k}")

k, out, err, v = curl("-s", "-O", "https://img.example.cz/{a,b}.jpg")
check("range {a,b} is refused", k == 2 and not v, f"code {k}")

k, out, err, v = curl("-sg", "-o", "x.jpg", "https://img.example.cz/a[1].jpg")
check("with -g a bracket passes", k == 0 and len(v) == 1, f"code {k}")

k, out, err, v = curl("-s", "-o", "out.jpg", "https://img.example.cz/x.jpg")
check("the value of -o (\"out.jpg\") is not a second URL", k == 0 and len(v) == 1, f"code {k}")

k, out, err, v = curl("-sSLo", "work/x.jpg", "https://img.example.cz/x.jpg")
check("combined -sSLo takes the next argument as the file", k == 0 and len(v) == 1, f"code {k}")

k, out, err, v = curl("-s", "-o", "x.jpg", "-w", "%{http_code}", "https://search.example.be/api/x", code="429", state="b")
check("own -w: the output stays for the user", out == "429", repr(out))
check("own -w: 429 stops the site", k == 3 and "is stopped" in err, f"code {k}")
k2, _, err2, v2 = curl("-s", "https://search.example.be/api/y", state="b")
check("after 429 the next request is not sent", k2 == 3 and not v2, f"code {k2}")

print(f"\n{sum(results)} of {len(results)} tests passed")
sys.exit(0 if all(results) else 1)
