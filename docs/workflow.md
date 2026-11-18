# How the research works

This page explains what Claude does behind the scenes, so you can follow, steer and check it.

## The project folder
```
data/            all facts in plain text
  people.py        ancestors by Ahnentafel (Kekulé) number, relatives, open questions, hypotheses
  records.json     every register entry used (with image link, who read it, who checked it)
  transcripts.json original text and translation of every entry
  volumes.json     the register books used
  research_log.md  every search, also unsuccessful ones
  family_info.md   what relatives told and where it came from
  STATUS.md        where we are and what comes next
  story.md, curiosities.md   texts for the website
documents/       your scanned family documents
crops/, sources/ crops of record entries (web size / full resolution)
work/            downloaded scans and intermediate files (can be cleaned up)
web/             the website
tools/           the tools (copied from the skill)
```
Ancestor numbers: you are 1, your father 2, your mother 3; the father of person *n* is 2*n*, the mother 2*n*+1.

## One research round
1. **Choose a target** – the youngest ancestor without a document, and their youngest known event.
2. **Find the book** – which parish or civil registry, which archive, which volume and image.
3. **Download and read** – Claude reads the entry from a zoomed crop, including margin notes.
4. **Record it** (always all steps): volume → record → crop → highlight frame → transcription + translation → person.
5. **Log it** in the research log with the range searched.
6. **Check** – `tools/check.py` looks for inconsistencies.
7. **Update stories** – every finding is checked against the family story, curiosities and person summaries.

## Statuses of facts
| Status | Meaning |
|---|---|
| `doc` | documented – read directly from an original record image |
| `prob` | probable – data agree, but no direct proof |
| `fam` | from the family or a family document |
| `mh` | only from somebody else's online tree – a clue, not proof |
| `unk` | unknown – just a place in the tree |

## Four eyes
Helpers (sub-agents) can search several books in parallel. Their readings are always verified on the image by the main
model. Uncertain or key readings, and every conflict with another source (even a professional genealogist), go to an
**independent second model** that re-reads enhanced crops without seeing the first reading. Each record lists who read
it and who checked it.

## Hard questions
When two candidates compete (e.g. two possible fathers), Claude opens a *case* (`tools/cases.py`) with candidates,
evidence for and against, and an estimate. A proof summary (`data/proof_summary.md`) explains the key links of the main
line in the style of the Genealogical Proof Standard.

## Beyond the registers
When registers end or are missing: land records and urbaria, censuses and population registers, notarial records,
military records, newspapers, school and guild records, emigration lists. See
`skills/genealogy/methodology/beyond_registers.md` and the country guides.

## Writing to archives
Some records exist only in reading rooms or offices. Claude prepares a short, polite e-mail – **one per institution**,
then waits for its reply – and logs it in `data/archive_requests.md`. You send it yourself.
