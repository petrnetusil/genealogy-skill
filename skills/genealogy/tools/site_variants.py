#!/usr/bin/env python3
"""Partial websites ("variants") of the family tree, built from the same data as the main website.

A variant shows only one branch of the tree: its home person is an ancestor of the main tree (e.g. the father,
Kekulé 2) and every person is renumbered so that this ancestor becomes number 1 (2 → 1, 4 → 2, 5 → 3, 8 → 4 …).
The lines (fan chart) of the variant are then the eight great-great-grandparents of the new home person.
Data of the rest of the tree never get into the copy (people, records, images, memories, chapters of the texts,
news points mentioning surnames of the other branches); open issues (ISSUES) and hypotheses (HYPOTHESES) stay on the
main website only.

Configuration – data/variants.json (a list; missing or empty file = no variants, only the main website):
  [
    {"name": "father",                      # required: folder variants/<name>/, letters a-z, digits, - and _
     "root": 2,                             # required: Kekulé number of the variant's home person (>= 2)
     "title": "The Novák family tree",      # required: website title of the variant
     "gate": {"question": "…", "answer": "…"},   # required: login question and answer of the variant
     "domain": "",                          # optional: custom domain (e.g. "novak.example.org"); empty = the
                                            #   workers.dev address that web/scripts/deploy_cloudflare.mjs gets
     "worker": "",                          # optional: Cloudflare worker name; default "<main worker>-<name>"
                                            #   (it must differ from the main site, or it would overwrite it)
     "story": "story_novak.md",             # optional: story file in data/ shown as the variant's story
     "story_config": {"menu": "…", "line": 8, "button": "…"},   # optional: website.json "story" of the variant
     "home_curiosities": ["…"],             # optional: titles of home-page curiosity cards to keep
                                            #   (default: every card whose chapter is on the variant)
     "lines": {"9": ["Dubois", "Weavers from Ghent."]},   # optional: names/descriptions of new lines 8–15
                                            #   (default: taken from data/people.py LINES or the ancestor's surname)
     "hide_words": ["Opwijk"]}              # optional: extra words (typical places of the other branches);
  ]                                         #   news points mentioning them are left out of the variant
The variants file is never exported to the website (the answers would otherwise leak) – keep the gate answers
only there, not in website.json.

Usage (from the project root):
  python3 -I tools/site_variants.py <name> [--deploy]   builds variants/<name>/ (and deploys it with --deploy)
  python3 -I tools/site_variants.py --all [--deploy]    all variants
  python3 -I tools/site_variants.py --deploy-main       deploys the main website (web/) to Cloudflare
  python3 -I tools/site_variants.py --list              prints the variant names, one per line
  python3 -I tools/site_variants.py --urls              prints "<site>\t<url>" of the main site and each variant
                                                        (custom domain, else the workers.dev address in web/.wrangler/url.txt)
The copy is built in variants/<name>/: data/ trimmed, web/ copied without images and generated files (its own
.wrangler/ and node_modules link are kept), tools/, crops/ and sources/ as links to the project's folders.
Deployment: `npm run data` (check that no person of another branch got in), then `npm run deploy-cloudflare`
(export, build, web/scripts/deploy_cloudflare.mjs) and, with a domain, `npx -y wrangler@4 deploy --domain <domain>`.
tools/deploy_all.sh deploys the main site and every variant and then checks every gate (HTTP 401).
"""
import json, os, re, shutil, subprocess, sys, unicodedata
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CONFIG = os.path.join(DATA, "variants.json")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,40}")
WORKER_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?")
# Copied from web/ into the variant: everything except dependencies, build output and generated or image files.
WEB_SKIP = {"node_modules", "dist", ".astro", ".wrangler", "wrangler.jsonc", "nginx.conf"}
WEB_SKIP_PATHS = {"public/img", "public/full", "public/login.html", "src/data", "src/generated",
                  "cloudflare/worker.js", "netlify/edge-functions"}


def jload(path, default):
    return json.load(open(path, encoding="utf-8-sig")) if os.path.exists(path) else default


def jdump(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def variants():
    """Variants from data/variants.json, checked; [] when the file is missing or empty."""
    try:
        v = jload(CONFIG, [])
    except ValueError as e:
        sys.exit(f"ERROR: data/variants.json is not valid JSON: {e}")
    if isinstance(v, dict):   # also accept {"father": {...}, …}
        v = [dict(c, name=c.get("name", n)) for n, c in v.items()]
    if not isinstance(v, list):
        sys.exit("ERROR: data/variants.json must be a list of variants (see tools/site_variants.py --help).")
    seen = set()
    for c in v:
        n = str(c.get("name", ""))
        if not NAME_RE.fullmatch(n) or n in seen:
            sys.exit(f"ERROR: data/variants.json – bad or duplicate name {n!r} (letters a-z, digits, - and _).")
        seen.add(n)
        if not isinstance(c.get("root"), int) or c["root"] < 2:
            sys.exit(f"ERROR: data/variants.json – variant {n}: \"root\" must be a Kekulé number >= 2 (e.g. 2 = father).")
    return v


def find(name):
    for c in variants():
        if c["name"] == name:
            return c
    sys.exit(f"ERROR: variant {name!r} is not in data/variants.json.\n" + __doc__)


def in_branch(k, root):
    """Does person k (Kekulé of the main tree) belong to the branch of `root`?"""
    d = k.bit_length() - root.bit_length()
    return d >= 0 and (k >> d) == root


def new_number(k, root):
    """Kekulé in the variant, where `root` becomes the home person 1."""
    d = k.bit_length() - root.bit_length()
    return k - (root << d) + (1 << d)


def old_number(n, root):
    d = n.bit_length() - 1
    return n - (1 << d) + (root << d)


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def person_links(text):
    return re.findall(r"/person/([^/\s)\"'#?<>\]]+)", text)


def card_title(c):
    return c.get("title") or c.get("heading") or ""


def main_worker(cfg):
    cf = cfg.get("cloudflare") or {}
    return (cf.get("worker") or "").strip() or "genealogy"


def variant_lines(ns, P0, root, conf):
    """Lines 8–15 of the variant: names from the config, else from LINES of the main tree when the line's ancestor
    descends in the male line from a main line (same surname), else the ancestor's surname."""
    L0, given = ns.get("LINES", {}), conf.get("lines") or {}
    out = {}
    for n in range(8, 16):
        if str(n) in given or n in given:
            g = given.get(str(n), given.get(n))
            out[n] = tuple(g) if isinstance(g, (list, tuple)) else (str(g), "")
            continue
        o = old_number(n, root)
        ol = o >> (o.bit_length() - 4) if o >= 8 else None
        if ol in L0 and o == ol << (o.bit_length() - 4):
            out[n] = tuple(L0[ol])
        elif o in P0 and P0[o].get("n") and not P0[o]["n"].startswith("?"):
            surname = re.sub(r"\(.*?\)", "", P0[o]["n"]).split()[-1]
            out[n] = (surname, "")
    return out


def build(conf):
    name, root = conf["name"], conf["root"]
    title = (conf.get("title") or "").strip()
    gate = conf.get("gate") or {}
    if not title:
        sys.exit(f"ERROR: data/variants.json – variant {name}: \"title\" is missing.")
    if not norm(str(gate.get("answer", ""))):
        sys.exit(f"ERROR: data/variants.json – variant {name}: gate.answer is missing – the website would be open.")
    dst = os.path.join(ROOT, "variants", name)

    # --- people ---
    ns = {}
    exec(open(os.path.join(DATA, "people.py"), encoding="utf-8-sig").read(), ns)
    if root not in ns["P"]:
        sys.exit(f"ERROR: variant {name}: person {root} is not in data/people.py.")
    n = lambda k: new_number(k, root)
    P0 = {k: p for k, p in ns["P"].items() if in_branch(k, root)}            # original numbers
    P = {n(k): p for k, p in P0.items()}                                    # new numbers
    SAME = {n(a): n(c) for a, c in ns.get("SAME", {}).items() if a in P0 and c in P0}
    SIDE = [dict(s, k=n(s["k"])) for s in ns.get("SIDE", []) if s.get("k") in P0]
    LINES = dict(sorted(variant_lines(ns, P0, root, conf).items()))
    # the line down to the main home person and the root's spouse: not on the variant, but a document showing them
    # together with the variant's people is fine
    neutral = {root ^ 1} | {root >> i for i in range(1, root.bit_length())}
    excluded = {k for k in ns["P"] if k not in P0 and k not in neutral}

    os.makedirs(os.path.join(dst, "data"), exist_ok=True)
    with open(os.path.join(dst, "data", "people.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Trimmed copy of data/people.py for the website \"{title}\" – made by tools/site_variants.py, do not edit.\n")
        f.write(f"P = {P!r}\nLINES = {LINES!r}\nSIDE = {SIDE!r}\nISSUES = []\nHYPOTHESES = []\nSAME = {SAME!r}\n")

    # --- records, transcripts, volumes, highlights, places ---
    recs = {r for p in P.values() for r in p.get("r", [])} | {r for s in SIDE for r in s.get("r", [])}
    rec_list = [z for z in jload(os.path.join(DATA, "records.json"), []) if z.get("key") in recs]
    vols = {z.get("volume") for z in rec_list}
    out = lambda fn, o: jdump(os.path.join(dst, "data", fn), o)
    out("records.json", rec_list)
    out("transcripts.json", {k: v for k, v in jload(os.path.join(DATA, "transcripts.json"), {}).items() if k in recs})
    vl = jload(os.path.join(DATA, "volumes.json"), {})
    out("volumes.json", {k: v for k, v in vl.items() if k in vols} if isinstance(vl, dict) else vl)
    out("highlights.json", {k: v for k, v in jload(os.path.join(DATA, "highlights.json"), {}).items() if k in recs})
    if os.path.exists(os.path.join(DATA, "places.json")):
        shutil.copy2(os.path.join(DATA, "places.json"), os.path.join(dst, "data", "places.json"))
    names = {v[0] for v in LINES.values()}
    out("lines.json", {k: v for k, v in jload(os.path.join(DATA, "lines.json"), {}).items() if k in names})

    # --- documents and memories ---
    docs = []
    for d in jload(os.path.join(DATA, "documents.json"), []):
        ppl = [o for o in d.get("people", []) if isinstance(o, int)]
        if any(o in P0 for o in ppl) and not any(o in excluded for o in ppl):
            docs.append(dict(d, people=[n(o) for o in ppl if o in P0]))
    out("documents.json", docs)
    mem = jload(os.path.join(DATA, "memories.json"), {})
    out("memories.json", {str(n(int(k))): v for k, v in mem.items() if str(k).isdigit() and int(k) in P0})

    # --- slugs of the whole tree (to filter the texts) – the same rule as export_web.py ---
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import export_web as ew   # noqa: E402

    def slugs(PP):
        s, used = {}, set()
        for k in sorted(PP):
            p = PP[k]
            if ew.placeholder(p) or k in ns.get("SAME", {}):
                continue
            yv = (p.get("y") or "").strip()
            ys = [] if yv.startswith(("?", "†")) else re.findall(r"\d{4}", yv)
            x = ew.slugify(p["n"] + (" " + ys[0] if ys else ""))
            if x in used or not x:
                x = f"{x}-{k}"
            used.add(x); s[k] = x
        return s
    every = slugs(ns["P"])
    forbidden = {s for k, s in every.items() if k in excluded or k in neutral}
    allowed = {s for k, s in every.items() if k in P0}

    def filter_md(text):
        """Keeps the head and the chapters (## …) that link only to people of this branch (and to at least one)."""
        parts = re.split(r"(?m)^(?=## )", text)
        head, chapters = parts[0], parts[1:]
        keep = [c for c in chapters if not set(person_links(c)) & forbidden and set(person_links(c)) & allowed]
        if set(person_links(head)) & forbidden:
            head = re.sub(r"(?m)^(?!#|---|title:|lead:).*$", "", head)
        return head + "".join(keep), len(keep), len(chapters)

    cur_src = os.path.join(DATA, "curiosities.md")
    cur, kept, total = filter_md(open(cur_src, encoding="utf-8-sig").read()) if os.path.exists(cur_src) else ("", 0, 0)
    open(os.path.join(dst, "data", "curiosities.md"), "w", encoding="utf-8", newline="\n").write(cur)
    print(f"curiosities: {kept} of {total} chapters")
    story_dst = os.path.join(dst, "data", "story.md")
    if conf.get("story"):   # links to people outside the variant → plain text
        src = os.path.join(DATA, conf["story"])
        if not os.path.exists(src):
            sys.exit(f"ERROR: variant {name}: story file data/{conf['story']} does not exist.")
        t = open(src, encoding="utf-8-sig").read()
        t = re.sub(r"\[([^\]]+)\]\(/person/([^/)]+)/?\)", lambda m: m.group(1) if m.group(2) in forbidden else m.group(0), t)
        open(story_dst, "w", encoding="utf-8", newline="\n").write(t)
    elif os.path.exists(story_dst):
        os.remove(story_dst)
    open(os.path.join(dst, "data", "research_log.md"), "w", encoding="utf-8", newline="\n").write(
        "# Research log\n\nThe research log is only on the main website.\n")
    open(os.path.join(dst, "data", "archive_requests.md"), "w", encoding="utf-8", newline="\n").write(
        "# Sources outside the online registers\n\nThe overview of archive requests is only on the main website.\n")

    # --- website settings ---
    cfg = jload(os.path.join(DATA, "website.json"), {})
    worker = (conf.get("worker") or f"{main_worker(cfg)}-{name}".replace("_", "-"))[:50].strip("-")
    if not WORKER_RE.fullmatch(worker):
        sys.exit(f"ERROR: variant {name}: worker name {worker!r} – only lowercase letters, digits and hyphens.")
    cfg["title"] = title
    cfg["gate"] = dict(cfg.get("gate") or {}, question=gate.get("question", ""), answer=gate["answer"])
    cf = {k: v for k, v in (cfg.get("cloudflare") or {}).items() if k not in ("web", "worker", "domain")}
    cfg["cloudflare"] = dict(cf, worker=worker, domain=(conf.get("domain") or "").strip())
    if conf.get("story") and conf.get("story_config"):
        cfg["story"] = conf["story_config"]
    elif not conf.get("story"):
        cfg.pop("story", None)
    # a home-page card only when its curiosity really is on this website (otherwise it would lead nowhere)
    def card_has_chapter(c):
        first = norm(re.split(r"[ ,]", card_title(c))[0]) if card_title(c) else ""
        return first and first in norm(cur)
    wanted = conf.get("home_curiosities")
    cfg["home_curiosities"] = [c for c in cfg.get("home_curiosities", [])
                               if (wanted is None or card_title(c) in wanted) and card_has_chapter(c)]
    out("website.json", cfg)

    # --- copy of the website, links to tools and images ---
    for d in ("tools", "crops", "sources"):
        link = os.path.join(dst, d)
        if not os.path.lexists(link):
            os.makedirs(os.path.join(ROOT, d), exist_ok=True)
            try:
                os.symlink(os.path.join(ROOT, d), link, target_is_directory=True)
            except OSError as e:
                sys.exit(f"ERROR: cannot create the link {link} ({e}). On Windows turn on Developer Mode "
                         "(symbolic links) and run again.")
    copy_web(os.path.join(ROOT, "web"), os.path.join(dst, "web"))

    # news: only points not mentioning surnames of the other branches
    # A foreign surname as a stem (whole surname without the last letter, at least 4 characters), compared with the
    # starts of words – "Strand" does not catch "strange" and "Petrak" does not catch "Petra".
    given = {norm(p["n"].split()[0]) for p in ns["P"].values() if p.get("n")}   # given names are no surnames
    def stem(t):
        t = norm(t)
        return t[:max(4, len(t) - 1)] if len(t) >= 4 and t not in given else None
    foreign = set()
    for k in excluded:
        for t in [t for t in re.sub(r"\(.*?\)", "", ns["P"][k].get("n", "")).split() if t[:1].isupper()][-1:]:
            if stem(t): foreign.add(stem(t))
    foreign |= {stem(v[0]) for k, v in ns.get("LINES", {}).items() if v and v[0] not in names and stem(v[0])}
    foreign -= {stem(p["n"].split()[-1]) for k, p in P.items() if p.get("n") and k > 1}   # surnames this branch has too
    foreign |= {norm(w)[:5] for w in conf.get("hide_words", []) if norm(w)}
    foreign.discard(None)
    def mentions(text):
        words = [norm(s) for s in re.split(r"[\s,;:.()„“\"'–—/-]+", text) if s]
        return any(w.startswith(c) for w in words for c in foreign)
    news_p = os.path.join(dst, "web", "src", "news.json")
    news = jload(news_p, [])
    kept_news = []
    for item in news:
        points = [b for b in item.get("points", []) if not mentions(b)]
        if points and not mentions(item.get("title", "")):
            # people touched by the version (tools/news_people.py): only this branch, renumbered, only its records
            ppl = [dict(o, k=new_number(o["k"], root), records=[r for r in o.get("records", []) if r in recs])
                   for o in item.get("people", []) if o.get("k") in P0]
            kept_news.append(dict(item, points=points, people=ppl))
    if os.path.exists(news_p):
        jdump(news_p, kept_news)
    print(f"{title}: {len(P)} people, {len(rec_list)} records, {len(docs)} documents, news {len(kept_news)} of {len(news)}")
    return dst, P


def copy_web(src, dst):
    """Copies web/ into the variant like `rsync --delete`, without dependencies, build output, generated files and
    images; keeps the variant's own .wrangler/ (deployment address) and the node_modules link."""
    os.makedirs(dst, exist_ok=True)
    for e in os.listdir(dst):
        if e in (".wrangler", "node_modules"):
            continue
        p = os.path.join(dst, e)
        shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)

    def ignore(d, names):
        rel = os.path.relpath(d, src).replace(os.sep, "/")
        rel = "" if rel == "." else rel + "/"
        return {x for x in names if x in WEB_SKIP or rel + x in WEB_SKIP_PATHS}
    for e in os.listdir(src):
        if e in WEB_SKIP or e in WEB_SKIP_PATHS:
            continue
        s, t = os.path.join(src, e), os.path.join(dst, e)
        shutil.copytree(s, t, ignore=ignore, symlinks=True) if os.path.isdir(s) else shutil.copy2(s, t)
    nm = os.path.join(dst, "node_modules")
    if not os.path.lexists(nm) and os.path.isdir(os.path.join(src, "node_modules")):
        try:
            os.symlink(os.path.join(src, "node_modules"), nm, target_is_directory=True)
        except OSError:
            pass   # npm install in the variant's web/ then


def npm(web_dir, *args):
    exe = shutil.which("npm") or shutil.which("npm.cmd")
    if not exe:
        sys.exit("ERROR: npm not found – install Node.js (see web/.nvmrc) and run again.")
    subprocess.run([exe, *args], cwd=web_dir, check=True)


def deploy(web_dir, domain):
    """npm run deploy-cloudflare (export, build, deploy_cloudflare.mjs) and, with a domain, attach it."""
    npm(web_dir, "run", "deploy-cloudflare")
    if domain:
        exe = shutil.which("npx") or shutil.which("npx.cmd")
        subprocess.run([exe, "-y", "wrangler@4", "deploy", "--domain", domain], cwd=web_dir, check=True)


def deploy_variant(conf, dst, P):
    w = os.path.join(dst, "web")
    npm(w, "run", "data")   # export only – check before anything is uploaded
    site = jload(os.path.join(w, "src", "data", "site.json"), {})
    expected = {(p.get("n"), p.get("y")) for p in P.values()}
    leaked = sorted(o.get("name", "?") for o in site.get("people", {}).values()
                    if (o.get("name"), o.get("y")) not in expected)
    if leaked or not site.get("people"):
        sys.exit(f"ERROR: the variant {conf['name']} contains people of other branches: {leaked[:5]} – not deploying.")
    deploy(w, (conf.get("domain") or "").strip())


def address(web_dir, domain):
    if domain:
        return "https://" + re.sub(r"^https?://", "", domain).strip("/") + "/"
    for f in ("url.txt", "address.txt", "adresa.txt"):
        p = os.path.join(web_dir, ".wrangler", f)
        if os.path.exists(p):
            return open(p, encoding="utf-8").read().strip().rstrip("/") + "/"
    return ""


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    if a[0] == "--list":
        for c in variants():
            print(c["name"])
        return
    if a[0] == "--urls":
        cfg = jload(os.path.join(DATA, "website.json"), {})
        print(f"main\t{address(os.path.join(ROOT, 'web'), (cfg.get('cloudflare') or {}).get('domain', ''))}")
        for c in variants():
            print(f"{c['name']}\t{address(os.path.join(ROOT, 'variants', c['name'], 'web'), c.get('domain', ''))}")
        return
    if a[0] == "--deploy-main":
        cfg = jload(os.path.join(DATA, "website.json"), {})
        deploy(os.path.join(ROOT, "web"), ((cfg.get("cloudflare") or {}).get("domain") or "").strip())
        return
    confs = variants() if a[0] == "--all" else [find(a[0])]
    if not confs:
        print("No variants in data/variants.json – only the main website.")
    for conf in confs:
        dst, P = build(conf)
        if "--deploy" in a:
            deploy_variant(conf, dst, P)


if __name__ == "__main__":
    main()
