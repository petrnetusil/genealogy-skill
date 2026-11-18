# Helper brief template (one research round = one archive)

<!-- Sources of the template (MIT): xsigik/rodokmen-skill reference/zadani_pomocnika.md (Jindřich Šaršon and
contributors; "control entry", closed list of images, at most ~50 images, state of every image);
zbysekvoda/rodokmen-plus skills/paralelni-badani/SKILL.md (Zbyšek Voda; "by portal, not by person", verification
wave, an uncertain reading is not a negative result, numbers assigned in advance). Extended with the experience of
about 150 research rounds in one family project. -->

A helper (sub-agent) does not know the project – it knows only what is in the brief. So the main model
(coordinator), **before writing the brief**:

1. **Orientation in the book** – take it from the `orientation` field in `data/volumes.json` and from
   `python3 -I tools/searched_books.py --book <reference>` (what has already been searched in the book). Check it on
   one image. A helper that has to find out where the book starts spends most of its run on orientation.
2. **Control entry** – choose one already documented entry from the same book (person, date, image). The helper must
   find it first; this proves it reads the right book and that images reach it.
3. **Small batch:** 1 book / 1 parish / 1 archive, 4–6 people, **at most ~50 downloaded images per round**. Split a
   longer book into more rounds (with hundreds of images a helper stops seeing part of them and does not notice).
4. **By portal, not by person:** only one helper works on one archive at a time (they share the brake's limit). No
   helpers at all on browser-only portals with daily limits (see the country guide).
5. **Model:** a cheaper model (e.g. Sonnet) for searching and first reading of indexed, legible books. 17th–18th-century
   Kurrent, faded leaves and books without an index (blind search) need a stronger model; give such a place as an exact
   image and verify it yourself or send it to the independent review (Fable).
6. **Login check:** if the round needs a login (FamilySearch, a library account), check it with one request first
   (401 / "Sign in" = logged out – ask the user to log in; it is not a block).
7. Fill in all `<…>` below and leave the rest unchanged. Save the brief as `work/brief_<round>_<branch>.md`.

---

## TEMPLATE – copy from this line

```
# Brief – <portal> round <N>: <line / question in one sentence>

You are a helper in searching for ancestors in registers. Your role is to FIND entries and READ them; the main
model writes and verifies the data. Communicate in <language>.

PROJECT: <absolute project path>   (run commands from the project root)
OUTPUT:  work/helper_<branch>/findings.md   – write ONLY into the folder work/helper_<branch>/, never into data/
CONTEXT (read first): <earlier findings files, people <numbers> in data/people.py – read only>

## What we know (only facts with evidence)
- <person (Kekulé number), what is documented, where (volume + image), what is only a hypothesis and how likely>
- <what is already EXCLUDED / searched – so it is not searched again: book, images, years, log row>

## Book (orientation verified by the main model)
BOOK: <archive>, ref. <…>, id <full id>, kind <B/M/D>, years <…>, <number> images
LAYOUT: <from orientation: sections, where years start, image ↔ folio/page conversion with its range of validity>
STRUCTURE: <what is in which column; whether the index covers only deaths or is shared; language and script>
IMAGES TO GO THROUGH: <closed list or range, e.g. images 99–140>; outside them only probes every <k> images.
BUDGET: at most <≤ 50> downloaded images; full resolution only where there is a candidate.

## CONTROL ENTRY – find it first
<name, date, village/house> on image <n> (<page>). If you do not find it, stop and write why –
without it "not found" does not count for the other tasks.

## Tasks (in this order; for each the expected year ± range, village/house, parents/spouse)
1. <…>
2. <…>
(If you do not finish something, write what and where you stopped – do not guess.)

## Tools
- image:   <portal tool command, e.g. python3 -I tools/aron_img.py <id> <image> <level 0|1|2> work/helper_<branch>/<file>.jpg [x0,y0,x1,y1]>
           (download ONE image per command – the network guard rejects loops of several downloads in one command;
            output only inside the project)
- verify:  python3 -I tools/verify.py <image.jpg> x0,y0,x1,y1 work/helper_<branch>/verify_<x> [v] [--contrast]
- book map (header probes): python3 -I tools/book_map.py <portal> <book> <from> <to> <step> --crop 0,0,1,0.2
           -o work/helper_<branch>/map_x.jpg   (first check the number of images in the volume)
- faded leaves: python3 -I tools/enhance.py <image.jpg> [x0,y0,x1,y1] --strips <N>   (show-through from the reverse
           side: only raise levels, no background division)
- <ImageMagick note for this computer, e.g. export PATH=/opt/local/bin:$PATH (ImageMagick 6: convert, not magick)>
- before downloading, check whether the image is already in work/ (find work -name '*<image>*').

## Brake rules (network)
- Archive websites ONLY through the project's tools or python3 -I tools/polite.py (curl, own scripts).
- End of work on an archive = exit code 3 / message "stopped", response 403/429/503, timeout: STOP with this archive
  AT ONCE, repeat nothing, work around nothing (other address, proxy, browser). Write it into the output with the time.
- Browser (FamilySearch, browser-only portals): your own tab, 5–10 s between pages, no loops over a whole volume;
  first check the login with one request (401 = logged out → stop and write it, it is NOT a block). Works that may only
  be read: read only.
- Never type passwords, never solve CAPTCHAs – stop and report.

## Reading rules (from mistakes of past rounds)
1. **Never write a fact you did not see on the image.** Uncertain reading "(?)", illegible "[…]". An uncertain
   reading is NOT a negative result – record it as uncertain.
2. **An image to read is at most ~2000 px** (larger is not displayed); read a candidate from a full-resolution crop
   (verify.py). If an image does not display ("media removed", empty), stop and write which image.
3. **An index line is only a candidate.** Read name, date, house and reference (fol./pag.) on the SAME line – in
   slanted indexes it is easy to take the name from the neighbouring line. Verify every index line in the register
   before reporting it. Indexes sometimes give the godparent instead of the child or a wrong date. "fol." in an index
   may be the page or refer to the right page of the previous image; if it does not fit, look for another (ink)
   pagination or a second series of the same year.
4. **Two people of the same name in one village are common.** Identify only by TWO independent characteristics
   (house + wife, both parents, godparents); otherwise "candidate". For each identification list the other bearers of
   the name in the parish and why they do not fit.
5. **Renumbered houses:** a different house number for the same family does not mean another family – and the same
   number does not mean the same family. Keep a table house → holder by year before identifying.
6. **Do not complete word fragments to what you are looking for.** Compare an illegible place with a legible entry by
   the same hand (same form) and only then guess – with (?).
7. **Age at death is often exaggerated** (old people by 5–15 years). Look for the baptism from −10 to +3 years of the
   age; at marriage ±3 years. Age alone does not identify a person.
8. **Dates:** 7ber/7bris = September, 8ber = October, 9ber = November, Xber = December. "Retour à la page…",
   "vide pag." = the year continues elsewhere – find it before writing "not found". Volumes are often bound out of order
   (inserted leaves of other years) – take the year from the header/entry, not from the image order.
9. **Other-language names of places and people:** find them in advance (<list the known forms for this round>).
   Surnames were sometimes written after the farm – look for aliases too.
10. After EACH task write the result into findings.md at once (the run may end early – what is written is not lost).
11. Delete large scans (full-resolution whole pages) after extraction; keep the crops crop_*.jpg and verify_*.jpg.

## OUTPUT FORMAT – work/helper_<branch>/findings.md
# <portal> round <N> – <topic> (helper, <date>)

## Control entry
found / NOT found – image <n>, <what is really there>

## Ranges gone through
| Volume (ref., id 8 chars) | Images | Years | Section | How (every entry / name column / probes; resolution) | Result | Evidence (with evidence / orientation only) |
(also without a finding – so the same images are not searched again)

## Findings (for each)
### ★ <date> <village house> – <kind>: <name> (Kekulé <k>, if any)
- volume <ref.> (id <8 chars>), **image <n>, <left/right> page (<fol./pag.>), <order> entry**
- coordinates of the entry (fractions of the whole page): x0,y0,x1,y1
- crop: work/helper_<branch>/crop_<…>.jpg; link: <permalink command or URL>
- transcription (faithful, abbreviations kept, (?) and […]): "…"
- translation: …
- godparents / witnesses / midwife (in full, with residence – they are clues)
- reading certainty and identification certainty + why (two characteristics) + other candidates

## Side findings
<the same surname, the same house, godparents from the family – with the image>

## State of images (what I REALLY saw on each image) – EVIDENCE for every "not there"
<image> – <date of the FIRST entry> <FIRST name> … <date of the LAST entry> <LAST name> – read zoomed (full-resolution
crop, not the whole page scaled to the screen) / illegible / not downloaded (why)
Consecutive ranges OVERLAP by one image (the last image of a range = the first image of the next).
An image without first and last names and dates was gone through only for ORIENTATION; "not found" does not count for it.

## Book orientation (newly found)
<image = year / folio / section; starts of sections and indexes; misbound leaves> – the main model transfers it to
`orientation`

## New clues and offline sources
<what to search next and where; what exists only in the archive (for data/offline_sources.md)>

## Summary (at most 20 lines)
<findings with certainty, what was excluded, how many images downloaded, whether the brake intervened>
```

---

## After the helper returns (done by the main model)
- Control entry or state of images missing → the result is incomplete, "not found" does not count.
- **Read every finding yourself on the crop** (`tools/verify.py`) before it becomes `doc`. Distinguish "the entry is
  documented" from "the link to the family is documented" – a name match from an index is a candidate, not proof.
- **Who read it:** in `data/records.json` `"read_by"` = whoever read and wrote the entry (a helper whose reading you
  only adopted goes into `read_by`, e.g. `"AI model Claude Sonnet 5 (18 Nov 2026)"`), and after your own check you go
  into `"checked_by"` (`["AI model Claude Opus 5.5 (18 Nov 2026)"]`). Always the form "AI model Claude <Model>
  <version> (<date>)". Shown on the record page (Read by / Checked by).
- **Negative result only with evidence:** accept "it is not there" only for images where the helper gave the first and
  last name and the date range read at zoom, with overlapping ranges. In the log mark each range **"with evidence"** or
  **"orientation only"** – "searched, do not search again" applies only to the first.
- Write the ranges gone through into the research log; transfer the book orientation into `orientation`.
- **Impact on the texts:** after writing a finding search `data/story*.md`, `data/curiosities.md`, `data/lines.json`
  and the `summary` of the people concerned (name, place, year) and update them – readable for the family, without
  percentages and apparatus.
- Key and disputed readings (Kurrent, identification of two namesakes) go to the **independent review** (Fable or
  another model with clean context) automatically after about every 8 rounds, and at once when readings conflict.
- Delete the round's large scans once extracted (the image cache keeps archive images); keep `findings.md`, crops and
  verify images.
- Insights about tools and portals go into `notes_for_skill.md`.
