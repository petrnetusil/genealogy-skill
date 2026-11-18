#!/usr/bin/env python3
"""Ancestor fan chart (360°) from data/people.py as SVG.
Usage: fan_chart.py <out_dir>                         (poster: SVG + HTML with title and legend, PNG via Chrome if available)
       fan_chart.py <out_file.svg> --web <hrefs.json>  (bare clickable SVG for the website – called by export_web.py)"""
import html, itertools, json, math, os, re, subprocess, sys
if sys.argv[1:2] in (["-h"], ["--help"]):   # help instead of a crash
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):   # UTF-8 output even on Windows without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "output")
WEB = "--web" in sys.argv
HREFS = {int(k): v for k, v in json.load(open(sys.argv[sys.argv.index("--web") + 1])).items()} if WEB else {}
CHROME = next((c for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                           "C:/Program Files/Google/Chrome/Application/chrome.exe",
                           "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
                           "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
                           "google-chrome", "chromium", "chromium-browser")
               if os.path.exists(c) or __import__("shutil").which(c)), None)

ns = {}
exec(open(os.path.join(ROOT, "data", "people.py"), encoding="utf-8-sig").read(), ns)
P, LINES = ns["P"], ns.get("LINES", {})
WEBCFG = json.load(open(os.path.join(ROOT, "data", "website.json"), encoding="utf-8-sig")) if os.path.exists(os.path.join(ROOT, "data", "website.json")) else {}
# Names of placeholder people (an unnamed parent) – same list as in export_web.py and check.py
PLACEHOLDER_NAMES = ("father unknown", "mother unknown", "father not named", "mother not named",
                     "unknown father", "unknown mother")

W, H = (4520, 4520) if WEB else (4600, 5720)   # poster: +70 px for the legend row about repeated ancestors
CX, CY = (2260, 2260) if WEB else (W / 2, 2760)
RINGS = [(0, 240), (240, 440), (440, 650), (650, 880), (880, 1100), (1100, 1380),
         (1380, 1640), (1640, 1870), (1870, 2010), (2010, 2130), (2130, 2240)]
# warm tones of the lines; the fan fills are their lighter shades
BASE = {8: "#D49A3E", 9: "#CF6F52", 10: "#C46482", 11: "#8F7CC0",
        12: "#5E93C8", 13: "#4FA48F", 14: "#7FAA55", 15: "#B9A93E"}
LIGHT = {3: 0.12, 4: 0.26, 5: 0.37, 6: 0.47, 7: 0.56, 8: 0.63, 9: 0.7, 10: 0.76}
SIDE_COL = {0: "#E9D6B8", 1: "#CFDDEA"}          # father / mother half, generations 1–2
EMPTY, FONT = "#EEE9E1", "'Plus Jakarta Sans', 'Segoe UI', Helvetica, Arial, sans-serif"
MINF = {5: 15, 6: 13, 7: 11, 8: 9.5, 9: 8.5, 10: 7.5}
MAXF = {5: 26, 6: 22, 7: 18, 8: 14, 9: 11, 10: 9}


def mix(hex_, t):
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(round(c + (255 - c) * t) for c in (r, g, b))


CIRCA = re.compile(r"^(c\.|ca\.?|circa|about|abt\.?|≈|~)", re.I)


def years(y):
    """Short years: "1850–1910", "≈1720–1785", "* 1931", "† before 1743", "alive 1921" (like export_web.py)."""
    y = (y or "").strip()
    ys = re.findall(r"\d{4}", y)
    if not ys:
        return ""
    approx = "≈" if CIRCA.match(y) else ""
    head, dash, tail = y.partition("–")
    if y.startswith(("?", "†")) or (dash and not re.search(r"\d", head)) or re.match(r"after\b", y, re.I):
        # unknown birth: show only the death ("? – before 1743" → "† before 1743", "– after 1921" → "alive 1921")
        if re.search(r"\bafter\b", tail or y, re.I):
            return "alive " + ys[-1]
        return "† " + ("before " if re.search(r"\bbefore\b", y, re.I) else "") + ys[-1]
    if y.startswith("*"):
        return "* " + ys[0]
    if len(ys) == 1:
        return approx + ys[0] + ("–?" if dash else "")
    second = "?" if re.search(r"\bbefore\b", tail, re.I) else ("after " if re.search(r"\bafter\b", tail, re.I) else "") + \
        ("≈" if re.search(r"(\bc\.|\bca\b|circa|about|≈|~)", tail, re.I) else "") + ys[-1]
    return f"{approx}{ys[0]}–{second}"


def pt(r, a):
    t = math.radians(a)
    return CX + r * math.sin(t), CY - r * math.cos(t)


def sector(r0, r1, a0, a1):
    large = 1 if a1 - a0 > 180 else 0
    x0, y0 = pt(r1, a0); x1, y1 = pt(r1, a1); x2, y2 = pt(r0, a1); x3, y3 = pt(r0, a0)
    if r0 == 0:
        return f"M{CX},{CY} L{x0:.1f},{y0:.1f} A{r1},{r1} 0 {large} 1 {x1:.1f},{y1:.1f} Z"
    return (f"M{x0:.1f},{y0:.1f} A{r1},{r1} 0 {large} 1 {x1:.1f},{y1:.1f} "
            f"L{x2:.1f},{y2:.1f} A{r0},{r0} 0 {large} 0 {x3:.1f},{y3:.1f} Z")


def gen(k):
    return k.bit_length() - 1


# An ancestor several times in the tree (pedigree collapse, SAME = {alias: main number}).
# Merging of shared ancestors taken (MIT) from the fork vmi43 (Vaclav Miller), commit 5bd5904:
# https://github.com/vmi43/rodokmen-skill/blob/5bd59042d10714fe914bd6c48c54c7b065dd39ea/skills/rodokmen/tools/fan_chart.py
# and from the change in zbysekvoda/rodokmen-plus (Zbyšek Voda): siblings with the same parents (both via SAME) stand
# side by side and their parents get one double-width sector with a dashed outline; a repetition that cannot be merged
# is a hatched marker "↺ see no. N" up to the edge of the fan (the person is not drawn twice).
SAME = ns.get("SAME", {})
OWN = set(P) - set(SAME)   # people without repetitions – for the statistics


def canon(k):
    """Slot → canonical slot: an ancestor (and their whole branch above) found several times is taken from the main number (SAME)."""
    for j in range(gen(k) + 1):
        if (k >> j) in SAME:
            return canon((SAME[k >> j] << j) | (k & ((1 << j) - 1)))
    return k


def parents_of(k, flags):
    return (2 * k + 1, 2 * k) if flags.get(k) else (2 * k, 2 * k + 1)


def pos(k, flags):
    """Position of the slot in its ring (left to right) for the given flipping of parents."""
    g, idx = gen(k), 0
    for lev in range(1, g + 1):
        node = k >> (g - lev)
        idx = idx * 2 + ((node & 1) ^ (1 if flags.get(node >> 1) else 0))
    return idx


def sibling_pairs():
    """Pairs of slots (pa, pb) in the same ring whose parents are the same couple (SAME) – siblings."""
    out = set()
    for b, a in SAME.items():
        pa, pb = a // 2, b // 2
        if pa != pb and gen(pa) == gen(pb) and canon(pa) in P and canon(pb) in P \
                and canon(2 * pa) == canon(2 * pb) and canon(2 * pa + 1) == canon(2 * pb + 1):
            out.add((min(pa, pb), max(pa, pb)))
    return sorted(out)


def solve_flags():
    """Which parent pairs to flip (man ↔ woman) so that siblings stand side by side; as few flips as possible."""
    flags, locked = {}, set()
    for pa, pb in sibling_pairs():
        var, x, y = set(), pa, pb
        while x != y:
            x >>= 1; y >>= 1
            var |= {x, y}
        var.discard(1)
        free = sorted(var - locked)
        for r in range(min(len(free), 6) + 1):
            hit = next((c for c in itertools.combinations(free, r)
                        if abs(pos(pa, {**flags, **dict.fromkeys(c, True)}) - pos(pb, {**flags, **dict.fromkeys(c, True)})) == 1), None)
            if hit is not None:
                flags.update(dict.fromkeys(hit, True))
                locked |= var
                break
    return flags


def build_cells(flags):
    """Sectors per ring (angle as a fraction 0–1). Siblings side by side share their parents: those get double width
    (merged). A repeated ancestor that cannot be merged is a "repeat" sector without parents."""
    rings = {0: [dict(k=1, f0=0.0, f1=1.0)]}
    for g in range(0, len(RINGS) - 1):
        out, cells, i = [], rings[g], 0
        while i < len(cells):
            c = cells[i]; i += 1
            if c.get("repeat") or canon(c["k"]) not in P:
                continue
            k, nxt = c["k"], cells[i] if i < len(cells) else None
            f1, merged = c["f1"], False
            if (nxt and not nxt.get("repeat") and abs(c["f1"] - nxt["f0"]) < 1e-9 and canon(nxt["k"]) in P
                    and canon(2 * k) in P and canon(2 * k + 1) in P
                    and (canon(2 * k), canon(2 * k + 1)) == (canon(2 * nxt["k"]), canon(2 * nxt["k"] + 1))):
                f1, merged = nxt["f1"], True; i += 1
            half = (f1 - c["f0"]) / 2
            for j, pk in enumerate(parents_of(k, flags) if g else (2, 3)):
                cell = dict(k=pk, f0=c["f0"] + j * half, f1=c["f0"] + (j + 1) * half, merged=merged)
                if not merged and pk in SAME:
                    cell["repeat"] = canon(pk)
                out.append(cell)
        rings[g + 1] = out
    return [c for g in sorted(rings) for c in rings[g]]


def fill(k):
    g = gen(k); p = P.get(canon(k))
    if p is None or p.get("st") == "unk":
        return EMPTY
    if g == 0:
        return "#7A2E1C"
    if g <= 2:
        return SIDE_COL[(k >> (g - 1)) & 1]
    c = mix(BASE[k >> (g - 3)], LIGHT[g])
    return mix(c, 0.45) if p.get("st") in ("prob", "mh") else c


def fit(text, avail, fmax, fmin):
    return max(fmin, min(fmax, avail / (0.56 * max(len(text), 1))))


paths, defs, texts, links = [], [], [], []
REPEAT_COL = "#E7DFD2"   # hatching of a repeated ancestor in the warm tones of the fan
defs.append('<pattern id="fan-repeat" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="14" height="14" fill="{REPEAT_COL}"/><rect width="5" height="14" fill="#D6CAB6"/></pattern>')
n_merged = n_repeat = 0
for cell in build_cells(solve_flags()):   # the fan has 11 rings (generations 0–10); older ancestors are left out
    k = cell["k"]
    g = gen(k)
    r0, r1 = RINGS[g]
    a0, a1 = (0, 360) if g == 0 else (180 + cell["f0"] * 360, 180 + cell["f1"] * 360)
    ck = canon(k)
    if cell.get("repeat"):   # repeated ancestor: hatched marker up to the edge, without name and branch
        n_repeat += 1
        rr = RINGS[-1][1]
        d = sector(r0, rr, a0, a1)
        paths.append(f'<path class="fan-repeat" data-k="{k}" d="{d}" fill="url(#fan-repeat)" stroke="#9E7B56" stroke-width="2" '
                     f'stroke-dasharray="10 6" vector-effect="non-scaling-stroke"/>')
        p = P.get(ck, {})
        lab = f"↺ see no. {ck}"
        am, rm = (a0 + a1) / 2, (r0 + r1) / 2
        f1 = min(30, max(7, math.radians(a1 - a0) * rm / 1.4), (r1 - r0) / (0.56 * len(lab)) if g > 4 else 30)
        rot = am - 90 if (am % 360) < 180 else am + 90
        if g <= 4:
            rot = am if (am % 360) <= 90 or (am % 360) >= 270 else am + 180
        x, y = pt(rm, am)
        texts.append(f'<text transform="translate({x:.1f},{y:.1f}) rotate({rot:.2f})" y="{f1 * 0.35:.1f}" text-anchor="middle" '
                     f'font-size="{f1:.1f}" font-style="italic" font-weight="600" fill="#5A4632">{html.escape(lab)}</text>')
        if ck in HREFS:
            links.append(f'<a href="{HREFS[ck]}" class="fan-repeat-link" data-same="{ck}"><title>{html.escape(p.get("n", ""))} {html.escape(years(p.get("y")))} – '
                         f'in the tree a second time (relatives married relatives), branch see no. {ck}</title><path d="{d}"/></a>')
        continue
    if g == 0:
        paths.append(f'<circle cx="{CX}" cy="{CY}" r="{r1}" fill="{fill(k)}" stroke="#fff" stroke-width="3"/>')
    else:
        paths.append(f'<path d="{sector(r0, r1, a0, a1)}" fill="{fill(k)}" stroke="#F7F4EF" stroke-width="{3 if g < 6 else 1.6}"/>')
    p = P.get(ck)
    if cell.get("merged") and p:   # common parents of siblings: dashed outline = ancestor shared by two lines
        n_merged += 1
        paths.append(f'<path class="fan-merged" d="{sector(r0, r1, a0, a1)}" fill="none" stroke="#8B5E34" stroke-width="2.4" '
                     f'stroke-dasharray="9 6" vector-effect="non-scaling-stroke"/>')
    if not p:
        continue
    k = ck   # lines (LINES) and links by the main number
    name, yrs, st = p["n"], years(p.get("y")), p.get("st")
    if k in HREFS:
        shape = (f'<circle cx="{CX}" cy="{CY}" r="{r1}"/>' if g == 0 else f'<path d="{sector(r0, r1, a0, a1)}"/>')
        note = " (common ancestor of two lines – relatives married relatives)" if cell.get("merged") else ""
        links.append(f'<a href="{HREFS[k]}"><title>{html.escape(name)} {html.escape(yrs)}{note}</title>{shape}</a>')
    unknown = st == "unk"
    style = 'font-style="italic" fill="#8A8278"' if unknown else ('font-style="italic" fill="#2B2620"' if st in ("prob", "mh") else 'fill="#1F1A15"')
    if g == 0:
        texts.append(f'<text x="{CX}" y="{CY - 8}" text-anchor="middle" font-size="44" font-weight="700" fill="#FFF8EE">{html.escape(name)}</text>')
        texts.append(f'<text x="{CX}" y="{CY + 46}" text-anchor="middle" font-size="34" fill="#F1E3CF">{html.escape(yrs)}</text>')
        continue
    am = (a0 + a1) / 2
    if g <= 4:   # tangential text on arcs
        rm = (r0 + r1) / 2
        lines = []
        if g == 3 and k in LINES:
            lines.append((LINES[k][0].upper(), 21, 'font-weight="700" letter-spacing="4" fill="#5A4632"'))
        lines.append((name, {1: 40, 2: 34, 3: 30, 4: 27}[g], f'font-weight="600" {style}'))
        if yrs:
            lines.append((yrs, {1: 30, 2: 27, 3: 24, 4: 22}[g], f'{style}'))
        gap = [s * 1.25 for _, s, _ in lines]
        total = sum(gap)
        bottom = 90 < (am % 360) < 270
        # radii from outer to inner as read top-to-bottom
        cur = rm + total / 2
        order = []
        for (t, s, a), h in zip(lines, gap):
            cur -= h
            order.append((t, s, a, cur + h * 0.28))
        if bottom:   # read inner→outer, so reverse radii
            radii = [o[3] for o in order][::-1]
            order = [(t, s, a, r + s * 0.55) for (t, s, a, _), r in zip(order, radii)]
        for j, (t, s, a, r) in enumerate(order):
            pid = f"p{k}_{j}"
            pad = min(3.0, (a1 - a0) * 0.04)
            b0, b1 = a0 + pad, a1 - pad
            arc_len = math.radians(b1 - b0) * r
            s = min(s, arc_len / (0.56 * max(len(t), 1)))
            if bottom:
                xa, ya = pt(r, b1); xb, yb = pt(r, b0)
                d = f"M{xa:.1f},{ya:.1f} A{r:.1f},{r:.1f} 0 {1 if b1 - b0 > 180 else 0} 0 {xb:.1f},{yb:.1f}"
            else:
                xa, ya = pt(r, b0); xb, yb = pt(r, b1)
                d = f"M{xa:.1f},{ya:.1f} A{r:.1f},{r:.1f} 0 {1 if b1 - b0 > 180 else 0} 1 {xb:.1f},{yb:.1f}"
            defs.append(f'<path id="{pid}" d="{d}" fill="none"/>')
            texts.append(f'<text font-size="{s:.1f}" {a}><textPath href="#{pid}" startOffset="50%" text-anchor="middle">{html.escape(t)}</textPath></text>')
    else:        # radial text
        rm = (r0 + r1) / 2
        depth = (r1 - r0) - 22
        arc = math.radians(a1 - a0) * rm
        f1 = fit(name, depth, MAXF[g], MINF[g])
        f2 = fit(yrs, depth, MAXF[g] * 0.85, MINF[g] * 0.9) if yrs else 0
        two = yrs and arc >= (f1 + f2) * 1.15
        if not two:
            f1 = min(f1, arc / 1.25)
        rot = am - 90 if (am % 360) < 180 else am + 90
        x, y = pt(rm, am)
        tw = f'transform="translate({x:.1f},{y:.1f}) rotate({rot:.2f})"'
        if two:
            h = (f1 + f2) * 1.08
            texts.append(f'<g {tw}><text y="{-h / 2 + f1 * 0.85:.1f}" text-anchor="middle" font-size="{f1:.1f}" font-weight="600" {style}>{html.escape(name)}</text>'
                         f'<text y="{h / 2 - f2 * 0.15:.1f}" text-anchor="middle" font-size="{f2:.1f}" {style}>{html.escape(yrs)}</text></g>')
        else:
            texts.append(f'<g {tw}><text y="{f1 * 0.35:.1f}" text-anchor="middle" font-size="{f1:.1f}" font-weight="600" {style}>{html.escape(name)}</text></g>')

# statistics
known = [k for k in OWN if k > 1 and not P[k]["n"].lower().startswith(PLACEHOLDER_NAMES)]
doc = [k for k in known if P[k].get("st") == "doc"]
zpath = os.path.join(ROOT, "data", "records.json")
recs = json.load(open(zpath, encoding="utf-8-sig")) if os.path.exists(zpath) else []
maxg = max(gen(k) for k in P)

title = (f'<text x="{W / 2}" y="250" text-anchor="middle" font-family="Lora, Georgia, \'Times New Roman\', serif" font-size="128" fill="#1C1917">{html.escape(WEBCFG.get("title", "Family Tree"))}</text>'
         f'<text x="{W / 2}" y="370" text-anchor="middle" font-size="50" fill="#6B5A48">{len(known)} known ancestors in {maxg + 1} generations · {len(doc)} documented by records · {len(recs)} register records</text>')

lx, ly = 300, CY + 2240 + 170
legend = []
items = [(k, LINES[k][0]) for k in range(8, 16) if k in LINES]


def line_description(text, name):
    """First sentence of the line's description, shortened to a whole word so that it fits the legend column.
    A full stop ends the sentence only before a capital letter or at the end and after a word of at least 4 characters –
    "no. 41", "St. John" or "née Nová" do not end the sentence."""
    t = text.split(";")[0].strip()
    for m in re.finditer(r"\.(\s+|$)", t):
        after, before = t[m.end():m.end() + 1], t[:m.start()].split()[-1:]
        if (not after or after.isupper()) and before and len(before[0]) >= 4:
            t = t[:m.start()]
            break
    t = t.rstrip(". ")
    limit = max(30, 84 - len(name))   # the legend column holds about 85 characters at 40 px
    if len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0].rstrip(",;:–- ") + "…"
    return t


desc = {k: line_description(LINES[k][1], nm) for k, nm in items}
for idx, (k, nm) in enumerate(items):
    col, row = idx // 4, idx % 4
    x, y = lx + col * 1950, ly + row * 78
    legend.append(f'<rect x="{x}" y="{y - 40}" width="52" height="52" rx="8" fill="{BASE[k]}"/>'
                  f'<text x="{x + 76}" y="{y}" font-size="40"><tspan font-weight="700" fill="#3B2E22">{html.escape(nm)}</tspan>'
                  f'<tspan fill="#5E5245"> – {html.escape(desc[k])}</tspan></text>')
sy = ly + 4 * 78 + 50
legend.append(f'<rect x="{lx}" y="{sy - 34}" width="44" height="44" rx="6" fill="{mix(BASE[8], 0.2)}"/>'
              f'<text x="{lx + 64}" y="{sy}" font-size="36" fill="#3B2E22">documented by records</text>'
              f'<rect x="{lx + 520}" y="{sy - 34}" width="44" height="44" rx="6" fill="{mix(mix(BASE[8], 0.2), 0.45)}"/>'
              f'<text x="{lx + 584}" y="{sy}" font-size="36" font-style="italic" fill="#3B2E22">probable</text>'
              f'<rect x="{lx + 1000}" y="{sy - 34}" width="44" height="44" rx="6" fill="{EMPTY}"/>'
              f'<text x="{lx + 1064}" y="{sy}" font-size="36" fill="#3B2E22">not yet known</text>'
              f'<text x="{lx + 1500}" y="{sy}" font-size="36" fill="#5E5245">{html.escape(P[1]["n"].split()[0])} in the centre, each ring = one generation older; father’s side left, mother’s side right</text>')
if n_repeat or n_merged:   # pedigree collapse: explanation of the markers in the fan
    sy2 = sy + 70
    legend.append(f'<rect x="{lx}" y="{sy2 - 34}" width="44" height="44" rx="6" fill="url(#fan-repeat)" stroke="#9E7B56" stroke-width="2" stroke-dasharray="6 4"/>'
                  f'<text x="{lx + 64}" y="{sy2}" font-size="36" fill="#3B2E22">↺ see no. N – the ancestor is in the tree a second time (relatives married relatives), their branch is at number N</text>')
    if n_merged:
        legend.append(f'<rect x="{lx + 2560}" y="{sy2 - 34}" width="44" height="44" rx="6" fill="none" stroke="#8B5E34" stroke-width="2.4" stroke-dasharray="7 5"/>'
                      f'<text x="{lx + 2624}" y="{sy2}" font-size="36" fill="#3B2E22">common parents of two siblings (one wider sector)</text>')
footer = (f'<text x="{W / 2}" y="{H - 50}" text-anchor="middle" font-size="36" fill="#7A6B5B">'
          f'{html.escape(WEBCFG.get("footer", ""))}</text>')

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">'
       f'<rect width="{W}" height="{H}" fill="#F7F4EF"/><defs>{"".join(defs)}</defs>'
       f'{title}{"".join(paths)}{"".join(texts)}{"".join(legend)}{footer}</svg>')
if WEB:
    open(OUT, "w", encoding="utf-8", newline="\n").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}" class="fan">'
        f'<defs>{"".join(defs)}</defs>{"".join(paths)}{"".join(texts)}<g class="fan-links">{"".join(links)}</g></svg>')
    print(OUT, len(links), "links,", n_merged, "merged shared ancestors,", n_repeat, "repetitions")
    sys.exit(0)
os.makedirs(OUT, exist_ok=True)
svg_path = os.path.join(OUT, "fan_chart.svg")
html_path = os.path.join(OUT, "fan_chart.html")
png_path = os.path.join(OUT, "fan_chart.png")
open(svg_path, "w", encoding="utf-8", newline="\n").write(svg)
open(html_path, "w", encoding="utf-8", newline="\n").write(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#F7F4EF}}</style>{svg}')
import shutil, tempfile
if not CHROME:
    print(svg_path, "(PNG not created – Google Chrome is missing; open the HTML in a browser and print it to PDF)")
    sys.exit(0)
prof = tempfile.mkdtemp(prefix="fanchart-")
before = os.path.getmtime(png_path) if os.path.exists(png_path) else 0
try:   # a big poster on a slow machine: Chrome finishes the PNG but exits after the limit – what counts is whether the PNG exists
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                    "--force-device-scale-factor=1", f"--window-size={W},{H}", f"--screenshot={png_path}",
                    __import__("pathlib").Path(html_path).as_uri()], check=True, capture_output=True, timeout=300)
except subprocess.TimeoutExpired:
    pass
shutil.rmtree(prof, ignore_errors=True)
if not os.path.exists(png_path) or os.path.getmtime(png_path) <= before:
    sys.exit(f"The PNG was not generated (Chrome) – the poster is in {html_path}, open it in a browser and print it to PDF")
print(png_path, len(known), "ancestors", len(doc), "doc", len(recs), "records", maxg + 1, "generations")
