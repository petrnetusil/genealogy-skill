#!/usr/bin/env python3
"""Crop a record out of a downloaded page image (from any portal).

Usage:
  crop.py <image.jpg> <key> [x0,y0,x1,y1] [--contrast]
      x0..y1 = the record's area as fractions of the page width and height (0..1); without them the whole page is used.
      Saves sources/<key>.jpg (full resolution) and crops/<key>.jpg (scaled down to max. 1800 px for the website).
      --contrast = faded record: greyscale, paper whitened and ink darkened (in both sources/ and crops/).

Crop generously: the whole record including column headers, margin notes and signatures.
Needs ImageMagick (`magick`, or `convert` of ImageMagick 6).
"""
import glob, os, shutil, subprocess, sys
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Faded images: the brightest 35 % of pixels (paper) go to white, the darkest 2 % to black. It follows the brightness
# distribution, so it also works next to dark printed lines (a fixed -level would barely change the ink there).
CONTRAST = ["-colorspace", "Gray", "-contrast-stretch", "2%x35%"]


def magick():
    """Path to ImageMagick; if it is missing, stop right away (before any download) with a clear message."""
    m = (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
         or (os.name != "nt" and shutil.which("convert")))   # ImageMagick 6 has no magick; on Windows convert.exe is another program
    if not m:
        sys.exit("ImageMagick is missing (command magick). Install it (macOS: brew install imagemagick, "
                 "Windows: winget install ImageMagick.ImageMagick and restart Claude Code) and run the tool again.")
    return m


def main():
    contrast = "--contrast" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--contrast"]
    if len(args) < 2 or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    src, key = args[0], args[1]
    MAGICK = magick()
    full = os.path.join(ROOT, "sources", key + ".jpg")
    small = os.path.join(ROOT, "crops", key + ".jpg")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    os.makedirs(os.path.dirname(small), exist_ok=True)
    cmd = [MAGICK, src, "-auto-orient"]   # phone photos: rotate by EXIF (+profile then strips EXIF incl. GPS, the ICC colour profile stays)
    if len(args) > 2:
        try:
            x0, y0, x1, y1 = (float(v) for v in args[2].split(","))
        except ValueError:
            sys.exit(f"Area {args[2]} must be four numbers x0,y0,x1,y1 (fractions 0..1, decimal point).")
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):   # with pixels ImageMagick would only warn and save the whole page
            sys.exit(f"Area {args[2]} must be fractions 0..1 (x0 < x1, y0 < y1), not pixels – "
                     "e.g. 0.1,0.25,0.9,0.6 = from 10 % to 90 % of the width and from 25 % to 60 % of the height.")
        w, h = (int(v) for v in subprocess.run([MAGICK, src + "[0]", "-auto-orient", "-format", "%w %h", "info:"],
                                                capture_output=True, text=True, check=True).stdout.split())
        cmd += ["-crop", f"{round((x1 - x0) * w)}x{round((y1 - y0) * h)}+{round(x0 * w)}+{round(y0 * h)}", "+repage"]
    if contrast:
        cmd += CONTRAST
    subprocess.run(cmd + ["+profile", "!icc,*", "+set", "comment", "-quality", "90", full], check=True)
    subprocess.run([MAGICK, full, "-resize", "1800x1800>", "-quality", "85", small], check=True)
    print("saved:", full, "and", small, "(contrast raised – mention it in the transcript)" if contrast else "")


if __name__ == "__main__":
    main()
