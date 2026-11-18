#!/usr/bin/env python3
"""Highlight frame – which part of the crop we are reading (data/highlights.json).

Usage:
  frame.py <key> x0,y0,x1,y1 [x0,y0,x1,y1 ...] [--note "note"]
      coordinates are fractions of the width and height of the image crops/<key>.jpg (0..1)
      Writes the frame and creates a check image work/frame_<key>.jpg – ALWAYS look at it to see
      whether the frame really encloses the whole record being read (name, dates, parents, margin notes).
  frame.py <key> --preview      only re-creates the check image
"""
import glob, json, os, shutil, subprocess, sys
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "highlights.json")


def magick():
    """Path to ImageMagick; if it is missing, stop right away with a clear message."""
    m = (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
         or (os.name != "nt" and shutil.which("convert")))   # ImageMagick 6 has no magick; on Windows convert.exe is another program
    if not m:
        sys.exit("ImageMagick is missing (command magick). Install it (macOS: brew install imagemagick, "
                 "Windows: winget install ImageMagick.ImageMagick and restart Claude Code) and run the tool again.")
    return m


def preview(key, boxes):
    MAGICK = magick()
    src = os.path.join(ROOT, "crops", key + ".jpg")
    out = os.path.join(ROOT, "work", f"frame_{key}.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    w, h = (int(v) for v in subprocess.run([MAGICK, src + "[0]", "-format", "%w %h", "info:"],
                                            capture_output=True, text=True, check=True).stdout.split())
    cmd = [MAGICK, src, "-fill", "none", "-stroke", "#d7302a", "-strokewidth", str(max(3, w // 400))]
    for x0, y0, x1, y1 in boxes:
        cmd += ["-draw", f"rectangle {x0 * w:.0f},{y0 * h:.0f},{x1 * w:.0f},{y1 * h:.0f}"]
    subprocess.run(cmd + [out], check=True)
    return out


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    key = sys.argv[1]
    magick()   # without ImageMagick stop before the frame is written
    if not os.path.exists(os.path.join(ROOT, "crops", key + ".jpg")):   # the frame is drawn into the crop – crop first
        sys.exit(f"Crop crops/{key}.jpg is missing – make it first (tools/crop.py), then the frame. Nothing was written.")
    data = json.load(open(PATH, encoding="utf-8-sig")) if os.path.exists(PATH) else {}
    if sys.argv[2] == "--preview":
        print(preview(key, data.get(key, {}).get("boxes", [])))
        return
    args, note = sys.argv[2:], ""
    if "--note" in args:
        i = args.index("--note")
        if i + 1 >= len(args):
            sys.exit('--note needs a text, e.g. --note "right margin illegible"')
        note = args[i + 1]
        args = args[:i] + args[i + 2:]
    try:
        boxes = [[round(float(v), 3) for v in a.split(",")] for a in args]
    except ValueError:
        sys.exit(f"Frames must be numbers x0,y0,x1,y1 (fractions 0..1, decimal point), not {' '.join(args)}")
    if not boxes:
        sys.exit(__doc__)
    for b in boxes:
        if len(b) != 4 or not (0 <= b[0] < b[2] <= 1 and 0 <= b[1] < b[3] <= 1):
            sys.exit(f"Bad frame {b}: must be x0,y0,x1,y1 in the range 0..1 with x0<x1, y0<y1")
    data[key] = dict(boxes=boxes, status="ok", note=note)
    json.dump(data, open(PATH, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print("written; check it:", preview(key, boxes))


if __name__ == "__main__":
    main()
