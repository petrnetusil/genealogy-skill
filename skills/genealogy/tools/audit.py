#!/usr/bin/env python3
"""Brief for an independent audit of a record (a second look): transcript checked against the crop, other readings,
where to search next.

Adapted from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), modified for the project: instead of a person graph
it uses Kekulé numbers from data/people.py (person k, father 2k, mother 2k+1, spouse k^1, child k//2; SAME, SIDE,
HYPOTHESES), the crop from crops/ and sources/ (the record's "crop" field), research log rows and work files (reviews,
rounds) mentioning the record. It formalises the independent reviews of readings.
The idea "reader on a cheaper model + independent auditor" is taken from
  https://github.com/jozefizso/rodokmen-skill/blob/38850a5aa4dbebe3faf1eb6ed5c5e8c9007c2d68/skills/rodokmen/tools/audit.py
  (author Jozef Izso, version 0.11; MIT licence – see the third-party notices in LICENSE). There the audit runs Codex; here no model is started:
  the agent runs the auditor as a Claude sub-agent (another model / effort, clean context) – see the skill's section
  on parallel research.

Usage (from the project root):
  python3 -I tools/audit.py brief <key> [<key> …] [--round N] [--name NAME]
      → work/audit/<name>_brief.md: the record from records.json, its volume, the transcript from transcripts.json,
        paths to the crops, the people (Kekulé, data/people.py) citing the record in `r` with parents, spouse and the
        child in the line, relatives outside the line (SIDE) and hypotheses with this key, research log rows and work
        files mentioning the key, a checklist and the JSON schema of the answer. With --round N it adds the reports from
        work/*round*<N>*/ and work/helper_*.
  python3 -I tools/audit.py load <answer.json|-> [--name NAME]
      → checks the auditor's answer (JSON, may be inside a ```json block), saves work/audit/<name>.json
        and prints a summary: decision, discrepancies, other readings, where to search, tasks.
  python3 -I tools/audit.py schema → JSON schema of the answer

The tool makes no network calls and does not change data/ – only the main agent writes audit results into the data,
after checking them itself.
Exit code: 0 OK, 1 error (unknown key, invalid answer).
"""
import datetime, glob, json, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script's folder itself
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(ROOT, "work")
AUDIT = os.path.join(WORK, "audit")

GENERATED = {"searched_books.md", "godparents.md", "search_queue.md"}   # tool outputs, not reviews
DECISIONS = ["ok", "fix", "reread", "ask_user"]
SEVERITIES = ["error", "risk", "note"]

SCHEMA = {
    "type": "object",
    "required": ["decision", "reasoning", "discrepancies", "alternative_readings", "where_to_search",
                 "questions_for_user", "viewed"],
    "properties": {
        "decision": {"type": "string", "enum": DECISIONS},
        "reasoning": {"type": "string"},
        "discrepancies": {"type": "array", "items": {
            "type": "object", "required": ["severity", "where", "problem", "evidence", "suggestion"],
            "properties": {"severity": {"type": "string", "enum": SEVERITIES}, "where": {"type": "string"},
                           "problem": {"type": "string"}, "evidence": {"type": "string"},
                           "suggestion": {"type": "string"}}}},
        "alternative_readings": {"type": "array", "items": {
            "type": "object", "required": ["claim", "why", "how_to_check"],
            "properties": {"claim": {"type": "string"}, "why": {"type": "string"},
                           "how_to_check": {"type": "string"}}}},
        "where_to_search": {"type": "array", "items": {
            "type": "object", "required": ["priority", "source", "what_to_find", "why"],
            "properties": {"priority": {"type": "integer"}, "source": {"type": "string"},
                           "what_to_find": {"type": "string"}, "why": {"type": "string"},
                           "link": {"type": "string"}}}},
        "questions_for_user": {"type": "array", "items": {"type": "string"}},
        "viewed": {"type": "array", "items": {"type": "string"}},
    },
}

BRIEF = """\
# Independent audit of a register record

You are an independent genealogist (parish and civil registers). The main agent or a reader on a cheaper model read
the record(s) below and wrote them into the data. You are the second look with a clean context. Two tasks, equally
important: **A) check the transcript against the crop and against the data**, **B) look at the result differently**
and advise where to search next.

## Rules
- Read only. Change nothing, download nothing, do not visit archive websites. You may read the project files
  (data/people.py – Kekulé numbers: the father of person k = 2k, the mother = 2k+1) and run `python3 -I tools/check.py`.
- **Open and read the crops yourself** (Read tool on the .jpg) before reading the transcript – so it does not anchor
  you. Put the paths of the crops you really looked at into `viewed`. A missing crop is a `risk`.
- Do not report an uncertain reading as an `error` but as a `risk`, and write what exactly you see in the crop.
- Sample data (flag `sample`, an invented record) is not a research error – only a note.
- Living people: do not search for them and do not write more about them than the name and year of birth.
- Write in English, briefly and concretely (record key, person id, field).

## A) Checklist
1. Transcript × crop: name, date (day, month, year), house number, village, parents, godparents/witnesses, marital
   status, occupation, age.
2. Transcript × translation (`orig` × `translation`) × `summary` in records.json × the people's facts (`f`, `y`):
   do the numbers and names match?
3. Evidence status: `doc` only for what is in the crop; an uncertain reading ("(?)") must not support a `doc` fact.
4. Logic: parents' age at the birth (mother 15–50), age at marriage × year of birth, a child after a parent's death,
   two families of the same name in the village, mixed-up generations (father and son of the same name and house).
5. Completeness: does the record have a volume (`volumes.json`), a crop, a transcript? Are the godparents/witnesses
   of the record among the people, in SIDE or in HYPOTHESES?
6. Person status (`st`): `doc` only when the record documents the person directly; linking "this record = this
   person" only by a matching name without another detail (house, parents, age) is `prob`.

## B) Another view
- `alternative_readings`: what else the data allow (another family of the same name, another reading of the
  village/house number, migration, illegitimate birth, wrongly linked records) – each with why and how to check.
- `where_to_search`: concrete sources (neighbouring parishes, indexes, censuses, land registers, lists of subjects,
  military and residence records, newspapers), ordered by priority (1 = first).

## Decision (`decision`)
- `ok` – no `error`.
- `fix` – the data contain an error that can be fixed from what is already read (write the suggested fix).
- `reread` – a `doc` detail does not match the crop, or the crop is missing/illegible: the main agent must read again.
- `ask_user` – the decision belongs to a human (conflict with family information, two equally likely persons,
  privacy).

Answer **only JSON** following the schema at the end (no other text).
"""


def load_json(name, default):
    try:
        return json.load(open(os.path.join(DATA, name), encoding="utf-8-sig"))
    except FileNotFoundError:
        return default


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def crops(key, z=None):
    names = dict.fromkeys([key] + ([z["crop"]] if z and z.get("crop") else []))
    return [rel(p) for j in names for d in ("crops", "sources")
            for p in sorted(glob.glob(os.path.join(ROOT, d, glob.escape(j) + "*.*")))]


def people_py():
    ns = {}
    exec(open(os.path.join(DATA, "people.py"), encoding="utf-8-sig").read(), ns)
    return ns


def describe_person(O, k):
    P, SAME = O["P"], O.get("SAME", {})
    d = P[k]
    sex = d.get("sex") or ("M" if k % 2 == 0 else "F")
    lines = [f"- Kekulé `{k}` {d.get('n', '?')} ({sex}, {d.get('y', '')}, st={d.get('st', 'unk')})"
             + (f" – same person as `{SAME[k]}` (SAME)" if k in SAME else "")]
    for field in ("f", "r", "note"):
        if d.get(field):
            lines.append(f"  - {field}: {json.dumps(d[field], ensure_ascii=False)}")
    relatives = [("father", 2 * k), ("mother", 2 * k + 1)]
    if k >= 2:
        relatives += [("spouse", k ^ 1), ("child in the line", k // 2)]
    for role, j in relatives:
        j = SAME.get(j, j) if j not in P else j
        if j in P:
            o = P[j]
            lines.append(f"  - {role}: `{j}` {o.get('n', '?')} ({o.get('y', '')}, st={o.get('st', 'unk')})")
    for s in O.get("SIDE", []):
        if s.get("k") == k:
            lines.append(f"  - relative outside the line (SIDE): {s.get('n', '')}")
    return "\n".join(lines)


def mentions(key):
    """Research log rows and work files (.md) mentioning the key – reviews, helper reports."""
    log = os.path.join(DATA, "research_log.md")
    rows = [r.strip()[:400] for r in open(log, encoding="utf-8") if key in r] if os.path.exists(log) else []
    files = []
    for p in sorted(glob.glob(os.path.join(WORK, "**", "*.md"), recursive=True)):
        if os.path.basename(os.path.dirname(p)) == "audit" or os.path.basename(p) in GENERATED:
            continue
        try:
            if key in open(p, encoding="utf-8", errors="replace").read():
                files.append(rel(p))
        except OSError:
            pass
    return rows, files


def reports(rnd):
    dirs = sorted(glob.glob(os.path.join(WORK, f"*round*{rnd}*"))) + sorted(glob.glob(os.path.join(WORK, "helper_*")))
    out = []
    for d in dirs:
        for base, _, files in os.walk(d):
            out += [rel(os.path.join(base, f)) for f in sorted(files) if f.lower().endswith((".md", ".txt", ".json"))]
    return out


def build(keys, rnd=None):
    records = {z.get("key"): z for z in load_json("records.json", [])}
    transcripts = load_json("transcripts.json", {})
    volumes = load_json("volumes.json", {})
    O = people_py()
    unknown = [k for k in keys if k not in records]
    if unknown:
        sys.exit(f"Key not in data/records.json: {', '.join(unknown)}")
    parts = [BRIEF]
    for k in keys:
        z = records[k]
        parts.append(f"\n## Record `{k}`\n```json\n{json.dumps(z, ensure_ascii=False, indent=1)}\n```\n")
        vol = volumes.get(z.get("volume")) if isinstance(volumes, dict) else None
        parts.append(f"Volume `{z.get('volume')}`: " + (json.dumps(vol, ensure_ascii=False) if vol else
                     "**not in volumes.json**") + "\n")
        p = transcripts.get(k)
        parts.append("\n### Transcript (transcripts.json)\n" + (
            f"orig:\n```\n{p.get('orig', '')}\n```\ntranslation: {p.get('translation', '')}\n"
            if p else "**Transcript missing.**\n"))
        v = crops(k, z)
        parts.append("\n### Crops – open them\n" + ("\n".join(f"- `{x}`" for x in v) if v else "**No crop found.**") + "\n")
        persons = sorted(i for i, d in O["P"].items() if k in d.get("r", []))
        parts.append("\n### People (Kekulé, data/people.py) citing the record\n" + ("\n".join(describe_person(O, i) for i in persons)
                     or "No person has this key in `r`.") + "\n")
        side = [s for s in O.get("SIDE", []) if k in s.get("r", [])]
        if side:
            parts.append("\nRelatives outside the line (SIDE) with this record:\n" + "\n".join(
                f"- at ancestor `{s.get('k')}`: {s.get('n', '')} – {s.get('t', '')[:300]}" for s in side) + "\n")
        hyp = [h for h in O.get("HYPOTHESES", []) if k in json.dumps(h, ensure_ascii=False)]
        if hyp:
            parts.append("\nHypotheses (HYPOTHESES) with the record:\n" + "\n".join(
                f"- {json.dumps(h, ensure_ascii=False)[:400]}" for h in hyp) + "\n")
        rows, files = mentions(k)
        if rows:
            parts.append("\n### Research log rows (research_log.md) with the key\n" + "\n".join(f"- {r}" for r in rows) + "\n")
        if files:
            parts.append("\n### Work files mentioning the record (reviews, reports) – look at them\n"
                         + "\n".join(f"- `{x}`" for x in files) + "\n")
    if rnd is not None:
        h = reports(rnd)
        parts.append(f"\n## Readers' reports (round {rnd}) – read them\n" + ("\n".join(f"- `{x}`" for x in h)
                     or "- no reports") + "\n")
    parts.append("\n## Answer schema\n```json\n" + json.dumps(SCHEMA, ensure_ascii=False, indent=1) + "\n```\n")
    return "".join(parts)


def validate(v):
    """→ list of errors in the answer (empty = valid)."""
    if not isinstance(v, dict):
        return ["the answer is not a JSON object"]
    err = [f"field {k} missing" for k in SCHEMA["required"] if k not in v]
    if v.get("decision") not in DECISIONS:
        err.append(f"decision must be one of {DECISIONS}")
    for k in ("discrepancies", "alternative_readings", "where_to_search", "questions_for_user", "viewed"):
        if k in v and not isinstance(v[k], list):
            err.append(f"{k} must be a list")
    for n in v.get("discrepancies", []) if isinstance(v.get("discrepancies"), list) else []:
        if not isinstance(n, dict) or n.get("severity") not in SEVERITIES:
            err.append(f"discrepancy without a valid severity: {n}")
    return err


def parse(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    s = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(s)


def summary(v):
    print(f"Auditor's decision: {v['decision']}\n  {v['reasoning']}")
    for z in SEVERITIES:
        n = [x for x in v["discrepancies"] if x["severity"] == z]
        if n:
            print(f"\n{z.upper()} ({len(n)}):")
            for x in n:
                print(f"  - [{x.get('where', '')}] {x.get('problem', '')}\n      evidence: {x.get('evidence', '')}"
                      f"\n      suggestion: {x.get('suggestion', '')}")
    if v["alternative_readings"]:
        print("\nOther readings:")
        for h in v["alternative_readings"]:
            print(f"  - {h.get('claim', '')}\n      why: {h.get('why', '')}\n      check: {h.get('how_to_check', '')}")
    if v["where_to_search"]:
        print("\nWhere to search:")
        for k in sorted(v["where_to_search"], key=lambda k: k.get("priority", 99)):
            print(f"  {k.get('priority', '?')}. {k.get('source', '')}: {k.get('what_to_find', '')} – {k.get('why', '')}"
                  + (f"\n      {k['link']}" if k.get("link") else ""))
    if v["questions_for_user"]:
        print("\nQuestions for the user:")
        for q in v["questions_for_user"]:
            print(f"  - {q}")
    print(f"\nCrops the auditor viewed: {', '.join(v['viewed']) or 'none'}")


def arg(name):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 >= len(sys.argv):
            sys.exit(f"Value missing after {name}.")
        value = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        return value
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    rnd, name = arg("--round"), arg("--name")
    if rnd is not None and not rnd.isdigit():
        sys.exit(f"--round expects a number, not \"{rnd}\".")
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "schema":
        print(json.dumps(SCHEMA, ensure_ascii=False, indent=1))
        return 0
    if cmd == "brief" and rest:
        text = build(rest, int(rnd) if rnd is not None else None)
        os.makedirs(AUDIT, exist_ok=True)
        name = name or (rest[0] if len(rest) == 1 else f"round_{rnd}" if rnd else rest[0] + f"_and_{len(rest) - 1}")
        p = os.path.join(AUDIT, f"{name}_brief.md")
        open(p, "w", encoding="utf-8").write(text)
        print(f"Audit brief: {rel(p)}\nGive it to a sub-agent with a clean context (read only) and load its answer:\n"
              f"  python3 -I tools/audit.py load <answer.json> --name {name}")
        return 0
    if cmd == "load" and len(rest) == 1:
        text = sys.stdin.read() if rest[0] == "-" else open(rest[0], encoding="utf-8").read()
        try:
            v = parse(text)
        except ValueError as e:
            print(f"The auditor's answer is not valid JSON: {e}")
            return 1
        err = validate(v)
        if err:
            print("Invalid auditor answer:\n  " + "\n  ".join(err))
            return 1
        v["time"] = datetime.datetime.now().isoformat(timespec="seconds")
        os.makedirs(AUDIT, exist_ok=True)
        name = name or (os.path.splitext(os.path.basename(rest[0]))[0] if rest[0] != "-" else "audit")
        out = os.path.join(AUDIT, f"{name}.json")
        json.dump(v, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        summary(v)
        print(f"\nSaved: {rel(out)}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
