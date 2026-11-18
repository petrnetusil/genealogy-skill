#!/usr/bin/env python3
"""20th-century print from the Czech National Library's Kramerius (ndk.cz): search, snippets from non-public pages,
bulk reading and address search.

Most print from 1900–2000 is "private", but with DNNT (out-of-commerce works) – readable after logging in at ndk.cz
(reference/countries/czech-republic.md → DNNT). Search and snippets work without logging in; the full text and scan of a non-public
page only through a logged-in browser.

Usage (from the project root):
  dnnt.py search '<solr query>' [--from 1925 --to 1940] [--title 'Adresář*'] [--max 200] [--save name]
      pages with a hit: year | title | page | access (public / DNNT / library only) | pid | snippets.
      Query as in kramerius.py, e.g. 'text_ocr:"Dlouhá 14"'. --save stores the list in work/dnnt/<name>.tsv.
      Note: --from/--to drop periodical issues without a date – with few hits try without them too.
  dnnt.py context <pid> '<words>'
      snippets from the given page (also non-public) around the words – context without logging in; 0 snippets =
      the words are not on the page. A snippet from OCR is "lit" (literature), not "doc" (doc = read on the scan).
  dnnt.py ocr <list.tsv | key=pid | pid ...> [--folder work/dnnt/ocr]
      downloads the OCR text of public pages (<key>.txt); for non-public ones it tells you to use "js".
  dnnt.py js <list.tsv | key=pid ...> [--images]
      prints a JS function for chrome-devtools evaluate_script on a logged-in ndk.cz page (the user logs in
      themselves in the window opened by new_page). Save the output with the filePath parameter into a file, then
      "unpack" it. --images adds the scans (base64, ~1–9 MB per page – only a few pages at a time).
  dnnt.py unpack <output.json> [folder=work/dnnt/ocr]
      turns the JS output into <key>.txt and <key>.jpg.
  dnnt.py address <folder> "<Street>" <number> [number ...]
      goes through *.txt and finds the address also when split at a line end ("Dlou-\\nhá 14"), with the Czech
      variants "č.", "čp.", "čís." (= no.); prints the file, the page header (section of the directory) and the
      surroundings of the hit.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: network through our brake
tools/polite.py, the project's User-Agent. Without logging in only search/context/ocr of public pages; "js" (logged-in
browser) only when the user asks for it – DNNT is for reading only, do not redistribute anything.
"""
import base64, glob, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # shared rate limit for archive websites (polite.py)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(os.path.join(ROOT, "data", "STATUS.md")):   # run from the skill folder: no project data there, writes would go into the skill
    sys.exit(f"{os.path.basename(__file__)}: {ROOT} is not a project folder (data/STATUS.md is missing). "
             f"Run the project copy from the project root: python3 -I tools/{os.path.basename(__file__)} …")
API = "https://kramerius5.nkp.cz/search/api/v5.0/"
DIR = os.path.join(ROOT, "work", "dnnt")
UA = {"User-Agent": polite.UA}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def solr(params):
    return json.loads(get(API + "search?" + urllib.parse.urlencode({"wt": "json", **params})))


def access(x):
    d = x.get("dostupnost") or "?"   # Kramerius field names are Czech (dostupnost = availability)
    dn = x.get("dnnt") or "dnnto" in (x.get("dnnt-labels") or [])   # "dnnto" = online after logging in
    return "DNNT" if d == "private" and dn else ("library only" if d == "private" else d)


def page_no(x):
    return str(x["details"][0]).split()[0] if x.get("details") else ""


def clean(h):
    return re.sub(r"\s+", " ", h).replace("<em>", "[").replace("</em>", "]")


def opt(a, name, default=None):
    if name in a:
        i = a.index(name)
        v = a[i + 1]
        del a[i:i + 2]
        return v
    return default


def search(a):
    start_y, end_y, title = opt(a, "--from"), opt(a, "--to"), opt(a, "--title")
    mx, save = int(opt(a, "--max", "200")), opt(a, "--save")
    q = f"({a[0]}) AND fedora.model:page"
    if start_y or end_y:
        q += f" AND datum_begin:[{start_y or '*'} TO {end_y or '*'}]"
    if title:
        q += f' AND root_title:{title}'
    rows, start, docs, hl, total = min(mx, 100), 0, [], {}, 0
    while start < mx:
        d = solr({"q": q, "rows": rows, "start": start, "fl": "PID,root_title,datum_str,details,dostupnost,dnnt,dnnt-labels",
                  "hl": "true", "hl.fl": "text_ocr", "hl.fragsize": "200", "hl.snippets": "3"})
        total = d["response"]["numFound"]
        docs += d["response"]["docs"]
        hl.update(d.get("highlighting", {}))
        start += rows
        if start >= total:
            break
        time.sleep(0.5)
    print(f"found {total} pages, listing {len(docs)}")
    lines = []
    for x in sorted(docs, key=lambda x: (x.get("datum_str") or "")[-4:]):
        u = " || ".join(clean(h) for h in hl.get(x["PID"], {}).get("text_ocr", []))[:300]
        print(f"{x.get('datum_str', '')} | {str(x.get('root_title'))[:45]} | p. {page_no(x)} | {access(x)} | {x['PID']}\n    {u}")
        lines.append("\t".join([x["PID"], x.get("datum_str", ""), page_no(x), access(x), str(x.get("root_title"))[:80]]))
    if save:
        os.makedirs(DIR, exist_ok=True)
        path = os.path.join(DIR, save + ".tsv")
        open(path, "w", encoding="utf-8").write("pid\tdate\tpage\taccess\ttitle\n" + "\n".join(lines) + "\n")
        print("saved:", os.path.relpath(path, ROOT))


def context(pid, words):
    d = solr({"q": f'PID:"{pid}" AND text_ocr:({words})', "rows": 1, "fl": "PID,root_title,datum_str,details,dostupnost,dnnt,dnnt-labels",
              "hl": "true", "hl.fl": "text_ocr", "hl.fragsize": "400", "hl.snippets": "20", "hl.mergeContiguous": "true"})
    if not d["response"]["docs"]:
        print("0 snippets – the words are not on the page (or the OCR read them differently).")
        return
    x = d["response"]["docs"][0]
    print(f"{x.get('datum_str', '')} | {x.get('root_title')} | p. {page_no(x)} | {access(x)}")
    for h in d.get("highlighting", {}).get(pid, {}).get("text_ocr", []):
        print("  …", clean(h))


def items(args):
    """[(key, pid)] from a .tsv file, from "key=pid" or from bare pids."""
    out = []
    for a in args:
        if a.endswith(".tsv") and os.path.exists(a):
            for r in open(a, encoding="utf-8").read().splitlines()[1:]:
                c = r.split("\t")
                if c and c[0].startswith("uuid:"):
                    out.append((re.sub(r"\W+", "_", f"{c[1][-4:]}_{c[2]}_{c[0][5:13]}").strip("_"), c[0]))
        elif "=" in a:
            k, p = a.split("=", 1)
            out.append((k, p))
        elif a.startswith("uuid:"):
            out.append((a[5:13], a))
    return out


def ocr(args):
    folder = opt(args, "--folder", os.path.join(DIR, "ocr"))
    pages = items(args)
    os.makedirs(folder, exist_ok=True)
    restricted = []
    for k, pid in pages:
        out = os.path.join(folder, k + ".txt")
        if os.path.exists(out):
            continue
        try:
            open(out, "wb").write(get(f"{API}item/{pid}/streams/TEXT_OCR"))
            time.sleep(0.3)
        except urllib.error.HTTPError as e:
            if e.code == 403:
                restricted.append(f"{k}={pid}")
            else:
                raise
    print(f"downloaded into {os.path.relpath(folder, ROOT)}; non-public: {len(restricted)}")
    if restricted:
        print("Read the non-public pages through the logged-in browser:  dnnt.py js " + " ".join(restricted[:40]) +
              (" …" if len(restricted) > 40 else ""))


def js(args):
    images = "--images" in args
    pages = items([a for a in args if a != "--images"])
    if not pages:
        sys.exit("No pages – give key=pid or a .tsv list.")
    if images and len(pages) > 6:
        print("// NOTE: more than 6 scans – the output will be large; split it into smaller batches.", file=sys.stderr)
    mapping = json.dumps(dict(pages), ensure_ascii=False)
    print(f"""async () => {{ const p = {mapping}; const out = {{}};
  for (const [k, v] of Object.entries(p)) {{
    const r = await fetch('/search/api/v5.0/item/' + v + '/streams/TEXT_OCR');
    out[k] = {{pid: v, status: r.status, text: await r.text()}};{'''
    const ri = await fetch('/search/img?pid=' + v + '&stream=IMG_FULL&action=GETRAW');
    const b = new Uint8Array(await ri.arrayBuffer()); let s = '';
    for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768));
    out[k].img = btoa(s);''' if images else ''}
  }}
  return out; }}""")


def unpack(path, folder):
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, str):   # chrome-devtools sometimes stores the result as a string with JSON
        d = json.loads(d)
    os.makedirs(folder, exist_ok=True)
    for k, v in d.items():
        if v.get("status") == 200 and v.get("text"):
            open(os.path.join(folder, k + ".txt"), "w", encoding="utf-8").write(v["text"])
        elif v.get("status"):
            print(f"{k}: HTTP {v['status']} – is the user logged in at ndk.cz?")
        if v.get("img"):
            open(os.path.join(folder, k + ".jpg"), "wb").write(base64.b64decode(v["img"]))
    print(f"unpacked {len(d)} pages into {os.path.relpath(folder, ROOT)}")


def no_diacritics(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def address(folder, street, numbers):
    # join split words ("Dlou-\nhá") and normalise spaces; compare without diacritics (OCR "Dlouha", "Dlóuhá")
    street_rx = r"\W*".join(re.escape(c) for c in no_diacritics(street).replace(" ", ""))
    # optional Czech number prefixes č. / čp. / čís. (= no.), already without diacritics here
    pattern = re.compile(rf"{street_rx}\W{{0,3}}(?:c\.?\s*p\.?|cis\.?|c\.)?\s*({'|'.join(map(re.escape, numbers))})(?!\d)")
    n = 0
    for f in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        t = open(f, encoding="utf-8-sig", errors="replace").read()
        joined = re.sub(r"[-¬]\s*\n\s*", "", t)
        one_line = re.sub(r"\s+", " ", joined)
        nd = no_diacritics(one_line)
        head = " / ".join(r.strip() for r in t.splitlines()[:3] if r.strip())[:90]
        for m in pattern.finditer(nd):
            n += 1
            print(f"{os.path.basename(f)} | {head}\n    …{one_line[max(0, m.start() - 160):m.end() + 40]}")
    print(f"{n} hits. Check on the scan (doc) and convert the address by the date into the house number "
          "(reference/registers.md → house numbers).")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    c, a = a[0], a[1:]
    if c == "search" and a:
        search(a)
    elif c == "context" and len(a) == 2:
        context(*a)
    elif c == "ocr" and a:
        ocr(a)
    elif c == "js" and a:
        js(a)
    elif c == "unpack" and a:
        unpack(a[0], a[1] if len(a) > 1 else os.path.join(DIR, "ocr"))
    elif c == "address" and len(a) >= 3:
        address(a[0], a[1], a[2:])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
