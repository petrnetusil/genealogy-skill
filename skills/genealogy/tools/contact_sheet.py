#!/usr/bin/env python3
"""Contact sheet: a range of a book's images as several whole images in one picture – quick browsing of a book
without an index, finding a section, checking where a year starts.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: archives aron, pf, ahmp (MZA forbids
scripts – browser only), --year also without image_for_year in our book_map.py, ImageMagick 6 (convert).
Originally taken over and adapted from:
  https://github.com/xsigik/rodokmen-skill/blob/6a62def5e10ab169018282a124f033fe4280be71/skills/rodokmen/tools/nahledy.py
  (fork xsigik, change #10; later replaced by mapa_knihy.py in that fork, here both: book map = strips,
  contact sheet = whole images)
Licence: MIT (original © Jakub Valenta, xsigik; changes rodokmen-plus).

Usage (from the project root):
  contact_sheet.py <archive> <book> <from> <to> [options]
  contact_sheet.py <archive> <book> --year <volume key> <year> [options]   -> range from data/volumes.json → orientation.years
    archive = a portal with an image tool: aron | pf | ahmp (book as for book_map.py: aron = apu id, e.g. 1a0b2337-…)
  --year needs the field "orientation" with anchors {"years": {"1746": 104, …}} for the volume in data/volumes.json.
  For images you already have (any archive or country) use `book_map.py files …`.

Options:
  --crop x0,y0,x1,y1   only part of every image (fractions 0–1), e.g. the column with names 0,0,0.5,1
  --sharp              higher resolution (small script in the crop); the default is a preview
  --per N              images per picture (default 6, at most 12)
  --columns N          tiles side by side (default 3)
  --width PX           tile width (default 700)
  -o <folder>          default work/contact_sheets/

Creates <folder>/<archive>_<book>_<from>-<to>_<i>.jpg, every tile carries its image number, and prints the paths.
The images are downloaded by the archive tool (fetch() from book_map.py) through the shared cache tools/cache.py and
the brake tools/polite.py, one after another, without parallelism of its own. A second run takes the whole range
from disk. At most 60 images per run; go through a longer book in batches, systematically with a record of the images
read via tools/sieve.py.
"""
import json, os, re, shutil, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import book_map   # noqa: E402 – fetch() through the archive tools → cache.py → polite.py; magick(), FONT, image_for_year()

ROOT = os.path.dirname(TOOLS)
MAX_IMAGES = 60
ARCHIVES = ("aron", "pf", "ahmp")   # mza: MZA does not allow scripts since 2 Nov 2026 (polite.py)


def image_for_year(volume, year):
    """(from, to|None, note) from the anchors of the volume's orientation – from rodokmen-plus mapa_knihy.py (ours lacks it)."""
    if hasattr(book_map, "image_for_year"):
        return book_map.image_for_year(volume, year)
    o = volume.get("orientation")
    years = o.get("years") if isinstance(o, dict) else None
    if not years:
        if o:
            print(f"orientation of the volume (text): {o}", file=sys.stderr)
        return None
    anchors = sorted((int(r), int(s)) for r, s in years.items())
    before = [k for k in anchors if k[0] <= year]
    if not before:
        return None
    y0, start = before[-1]
    later = [s for r, s in anchors if r > year]
    end = later[0] - 1 if later else volume.get("images")
    note = "" if y0 == year else f"year {year} has no anchor of its own – start at the anchor {y0} and page forward"
    return start, end if end is None or end >= start else start, note


def year_range(volume, year, path=None):
    """(from, to) from the volume's orientation; to = end of the year (image before the next anchor), else +30 images."""
    path = path or os.path.join(ROOT, "data", "volumes.json")
    vols = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    if volume not in vols:
        sys.exit(f"volume \"{volume}\" is not in {path}")
    v = image_for_year(vols[volume], year)
    if not v:
        sys.exit(f"{volume}: the orientation has no anchor for a year ≤ {year} – make a book map (book_map.py) and add anchors")
    start, end, note = v
    if note:
        print(note, file=sys.stderr)
    return start, end or start + 29


def tile(M, src, n, width, out):
    cmd = [M, src + "[0]", "-resize", f"{width}x", "-background", "white", "-gravity", "North",
           "-splice", "0x48", "-fill", "#B00000", "-pointsize", "36"]
    cmd += ["-font", book_map.FONT] if book_map.FONT else []
    cmd += ["-annotate", "+0+4", f"img. {n}", "-bordercolor", "#888", "-border", "2", out]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def grid(M, pieces, columns, out):
    """Tiles in rows (columns side by side), rows stacked."""
    rows = []
    for k in range(0, len(pieces), columns):
        r = out + f".r{k}.png"
        subprocess.run([M, *pieces[k:k + columns], "-background", "white", "-gravity", "North", "+append", r], check=True)
        rows.append(r)
    subprocess.run([M, *rows, "-background", "white", "-append", "-quality", "85", out], check=True)
    for r in rows:
        os.remove(r)


def main(a):
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    options = {"--per": 6, "--columns": 3, "--width": 700}
    crop, sharp, outdir, year, rest = (0, 0, 1, 1), False, None, None, []
    i = 0
    while i < len(a):
        x = a[i]
        if x in options and i + 1 < len(a):
            options[x] = int(a[i + 1]); i += 2
        elif x == "--crop" and i + 1 < len(a):
            try:
                crop = tuple(float(v) for v in a[i + 1].split(","))
            except ValueError:
                crop = ()
            if len(crop) != 4 or not (0 <= crop[0] < crop[2] <= 1 and 0 <= crop[1] < crop[3] <= 1):
                sys.exit(f"--crop \"{a[i + 1]}\": give it as x0,y0,x1,y1 (fractions 0–1)")
            i += 2
        elif x == "--year" and i + 2 < len(a) and a[i + 2].isdigit():
            year = (a[i + 1], int(a[i + 2])); i += 3
        elif x == "--sharp":
            sharp = True; i += 1
        elif x == "-o" and i + 1 < len(a):
            outdir = a[i + 1]; i += 2
        else:
            rest.append(x); i += 1
    if len(rest) < 2 or rest[0] not in ARCHIVES:
        sys.exit(__doc__)
    archive, book = rest[0], rest[1]
    if year:
        start, end = year_range(*year)
    elif len(rest) == 4 and rest[2].isdigit() and rest[3].isdigit():
        start, end = int(rest[2]), int(rest[3])
    else:
        sys.exit("give the range <from> <to>, or --year <volume key> <year>")
    per, columns = max(1, min(options["--per"], 12)), max(1, options["--columns"])
    if start < 1 or start > end:
        sys.exit("range: 1 ≤ from ≤ to")
    if end - start + 1 > MAX_IMAGES:
        sys.exit(f"{end - start + 1} images is too many (at most {MAX_IMAGES}) – go through in batches (tools/sieve.py next)")
    M = book_map.magick()
    outdir = outdir or os.path.join(ROOT, "work", "contact_sheets")
    os.makedirs(outdir, exist_ok=True)
    name = f"{archive}_{re.sub(r'[^A-Za-z0-9-]', '', book)[:24]}_{start}-{end}"
    print(f"contact sheet {archive} {book}, images {start}–{end} …", file=sys.stderr)
    tmp = tempfile.mkdtemp(prefix="contact_sheet_")
    try:
        pieces, numbers = [], []
        for n in range(start, end + 1):
            s, d = os.path.join(tmp, f"s{n:05d}.jpg"), os.path.join(tmp, f"d{n:05d}.png")
            if book_map.fetch(archive, book, n, crop, sharp, s) and tile(M, s, n, options["--width"], d):
                pieces.append(d); numbers.append(n)
        if not pieces:
            sys.exit("no image was made")
        missing = sorted(set(range(start, end + 1)) - set(numbers))
        for k in range(0, len(pieces), per):
            target = os.path.join(outdir, f"{name}_{k // per + 1}.jpg")
            grid(M, pieces[k:k + per], columns, target)
            print(target, "– images", ", ".join(map(str, numbers[k:k + per])))
        if missing:
            print("missing images:", ", ".join(map(str, missing)), file=sys.stderr)
            sys.exit(2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1:])
