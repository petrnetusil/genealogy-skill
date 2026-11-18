#!/usr/bin/env python3
"""Book map and column montage – quick orientation in a book without downloading whole images
(reference/registers.md, "Books arranged by village").

Usage (from the project root):
  book_map.py <archive> <book> <from> <to> [step] [options]
    archive  = a portal with an image tool: aron (book = apu_id), pf (Porta fontium, book as for portafontium.py),
               ahmp (book = XID) – see the country guide
    from, to = range of images, step = every n-th image (default 10)
  book_map.py files <image> [<image> …] [options]   -> the same from images you already have (also screenshots) –
                                                       works for any archive or country

Options:
  --crop x0,y0,x1,y1   part of the image (fractions 0–1); default 0,0,1,0.15 = top strip with the village name and year
  --side-by-side       crops side by side (a column of names from several images), otherwise stacked (book map)
  --sharp              higher resolution (column of names, small script); the default is a preview
  --columns N          index by columns: cuts every image (or its --crop, e.g. one page of a double page) at full
                       resolution into N equal vertical strips; instead of N also boundaries "0.3,0.55,0.8" (fractions
                       of the crop width, e.g. parent – name – year – folio). A strip longer than 1500 px is split into
                       overlapping parts so that no line is lost. At most 4 images, default step 1.
  -o <output.jpg>      default work/book_map_<archive>_<book>_<from>-<to>.jpg

Every crop is labelled with its image number. Book map: the year and village in the header show the sections and the
order of years; then read only the wanted village's section at full resolution. Column montage: --side-by-side,
step 1, a crop of the column with names (at least 35 % of the page width), 4–8 images.
Columns: read each strip separately, top to bottom, line by line – do not rely on a negative result ("not in the
index") from a whole double page. Decorative capitals (Š written as "St"/"Sſt", W instead of V) sort names
elsewhere than you expect.
A big map is split into several pictures (15 crops stacked, 6 side by side). Downloads through the archive tools and
the brake (tools/polite.py) – download only the range you need.
"""
import glob, os, re, shutil, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
PART_HEIGHT = 1500  # columns: tallest part of a strip in px (Claude scales larger ones down and small script is lost)
OVERLAP = 80        # columns: overlap of parts and strips in px
PER_IMAGE = 15      # crops stacked per picture (Claude cannot read more)
SIDE = 6            # crops side by side per picture


def magick():
    m = (shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))), None)
         or (os.name != "nt" and shutil.which("convert")))   # ImageMagick 6 has no magick; on Windows convert.exe is a different program
    if not m:
        sys.exit("ImageMagick is missing (command magick). Install it (macOS: brew install imagemagick, "
                 "Windows: winget install ImageMagick.ImageMagick and restart Claude Code) and run the tool again.")
    return m


def font():
    """Font file for the image numbers (ImageMagick from Homebrew has no default font); None = no labels possible."""
    for pattern in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
                 "/System/Library/Fonts/Helvetica.ttc", r"C:\Windows\Fonts\arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/**/DejaVuSans.ttf",
                 "/usr/share/fonts/**/*.ttf"):
        f = next(iter(sorted(glob.glob(pattern, recursive=True))), None)
        if f:
            return f
    return None


FONT = font()


def fetch(archive, book, n, crop, sharp, out):
    """Crop of image n with the archive's tool (through its brake). Returns True when the picture was made."""
    v = ",".join(f"{x:g}" for x in crop)
    if archive == "aron":
        cmd = ["aron_img.py", book, str(n), "1" if sharp else "2", out, v]
    elif archive == "pf":
        cmd = ["portafontium.py", "image", book, str(n), out, v] + ([] if sharp else ["preview"])
    elif archive == "ahmp":
        cmd = ["ahmp_scan.py", book, str(n), out, "1" if sharp else "2", v]
    else:
        sys.exit(f"unknown archive \"{archive}\" – aron, pf, ahmp or files")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(TOOLS, cmd[0]), *cmd[1:]],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 3:   # brake: the archive stopped us – download nothing more
        sys.stderr.write(r.stderr)
        sys.exit(3)
    if r.returncode or not os.path.exists(out):
        error = (r.stderr.strip().splitlines() or r.stdout.strip().splitlines() or ["?"])[-1]
        print(f"  image {n}: failed ({error})", file=sys.stderr)
        return False
    return True


def label(M, src, n, crop, side, out):
    """Crop (for files it crops itself) and add the image number: on the left when stacked, on top side by side."""
    args = [M, src + "[0]"]
    if crop:
        r = subprocess.run([M, src + "[0]", "-format", "%w %h", "info:"], capture_output=True, text=True)
        try:
            W, H = map(int, r.stdout.split())
        except ValueError:
            print(f"  {src}: not an image", file=sys.stderr)
            return False
        x0, y0, x1, y1 = crop
        args += ["-crop", f"{round((x1 - x0) * W)}x{round((y1 - y0) * H)}+{round(x0 * W)}+{round(y0 * H)}", "+repage"]
    args += ["-resize", "1600x>", "-background", "white", "-fill", "#B00000", "-pointsize", "40"]
    args += ["-font", FONT] if FONT else []
    if not FONT:   # without a font at least a margin; main() prints the order of the crops
        args += ["-gravity", "West", "-splice", "8x0"]
    elif side:
        args += ["-gravity", "North", "-splice", "0x56", "-annotate", "+0+6", f"img. {n}"]
    else:
        args += ["-gravity", "West", "-splice", "170x0", "-annotate", "+12+0", f"img. {n}"]
    args += ["-bordercolor", "#888", "-border", "2", out]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        print(f"  image {n}: ImageMagick failed ({(r.stderr.strip().splitlines() or ['?'])[-1]})", file=sys.stderr)
    return r.returncode == 0


def column_bounds(text):
    """"4" -> 4 equal strips; "0.3,0.55,0.8" -> inner boundaries (fractions 0–1). Returns the boundaries incl. 0 and 1."""
    try:
        if "," not in text and "." not in text:
            n = int(text)
            if not 2 <= n <= 12:
                raise ValueError
            return [k / n for k in range(n + 1)]
        h = [float(v) for v in text.split(",")]
    except ValueError:
        sys.exit(f"--columns \"{text}\": number of strips 2–12, or boundaries as fractions 0–1 (\"0.3,0.55,0.8\")")
    if not all(0 < x < 1 for x in h) or h != sorted(set(h)):
        sys.exit(f"--columns \"{text}\": the boundaries must be increasing fractions between 0 and 1")
    return [0.0] + h + [1.0]


def cut(M, src, n, crop, bounds, stem):
    """Cut the image (for files first the crop) into vertical strips at full resolution, long strips into overlapping
    parts. Returns a list of (file, label)."""
    r = subprocess.run([M, src + "[0]", "-format", "%w %h", "info:"], capture_output=True, text=True)
    try:
        W, H = map(int, r.stdout.split())
    except ValueError:
        print(f"  {src}: not an image", file=sys.stderr)
        return []
    x0, y0, x1, y1 = crop or (0, 0, 1, 1)
    ox, oy, w, h = round(x0 * W), round(y0 * H), round((x1 - x0) * W), round((y1 - y0) * H)
    parts = max(1, -(-(h - OVERLAP) // (PART_HEIGHT - OVERLAP)))
    height = -(-(h + (parts - 1) * OVERLAP) // parts)
    result = []
    for k in range(len(bounds) - 1):
        a = max(0, round(bounds[k] * w) - (OVERLAP // 2 if k else 0))
        b = min(w, round(bounds[k + 1] * w) + (OVERLAP // 2 if k < len(bounds) - 2 else 0))
        for d in range(parts):
            top = min(d * (height - OVERLAP), max(0, h - height))
            caption = f"img. {n} · column {k + 1}/{len(bounds) - 1}" + (f" · part {d + 1}/{parts}" if parts > 1 else "")
            target = f"{stem}_sn{n}_s{k + 1}" + (f"_{d + 1}" if parts > 1 else "") + ".jpg"
            args = [M, src + "[0]", "-crop", f"{b - a}x{min(height, h)}+{ox + a}+{oy + top}", "+repage",
                    "-background", "white", "-fill", "#B00000", "-pointsize", "32"]
            if FONT:
                args += ["-font", FONT, "-gravity", "North", "-splice", "0x48", "-annotate", "+0+6", caption]
            args += ["-quality", "92", target]
            r = subprocess.run(args, capture_output=True, text=True)
            if r.returncode:
                print(f"  {caption}: ImageMagick failed ({(r.stderr.strip().splitlines() or ['?'])[-1]})", file=sys.stderr)
            else:
                result.append((target, caption))
    return result


def main(a):
    if not a or a[0] in ("-h", "--help"):
        sys.exit(__doc__)
    crop, side, sharp, out, rest, columns = None, "--side-by-side" in a, "--sharp" in a, None, [], None
    i = 0
    while i < len(a):
        if a[i] == "--crop" and i + 1 < len(a):
            try:
                crop = tuple(float(v) for v in a[i + 1].split(","))
            except ValueError:
                crop = ()
            if len(crop) != 4 or not (0 <= crop[0] < crop[2] <= 1 and 0 <= crop[1] < crop[3] <= 1):
                sys.exit(f"--crop \"{a[i + 1]}\": give it as x0,y0,x1,y1 (fractions 0–1, x0 < x1, y0 < y1), not pixels")
            i += 2
        elif a[i] == "--columns" and i + 1 < len(a):
            columns, i = column_bounds(a[i + 1]), i + 2
        elif a[i] == "-o" and i + 1 < len(a):
            out, i = a[i + 1], i + 2
        elif a[i] in ("--side-by-side", "--sharp"):
            i += 1
        else:
            rest.append(a[i]); i += 1
    if not rest:
        sys.exit(__doc__)
    M = magick()
    if columns:
        return main_columns(M, rest, crop, columns, out)
    tmp = tempfile.mkdtemp(prefix="book_map_")
    try:
        pieces, numbers = [], []
        if rest[0] == "files":
            files = rest[1:]
            if not files:
                sys.exit("book_map.py files <image> [<image> …]")
            crop = crop or (0, 0, 1, 0.15)
            for j, f in enumerate(files):
                n = (re.findall(r"\d+", os.path.basename(f)) or [str(j + 1)])[-1]
                p = os.path.join(tmp, f"d{j:04d}.png")
                if label(M, f, n, crop, side, p):
                    pieces.append(p); numbers.append(n)
            name = "files"
        else:
            if len(rest) < 4:
                sys.exit(__doc__)
            archive, book = rest[0], rest[1]
            try:
                start, end = int(rest[2]), int(rest[3])
                step = int(rest[4]) if len(rest) > 4 else 10
            except ValueError:
                sys.exit("from, to and step are image numbers")
            if start > end or step < 1:
                sys.exit("range: from ≤ to, step at least 1")
            images = list(range(start, end + 1, step))
            if len(images) > 60:
                sys.exit(f"{len(images)} images is too many – increase the step or narrow the range (spare the archive)")
            crop = crop or (0, 0, 1, 0.15)
            print(f"downloading {len(images)} crops ({archive} {book}, images {start}–{end} every {step}) …", file=sys.stderr)
            for n in images:
                s = os.path.join(tmp, f"s{n:05d}.jpg")
                p = os.path.join(tmp, f"d{n:05d}.png")
                if fetch(archive, book, n, crop, sharp, s) and label(M, s, n, None, side, p):
                    pieces.append(p); numbers.append(n)
            name = f"{archive}_{re.sub(r'[^A-Za-z0-9-]', '', book)[:24]}_{start}-{end}"
        if not pieces:
            sys.exit("no crop was made")
        out = out or os.path.join(ROOT, "work", f"book_map_{name}.jpg")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        per = SIDE if side else PER_IMAGE
        groups = [(pieces[k:k + per], numbers[k:k + per]) for k in range(0, len(pieces), per)]
        stem, ext = os.path.splitext(out)
        for k, (grp, nums) in enumerate(groups):
            target = out if len(groups) == 1 else f"{stem}_{k + 1}{ext or '.jpg'}"
            subprocess.run([M, *grp, "-background", "white", "+append" if side else "-append", "-quality", "85", target], check=True)
            print(target, "– images", ", ".join(map(str, nums)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main_columns(M, rest, crop, bounds, out):
    """Index by columns: full resolution, every strip as a separate picture."""
    tmp = tempfile.mkdtemp(prefix="columns_")
    try:
        if rest[0] == "files":
            files = rest[1:]
            if not files:
                sys.exit("book_map.py files <image> [<image> …] --columns N")
            images = [((re.findall(r"\d+", os.path.basename(f)) or [str(j + 1)])[-1], f, crop)
                      for j, f in enumerate(files)]
            name = re.sub(r"[^A-Za-z0-9-]", "", os.path.splitext(os.path.basename(files[0]))[0])[:30] or "files"
        else:
            if len(rest) < 4:
                sys.exit(__doc__)
            archive, book = rest[0], rest[1]
            try:
                start, end = int(rest[2]), int(rest[3])
                step = int(rest[4]) if len(rest) > 4 else 1
            except ValueError:
                sys.exit("from, to and step are image numbers")
            if start > end or step < 1:
                sys.exit("range: from ≤ to, step at least 1")
            numbers = list(range(start, end + 1, step))
            if len(numbers) > 4:
                sys.exit(f"--columns: {len(numbers)} images is too many – at most 4 (each gives several full-resolution pictures)")
            images = []
            for n in numbers:
                s = os.path.join(tmp, f"s{n:05d}.jpg")
                if fetch(archive, book, n, crop or (0, 0, 1, 1), True, s):
                    images.append((n, s, None))   # the archive tool already made the crop
            name = f"{archive}_{re.sub(r'[^A-Za-z0-9-]', '', book)[:24]}"
        out = out or os.path.join(ROOT, "work", f"columns_{name}.jpg")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        stem = os.path.splitext(out)[0]
        everything = []
        for n, f, v in images:
            everything += cut(M, f, n, v, bounds, stem)
        if not everything:
            sys.exit("no strip was made")
        for target, caption in everything:
            print(target, "–", caption)
        print("Read each strip separately, line by line; write \"not in the index\" only after reading all strips.",
              file=sys.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1:])
