#!/usr/bin/env python3
"""Variants of a hard-to-read image or crop side by side – for reading faded and stained entries.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: ImageMagick 6 (convert/identify) and
7 (magick), output into work/ in the project root, plus the variants "downscaled" and "showthrough" and the --strips
mode (from a strip-by-strip workflow that gave the best results on faded 17th-century pages).

Usage (from the project root):
  python3 -I tools/enhance.py <image.jpg> [x0,y0,x1,y1] [options]
      x0..y1 = optional crop as fractions of width and height (0..1), as with crop.py.
      Creates work/<name>_<variant>.jpg and a summary picture <name>_variants.jpg (grid with labels).
  python3 -I tools/enhance.py <image.jpg> [x0,y0,x1,y1] --strips N [--level 78]
      "Strips" mode: cuts the crop into N horizontal strips overlapping by 70 px and enhances each by division by
      the background from a downscaled copy; work/<name>_strip_<i>.jpg, 1900 px wide. Read strip by strip, line by line.
Options:
  --enlarge 2        enlarge the crop (Lanczos) – small script
  --output <file>    name of the summary picture (default work/<name>_variants.jpg)
  --level 78         lower -level bound for "downscaled" and --strips in % (76–84 %; higher = lighter background,
                     thinner strokes)
  --only a,b         only selected variants (e.g. --only downscaled,showthrough)

Variants (each brings out different strokes – read from all and note in the transcription which one you used):
  original     – greyscale only,
  contrast     – contrast stretch (microfilm, faded overall),
  clahe        – local contrast (unevenly faded page, dark margins); ImageMagick without -clahe
                 (6 from MacPorts) uses -local-contrast 30x60,
  background   – background removed: division by a blurred copy at full resolution (yellowing, stains),
  downscaled   – USUALLY THE BEST: grey, light denoising (blur 0x1.3), division by the background computed on a 10 %
                 downscaled copy (blur 0x4, back to full size), -level 78 %,100 %. Faded ink on stained paper.
  showthrough  – no division: blur 0x1, -level 22 %,60 %, gamma 1.2 – when the reverse side shows through: division by
                 the background would also enhance the text bleeding through from the other side,
  channel      – the darkest colour channel of the ink with raised gamma (colour images only; greyscale scans gain nothing).
The tool deliberately does no edge detection or black-and-white thresholding: it doubles or erases the hairline
strokes of old cursive scripts.
The tool downloads nothing (it works with a file on disk). It does not write into data/.
"""
import glob, os, shutil, subprocess, sys
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERLAP = 70        # px overlap of strips (no line is lost at a boundary)
STRIP_WIDTH = 1900


def imagemagick():
    """(convert, identify) as argument lists: ImageMagick 7 "magick", otherwise 6 "convert" + "identify"
    (also from MacPorts /opt/local/bin when it is not in PATH)."""
    path = os.environ.get("PATH", "") + os.pathsep + os.pathsep.join(("/opt/local/bin", "/usr/local/bin", "/opt/homebrew/bin"))
    m = shutil.which("magick", path=path) or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
    if m:
        return [m], [m, "identify"]
    c, i = shutil.which("convert", path=path), shutil.which("identify", path=path)
    if c and i and os.name != "nt":   # on Windows convert.exe is a different program (disk conversion)
        return [c], [i]
    sys.exit("ImageMagick is missing (magick, or convert + identify). macOS: brew install imagemagick (or MacPorts: "
             "sudo port install ImageMagick), Windows: winget install ImageMagick.ImageMagick, Linux: the imagemagick package.")


def dimensions(ident, f):
    w, h = (int(v) for v in subprocess.run([*ident, "-format", "%w %h", f + "[0]"],
                                            capture_output=True, text=True, check=True).stdout.split())
    return w, h


def variants(w, h, level):
    """ImageMagick operations; w, h = image size after crop and enlargement (to scale the downscaled copy back)."""
    return {
        "original": ["-colorspace", "Gray"],
        "contrast": ["-colorspace", "Gray", "-contrast-stretch", "2%x30%"],
        "clahe": ["-colorspace", "Gray", "-clahe", "12x12%+128+3"],
        "background": ["-colorspace", "Gray", "(", "+clone", "-blur", "0x25", ")", "-compose", "Divide_Src", "-composite",
                       "-contrast-stretch", "1%x5%"],
        "downscaled": downscaled(w, h, level),
        "showthrough": ["-colorspace", "Gray", "-blur", "0x1", "-level", "22%,60%", "-gamma", "1.2"],
        # blue channel: yellow and brown paper tones come out much as in grey, but red/green stains and stamps
        # get lighter; gamma < 1 darkens faint strokes
        "channel": ["-colorspace", "sRGB", "-type", "TrueColor", "-channel", "B", "-separate", "+channel", "-gamma", "0.7",
                    "-contrast-stretch", "1%x10%"],
    }


def downscaled(w, h, level):
    """Division by the background from a downscaled copy: fast and cleanest on stained paper."""
    return ["-colorspace", "Gray", "-blur", "0x1.3",
            "(", "+clone", "-resize", "10%", "-blur", "0x4", "-resize", f"{w}x{h}!", ")",
            "-compose", "Divide_Src", "-composite", "-level", f"{level:g}%,100%"]


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    src = a.pop(0)
    if not os.path.isfile(src):
        sys.exit(f"File {src} does not exist.")
    box, enlarge, out, strips, level, only = None, 1.0, None, 0, 78.0, None
    try:
        while a:
            x = a.pop(0)
            if x == "--enlarge":
                enlarge = float(a.pop(0))
            elif x == "--output":
                out = a.pop(0)
            elif x == "--strips":
                strips = int(a.pop(0))
            elif x == "--level":
                level = float(a.pop(0))
            elif x == "--only":
                only = [v.strip() for v in a.pop(0).split(",") if v.strip()]
            else:
                box = [float(v) for v in x.split(",")]
                if len(box) != 4 or not all(0 <= v <= 1 for v in box) or box[0] >= box[2] or box[1] >= box[3]:
                    sys.exit("Give the crop as x0,y0,x1,y1 in fractions 0..1 (x0<x1, y0<y1).")
    except (IndexError, ValueError):
        sys.exit("Invalid option – see python3 -I tools/enhance.py --help")
    conv, ident = imagemagick()
    base = os.path.join(ROOT, "work", os.path.splitext(os.path.basename(src))[0])
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    W, H = dimensions(ident, src)
    x0, y0, x1, y1 = box or (0, 0, 1, 1)
    cw, ch, cx, cy = int((x1 - x0) * W), int((y1 - y0) * H), int(x0 * W), int(y0 * H)

    if strips:   # strips mode: N horizontal strips of the crop, each divided by the background from a downscaled copy
        if strips < 1 or strips > 40:
            sys.exit("--strips: 1 to 40")
        ph = ch // strips + OVERLAP
        results = []
        for i in range(strips):
            y = cy + i * ch // strips
            h = min(ph, cy + ch - y)
            f = f"{base}_strip_{i}.jpg"
            subprocess.run([*conv, src + "[0]", "-crop", f"{cw}x{h}+{cx}+{y}", "+repage", *downscaled(cw, h, level),
                            "-resize", f"{STRIP_WIDTH}x", "-quality", "92", f], check=True)
            results.append(f)
        print(f"{strips} strips (division by the background from a downscaled copy, level {level:g} %, width {STRIP_WIDTH} px):")
        for f in results:
            print(" ", os.path.relpath(f, os.getcwd()))
        return 0

    pre = [src + "[0]"]
    if box:
        pre += ["-crop", f"{cw}x{ch}+{cx}+{cy}", "+repage"]
    if enlarge != 1:
        pre += ["-filter", "Lanczos", "-resize", f"{enlarge * 100:g}%"]
    w, h = round(cw * enlarge), round(ch * enlarge)
    V = variants(w, h, level)
    if only:
        unknown = [v for v in only if v not in V]
        if unknown:
            sys.exit(f"Unknown variant {', '.join(unknown)} – available: {', '.join(V)}")
        V = {k: V[k] for k in only}
    files = []
    for name, ops in V.items():
        f = f"{base}_{name}.jpg"
        r = subprocess.run([*conv, *pre, *ops, "-quality", "92", f], capture_output=True, text=True)
        if r.returncode and name == "clahe":   # ImageMagick 6 from MacPorts does not know -clahe: local contrast differently
            r = subprocess.run([*conv, *pre, "-colorspace", "Gray", "-local-contrast", "30x60", "-quality", "92", f],
                               capture_output=True, text=True)
        if r.returncode:
            print(f"  {name}: failed ({(r.stderr.strip().splitlines() or ['?'])[-1]})", file=sys.stderr)
            continue
        files.append((name, f))
    if not files:
        sys.exit("No variant was made.")
    out = out or f"{base}_variants.jpg"
    direction = "+append" if h > w else "-append"   # narrow column -> side by side, wide row -> stacked
    font = next((p for p in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
                             r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
                 if os.path.exists(p)), None)
    for labels in (True, False):   # without a usable font (Ghostscript/fontconfig missing) at least without labels
        cmd = [*conv]
        for name, f in files:
            cmd += ["(", f, "-gravity", "North", "-background", "white", "-splice", "0x40"]
            cmd += (["-font", font] if font else []) + ["-pointsize", "28", "-annotate", "+0+6", name] if labels else []
            cmd += [")"]
        cmd += ["-gravity", "Center", "-background", "white", direction, "-quality", "90", out]
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            break
    else:
        sys.exit("The summary picture could not be assembled; the individual variants are listed below.")
    if not labels:
        print("(labels missing – ImageMagick found no font; order top-down/left-right: " + ", ".join(n for n, _ in files) + ")")
    print(os.path.relpath(out, os.getcwd()))
    for name, f in files:
        print(f"  {name}: {os.path.relpath(f, os.getcwd())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
