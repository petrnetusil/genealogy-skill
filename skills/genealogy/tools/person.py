#!/usr/bin/env python3
"""Edits one person in data/people.py – only that person's line changes, the rest of the file stays verbatim.

Usage (from the project root):
  python3 -I tools/person.py <number> [st=doc] [r+=key] [f+=text] [f-=text] [fr=old=>new]
                             [note=text] [note+=text] [summary=text] [y=...] [n=...] [sex=F]
    r+=key        add a record key to `r` (if not there yet)
    f+=text       add a fact;  f-=text  remove a fact;  fr=old=>new  replace a fact
    note+=text    append to the note;  <field>=value  set a field (st, y, n, note, summary, sex …)
The person must be on one line, as ` <number>: dict(...),` or ` <number>: {...},` (both styles are kept).
"""
import ast, re, sys, pathlib
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    sys.exit(__doc__.strip())
p = pathlib.Path("data/people.py")
lines = p.read_text(encoding="utf-8-sig").split("\n")
n = sys.argv[1]
for i, l in enumerate(lines):
    m = re.match(rf"(\s*){re.escape(n)}\s*:\s*(dict\(|\{{)", l)
    if m:
        break
else:
    sys.exit(f"person {n} not found (expected a line ` {n}: dict(...),` or ` {n}: {{...}},`)")
indent, style = m.group(1), m.group(2)
body = l.split(":", 1)[1].strip().rstrip(",")
try:
    d = eval(body, {"__builtins__": {}, "dict": dict}) if style == "dict(" else ast.literal_eval(body)
except Exception as e:  # noqa: BLE001
    sys.exit(f"person {n}: the line cannot be read ({e}) – is the person split over several lines? Edit it by hand.")
for a in sys.argv[2:]:
    if a.startswith("r+="):
        d.setdefault("r", [])
        a[3:] in d["r"] or d["r"].append(a[3:])
    elif a.startswith("f+="):
        d.setdefault("f", [])
        a[3:] in d["f"] or d["f"].append(a[3:])
    elif a.startswith("f-="):
        d["f"] = [x for x in d.get("f", []) if x != a[3:]]
    elif a.startswith("fr="):
        old, new = a[3:].split("=>", 1)
        if old not in d.get("f", []):
            sys.exit(f"person {n}: fact not found: {old}")
        d["f"][d["f"].index(old)] = new
    elif a.startswith("note+="):
        d["note"] = (d.get("note", "") + " " + a[6:]).strip()
    elif "=" in a:
        k, v = a.split("=", 1)
        d[k] = v
    else:
        sys.exit(f"unknown argument: {a} (see --help)")
order = ["n", "y", "st", "f", "r", "note", "summary", "sex"]
keys = [k for k in order if k in d] + [k for k in d if k not in order]
keys = [k for k in keys if k not in ("note", "summary", "sex") or d[k]]
if style == "dict(":
    parts = [f"{k}={d[k]!r}" for k in keys]
    lines[i] = f"{indent}{n}: dict({', '.join(parts)}),"
else:
    parts = [f"{k!r}: {d[k]!r}" for k in keys]
    lines[i] = f"{indent}{n}: {{{', '.join(parts)}}},"
p.write_text("\n".join(lines), encoding="utf-8")
print(lines[i][:300])
