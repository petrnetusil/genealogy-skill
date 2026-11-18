#!/usr/bin/env python3
"""Adds or replaces one item in the project data – the file format stays the same (indent 1, non-ASCII characters
kept, LF line endings), so the change in the history is just that one item.

Usage (from the project root):
  write.py <file> <key> <input.json> [--merge | --replace]
  write.py documents <old_key> --rename <new_key> [--preview]
    file       records | volumes | transcripts | highlights | places | documents   (= data/<file>.json)
    key        records: the record's "key"; documents: "img"; others: the key in the dictionary (volume id,
               record key, place name)
    input.json a file with one JSON object (write it with the Write tool into work/), "-" = from standard input
    --merge    only changes / adds the given fields, keeps the item's other fields
    --replace  replaces the whole item, even if the new input lacks some existing fields (those are lost)
    --rename   renames a document's "img" including its crops (crops/, sources/, web/public/), highlights,
               website.json "home.photo" and img/…jpg links in data and web/src; --preview only prints what it
               would change (changes nothing)
An item with the same key is replaced, otherwise it is appended. If the replacement lacks fields that the item had,
the tool changes nothing and lists them (then use --merge or --replace). Do not use Python scripts or `sed -i` on data.

  write.py link <person> <record key> [<key> …]
    Adds the key(s) to the `r` list in data/people.py: person = Ahnentafel number (P), or part of the name of a side
    relative (SIDE, must match exactly one). The rest of the file stays verbatim; the key must exist in records.json.

--rename taken from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted (only the added command, other
behaviour of this tool unchanged); originally from the fork xkraust/rodokmen-skill, commit 79d3685
(https://github.com/xkraust/rodokmen-skill/commit/79d36850afaa080b0ebcf70a368cbbb5237d700e), author xkraust, MIT.
"""
import ast, json, os, re, sys
import tempfile, unicodedata
from pathlib import Path
from urllib.parse import quote   # only encodes file names in links (--rename), no network
for _s in (sys.stdout, sys.stderr):   # UTF-8 output even on Windows without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):   # input "-" (pipe, heredoc) is UTF-8; on Windows it would be read as cp1250
    sys.stdin.reconfigure(encoding="utf-8-sig")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTS = {"records": "key", "documents": "img"}   # files holding a list: the field that identifies an item
DICTS = {"volumes", "transcripts", "highlights", "places"}
WS = re.compile(r"\s*")


def items(text):
    """Top-level items: [(key or None, start of value, end of value)] – positions in the original text."""
    dec, i = json.JSONDecoder(), WS.match(text).end()
    opening, i, out = text[i], i + 1, []
    while True:
        i = WS.match(text, i).end()
        if text[i] in "]}":
            return out
        key = None
        if opening == "{":
            key, i = dec.raw_decode(text, i)
            i = WS.match(text, WS.match(text, i).end() + 1).end()   # past the colon
        _, j = dec.raw_decode(text, i)
        out.append((key, i, j))
        i = WS.match(text, j).end()
        if text[i] == ",":
            i += 1


def like(text, s, e, v):
    """A JSON value in the same style as text[s:e] (on one line, or indented by one space)."""
    if "\n" not in text[s:e]:
        return json.dumps(v, ensure_ascii=False)
    indent = text[text.rfind("\n", 0, s) + 1:s]
    indent = indent[:len(indent) - len(indent.lstrip())]
    return json.dumps(v, ensure_ascii=False, indent=1).replace("\n", "\n" + indent)


def _atomic_bytes(path, content):
    """Write next to the target and replace it atomically, never leaving a half-written file."""
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def rename_document(root, old, new, preview=False):
    """Renames a document (img in data/documents.json), its crops and known links; on error reverts what was done.

    Taken from the fork xkraust/rodokmen-skill, commit 79d3685
    (https://github.com/xkraust/rodokmen-skill/commit/79d36850afaa080b0ebcf70a368cbbb5237d700e), author xkraust.
    Changes in rodokmen-plus: collisions are also checked against data/maps.json, a missing crop is only reported
    (a document without an image can be renamed too). Taken from zbysekvoda/rodokmen-plus@096315a (MIT), same logic."""
    root = Path(root).resolve()
    def canonical(key):
        return unicodedata.normalize("NFC", key).casefold()

    for key in (old, new):
        if (not key or key in (".", "..") or key[-1] in " ." or
                re.search(r'[<>:"/\\|?*\x00-\x1f]', key) or
                re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", key)):
            raise ValueError(f"Invalid image key: {key!r}; use a name without a path or extension.")
    if canonical(old) == canonical(new):
        raise ValueError("The new key must differ from the old one, also ignoring letter case.")

    def inside(path):
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"The path leads outside the project: {path}")
        return path

    docs_path = inside(root / "data" / "documents.json")
    raw = docs_path.read_bytes()
    text = raw.decode("utf-8-sig")
    docs = json.loads(text)
    if not isinstance(docs, list):
        raise ValueError("documents.json must be a list.")
    matches = [i for i, d in enumerate(docs) if isinstance(d, dict) and d.get("img") == old]
    if len(matches) != 1:
        raise ValueError(f"Key {old} must have exactly one item in documents.json.")
    if any(isinstance(d, dict) and canonical(d.get("img", "")) == canonical(new) for d in docs):
        raise ValueError(f"Document {new} already exists.")
    maps_path = inside(root / "data" / "maps.json")
    if maps_path.exists() and any(isinstance(m, dict) and canonical(m.get("img", "")) == canonical(new)
                                  for m in json.loads(maps_path.read_text(encoding="utf-8-sig"))):
        raise ValueError(f"Key {new} is already used by a map in maps.json.")
    records_path = inside(root / "data" / "records.json")
    if records_path.exists() and any(canonical(r["key"]) in (canonical(old), canonical(new))
                                     for r in json.loads(records_path.read_text(encoding="utf-8-sig"))):
        raise ValueError("The key is shared with a register record; renaming the document would change its image too.")

    idx = matches[0]
    _, s, e = items(text)[idx]
    changed = text[:s] + like(text, s, e, dict(docs[idx], img=new)) + text[e:]
    changes = {docs_path: changed.encode("utf-8")}
    moves = []
    for folder in ("crops", "sources", "web/public/img", "web/public/full"):
        directory = inside(root / folder)
        src, dst = inside(directory / (old + ".jpg")), inside(directory / (new + ".jpg"))
        if directory.exists() and any(canonical(p.name) == canonical(new + ".jpg") for p in directory.iterdir()):
            raise ValueError(f"The target file already exists: {dst}")
        if src.exists():
            if not src.is_file():
                raise ValueError(f"Expected a file: {src}")
            moves.append((src, dst))
    if not (root / "crops" / (old + ".jpg")).is_file():
        print(f"Note: crops/{old}.jpg is missing – only the data entry and links are renamed.")

    def links(value):
        # Relative paths and URLs, including URL-encoded names with diacritics.
        variants = [(old, False)]
        if quote(old, safe="") != old:
            variants.append((quote(old, safe=""), True))
        for before, encoded in variants:
            pattern = r"(?<![\w-])((?:img|full|crops|sources)/)" + re.escape(before) + r"\.jpg(?![\w.-])"
            def replace(match):
                url = encoded or match[1] in ("img/", "full/") or (match.start() > 0 and value[match.start() - 1] == "/")
                return match[1] + (quote(new, safe="") if url else new) + ".jpg"
            value = re.sub(pattern, replace, value)
        return value

    # Change source links; generated HTML and site.json are refreshed by the export/build.
    paths = list((root / "data").rglob("*"))
    src_dir = root / "web" / "src"
    if src_dir.exists():
        paths += [p for p in src_dir.rglob("*") if p.relative_to(src_dir).parts[0] not in ("data", "generated")]
    for path in paths:
        if not path.is_file() or path.suffix not in (".json", ".md", ".py", ".astro", ".js", ".ts", ".html", ".css"):
            continue
        inside(path)
        before = changes.get(path, path.read_bytes()).decode("utf-8-sig")
        after = before
        if path.suffix == ".json":
            data = json.loads(before)
            if path.name == "highlights.json" and old in data and any(canonical(k) == canonical(new) for k in data):
                raise ValueError(f"A highlight for {new} already exists.")
            photo_span, gate_span, highlight_span = None, None, None
            if path.name == "highlights.json" and old in data:
                start = next(s for k, s, e in items(before) if k == old)
                highlight_span = re.search(r'("(?:[^"\\]|\\.)*")\s*:\s*$', before[:start]).span(1)
            if path.name == "website.json":
                for field, start, end in items(before):
                    if field == "gate":
                        gate_span = (start, end)
                    if field == "home" and isinstance(data.get("home"), dict):
                        photo_span = next(((start + s, start + e) for k, s, e in items(before[start:end]) if k == "photo"), None)
            def token(match):
                if gate_span and gate_span[0] <= match.start() < gate_span[1]:
                    return match[0]
                value = json.loads(match[0])
                rename_key = (match.start(), match.end()) == highlight_span
                rename_value = (match.start(), match.end()) == photo_span
                replacement = new if value == old and (rename_key or rename_value) else links(value)
                return json.dumps(replacement, ensure_ascii=False) if replacement != value else match[0]
            after = re.sub(r'"(?:[^"\\]|\\.)*"', token, before)
            json.loads(after)
        else:
            after = links(before)
        if after != before:
            changes[path] = after.encode("utf-8")

    for src, dst in moves:
        print(f"{src.relative_to(root)} → {dst.relative_to(root)}")
    for path in changes:
        print(f"Update: {path.relative_to(root)}")
    if preview:
        print("Preview: nothing changed.")
        return

    originals = {p: p.read_bytes() for p in changes}
    moved, written = [], []
    try:
        for src, dst in moves:
            if dst.exists():
                raise FileExistsError(dst)
            os.rename(src, dst)
            moved.append((src, dst))
        for path, content in changes.items():
            _atomic_bytes(path, content)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            _atomic_bytes(path, originals[path])
        for src, dst in reversed(moved):
            os.rename(dst, src)
        raise
    print(f"Renamed: {old} → {new}. The original in documents/ is kept. "
          "Run check.py and the website export (export_web.py) so the website is regenerated.")


def byte_pos(src):
    """(line, column in UTF-8 bytes) from ast → byte position in the whole file."""
    starts, n = [0], 0
    for line in src.split(b"\n"):
        n += len(line) + 1
        starts.append(n)
    return lambda line, col: starts[line - 1] + col


def load_people(src):
    ns = {}
    exec(compile(src, "data/people.py", "exec"), ns)
    return ns


def link(person, keys):
    path = os.path.join(ROOT, "data", "people.py")
    src = open(path, "rb").read()
    try:
        tree = ast.parse(src)
        before = load_people(src)
    except Exception as e:
        sys.exit(f"data/people.py cannot be loaded ({e}) – fix it first (git diff shows the last change).")
    try:
        records = {z.get("key") for z in json.load(open(os.path.join(ROOT, "data", "records.json"), encoding="utf-8-sig"))}
    except (OSError, ValueError) as e:
        sys.exit(f"data/records.json cannot be read ({e}).")
    missing = [k for k in keys if k not in records]
    if missing:
        sys.exit(f"Record {', '.join(missing)} is not in data/records.json – write it first (write.py records …).")

    def value(name):   # P = {…} / SIDE = […] at the top level
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return node.value
        return None

    if re.fullmatch(r"\d+", person):
        P, k = value("P"), int(person)
        call = None
        if isinstance(P, ast.Dict):
            call = next((v for kl, v in zip(P.keys, P.values) if isinstance(kl, ast.Constant) and kl.value == k), None)
        if call is None:
            sys.exit(f"Person {k} is not in P (data/people.py).")
        label, old = f"person {k} ({before['P'][k].get('n')})", before["P"][k]
    else:
        side = value("SIDE")
        candidates = []
        for i, v in enumerate(side.elts if isinstance(side, ast.List) else []):
            if isinstance(v, ast.Dict):
                n = next((vv.value for kk, vv in zip(v.keys, v.values) if isinstance(kk, ast.Constant) and kk.value == "n"
                          and isinstance(vv, ast.Constant)), "")
            else:
                n = next((kw.value.value for kw in getattr(v, "keywords", []) if kw.arg == "n" and isinstance(kw.value, ast.Constant)), "")
            if person.lower() in str(n).lower():
                candidates.append((i, v, n))
        if len(candidates) != 1:
            sys.exit(f"Side relative \"{person}\" " + ("is not in SIDE." if not candidates else
                     "matches several: " + "; ".join(n for _, _, n in candidates) + " – give a longer part of the name."))
        i, call, n = candidates[0]
        label, old = f"side relative {n}", before["SIDE"][i]
    as_dict = isinstance(call, ast.Call) and getattr(call.func, "id", "") == "dict" and not call.args
    if not (as_dict or isinstance(call, ast.Dict)):
        sys.exit(f"{label}: expected dict(…) or {{…}} – edit it by hand.")

    new = [k for k in keys if k not in (old.get("r") or [])]
    if not new:
        print(f"{label}: already has the record, nothing changed.")
        return
    pos = byte_pos(src)
    if as_dict:
        r = next((kw.value for kw in call.keywords if kw.arg == "r"), None)
    else:
        r = next((v for kl, v in zip(call.keys, call.values) if isinstance(kl, ast.Constant) and kl.value == "r"), None)
    # quote style as in the file: the first string of the item (the sample and imports usually use apostrophes)
    first = next((n for n in ast.walk(call) if isinstance(n, ast.Constant) and isinstance(n.value, str)), None)
    apostrophe = first is not None and src[pos(first.lineno, first.col_offset):][:1] == b"'"
    string = lambda k: (repr(k) if apostrophe else json.dumps(k, ensure_ascii=False))
    insert = ", ".join(string(k) for k in new).encode("utf-8")
    if r is not None:
        if not isinstance(r, ast.List):
            sys.exit(f"{label}: r is not a list [ … ] – edit it by hand.")
        end = pos(r.end_lineno, r.end_col_offset) - 1          # position of "]"
        head = src[:end].rstrip()
        sep = b"" if not r.elts else (b" " if head.endswith(b",") else b", ")
    else:
        end = pos(call.end_lineno, call.end_col_offset) - 1   # position of ")" or "}"
        head = src[:end].rstrip()
        key_r = b"r=[" if as_dict else (string("r") + ": [").encode()
        sep = (b" " if head.endswith(b",") else b", ") + key_r
        insert += b"]"
    if r is not None and not r.elts:   # r=[] → r=["key"]
        result = src[:end] + insert + src[end:]
    else:   # after the last element / argument; spaces and the line end before "]" or ")" stay
        result = head + sep + insert + src[len(head):]

    # safety net: the file loads, the person got exactly those keys and nothing else changed
    try:
        after = load_people(result)
    except Exception as e:
        sys.exit(f"The change would break data/people.py ({e}) – nothing written, edit it by hand.")
    expected = dict(before)
    if label.startswith("person"):
        expected["P"] = {**before["P"], k: {**old, "r": (old.get("r") or []) + new}}
    else:
        expected["SIDE"] = [*before["SIDE"][:i], {**old, "r": (old.get("r") or []) + new}, *before["SIDE"][i + 1:]]
    for name in ("P", "SIDE", "LINES", "ISSUES", "HYPOTHESES", "SAME"):
        if after.get(name) != expected.get(name):
            sys.exit(f"The change would also alter {name} – nothing written, edit it by hand.")

    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(result)
    os.replace(tmp, path)
    print(f"data/people.py: {label} – added record {', '.join(new)}")


def main():
    if sys.argv[1:2] == ["link"]:
        if len(sys.argv) < 4:
            sys.exit(__doc__)
        return link(sys.argv[2], sys.argv[3:])
    if "--rename" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--preview"]
        if len(args) != 4 or args[0] != "documents" or args[2] != "--rename":
            sys.exit(__doc__)
        try:
            rename_document(ROOT, args[1], args[3], preview="--preview" in sys.argv)
        except (OSError, ValueError) as e:
            sys.exit(f"Renaming failed: {e}")
        return
    args = [a for a in sys.argv[1:] if a not in ("--merge", "--replace")]
    merge, replace = "--merge" in sys.argv, "--replace" in sys.argv
    if merge and replace:
        sys.exit("--merge and --replace cannot be combined – choose one.")
    if len(args) != 3 or args[0] not in {*LISTS, *DICTS}:
        sys.exit(__doc__)
    name, key, source = args
    path = os.path.join(ROOT, "data", name + ".json")
    try:
        obj = json.load(sys.stdin if source == "-" else open(source, encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        sys.exit(f"Input {source} is not valid JSON: {e}")
    if not isinstance(obj, dict):
        sys.exit("The input must be one JSON object ({…}).")
    is_list = name in LISTS
    if is_list and obj.setdefault(LISTS[name], key) != key:
        sys.exit(f"Key \"{key}\" does not match \"{LISTS[name]}\" in the input (\"{obj[LISTS[name]]}\").")
    text = open(path, encoding="utf-8-sig").read() if os.path.exists(path) else ""
    try:
        data = json.loads(text) if text.strip() else ([] if is_list else {})
        if not isinstance(data, list if is_list else dict):
            raise ValueError("expected " + ("a list [ … ]" if is_list else "a dictionary { … }"))
    except ValueError as e:
        sys.exit(f"data/{name}.json cannot be read ({e}) – fix it first (git diff shows the last change).")

    pos = items(text) if data else []
    if is_list:
        idx = next((n for n, x in enumerate(data) if isinstance(x, dict) and x.get(LISTS[name]) == key), None)
    else:
        idx = next((n for n, (k, _, _) in enumerate(pos) if k == key), None)
    old = None if idx is None else (data[idx] if is_list else data[key])
    new = {**old, **obj} if merge and isinstance(old, dict) else obj
    lost = sorted(set(old) - set(new)) if isinstance(old, dict) and not replace else []
    if lost:   # a silent replacement would delete fields (e.g. a volume's detailed list of places)
        sys.exit(f"data/{name}.json: \"{key}\" already exists and the replacement lacks the field(s) {', '.join(lost)} – "
                 "nothing changed. Add / change only the given fields: --merge; replace everything (fields are lost): --replace.")
    if not pos:   # empty or new file
        text = json.dumps([new] if is_list else {key: new}, ensure_ascii=False, indent=1) + "\n"
    elif idx is not None:   # replace only the text of that one item, the rest of the file stays verbatim
        _, s, e = pos[idx]
        text = text[:s] + like(text, s, e, new) + text[e:]
    else:   # append after the last item in the same style
        _, s, e = pos[-1]
        line = text[text.rfind("\n", 0, s) + 1:s]
        indent = line[:len(line) - len(line.lstrip())]
        text = (text[:e] + ",\n" + indent + ("" if is_list else json.dumps(key, ensure_ascii=False) + ": ")
                + like(text, s, e, new) + text[e:])
    json.loads(text)   # safety net: the result must be valid JSON

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)   # the whole file at once – an error never leaves it half-written
    print(f"data/{name}.json: {'added' if idx is None else 'changed'} \"{key}\"")


if __name__ == "__main__":
    main()
