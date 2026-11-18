#!/usr/bin/env python3
"""Exports the family-tree data (data/*) into the website in web/.

Reads data/people.py, data/records.json, data/volumes.json, data/transcripts.json, data/highlights.json,
data/places.json, data/website.json, data/documents.json, data/memories.json, data/lines.json and the markdown notes.
Writes web/src/data/site.json, web/src/generated/*, web/public/{img,full}, web/public/login.html,
web/nginx.conf, web/netlify/edge-functions/gate.js, web/cloudflare/worker.js and web/wrangler.jsonc.

Run from web/ with `npm run data` (or directly `python3 -I tools/export_web.py`, on Windows `python -I -X utf8 …`).
  --deploy   refuse to export without a gate answer (website.json "gate.answer"), unless "gate.open": true
"""
import hashlib, html, json, os, re, shutil, subprocess, sys, unicodedata
if sys.argv[1:2] in (["-h"], ["--help"]):   # help instead of a crash
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):   # UTF-8 output even on Windows without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DATA = os.path.join(ROOT, "data")
WEB = os.path.join(ROOT, "web")
CROPS = os.path.join(ROOT, "crops")        # crops of records and documents (about 1800 px) – shown on the website
SOURCES = os.path.join(ROOT, "sources")    # the same crops in full resolution (click-through)

LINE_COLORS = {8: "#D49A3E", 9: "#CF6F52", 10: "#C46482", 11: "#8F7CC0",
               12: "#5E93C8", 13: "#4FA48F", 14: "#7FAA55", 15: "#B9A93E"}
STATUS = {"doc": "documented by a record", "prob": "probable", "fam": "from the family",
          "mh": "only from an online tree", "unk": "unknown"}
KINDS = {"B": "Baptism/Birth", "M": "Marriage", "D": "Death/Burial", "C": "Census", "O": "Other"}
# Names of placeholder people (an unnamed parent, e.g. the father of an illegitimate child) – same list as in check.py
PLACEHOLDER_NAMES = ("father unknown", "mother unknown", "father not named", "mother not named",
                     "unknown father", "unknown mother")
SAME_PERSON_PREFIX = "SAME PERSON"   # a fact "SAME PERSON as no. 12 …" in people.py is not shown on the website
GATE_SALT = "genealogy"              # default; the real salt is read from web/login.template.html


def jload(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_people():
    ns = {}
    exec(open(os.path.join(DATA, "people.py"), encoding="utf-8-sig").read(), ns)
    for name, default in (("P", {}), ("SIDE", []), ("LINES", {}), ("ISSUES", []), ("HYPOTHESES", []), ("SAME", {})):
        ns.setdefault(name, default)
    return ns


def record_rows():
    volumes = jload("volumes.json", {})
    rows = []
    for z in jload("records.json", []):
        sv = volumes.get(z.get("volume", ""), {})
        key = z["key"]
        rows.append(dict(
            key=key, kind=z.get("kind", "O"), date=z.get("date", ""), title=z.get("title", key),
            summary=z.get("summary", ""), scan=z.get("image", ""),
            archive=sv.get("archive", ""), volume=sv.get("title", ""), vdesc=sv.get("description", ""),
            portal=sv.get("portal", "the archive"), url=z.get("link") or sv.get("url", ""),
            img=os.path.exists(os.path.join(CROPS, key + ".jpg")),
            full=os.path.exists(os.path.join(SOURCES, key + ".jpg")),
            readBy=z.get("read_by", ""),                    # e.g. "AI model Claude Opus 5.5 (16 Nov 2026)"
            checkedBy=[x for x in (z.get("checked_by") if isinstance(z.get("checked_by"), list) else [z.get("checked_by")]) if x],
        ))
    return rows


def strip_comments(md):
    """Notes <!-- … --> in markdown are for Claude, not for the website."""
    return re.sub(r"<!--.*?-->\n?", "", md, flags=re.S)


def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def norm_answer(text):
    """Same normalisation as in login.html: no diacritics, lower case, only a-z0-9."""
    t = unicodedata.normalize("NFD", text)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", t)


CIRCA = re.compile(r"^(c\.|ca\.?|circa|about|abt\.?|≈|~)", re.I)


def years(y):
    """Short years for the website: "1850–1910", "≈1720–1785", "* 1931", "† before 1743", "alive 1921"."""
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
        return approx + ys[0]
    second = "?" if re.search(r"\bbefore\b", tail, re.I) else ("after " if re.search(r"\bafter\b", tail, re.I) else "") + \
        ("≈" if re.search(r"(\bc\.|\bca\b|circa|about|≈|~)", tail, re.I) else "") + ys[-1]
    return f"{approx}{ys[0]}–{second}"


def gen(k):
    return k.bit_length() - 1


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def relation(k):
    g, male = gen(k), (k % 2 == 0)
    if g == 0:
        return "root person of the tree"
    if g == 1:
        return "father" if male else "mother"
    base = "grandfather" if male else "grandmother"
    if g == 2:
        return base
    if g == 3:
        return "great-" + base
    if g == 4:
        return "great-great-" + base
    return f"{ordinal(g - 2)} great-{base}"   # g = 5 → "3rd great-grandfather"


def placeholder(p):
    return p["n"].lower().startswith(PLACEHOLDER_NAMES) or p["n"] in ("", "?")


def magick_bin():   # ImageMagick 7 (magick), otherwise 6 (convert) – not on Windows, where convert.exe is another program
    return shutil.which("magick") or (os.name != "nt" and shutil.which("convert")) or None


def size(path):
    w, h = subprocess.run([magick_bin(), path + "[0]", "-format", "%w %h", "info:"],
                          capture_output=True, text=True, check=True).stdout.split()
    return int(w), int(h)


def draw_boxes(src, dst, boxes, small):
    """Copy of the full-resolution crop with the highlight boxes drawn (if it has the same aspect ratio as the web
    crop the boxes were measured on). Returns False, then it is copied without boxes."""
    if not os.path.exists(small) or not magick_bin():
        return False
    (W, H), (w, h) = size(src), size(small)
    if abs(W / H - w / h) > 0.015 * (w / h):
        return False
    sw = max(4, round(W / 450))
    cmd = [magick_bin(), src, "-fill", "none", "-stroke", "#d7302a", "-strokewidth", str(sw)]
    for x0, y0, x1, y1 in boxes:
        cmd += ["-draw", f"rectangle {x0 * W:.0f},{y0 * H:.0f},{x1 * W:.0f},{y1 * H:.0f}"]
    subprocess.run(cmd + ["-quality", "90", dst], check=True)
    return True


# AI model names on the website: data may use short names ("checked by Opus", "Fable review 3"); the website always
# shows "AI model <full name>". The table can be changed in data/website.json: "ai_models": {"Opus": "Claude Opus 5.5", …}.
AI_MODELS = {"Opus": "Claude Opus 5.5", "Sonnet": "Claude Sonnet 5.5", "Fable": "Claude Fable 5.2"}
_AI_RULE = None


def set_ai_models(models):
    """Builds the single-pass rule for the given table {short name: full name}."""
    global AI_MODELS, _AI_RULE
    AI_MODELS = {k: v for k, v in (models or {}).items() if isinstance(k, str) and isinstance(v, str) and k.strip()}
    if not AI_MODELS:
        _AI_RULE = None
        return
    names = "|".join(re.escape(n) for n in sorted(AI_MODELS, key=len, reverse=True))

    def model(group):   # optional "Claude " before, optional version ("5.5") after – the table's version is used
        return rf"(?:(?:Claude|Anthropic)\s+)?(?P<{group}>{names})(?:\s+\d+(?:\.\d+)+)?"
    _AI_RULE = re.compile(
        rf"(?<![\w-])(?:"
        rf"(?P<rv>[Rr]eview|[Aa]nalysis|[Cc]heck)\s+(?:by\s+)?(?:AI\s+models?\s+)?{model('rm')}"
        rf"\s+(?:no\.\s*)?(?P<rn>\d+)(?![\d.])"                                  # "review Fable 3"
        rf"|(?:AI\s+models?\s+)?{model('p1')}\s+(?:and|&)\s+{model('p2')}"   # "Opus and Fable"
        rf"|(?:AI\s+models?\s+)?{model('s')}"                        # a single name
        rf")(?![\w-])")


def _ai_sub(m):
    if m.group("rv"):
        return f"{m.group('rv')} by AI model {AI_MODELS[m.group('rm')]} (no. {m.group('rn')})"
    if m.group("p1"):
        return f"AI models {AI_MODELS[m.group('p1')]} and {AI_MODELS[m.group('p2')]}"
    return f"AI model {AI_MODELS[m.group('s')]}"


def ai_names(text):
    """Normalises AI model names to "AI model <full name>" (idempotent: already normalised text stays the same)."""
    return _AI_RULE.sub(_ai_sub, text) if _AI_RULE else text


set_ai_models(AI_MODELS)


def write(path, text):
    if path.endswith(os.path.join("src", "data", "site.json")) or (os.sep + "generated" + os.sep in path and path.endswith(".md")):
        text = ai_names(text)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def fill(template, values, name):
    """Replaces {{PLACEHOLDER}} values and warns about any placeholder left in the template."""
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", v)
    left = sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", template)))
    if left:
        print(f"WARNING: {name} still contains {', '.join('{{' + x + '}}' for x in left)} – template and "
              "tools/export_web.py do not match")
    return template


def login_files(cfg):
    """Login gate: the question is on the website, the server (nginx, Netlify, Cloudflare) only has a fingerprint of
    the answer (SHA-256). The login page computes the same fingerprint and stores it in a cookie – the answer itself
    is never stored."""
    gate = cfg.get("gate") or {}
    answer = norm_answer(str(gate.get("answer", "")))   # also a number ("1923" without quotes)
    tpl = open(os.path.join(WEB, "login.template.html"), encoding="utf-8").read()
    salt = re.search(r"""['"]([A-Za-z0-9_-]+):['"]\s*\+""", tpl)   # 'genealogy:' + answer → SHA-256
    if not salt:   # an old template stores the answer itself in the cookie – nobody could log in with the new gate
        sys.exit("ERROR: web/ has an old login template. Update the project: "
                 "python3 -I <skill>/tools/new_project.py <project folder>")
    salt = salt.group(1) or GATE_SALT
    contact = cfg.get("contact") or {}
    hint = ""
    if contact.get("email"):
        hint = (f'Don\'t know the answer? Write to {html.escape(contact.get("name", ""))} at '
                f'<a href="mailto:{html.escape(contact["email"])}">{html.escape(contact["email"])}</a>.')
    page = fill(tpl, {"TITLE": html.escape(cfg.get("title", "Family Tree")),
                      "INTRO": html.escape(gate.get("intro", "This website is only for family and relatives.")),
                      "QUESTION": html.escape(gate.get("question", "Answer to the family question")),
                      "HINT": hint}, "login.template.html")
    write(os.path.join(WEB, "public", "login.html"), page)

    edge = os.path.join(WEB, "netlify", "edge-functions", "gate.js")
    digest = ""
    if answer:
        digest = hashlib.sha256((salt + ":" + answer).encode()).hexdigest()
        nginx_map = f'  "{digest}" 1;'
        write(edge, fill(open(os.path.join(WEB, "netlify", "gate.template.js"), encoding="utf-8").read(),
                         {"HASH": digest}, "netlify/gate.template.js"))
    else:   # no gate – the website is open
        nginx_map = "  default 1;"
        if os.path.exists(edge):
            os.remove(edge)
    nginx = open(os.path.join(WEB, "nginx.template.conf"), encoding="utf-8").read()
    if not answer:   # open website: "default 0" in the login map is replaced by "default 1" (nginx refuses two defaults)
        nginx = re.sub(r"(map \$cookie_\w+ \$\w+ \{.*?)\n *default 0;", r"\1", nginx, count=1, flags=re.S)
    nginx = fill(nginx, {"ANSWER": nginx_map}, "nginx.template.conf")
    write(os.path.join(WEB, "nginx.conf"), nginx)
    cloudflare_files(cfg, digest)
    return bool(answer)


def cloudflare_files(cfg, digest):
    """Gate for Cloudflare (web/cloudflare/worker.js) and web/wrangler.jsonc for `npm run deploy-cloudflare`."""
    tpl = os.path.join(WEB, "cloudflare", "worker.template.js")
    if not os.path.exists(tpl):
        return
    # Address https://<worker>.<subdomain>.workers.dev: cloudflare.subdomain = the account's subdomain (one per account,
    # created by deploy_cloudflare.mjs), cloudflare.worker = the website's name on the account (default "genealogy";
    # a second project on the same account needs another one, otherwise it would overwrite the first website).
    cf = cfg.get("cloudflare") or {}
    for field, example in (("subdomain", "novak-family"), ("worker", "family-tree-dvorak")):
        value = (cf.get(field) or "").strip()
        if value and not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?", value):
            sys.exit(f"ERROR: cloudflare.{field} in data/website.json \"{value}\" cannot be used – only lower-case letters "
                     f"without diacritics, digits and hyphens (at most 50 characters), e.g. \"{example}\".")
    worker_name = (cf.get("worker") or "").strip() or "genealogy"
    worker = fill(open(tpl, encoding="utf-8").read(), {"HASH": digest, "OPEN": "false" if digest else "true"},
                  "cloudflare/worker.template.js")
    write(os.path.join(WEB, "cloudflare", "worker.js"), worker)
    wrangler = {
        "name": worker_name,
        "main": "cloudflare/worker.js",
        "compatibility_date": "2026-10-01",
        "workers_dev": True,      # address https://<worker>.<subdomain>.workers.dev
        "preview_urls": False,    # no separate addresses for individual versions
        "assets": {"directory": "./dist", "binding": "ASSETS", "run_worker_first": True,
                   "not_found_handling": "404-page"},
    }
    write(os.path.join(WEB, "wrangler.jsonc"),
          "// Generated by tools/export_web.py – do not edit by hand. Deployment: npm run deploy-cloudflare.\n"
          + json.dumps(wrangler, ensure_ascii=False, indent=2) + "\n")


def main():
    ns = load_people()
    P, LINES, SIDE, ISSUES = ns["P"], ns["LINES"], ns["SIDE"], ns["ISSUES"]
    if 1 not in P:
        sys.exit("The root person (number 1) is missing in data/people.py.")
    SAME = ns["SAME"]                       # alias Ahnentafel number → canonical number (ancestor several times in the tree)
    cfg = jload("website.json", {})
    if isinstance(cfg.get("ai_models"), dict):
        set_ai_models(cfg["ai_models"])
    gate = cfg.get("gate") or {}
    if "--deploy" in sys.argv and not norm_answer(str(gate.get("answer", ""))) and not gate.get("open"):
        if str(gate.get("answer", "")).strip():
            sys.exit("ERROR: the answer to the gate question must contain Latin letters or digits "
                     "(Cyrillic or only symbols do not work, diacritics are fine). Choose another answer with the user.")
        sys.exit("ERROR: data/website.json has no answer to the gate question – the website would be open to anyone.\n"
                 "Set gate.answer, or (only if you really want it) gate.open: true.")
    docs_cfg = jload("documents.json", [])
    memories_cfg = jload("memories.json", {})
    lines_cfg = jload("lines.json", {})
    recs = {r["key"]: r for r in record_rows()}

    slugs, used = {}, set()
    for k in sorted(P):
        p = P[k]
        if placeholder(p) or k in SAME:
            continue
        yv = (p.get("y") or "").strip()
        ys = [] if yv.startswith(("?", "†")) else re.findall(r"\d{4}", yv)   # never put the year of death in the address
        s = slugify(p["n"] + (" " + ys[0] if ys else ""))
        if s in used or not s:
            s = f"{s}-{k}"
        used.add(s)
        slugs[k] = s
    for a, c in list(SAME.items()):
        if c not in slugs:   # the main person is a placeholder (no name) or missing – the alias has nowhere to point
            print(f"WARNING: SAME {a} -> {c} – person {c} is a placeholder or missing, skipping the alias (fix data/people.py)")
            del SAME[a]
            continue
        slugs[a] = slugs[c]
    aliases_of = {}
    for a, c in SAME.items():
        aliases_of.setdefault(c, []).append(a)

    def line_of(k):
        g = gen(k)
        return k >> (g - 3) if g >= 3 else None

    people = {}
    for k, p in sorted(P.items()):
        if k not in slugs or k in SAME:
            continue
        path, c = [], k
        while c >= 1:
            path.append(slugs.get(c))
            c //= 2
        people[slugs[k]] = dict(
            k=k, slug=slugs[k], name=p["n"], y=p.get("y", ""), years=years(p.get("y")), st=p.get("st", "unk"),
            status=STATUS.get(p.get("st"), ""), gen=gen(k), sex="M" if k == 1 and p.get("sex", "M") == "M" or k > 1 and k % 2 == 0 else "F",
            rel=relation(k), line=line_of(k), facts=p.get("f", []), note=p.get("note", ""), summary=p.get("summary", ""),
            records=[r for r in p.get("r", []) if r in recs],
            father=slugs.get(2 * k), mother=slugs.get(2 * k + 1),
            fatherUnknown=(2 * k in P and placeholder(P[2 * k])), motherUnknown=(2 * k + 1 in P and placeholder(P[2 * k + 1])),
            child=slugs.get(k // 2) if k > 1 else None, spouse=slugs.get(k ^ 1) if k > 1 else None,
            family=None, ownFamily=None, path=path,
            side=[dict(name=s["n"], text=s.get("t", ""), records=[r for r in s.get("r", []) if r in recs]) for s in SIDE if s["k"] == k],
            docs=[dict(img=d["img"], caption=d.get("caption", "")) for d in docs_cfg if k in d.get("people", [])],
            memories=[dict(kind=v.get("kind", "memory"), text=v["text"], source=v.get("source", "")) for v in memories_cfg.get(str(k), [])],
            children=[slugs[c] for c in [k // 2] + [a // 2 for a in aliases_of.get(k, [])] if k > 1 and c in slugs],
            also=[dict(k=a, rel=relation(a), line=line_of(a), child=slugs.get(a // 2)) for a in aliases_of.get(k, [])],
        )
        if aliases_of.get(k):
            for a in aliases_of[k]:
                people[slugs[k]]["records"] = list(dict.fromkeys(people[slugs[k]]["records"] + [r for r in P.get(a, {}).get("r", []) if r in recs]))
            people[slugs[k]]["facts"] = [f for f in people[slugs[k]]["facts"] if not f.startswith(SAME_PERSON_PREFIX)]

    families = {}
    for k in sorted(P):
        f, m = 2 * k, 2 * k + 1
        if k not in slugs or k in SAME or (f not in slugs and m not in slugs):
            continue
        fs, ms = slugs.get(f), slugs.get(m)
        fid = "-and-".join(x for x in (fs, ms) if x) if fs and ms else (fs or ms) + "-family"
        surname = ((P[m]["n"].split() or [""])[-1] if m in P else "").strip("()?")   # also a placeholder mother without a name
        mfacts = [x for x in P.get(f, {}).get("f", []) + P.get(m, {}).get("f", []) if x.startswith("×")]
        marriage = [x for x in mfacts if surname and surname[:5] in x] or mfacts
        frec = P.get(f, {}).get("r", []) + P.get(m, {}).get("r", [])
        child_rec = [r for r in P[k].get("r", []) if r in recs and recs[r]["kind"] == "B"]
        rlist = [r for r in dict.fromkeys(frec) if r in recs and recs[r]["kind"] == "M"] + child_rec
        if fid in families:   # the same couple met twice (ancestor several times in the tree) – one family, more children
            fam = families[fid]
            fam["children"].append(slugs[k])
            fam["records"] = list(dict.fromkeys(fam["records"] + rlist))
            fam["side"] += people[slugs[k]]["side"]
        else:
            families[fid] = dict(id=fid, father=fs, mother=ms, fatherUnknown=f in P and placeholder(P[f]),
                                 child=slugs[k], children=[slugs[k]], marriage=marriage, records=rlist,
                                 line=line_of(f) if f in P else line_of(m), gen=gen(f), side=list(people[slugs[k]]["side"]))
        people[slugs[k]]["family"] = fid
        for x in (fs, ms):
            if x:
                people[x]["ownFamily"] = fid

    refs = {}
    for s, p in people.items():
        for r in p["records"] + [r for e in p["side"] for r in e["records"]]:
            refs.setdefault(r, []).append(s)
    hl = jload("highlights.json", {})
    transcripts = jload("transcripts.json", {})
    records = []
    for key, r in recs.items():
        r = dict(r)
        r["boxes"] = hl.get(key, {}).get("boxes", [])
        tr = transcripts.get(key, {})
        r["orig"], r["translation"] = tr.get("orig", ""), tr.get("translation", "")
        r["kindName"] = KINDS.get(r["kind"], r["kind"])
        r["people"] = list(dict.fromkeys(refs.get(key, [])))
        records.append(r)

    lines = {}
    for k, (name, desc) in sorted(LINES.items()):
        if k not in LINE_COLORS:
            continue
        members = [(p["k"], p) for p in people.values() if p["line"] == k]
        members += [(a["k"], p) for p in people.values() for a in p["also"] if a["line"] == k]
        members.sort(key=lambda x: x[0])
        ls = slugify(name)
        if ls in lines:   # two lines of the same name (e.g. Nováks on both sides) – otherwise one would silently vanish
            print(f"WARNING: lines {lines[ls]['k']} and {k} have the same name \"{name}\" – tell them apart in LINES (data/people.py)")
            ls = f"{ls}-{k}"
        line_cfg = lines_cfg.get(name, {})   # data/lines.json – a short story of the line
        lines[ls] = dict(k=k, slug=ls, name=name, desc=desc, color=LINE_COLORS[k],
                         story=line_cfg.get("story", []), unknown=line_cfg.get("unknown", ""),
                         root=slugs.get(k), people=[p["slug"] for _, p in members],
                         gens={p["slug"]: gen(kk) for kk, p in members})
    lines = {s: l for s, l in lines.items() if l["root"]}
    for p in people.values():
        p["lineSlug"] = next((l["slug"] for l in lines.values() if l["k"] == p["line"]), None)

    places = []
    for name, e in jload("places.json", {}).items():
        if "lat" not in e:
            continue
        rx = re.compile(e.get("re") or re.escape(name))
        hits = [p for p in people.values() if rx.search(" ".join(p["facts"]))]
        byline = {}
        for p in sorted(hits, key=lambda p: p["k"]):
            byline.setdefault(p["line"] or 0, []).append(p["slug"])
        if e.get("hypothesis"):
            byline = {e.get("line", 0): []}
        if not byline:
            continue
        yrs = [int(y) for p in hits for y in re.findall(r"\b1[4-9]\d\d\b", p["y"] or "")]
        places.append(dict(name=name, lat=e["lat"], lon=e["lon"], lines=[dict(k=k, people=v) for k, v in sorted(byline.items())],
                           years=[min(yrs), max(yrs)] if yrs else None, hypothesis=bool(e.get("hypothesis"))))

    known = [p for p in people.values() if p["k"] > 1]
    stats = dict(ancestors=len(known), documented=sum(p["st"] == "doc" for p in known), records=len(records),
                 generations=max(p["gen"] for p in people.values()) + 1)
    hypotheses = [dict(line=h.get("line"), title=h.get("title", "Hypothesis"), text=h.get("text", ""),
                       items=[dict(name=a, text=b) for a, b in h.get("items", [])],
                       records=[r for r in h.get("records", []) if r in recs]) for h in ns["HYPOTHESES"]]

    has_story = os.path.exists(os.path.join(DATA, "story.md"))
    public_cfg = {k: v for k, v in cfg.items() if k not in ("gate", "ai_models")}
    public_cfg["hasStory"] = has_story
    site = dict(config=public_cfg, places=places, root=slugs[1], aliases={a: slugs[a] for a in SAME}, people=people,
                families=families, records=records, lines=lines,
                issues=[dict(title=i, text="") if isinstance(i, str) else dict(title=i[0], text=i[1]) for i in ISSUES
                        if isinstance(i, str) or (isinstance(i, (tuple, list)) and len(i) == 2)],   # others are reported by check.py
                stats=stats, hypotheses=hypotheses,
                docs=[dict(img=d["img"], caption=d.get("caption", ""), kind=d.get("type", "photo"), date=d.get("date", ""),
                           people=[slugs[k] for k in d.get("people", []) if k in slugs])
                      for d in docs_cfg if os.path.exists(os.path.join(CROPS, d["img"] + ".jpg"))])

    write(os.path.join(WEB, "src", "data", "site.json"), json.dumps(site, ensure_ascii=False, indent=1))
    gen_dir = os.path.join(WEB, "src", "generated")
    for src, dst in (("archive_requests.md", "questions.md"), ("research_log.md", "log.md"),
                     ("curiosities.md", "curiosities.md"), ("offline_sources.md", "offline_sources.md")):
        path = os.path.join(DATA, src)
        text = open(path, encoding="utf-8-sig").read() if os.path.exists(path) else ""
        write(os.path.join(gen_dir, dst), strip_comments(re.sub(r"^# .*\n", "", text, count=1)))
    story = os.path.join(DATA, "story.md")
    write(os.path.join(gen_dir, "story.md"), strip_comments(open(story, encoding="utf-8-sig").read()) if has_story else "---\ntitle: Story\nlead: ''\n---\n")
    # further stories (data/story_<line>.md, e.g. one per family side) – the stories page renders every generated story_*.md
    extra_stories = sorted(f for f in os.listdir(DATA) if re.fullmatch(r"story_[\w-]+\.md", f))
    for f in os.listdir(gen_dir):
        if re.fullmatch(r"story_[\w-]+\.md", f) and f not in extra_stories:
            os.remove(os.path.join(gen_dir, f))
    for f in extra_stories:
        write(os.path.join(gen_dir, f), strip_comments(open(os.path.join(DATA, f), encoding="utf-8-sig").read()))

    hrefs = os.path.join(gen_dir, "fan_hrefs.json")
    json.dump({k: f"/person/{s}/" for k, s in slugs.items()}, open(hrefs, "w", encoding="utf-8", newline="\n"))
    subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(TOOLS, "fan_chart.py"),
                    os.path.join(gen_dir, "fan.svg"), "--web", hrefs], check=True, capture_output=True)

    gated = login_files(cfg)

    copied = 0
    hl_path = os.path.join(DATA, "highlights.json")
    hl_mtime = os.path.getmtime(hl_path) if os.path.exists(hl_path) else 0
    for sub, src_dir in (("img", CROPS), ("full", SOURCES)):
        dst_dir = os.path.join(WEB, "public", sub)
        os.makedirs(dst_dir, exist_ok=True)
        for key in list(recs) + [d["img"] for d in docs_cfg] + ([cfg["home"]["photo"]] if (cfg.get("home") or {}).get("photo") else []):
            src = os.path.join(src_dir, key + ".jpg")
            dst = os.path.join(dst_dir, key + ".jpg")
            if not os.path.exists(src):
                continue
            boxes = hl.get(key, {}).get("boxes", [])
            stale = not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst) \
                or (sub == "full" and boxes and hl_mtime > os.path.getmtime(dst))
            if not stale:
                continue
            if sub == "full" and boxes and draw_boxes(src, dst, boxes, os.path.join(CROPS, key + ".jpg")):
                copied += 1
                continue
            shutil.copy2(src, dst)
            copied += 1
    print(f"{len(people)} people, {len(families)} families, {len(records)} records, {len(lines)} lines, {len(places)} places; "
          f"copied {copied} images; login gate {'on' if gated else 'OFF (the website is open)'}")

    # links in texts that lead nowhere (a person's address changes e.g. when a birth year is added: jan-novak → jan-novak-1798)
    targets = dict(person=people, source=recs, line=lines, family=families)
    texts = {f: open(os.path.join(gen_dir, f), encoding="utf-8").read() for f in ("story.md", "curiosities.md", *extra_stories)}
    texts["website.json"] = json.dumps(cfg, ensure_ascii=False)
    texts["lines.json"] = json.dumps(lines_cfg, ensure_ascii=False)   # stories of the lines
    texts["people.py (HYPOTHESES)"] = json.dumps(hypotheses, ensure_ascii=False)
    broken = [(f, m.group(0)) for f, t in texts.items()
              for m in re.finditer(r"/(person|source|line|family)/([^/\s)\"'#?<>\]]+)", t) if m.group(2) not in targets[m.group(1)]]
    for f, link in dict.fromkeys(broken):
        print(f"WARNING: broken link {link}/ in {f} – fix it (page addresses are in web/src/data/site.json)")


if __name__ == "__main__":
    main()
