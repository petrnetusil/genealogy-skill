"""Test of the check of partners at the neighbouring Kekulé number and of house numbers against the transcripts
in tools/check.py.

From the repository root, the check under test is the argument:
  python3 -I tests/check/test_numbers.py skills/genealogy/tools/check.py
  (Windows: python -I -X utf8 …)
Each case builds its own temporary project (data/people.py, records.json, transcripts.json) with an invented family,
copies check.py into it and runs it. Downloads nothing, only the standard library.
The transcriptions ("orig") keep register wording in the original languages (Czech, German, Latin) on purpose –
that is what real transcripts look like; the facts use the project's English syntax ("* 3 May 1900 Holice no. 34").
"""
import json, os, shutil, subprocess, sys, tempfile

CHECK = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy/tools/check.py")
PY = [sys.executable, "-I", "-X", "utf8"]
RESULTS = []


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def check(P, SAME=None, records=(), transcripts=None, sample=(), places=None):
    """Builds the project and returns the output of check.py; records with a key in `sample` are invented (like in
    the sample). When the check does not end with code 0 (data error, crash), the output starts with "EXIT CODE" and
    the case fails."""
    tmp = tempfile.mkdtemp(prefix="check_numbers_")
    try:
        write(os.path.join(tmp, "data", "people.py"), f"P = {P!r}\nSAME = {SAME or {}!r}\n")
        if places:
            write(os.path.join(tmp, "data", "places.json"), json.dumps(places, ensure_ascii=False))
        recs = [dict(key=k, kind="B", date="1900", title=k, summary=s, link="https://example.org/image",
                     **({"sample": True} if k in sample else {})) for k, s in records]
        write(os.path.join(tmp, "data", "records.json"), json.dumps(recs, ensure_ascii=False))
        write(os.path.join(tmp, "data", "transcripts.json"), json.dumps(transcripts or {}, ensure_ascii=False))
        os.makedirs(os.path.join(tmp, "tools"))
        shutil.copy(CHECK, os.path.join(tmp, "tools", "check.py"))
        r = subprocess.run(PY + [os.path.join(tmp, "tools", "check.py")], capture_output=True, text=True,
                           encoding="utf-8")
        return (f"EXIT CODE {r.returncode}\n" if r.returncode else "") + r.stdout + r.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def expect(name, output, text, wanted):
    ok = (text in output) == wanted and not output.startswith("EXIT CODE")
    RESULTS.append(ok)
    print(("OK   " if ok else "FAIL ") + name)
    if not ok:
        print(f"    {'expected' if wanted else 'did not expect'} \"{text}\" in the output:\n    "
              + output.replace("\n", "\n    "))


def person(n, *f, **kw):
    return dict(n=n, y="", st=kw.pop("st", "fam"), f=list(f), **kw)


PARTNER = "names partner"
BASE = {1: person("Petr Novák"), 2: person("Jan Novák", "× 1950 Holice Marie Králová"),
        3: person("Marie Králová", "× 1950 Holice Jan Novák")}

# 1. The partner is in the × fact
expect("partner named in the marriage – no warning", check(BASE), PARTNER, False)

# 2. The marriage belongs to someone else (second marriage of a widower stuck to the wife)
P = dict(BASE)
P[3] = person("Marie Králová", "× 1955 Holice Anna Hrubá")
out = check(P)
expect("marriage does not name the partner – warning", out,
       "person 3 (Marie Králová): no marriage (×) names partner 2", True)
expect("no warning for the partner with the right marriage", out, "person 2 (Jan Novák): no marriage", False)

# 3. Widower: second marriage with another woman and the marriage with the partner
P = dict(BASE)
P[2] = person("Jan Novák", "× 1950 Holice Marie Králová", "× 1960 Holice Anna Hrubá")
expect("second marriage next to the right one – no warning", check(P), PARTNER, False)

# 4. Diacritics and letter case, date and place before the name
P = dict(BASE)
P[2] = person("Jan Novák", "× 2 Feb 1950 Unserfrau MARIE KRALOVA")
expect("name without diacritics in capitals – no warning", check(P), PARTNER, False)

# 5. The partner is missing – an unknown partner is common
P = {1: person("Petr Novák"), 2: person("Jan Novák", "× 1950 Holice Anna Hrubá")}
expect("partner not in the data – no warning", check(P), PARTNER, False)

# 6. SAME: the ancestor is twice in the tree, the partner is at the other number
P = {1: person("Petr Novák"), 2: person("Jan Novák"), 3: person("Marie Králová"),
     4: person("Josef Novák", "× 1920 Holice Anna Malá"), 6: person("Karel Král"), 7: person("Ludmila Malá"),
     12: person("Josef Novák", "SAME PERSON as 4"), 13: person("Anna Malá", "× 1920 Holice Josef Novák")}
expect("SAME – partner at the other number named – no warning", check(P, SAME={12: 4}), PARTNER, False)
P[4] = person("Josef Novák", "× 1920 Holice Rozálie Hrubá")
out = check(P, SAME={12: 4})
expect("SAME – partner at the other number not named – warning", out,
       "person 4 (Josef Novák): no marriage (×) names partner 13", True)
P[4] = person("Josef Novák", "× 1920 Holice Anna Malá")
P[13] = person("Anna Malá", "× 1920 Holice Karel Hrubý")
expect("SAME – the alias is turned into the main person – warning at 13", check(P, SAME={12: 4}),
       "person 13 (Anna Malá): no marriage (×) names partner 4", True)

# House numbers
HN = "is in no cited record"
REC = [("baptism_jan_1900", "Baptism of Jan Novák in Holice")]
TR = {"baptism_jan_1900": {"orig": "[Date] 3. 5. 1900\n[House] No 34\n[Name] Jan", "translation": "Jan was born in Holice."}}
P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 34", st="doc", r=["baptism_jan_1900"])}
expect("house no. in the transcript as \"No 34\" – no warning", check(P, records=REC, transcripts=TR), HN, False)

P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 36", "farmer in Holice no. 134", st="doc", r=["baptism_jan_1900"])}
out = check(P, records=REC, transcripts=TR)
expect("house no. missing in the records – warning", out, "person 1 (Jan Novák): house no. 36 is in no cited record", True)
expect("house no. 134 does not match \"34\" (number boundary) – warning", out, "house no. 134 " + HN, True)

REC2 = [("baptism_jan_1900", "Baptism of Jan Novák, Holice no. 36")]
P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 36", st="doc", r=["baptism_jan_1900"])}
expect("house no. in the record's summary – no warning", check(P, records=REC2, transcripts=TR), HN, False)

P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 36", st="doc")}
expect("person without 'r' – no warning", check(P, records=REC, transcripts=TR), HN, False)

P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 36", st="doc", r=["baptism_jan_1900"])}
expect("cites only an invented sample record – no warning", check(P, records=REC, sample={"baptism_jan_1900"}), HN,
       False)
P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 36", "farmer, Holice no. 41", st="doc",
               r=["baptism_jan_1900", "marriage_jan_1925"])}
out = check(P, records=REC + [("marriage_jan_1925", "Groom Jan Novák (Holice no. 41)")], sample={"marriage_jan_1925"})
expect("real and invented record – the house no. from the sample's summary counts", out, "house no. 41 " + HN, False)
expect("real and invented record – a missing house no. is reported", out, "house no. 36 " + HN, True)

P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 34", st="doc", r=["baptism_jan_1900"],
               note="Neighbours Hrubý from no. 99.")}
expect("house no. only in the note – no warning", check(P, records=REC, transcripts=TR), HN, False)

P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 36 (per online tree)", "farmer, Holice no. 41 (family story)",
               "† Holice no. 52 (mill)", st="doc", r=["baptism_jan_1900"])}
out = check(P, records=REC, transcripts=TR)
expect("house no. with the source \"(per online tree)\" – no warning", out, "house no. 36 " + HN, False)
expect("house no. with the source \"(family story)\" – no warning", out, "house no. 41 " + HN, False)
expect("another bracket (\"(mill)\") marks no source – warning", out, "house no. 52 " + HN, True)

P = {1: person("Jan Novák", "* 3 May 1900 Holice no. 36", r=["baptism_jan_1900"])}
expect("person not 'doc' – no warning", check(P, records=REC, transcripts=TR), HN, False)

# Regression from a review: a date, an age or another number does not document a house number
TR_DATE = {"baptism_jan_1900": {"orig": "[Date] 5. 1. 1767\n[House] No 34\n[Age] 23 years",
                                "translation": "Born 5 January 1767."}}
P = {1: person("Jan Novák", "* 5 Jan 1767 Holice no. 5", "blacksmith in Holice no. 1", "farmer, Holice no. 23", st="doc",
               r=["baptism_jan_1900"])}
out = check(P, records=REC, transcripts=TR_DATE)
expect("the day of a date does not document house no. 5 – warning", out, "house no. 5 " + HN, True)
expect("the month of a date does not document house no. 1 – warning", out, "house no. 1 " + HN, True)
expect("an age does not document house no. 23 – warning", out, "house no. 23 " + HN, True)

# House numbers as written in real transcripts (invented places and numbers)
FORMS = ["Rottenschachen No 34", "z Neplachova No 21", "Putim No. 81", "Neplachov čp. 35", "č. 18", "N. 6", "Nro 7",
         "N° 9", "Stožice čís. 10, okres Vodňany", "Erdweiss No. 5 |", "domu 44", "Haus 45", "v domě čp. 112"]
TR_F = {"baptism_jan_1900": {"orig": "[Date] 3. 5. 1900\n" + "\n".join(f"[Witness] Josef Malý, {t}" for t in FORMS)
                             + "\n[House] Neplachov 46\n[Haus] 47\n[Bride's house number] 48 | kath. | 24",
                             "translation": ""}}
NUMBERS = [34, 21, 81, 35, 18, 6, 7, 9, 10, 5, 44, 45, 112, 46, 47, 48]
P = {1: person("Jan Novák", *[f"Holice no. {c}" for c in NUMBERS], st="doc", r=["baptism_jan_1900"])}
out = check(P, records=REC, transcripts=TR_F)
for c in NUMBERS:
    expect(f"house number form {c} from the transcript is accepted", out, f"house no. {c} " + HN, False)

# A number right after a place from places.json ("from Holice 23", "Holice 24;"), but not a date or year after it
PLACES = {"Holice": {"lat": 50.0, "lon": 16.0, "re": "Holic"}}
TR_PL = {"baptism_jan_1900": {"orig": "Holice 24; 26; ledig | Holice 5. 1. 1767 | Holice 1767",
                              "translation": "Jan Novák, farmer from Holice 23, 55 years."}}
P = {1: person("Jan Novák", "* Holice no. 23", "Holice no. 24", "Holice no. 5", "Holice no. 176", st="doc",
               r=["baptism_jan_1900"])}
out = check(P, records=REC, transcripts=TR_PL, places=PLACES)
expect("\"from Holice 23\" documents house no. 23", out, "house no. 23 " + HN, False)
expect("\"Holice 24;\" documents house no. 24", out, "house no. 24 " + HN, False)
expect("\"Holice 5. 1. 1767\" does not document house no. 5 – warning", out, "house no. 5 " + HN, True)
expect("\"Holice 1767\" does not document house no. 176 – warning", out, "house no. 176 " + HN, True)

# An unknown parent ("father unknown", "?") is no partner the marriage should name
for unknown in ("father unknown", "?"):
    P = {1: person("Petr Novák"), 2: person(unknown, st="unk"), 3: person("Anna Malá", "× 1900 Holice Josef Hrubý")}
    expect(f"partner \"{unknown}\" – no warning", check(P), PARTNER, False)

# SAME: a record cited at the alias documents the house number of the main person (and the other way round)
P = {1: person("Petr Novák"), 2: person("Jan Novák"), 3: person("Marie Králová"),
     4: person("Josef Novák", "* 1880 Holice no. 34", st="doc", r=["r1"]), 6: person("Karel Král"),
     7: person("Ludmila Malá"), 12: person("Josef Novák", "SAME PERSON as 4", "farmer, Holice no. 35", st="doc", r=["r2"])}
out = check(P, SAME={12: 4}, records=[("r1", "Baptism of Josef Novák, Holice no. 35"), ("r2", "Marriage")],
            transcripts={"r2": {"orig": "[House] No 34", "translation": ""}})
expect("SAME – house no. documented by the alias's record – no warning", out, "house no. 34 " + HN, False)
expect("SAME – the alias's house no. documented by the main person's record – no warning", out, "house no. 35 " + HN, False)

# The marriage place does not count as the partner's name (Holice × Holický)
PLACES = {"Holice": {"lat": 50.0, "lon": 16.0, "re": "Holic"}}
P = {1: person("Petr Novák"), 2: person("Jan Holický", "× 1950 Holice Marie Králová"),
     3: person("Anna Malá", "× 1950 Holice Karel Hrubý")}
expect("marriage place (Holice) does not mean the partner Holický – warning", check(P, places=PLACES),
       "person 3 (Anna Malá): no marriage (×) names partner 2", True)

# Regression from the 2nd review
# A place expression with its own flag or group: the check does not crash and finds the number after the place
for expr, text in (("(?i)Holic", "z holic 23"), ("(Holic|Holitz)", "z Holitz 23")):
    P = {1: person("Jan Novák", "* Holice no. 23", "× 1920 Holice Marie Králová", st="doc", r=["baptism_jan_1900"]),
         2: person("Karel Novák"), 3: person("Marie Králová", "× 1920 Holice Karel Novák")}
    out = check(P, records=REC, transcripts={"baptism_jan_1900": {"orig": text, "translation": ""}},
                places={"Holice": {"lat": 50.0, "lon": 16.0, "re": expr}})
    expect(f"place expression {expr} – the check finishes and \"{text}\" documents house no. 23", out,
           "house no. 23 " + HN, False)

# A date with a month name is no house number (register wording in Czech, German and Latin)
for date in ("v Holicích 23. února 1890", "Holic No 23. Februar 1890", "Holice 23. Januarii 1767", "Holice 23. 9bris"):
    P = {1: person("Jan Novák", "* Holice no. 23", st="doc", r=["baptism_jan_1900"])}
    out = check(P, records=REC, transcripts={"baptism_jan_1900": {"orig": f"Natus {date}.", "translation": ""}},
                places=PLACES)
    expect(f"\"{date}\" does not document house no. 23 – warning", out, "house no. 23 " + HN, True)

# Transcript and translation are read separately: a [House] field at the end of the transcript does not run on into
# the translation
P = {1: person("Jan Novák", "* Holice no. 23", "Holice no. 34", st="doc", r=["baptism_jan_1900"])}
out = check(P, records=REC, transcripts={"baptism_jan_1900": {"orig": "[Date] 1900\n[House] 34",
                                                               "translation": "Jan died at the age of 23."}})
expect("an age in the translation after a [House] field does not document house no. 23 – warning", out,
       "house no. 23 " + HN, True)
expect("a [House] field at the end of the transcript documents house no. 34", out, "house no. 34 " + HN, False)

# The place is removed from a marriage fact only at the start (after the date), not from the partner's name
P = {1: person("Petr Novák"), 2: person("Jan Holický", "× 1900 Holice Anna Malá"),
     3: person("Anna Malá", "× 1900 Holice Johann Holický")}
expect("\"× 1900 Holice Johann Holický\" names Jan Holický – no warning", check(P, places=PLACES), PARTNER, False)

# A place without coordinates is recognised in the text too
NO_LAT = {"Holice": {"re": "Holic"}}
P = {1: person("Jan Novák", "* Holice no. 23", st="doc", r=["baptism_jan_1900"])}
out = check(P, records=REC, transcripts={"baptism_jan_1900": {"orig": "", "translation": "farmer from Holice 23"}},
            places=NO_LAT)
expect("place without coordinates – \"from Holice 23\" documents house no. 23", out, "house no. 23 " + HN, False)
P = {1: person("Petr Novák"), 2: person("Jan Holický", "× 1950 Holice Marie Králová"),
     3: person("Anna Malá", "× 1950 Holice Karel Hrubý")}
expect("place without coordinates – Holice does not mean the partner Holický – warning", check(P, places=NO_LAT),
       "person 3 (Anna Malá): no marriage (×) names partner 2", True)

# A number of an entry, page or image is no house number
for number in ("entry no. 23", "page no. 23", "image no. 23", "fol. No 23", "str. č. 23"):
    P = {1: person("Jan Novák", "* Holice no. 23", st="doc", r=["baptism_jan_1900"])}
    out = check(P, records=[("baptism_jan_1900", f"Baptism of Jan Novák, {number}")])
    expect(f"\"{number}\" does not document house no. 23 – warning", out, "house no. 23 " + HN, True)

print(f"\n{sum(RESULTS)} of {len(RESULTS)} correct")
sys.exit(0 if all(RESULTS) else 1)
