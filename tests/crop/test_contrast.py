"""Test of the --contrast switch in crop.py and verify.py (faded images).

From the repository root:
  python3 -I tests/crop/test_contrast.py skills/genealogy/tools
  (Windows: python -I -X utf8 …)
Each case builds a temporary project with an invented faded image (light grey ink on grey paper), copies the tool
into it and runs it. Downloads nothing; needs ImageMagick (magick, or convert of ImageMagick 6).
"""
import glob, os, shutil, subprocess, sys, tempfile

TOOLS = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy/tools")
PY = [sys.executable, "-I", "-X", "utf8"]
MAGICK = shutil.which("magick") or next(iter(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe")), None) or "convert"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(("OK   " if ok else "FAIL ") + name + ("" if ok else f"\n    {detail}"))


def spread(f):
    """Standard deviation of brightness (0..1) – small for a faded image, larger after raising the contrast."""
    out = subprocess.run([MAGICK, f, "-colorspace", "gray", "-format", "%[fx:standard_deviation]", "info:"],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def project():
    tmp = tempfile.mkdtemp(prefix="crop_contrast_")
    os.makedirs(os.path.join(tmp, "tools"))
    for n in ("crop.py", "verify.py"):
        shutil.copy(os.path.join(TOOLS, n), os.path.join(tmp, "tools", n))
    os.makedirs(os.path.join(tmp, "work"))
    image = os.path.join(tmp, "work", "faded.jpg")
    # A faded "record": paper 85 % grey, ink strokes 70 % – a difference like in a faded register (no fonts, only lines).
    strokes = []
    for y in range(150, 800, 90):
        for x in range(80, 1100, 60):
            strokes += ["-draw", f"line {x},{y} {x + 35},{y - 45}"]
    subprocess.run([MAGICK, "-size", "1200x900", "xc:gray85", "-stroke", "gray70", "-strokewidth", "5", *strokes, image],
                   check=True)
    return tmp, image


def run(tmp, *args):
    return subprocess.run(PY + list(args), cwd=tmp, capture_output=True, text=True)


# crop.py without the switch: the crop stays as faded as the original
tmp, image = project()
try:
    r = run(tmp, "tools/crop.py", image, "base", "0,0,1,1")
    src = os.path.join(tmp, "sources", "base.jpg")
    check("crop.py without --contrast saves the crop", r.returncode == 0 and os.path.exists(src), r.stderr)
    s_base = spread(src) if os.path.exists(src) else 0

    # crop.py with the switch after the area: sources/ and crops/ have higher contrast
    r = run(tmp, "tools/crop.py", image, "contrast", "0,0,1,1", "--contrast")
    src, web = (os.path.join(tmp, d, "contrast.jpg") for d in ("sources", "crops"))
    ok = r.returncode == 0 and os.path.exists(src) and os.path.exists(web)
    check("crop.py --contrast saves the crop", ok, r.stderr)
    if ok:
        check("crop.py --contrast raises the contrast in sources/", spread(src) > 2 * s_base,
              f"spread {spread(src):.3f} vs. without the switch {s_base:.3f}")
        check("crop.py --contrast raises the contrast in crops/ too (web)", spread(web) > 2 * s_base,
              f"spread {spread(web):.3f} vs. without the switch {s_base:.3f}")

    # switch without an area (whole page) and before the other arguments
    r = run(tmp, "tools/crop.py", "--contrast", image, "whole")
    src = os.path.join(tmp, "sources", "whole.jpg")
    check("crop.py --contrast without an area (whole page)",
          r.returncode == 0 and os.path.exists(src) and spread(src) > 2 * s_base, r.stderr)

    # pixels instead of fractions: refused, nothing saved
    r = run(tmp, "tools/crop.py", image, "pixels", "10,20,300,400")
    check("crop.py refuses pixel coordinates", r.returncode != 0 and not os.path.exists(os.path.join(tmp, "sources", "pixels.jpg")),
          r.stdout + r.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# verify.py: both halves with higher contrast
tmp, image = project()
try:
    pre_b, pre_c = (os.path.join(tmp, "work", "verify", n) for n in ("b", "c"))
    r0 = run(tmp, "tools/verify.py", image, "0,0,1,1", pre_b)
    r1 = run(tmp, "tools/verify.py", image, "0,0,1,1", pre_c, "--contrast")
    ok = r0.returncode == 0 and r1.returncode == 0 and all(os.path.exists(f"{p}_{i}.jpg") for p in (pre_b, pre_c) for i in (0, 1))
    check("verify.py --contrast saves both halves", ok, r0.stderr + r1.stderr)
    if ok:
        check("verify.py --contrast raises the contrast",
              all(spread(f"{pre_c}_{i}.jpg") > 2 * spread(f"{pre_b}_{i}.jpg") for i in (0, 1)))
    r2 = run(tmp, "tools/verify.py", image, "0,0,1,1", pre_c + "v", "v", "--contrast")
    check("verify.py --contrast together with a horizontal split (v)",
          r2.returncode == 0 and os.path.exists(pre_c + "v_1.jpg"), r2.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(RESULTS)} of {len(RESULTS)} correct")
sys.exit(0 if all(RESULTS) else 1)
