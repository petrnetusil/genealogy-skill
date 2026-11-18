#!/usr/bin/env python3
"""Portal health check: does every portal tool still work against the live portal?

Archives change addresses and APIs without notice. The check runs every tool on a fixed, known volume (reading + one
small image) in a temporary folder – it does not touch the project data – and prints what works and what does not.
The checked portals are the ones with ready-made tools (currently Czech, Austrian, Slovak and international ones);
add your own country's tools to CHECKS.

Usage (from the project root or from the skill folder):
  health.py                 all checks (~30 requests, about a minute)
  health.py --quick         without downloading images
  health.py --only aron,portafontium
                            only selected portals (names see the output)
Exit code 1 = at least one check failed. If a portal fails, try again in a while (outages are usually short);
if the error persists, the API has changed – fix the tool and note it in notes_for_skill.md.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: only portals and tools we have and that
allow scripts (no SOA Třeboň, eBadatelna, MZA, ZA Opava – forbidden in polite.py; no IPR Praha, VadeMeCum,
Litoměřice, Mauthausen, RÚIAN/OSM), Slovakiana without downloading an image (content.slovakiana.sk has Disallow in
robots.txt). Network through our brake tools/polite.py. Databases of victims and prisoners are only checked for a
responding server unless the user has given consent (consent.py) – the check never confirms consent.
"""
import os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # shared rate limit for archive websites (polite.py)

TOOLS = os.path.dirname(os.path.abspath(__file__))
PY = [sys.executable, "-I", "-X", "utf8"]

# (portal, description, command, regex in the output, output image or None)
# Fixed ids: when a portal renumbers a volume, the check fails – that is news too (links in project data stop working).
CHECKS = [
    ("aron", "volume search", ["aron_search.py", "Holice", "", "500"], r"0dfa5da8-0b8f-49f4-bc13-c2ea70fd100c", None),
    ("aron", "volume info", ["aron_img.py", "0dfa5da8-0b8f-49f4-bc13-c2ea70fd100c", "info"], r"scans", None),
    ("aron", "image", ["aron_img.py", "0dfa5da8-0b8f-49f4-bc13-c2ea70fd100c", "3", "2", "{out}"], r".", "ar.jpg"),
    ("portafontium", "books of a parish", ["portafontium.py", "parish", "dolni-bela"], r"^dolni-bela-17 \|", None),
    ("portafontium", "image", ["portafontium.py", "image", "dolni-bela-17", "5", "{out}", "preview"], r"link:", "pf.jpg"),
    ("ahmp", "volume search", ["bash", "ahmp_search.sh", "Smíchov"], r"9A79C81088C94C9DBEA2FC6758FD08E7", None),
    ("ahmp", "image", ["ahmp_scan.py", "9A79C81088C94C9DBEA2FC6758FD08E7", "5", "{out}", "1"], r".", "ah.jpg"),
    ("prague_police", "registration search", ["prague_police.py", "Kolar", "Josef"], r".", None),
    ("cuzk", "stable cadastre sheets", ["cuzk_maps.py", "sheets", "49.5234,14.4301"], r"TAB082018300", None),
    ("cuzk", "sheet export", ["cuzk_maps.py", "export", "skici", "195567", "{out}", "0,0,1,1", "400"], r"400×", "cz.jpg"),
    ("kramerius", "full text", ["kramerius.py", 'text_ocr:"Chyšky"', "1"], r"^found [1-9]", None),
    ("dnnt", "print search", ["dnnt.py", "search", 'text_ocr:"Chyšky"', "--max", "1"], r"found [1-9]", None),
    ("anno", "Austrian newspapers", ["anno.py", "Chischka", "1880", "1890", "1"], r"ANNOP_|anno\.onb", None),
    # databases of WWII victims and prisoners: a common surname, only the link format is checked, not personal data
    ("holocaust", "victims database", ["holocaust_victims.py", "search", "--surname", "Novák", "--pages", "1"],
     r"holocaust\.cz/databaze-obeti/", None),
    ("arolsen", "person search", ["arolsen.py", "search", "Novák", "--max", "1"], r"arolsen-archives\.org/en/document/\d+", None),
    ("terezin", "prisoners database", ["persecuted.py", "search", "--surname", "Novák", "--pages", "1"],
     r"pamatnik-terezin\.cz/vezen/", None),
    # Slovakiana (Slovak National Archives, 1 request per 10 s – the check takes ~20 s); no images: content.slovakiana.sk
    # has Disallow in robots.txt
    ("slovakiana", "village sheets 1930", ["slovakiana.py", "search", "Lopej", "--year", "1930", "--pages", "1"],
     r"^1930 \| .* \| cair-\w+ \|", None),
    ("slovakiana", "sheet description", ["slovakiana.py", "sheet", "cair-ko27a1l"], r"Box number: 1233", None),
]
# Portals that verify a human before entry (computation in the browser). The tool does not work around it and exits
# with this code; the check then reports OK with a note – the server is alive, the tool recognised the verification,
# search only in the browser.
HUMAN_CHECK = {}
# Tools that do not query the portal without the user's consent (consent.py): without consent only availability is checked.
CONSENT = {"holocaust": ("holocaust_victims", "https://www.holocaust.cz/databaze-obeti/"),
           "arolsen": ("arolsen", "https://collections.arolsen-archives.org/"),
           "terezin": ("persecuted", "https://www.pamatnik-terezin.cz/databaze")}


def has_consent(module):
    import importlib, consent
    try:
        m = importlib.import_module(module)
    except (ImportError, SystemExit):
        return False
    return consent.has_consent(m.CONSENT_KEY, m.CONSENT_TEXT)


# Portals without a fixed volume (only the browser gives the image path): only "the server answers"
AVAILABILITY = [
    ("matricula", "Matricula", "https://data.matricula-online.eu/"),
]


def is_jpeg(path):
    try:
        with open(path, "rb") as f:
            return f.read(3) == b"\xff\xd8\xff" and os.path.getsize(path) > 5000
    except OSError:
        return False


def server_answers(url):
    req = urllib.request.Request(url, headers={"User-Agent": polite.UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return True, str(r.status)
    except urllib.error.HTTPError as e:   # 404 at the root of an image server is fine – the server is alive
        return e.code < 500, str(e.code)
    except OSError as e:
        return False, str(getattr(e, "reason", e))
    except SystemExit as e:   # polite.py: site stopped or 403 on the first request – the check must go on
        return False, str(e)[:80]


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__)
        sys.exit(0)
    quick = "--quick" in args
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = set(args[i + 1].split(",")) if i + 1 < len(args) else set()
    portals = {k[0] for k in CHECKS} | {k[0] for k in AVAILABILITY}
    if only is not None and not only <= portals:
        sys.exit(f"Unknown portal: {', '.join(sorted(only - portals))}. Known: {', '.join(sorted(portals))}")

    tmp = tempfile.mkdtemp(prefix="genealogy_health_")
    failed = 0
    try:
        os.makedirs(os.path.join(tmp, "data"))
        open(os.path.join(tmp, "data", "STATUS.md"), "w").close()   # tools otherwise refuse to run outside a project
        shutil.copytree(TOOLS, os.path.join(tmp, "tools"), ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(tmp, "out"))
        for portal, desc, cmd, pattern, img in CHECKS:
            if (only is not None and portal not in only) or (quick and img):
                continue
            if portal in CONSENT and not has_consent(CONSENT[portal][0]):
                ok, code = server_answers(CONSENT[portal][1])
                print(f"{'OK   ' if ok else 'ERROR'} {portal:13} {desc:28} (no consent: availability only, {code})")
                failed += not ok
                continue
            out = os.path.join("out", img) if img and "/" not in img else img
            cmd = [c.replace("{out}", out or "") for c in cmd]
            cmd = ["bash", "tools/" + cmd[1], *cmd[2:]] if cmd[0] == "bash" else [*PY, "tools/" + cmd[0], *cmd[1:]]
            t = time.time()
            try:
                p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=180)
                output = p.stdout + p.stderr
                ok = p.returncode == 0 and re.search(pattern, p.stdout, re.M) is not None
                if not ok and p.returncode == polite.EXIT_CODE and "Do not work around this" in output:
                    print(f"OK    {portal:13} {desc:28} (the portal forbids scripts – browser only, see polite.py)")
                    continue
                if not ok and HUMAN_CHECK.get(portal) == p.returncode:
                    print(f"OK    {portal:13} {desc:28} (the portal verifies a human – browser only)")
                    continue
                if ok and img and not is_jpeg(os.path.join(tmp, out)):
                    ok, output = False, f"image {img} is missing or not a JPEG\n" + output
            except subprocess.TimeoutExpired:
                ok, output = False, "timed out (180 s)"
            lines = [r for r in output.strip().splitlines() if r.strip()]
            print(f"{'OK   ' if ok else 'ERROR'} {portal:13} {desc:28} {time.time() - t:5.1f} s")
            if not ok:
                failed += 1
                for r in lines[-3:]:
                    print("      ", r[:200])
        for portal, desc, url in AVAILABILITY:
            if only is not None and portal not in only:
                continue
            ok, code = server_answers(url)
            print(f"{'OK   ' if ok else 'ERROR'} {portal:13} {desc:28} (availability only, {code})")
            failed += not ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'Everything works.' if not failed else f'Failed: {failed}.'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
