"""Test of the --columns mode in book_map.py (index by columns at full resolution).

From the repository root:
  python3 -I tests/book_map/test_columns.py skills/genealogy/tools
  (Windows: python -I -X utf8 …)
Works only with files (`files`), downloads nothing; needs ImageMagick (magick, or convert for ImageMagick 6).
"""
import glob, os, shutil, subprocess, sys, tempfile

TOOLS = os.path.abspath(sys.argv[1])
PY = [sys.executable, "-I", "-X", "utf8"]
MAGICK = shutil.which("magick") or next(iter(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe")), None) or "convert"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(("OK   " if ok else "FAIL ") + name + ("" if ok else f"\n    {detail}"))


def size(f):
    w, h = subprocess.run([MAGICK, f, "-format", "%w %h", "info:"], capture_output=True, text=True, check=True).stdout.split()
    return int(w), int(h)


def run(tmp, *args):
    return subprocess.run(PY + [os.path.join(TOOLS, "book_map.py"), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=tmp)


tmp = tempfile.mkdtemp(prefix="book_map_columns_")
try:
    image = os.path.join(tmp, "index_12.jpg")
    subprocess.run([MAGICK, "-size", "4000x3200", "xc:white", image], check=True)
    out = os.path.join(tmp, "out", "s.jpg")

    r = run(tmp, "files", image, "--columns", "4", "-o", out)
    strips = sorted(glob.glob(os.path.join(tmp, "out", "s_sn12_s*.jpg")))
    check("4 strips × 3 parts (3200 px > 1500 px)", r.returncode == 0 and len(strips) == 12, r.stderr + r.stdout)
    if strips:
        w, h = size(strips[0])
        check("full resolution: strip ~1000 px + overlap, part ≤ 1500 px + label", 1000 <= w <= 1100 and h <= 1500 + 60,
              f"{w}x{h}")

    shutil.rmtree(os.path.join(tmp, "out"))
    r = run(tmp, "files", image, "--columns", "0.3,0.55,0.8", "--crop", "0,0,0.5,0.4", "-o", out)
    strips = sorted(glob.glob(os.path.join(tmp, "out", "s_sn12_s*.jpg")))
    check("own boundaries + crop: 4 strips, one part", r.returncode == 0 and len(strips) == 4, r.stderr + r.stdout)
    if strips:
        w, h = size(strips[0])
        check("first strip = 30 % of 2000 px (+ overlap)", 600 <= w <= 650 and h <= 1280 + 60, f"{w}x{h}")

    r = run(tmp, "files", image, "--columns", "0.5,0.3")
    check("decreasing boundaries refused", r.returncode != 0 and "increasing" in (r.stderr + r.stdout), r.stderr)
    r = run(tmp, "files", image, "--columns", "1")
    check("1 strip refused", r.returncode != 0, r.stderr)
    r = run(tmp, "aron", "x", "1", "9", "--columns", "3")
    check("more than 4 images from an archive refused (downloads nothing)", r.returncode != 0 and "at most 4" in (r.stderr + r.stdout),
          r.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(RESULTS)}/{len(RESULTS)} fine")
sys.exit(0 if all(RESULTS) else 1)
