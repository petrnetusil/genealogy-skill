#!/usr/bin/env python3
"""MyHeritage Family Tree Builder backup (.ftb = SQLite) -> GEDCOM and an overview of the direct line.

Usage (from the project root):
  python3 -I tools/ftb_export.py <tree.ftb> <output.ged>
      the whole tree as GEDCOM for tools/ged_import.py (without addresses, e-mails, phones and ID numbers)
  python3 -I tools/ftb_export.py <tree.ftb> <output.ged> "Given Surname" <birth year> <line.md> [folder with Photos]
      in addition an overview of the direct ancestors of this person (Kekulé numbers): all facts, notes,
      ORIGIN of the data (other trees via Smart Match) and attached photos/documents.
  … --lang <code>   preferred data language of the tree when it has several (MyHeritage code, e.g. 20 = Czech;
                    default 0 = the tree's default language)

A MyHeritage backup (a ZIP with the file <tree>.ftb and a folder Photos/) is not GEDCOM but an SQLite database.
Unpack the ZIP into its own folder in documents/. On Windows run `python -I -X utf8 tools/ftb_export.py …`.
"""
import html, os, pathlib, re, sqlite3, sys
from collections import defaultdict
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

SKIP_TAGS = {"ADDR", "EMAIL", "PHON", "WWW", "FAX", "IDNO", "SSN"}   # contacts and ID numbers do not belong in the export
LANG = 0   # preferred data language (--lang)
TAG_MAP = {"BAPM": "CHR"}                                          # baptism – ged_import knows only CHR


def skip(tag, ftype, val):
    """Contacts of living people: separate facts ADDR/EMAIL/PHON…, RESI of such a type
    and RESI whose text is XML from the address form (<Address1>, <Email>, <Phone>, <City>…)."""
    return tag in SKIP_TAGS or (tag == "RESI" and (ftype in SKIP_TAGS or val.lstrip().startswith("<")))


def txt(b):
    if b is None:
        return ""
    s = b.decode("utf-8", "replace") if isinstance(b, bytes) else str(b)
    if any("\x80" <= ch <= "\x9f" for ch in s):   # language 0 is often cp1250 read as latin-1
        try:
            s = s.encode("latin-1").decode("cp1250")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return s.strip()


def date_text(b):
    """The date is wrapped (protobuf): 0x0A, length, text "4 MAR 1973"."""
    if not b:
        return ""
    if b[0] != 0x0A:
        return txt(b)
    n, shift, i = 0, 0, 1
    while True:
        n |= (b[i] & 0x7F) << shift
        i += 1
        if not b[i - 1] & 0x80:
            break
        shift += 7
    return b[i:i + n].decode("utf-8", "replace").strip()


def pick(rows):
    """rows = [(language, value…)] – the preferred language (--lang) first, then the default (0), then the rest."""
    rows = sorted(rows, key=lambda r: 0 if r[0] == LANG else 1 if r[0] == 0 else 2)
    return rows[0] if rows else None


def load(path):
    # immutable=1: the database is in WAL mode – otherwise SQLite would create -shm/-wal files next to the backup
    c = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    c.text_factory = bytes
    q = lambda s: c.execute(s).fetchall()
    D = {}
    places = defaultdict(list)
    for pid, lang, p in q("select place_id, data_language, place from places_lang_data"):
        places[pid].append((lang, txt(p)))
    D["place"] = {k: pick(v)[1] for k, v in places.items()}

    names = defaultdict(list)
    for iid, lang, fn, ln, ms, nick in q("""select d.individual_id, l.data_language, l.first_name, l.last_name,
            l.married_surname, l.nickname from individual_lang_data l
            join individual_data_set d using(individual_data_set_id) where d.delete_flag = 0"""):
        names[iid].append((lang, txt(fn), txt(ln), txt(ms), txt(nick)))
    D["ind"] = {}
    for iid, sex, alive in q("select individual_id, gender, is_alive from individual_main_data where delete_flag = 0"):
        n = pick(names.get(iid, [])) or (0, "", "", "", "")
        D["ind"][iid] = dict(first=n[1], last=n[2], married=n[3], nick=n[4], sex=txt(sex) or "U")
        # is_alive (1/2/3) in the backup does not match reality – not used

    flang = defaultdict(list)
    for fid, lang, head, cause in q("select individual_fact_id, data_language, header, cause_of_death from individual_fact_lang_data"):
        flang[fid].append((lang, txt(head), txt(cause)))
    D["facts"] = defaultdict(list)
    for fid, iid, tok, ftype, age, d, pid, cur in q("""select individual_fact_id, individual_id, token, fact_type, age, date,
            place_id, is_current from individual_fact_main_data where delete_flag = 0
            order by individual_id, is_current desc, sorted_date"""):
        l = pick(flang.get(fid, [])) or (0, "", "")
        if skip(txt(tok), txt(ftype), l[1]):
            continue
        D["facts"][iid].append(dict(id=fid, tag=txt(tok), type=txt(ftype), age=txt(age), date=date_text(d),
                                    place=D["place"].get(pid, ""), val=l[1], cause=l[2]))

    D["fam"] = defaultdict(lambda: {"h": None, "w": None, "c": []})
    for fid, iid, role in q("""select family_id, individual_id, individual_role_type from family_individual_connection
            where delete_flag = 0 order by family_id, child_order_in_family"""):
        if iid not in D["ind"]:   # person deleted only in the main table – no dangling references (Gramps, MyHeritage)
            continue
        f = D["fam"][fid]
        if role == 2:
            f["h"] = iid
        elif role == 3:
            f["w"] = iid
        elif role == 5:
            f["c"].append(iid)
    fflang = defaultdict(list)
    for ffid, lang, head in q("select family_fact_id, data_language, header from family_fact_lang_data"):
        fflang[ffid].append((lang, txt(head)))
    D["famfacts"] = defaultdict(list)
    for ffid, fid, tok, ftype, d, pid in q("""select family_fact_id, family_id, token, fact_type, date, place_id
            from family_fact_main_data where delete_flag = 0 order by family_id, sorted_date"""):
        l = pick(fflang.get(ffid, [])) or (0, "")
        if skip(txt(tok), txt(ftype), l[1]):
            continue
        D["famfacts"][fid].append(dict(tag=txt(tok), type=txt(ftype), date=date_text(d),
                                       place=D["place"].get(pid, ""), val=l[1]))

    tokens = {tid: (eid, it) for tid, eid, it in q("select token_on_item_id, entity_id, item_type from token_on_item")}
    nlang = defaultdict(list)
    for nid, lang, t in q("select note_id, data_language, note_text from note_lang_data"):
        nlang[nid].append((lang, txt(t)))
    fact_owner = {f["id"]: iid for iid, fs in D["facts"].items() for f in fs}
    D["notes"] = defaultdict(list)
    for nid, tid in q("select note_id, external_token_on_item_id from note_to_item_connection where delete_flag = 0"):
        eid, it = tokens.get(tid, (None, None))
        owner = eid if it == 1 else fact_owner.get(eid) if it == 3 else None
        t = (pick(nlang.get(nid, [])) or (0, ""))[1]
        if owner is not None and t:
            D["notes"][owner].append(t)

    slang = defaultdict(list)
    for sid, lang, title, author in q("select source_id, data_language, title, author from source_lang_data"):
        slang[sid].append((lang, txt(title), txt(author)))
    D["sources"] = defaultdict(set)
    for sid, page, tid in q("select source_id, page, external_token_on_item_id from citation_main_data where delete_flag = 0"):
        eid, it = tokens.get(tid, (None, None))
        owner = eid if it == 1 else fact_owner.get(eid) if it == 3 else None   # citation at the person and at their fact
        if owner is not None:
            s = pick(slang.get(sid, [])) or (0, "?", "")
            D["sources"][owner].add(s[1] + (f" ({s[2]})" if s[2] else ""))

    mlang = defaultdict(list)
    for mid, lang, title, desc in q("select media_item_id, data_language, title, description from media_item_lang_data"):
        mlang[mid].append((lang, txt(title), txt(desc)))
    D["media"] = defaultdict(list)
    for mid, eid, it, size in q("""select c.media_item_id, c.token_entity_id, c.token_item_type, m.file_size
            from media_item_to_item_connection c join media_item_main_data m using(media_item_id) where c.delete_flag = 0"""):
        if it == 1:
            m = pick(mlang.get(mid, [])) or (0, "", "")
            D["media"][eid].append((mid, m[1], m[2], int(txt(size) or 0)))
    return D


def full_name(p):
    return re.sub(r"\s+", " ", f"{p['first']} {p['last']}").strip() or "(no name)"


def chunks(s, n=240):
    """Long text in pieces for CONC (GEDCOM 5.5.1 lines have at most 255 characters); never splits at a space, so it is not lost."""
    out = []
    while len(s) > n:
        i = n
        while i > n // 2 and (s[i - 1].isspace() or s[i].isspace()):
            i -= 1
        out.append(s[:i])
        s = s[i:]
    return out + [s]


def gtext(level, tag, value):
    out = []
    for k, line in enumerate((value or "").replace("\r", "").split("\n")):
        parts = chunks(line.rstrip())
        head = f"{level} {tag}" if k == 0 else f"{level + 1} CONT"
        out.append(f"{head} {parts[0]}" if parts[0] else head)
        out += [f"{level + 1} CONC {p}" for p in parts[1:]]
    return out


def write_ged(D, out):
    famc, fams = defaultdict(list), defaultdict(list)
    for fid, f in D["fam"].items():
        for p in (f["h"], f["w"]):
            if p:
                fams[p].append(fid)
        for ch in f["c"]:
            famc[ch].append(fid)
    L = ["0 HEAD", "1 SOUR ftb_export", "1 GEDC", "2 VERS 5.5.1", "1 CHAR UTF-8"]
    for iid, p in D["ind"].items():
        L.append(f"0 @I{iid}@ INDI")
        L.append(f"1 NAME {p['first']} /{p['last']}/".replace("  ", " "))
        if p["married"]:
            L.append(f"1 NAME {p['first']} /{p['married']}/")
            L.append("2 TYPE married")
        L.append(f"1 SEX {p['sex']}")
        for f in D["facts"].get(iid, []):
            tag = TAG_MAP.get(f["tag"], f["tag"])
            if tag == "EVEN":
                L += gtext(1, "EVEN", f["val"])
                L.append(f"2 TYPE {f['type']}")
            else:
                L += gtext(1, tag, f["val"])
            if f["date"]:
                L.append(f"2 DATE {f['date']}")
            if f["place"]:
                L.append(f"2 PLAC {f['place']}")
            if f["cause"]:
                L.append(f"2 CAUS {f['cause']}")
        for n in D["notes"].get(iid, []):
            L += gtext(1, "NOTE", n)
        L += [f"1 FAMC @F{x}@" for x in famc.get(iid, [])]
        L += [f"1 FAMS @F{x}@" for x in fams.get(iid, [])]
    for fid, f in D["fam"].items():
        L.append(f"0 @F{fid}@ FAM")
        if f["h"]:
            L.append(f"1 HUSB @I{f['h']}@")
        if f["w"]:
            L.append(f"1 WIFE @I{f['w']}@")
        L += [f"1 CHIL @I{c}@" for c in f["c"]]
        for e in D["famfacts"].get(fid, []):
            L += gtext(1, e["tag"], e["val"])
            if e["tag"] == "EVEN" and e["type"]:
                L.append(f"2 TYPE {e['type']}")
            if e["date"]:
                L.append(f"2 DATE {e['date']}")
            if e["place"]:
                L.append(f"2 PLAC {e['place']}")
    L.append("0 TRLR")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("GEDCOM:", out, "|", len(D["ind"]), "people,", len(D["fam"]), "families")


def birth_year(D, iid):
    for f in D["facts"].get(iid, []):
        if f["tag"] in ("BIRT", "CHR", "BAPM"):
            m = re.search(r"\d{4}", f["date"])
            if m:
                return int(m.group())
    return None


def write_line(D, root, out, photos):
    parents = {}
    for f in D["fam"].values():
        for ch in f["c"]:
            parents.setdefault(ch, (f["h"], f["w"]))
    files = defaultdict(list)   # files in Photos/ carry another number than media_item_id – matched by size
    if photos and os.path.isdir(photos):
        for fn in os.listdir(photos):
            files[os.path.getsize(os.path.join(photos, fn))].append(fn)
    tree, todo, seen = {1: root}, [1], {root}
    while todo:
        k = todo.pop(0)
        if k >= 2 ** 24:
            continue
        h, w = parents.get(tree[k], (None, None))
        for kk, p in ((2 * k, h), (2 * k + 1, w)):
            if p and p in D["ind"]:
                if p in seen:   # loop or an ancestor appearing several times (SAME)
                    tree[kk] = p
                    continue
                seen.add(p)
                tree[kk] = p
                todo.append(kk)
    L = ["# Direct line from MyHeritage (Family Tree Builder backup)", "",
         "Working extract – the data are NOT verified by a register. \"Origin\" = where the detail in the tree came from.", ""]
    for k in sorted(tree):
        iid = tree[k]
        p = D["ind"][iid]
        g = k.bit_length() - 1
        L.append(f"## {k}. {full_name(p)}  (generation {g}, id {iid})")
        if p["married"]:
            L.append(f"- married surname: {p['married']}")
        for f in D["facts"].get(iid, []):
            label = f["type"] if f["tag"] == "EVEN" else f["tag"]
            bits = [x for x in (f["val"], f["date"], f["place"], f"cause: {f['cause']}" if f["cause"] else "",
                                f"age {f['age']}" if f["age"] else "") if x]
            if bits:
                L.append(f"- {label}: {' | '.join(bits)}")
        for fid, f in D["fam"].items():
            if iid in (f["h"], f["w"]):
                sp = f["w"] if iid == f["h"] else f["h"]
                spn = full_name(D["ind"][sp]) if sp in D["ind"] else "?"
                ev = "; ".join(" | ".join(x for x in (e["tag"], e["date"], e["place"]) if x) for e in D["famfacts"].get(fid, []))
                kids = ", ".join(f"{full_name(D['ind'][c])} ({birth_year(D, c) or '?'})" for c in f["c"] if c in D["ind"])
                L.append(f"- family with: {spn} — {ev or 'no marriage details'}; children: {kids or '—'}")
        for n in D["notes"].get(iid, []):
            n = html.unescape(re.sub(r"<[^>]+>", " ", n))
            L.append("- note: " + re.sub(r"\s+", " ", n).strip()[:2000])
        src = sorted(D["sources"].get(iid, []))
        L.append("- origin: " + ("; ".join(src) if src else "no citation (entered by hand in the own tree)"))
        for mid, title, desc, size in D["media"].get(iid, []):
            fl = ", ".join(files.get(size, [])) or "(file not found)"
            L.append(f"- photo/document: {fl} — {title}{' – ' + desc if desc else ''}")
        L.append("")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    print("Direct line:", out, "|", len(tree), "ancestors, furthest generation", max(k.bit_length() - 1 for k in tree))


def main():
    global LANG
    if "--lang" in sys.argv:
        i = sys.argv.index("--lang")
        try:
            LANG = int(sys.argv[i + 1])
        except (IndexError, ValueError):
            sys.exit("--lang needs a number (MyHeritage data language code, e.g. 20)")
        del sys.argv[i:i + 2]
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    D = load(sys.argv[1])
    write_ged(D, sys.argv[2])
    if len(sys.argv) >= 6:
        q, y = sys.argv[3].lower().split(), int(sys.argv[4])
        hits = [i for i, p in D["ind"].items() if all(w in full_name(p).lower() for w in q) and birth_year(D, i) == y]
        if len(hits) != 1:
            sys.exit(f"The home person was not found unambiguously: {hits}")
        write_line(D, hits[0], sys.argv[5], sys.argv[6] if len(sys.argv) > 6 else "")


if __name__ == "__main__":
    main()
