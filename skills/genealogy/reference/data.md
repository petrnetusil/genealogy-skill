# Project data format

All data are in `data/`. The website is generated from them (`npm run data`); never edit
`web/src/data/site.json` by hand. After changes run `python3 -I tools/check.py`. Filled-in sample data are in
`SKILL_DIR/template/sample/`. Add and change items of the JSON files with `python3 -I tools/write.py` (it keeps the
file's format, see SKILL.md → Writing data).

**Dates** are written in one canonical form everywhere (facts, `date` fields, stories): `12 Mar 1873` (day, English
three-letter month, year); also `Mar 1873` or `1873`. Approximations: `c. 1720`, `before 1740`, `after 1801`,
`between 1700 and 1705`. The tools also accept old numeric dates `12. 3. 1873`, `12.03.1873`, `12/03/1873`
(day/month/year), but write new data in the canonical form. House numbers: `no. 47`.

## `people.py` – ancestors
Kekulé numbers (Ahnentafel): 1 = the starting person, the father of person n = 2n, the mother = 2n+1.
| number | who |
|---|---|
| 1 | the starting person (for a woman `sex="F"`) |
| 2, 3 | father, mother |
| 4–7 | grandparents (4, 5 father's parents; 6, 7 mother's) |
| 8–15 | great-grandparents = **8 family lines** (`LINES`) |
| 16–31, 32–63 … | each further generation doubles |

The father of ancestor 22 is 44, the mother 45; the child of ancestor 45 is 22 (45 // 2). Men have even numbers.

```python
P = {
 8: dict(n="Jan Novák", y="1890–1944", st="doc",
         f=["* 14 Feb 1890 Holice no. 112", "blacksmith", "× 20 Jun 1919 Holice Josefa Pokorná", "† 1944 Holice"],
         r=["holice_baptism_jan_novak_1890", "holice_marriage_jan_novak_josefa_pokorna_1919"],
         summary="Jan was the fourth generation of blacksmiths at no. 112 in Holice. He married Josefa from the "
                 "neighbouring village in 1919 and ran the forge through the hard 1930s.",
         note="Research notes: why uncertain / contradiction / where a fact comes from"),
 9: dict(n="Josefa Pokorná", y="* 1895", st="doc", f=[...], r=[...]),
 33: dict(n="father unknown", st="unk", f=[], note="Illegitimate son; the father is not in the register."),
}
```
- `n` name (women by maiden name; uncertain reading with "(?)"), `y` years for overviews (`"* 1895"`, `"1890–1944"`,
  `"c. 1720–1785"`, `"1680 – before 1740"`, `"† 1940"` if only the death is known; nothing known → `""`).
- `f` facts: start with `*` (birth/baptism), `×` (marriage), `†` (death/burial) or are free text (trade,
  residence). Place names in the facts are used by the map (`places.json` → `re`).
  A marriage names the partner (`× 1919 Holice Josefa Pokorná`); `check.py` reports when no marriage names the
  person with the neighbouring number (husband 2k, wife 2k+1, also via `SAME`). For `doc` it reports a house number
  that appears in no cited record (`summary`, transcription); a number taken from elsewhere is marked by its source:
  `* 1862 Ostřetín no. 23 (per online tree)` or `(family story)`. Facts from a baptism or burial instead of the birth or
  death itself start with `* (baptism) 3 Mar 1760 …` / `† (burial) 20 Mar 1773 …`.
- `r` keys of records in `records.json`; add them with `python3 -I tools/write.py link <number> <key> [<key> …]`
  (for `SIDE` a part of the name instead of the number) – the tool keeps the rest of the file and checks that the
  record exists. `st` see `registers.md` → Status of data.
- `summary` – **a short readable text** about the person (2–5 sentences, in the family's language, storytelling,
  no research apparatus). Shown prominently on the person's page. Set it with `tools/person.py <n> summary="…"`.
- `note` – **long research notes** (why uncertain, contradictions, which ranges were searched). On the website they
  are collapsed under "Research notes", so they may be technical. Do not put sensitive content here without
  approval – it still goes to the website.
- Unknown parent: `n="father unknown"` / `"mother unknown"` with `st="unk"` (the website shows it as unknown, not as
  a name).
- `sex` only for person 1 (`"M"`/`"F"`; for the others it follows from the number).
- Living people: name and birth year only (`note="Living – basic data only."`).
- Small edits of one person: `python3 -I tools/person.py <n> st=doc r+=<key> f+="text" f-="text"
  fr="old=>new" note="…" note+="…" summary="…" y="…"` – changes only that person's line.
- `LINES = {8: ("Novák", "Blacksmiths of Holice…"), …}` – only numbers 8–15; the line name = the surname (plural
  form as the family says it). Fill it in as soon as you know the great-grandparent – without `LINES` the website
  shows no lines and no story hint comes.
- `SIDE` – siblings and other relatives: `dict(k=<ancestor number>, n="Josef Novák (1865–1920)", t="text", r=[keys])`.
- `ISSUES` – pairs `("Question", "Resolved: … / Hypothesis: … / Open: …")` → the page "Open questions" (resolved ones
  are hidden). It goes to the website – nothing sensitive without consent.
- `HYPOTHESES` – `dict(line=8, title="…", text="…", items=[("name", "text")], records=[keys])` → the line's page.
- `SAME = {350: 140}` – an ancestor who appears twice in the tree (alias → main number; the alias in `P` may have
  `f=["SAME PERSON as 140"]`).

## `records.json` – records
```json
[{"key": "holice_baptism_jan_novak_1890", "volume": "1a0b2337", "image": 57, "kind": "B",
  "date": "14 Feb 1890", "title": "Baptism of Jan Novák",
  "summary": "Jan, son of Václav Novák, blacksmith at Holice no. 112, and Barbora née Malá from Ostřetín. Godparents: Josef Král and Anna Králová.",
  "link": "https://<portal>/…/image/57",
  "read_by": "AI model Claude Opus 5.5 (18 Nov 2026)",
  "checked_by": ["AI model Claude Fable 5.2 (19 Nov 2026)"]}]
```
- `key`: lowercase ASCII without diacritics, `<place>_<baptism|marriage|death|burial|census|…>_<names>_<year>`.
  It is also the image name in `crops/` and `sources/`.
- `kind`: `B` birth/baptism, `M` marriage, `D` death/burial, `C` census, `O` other source (land record, newspaper,
  document, index copy…).
- `date` in the canonical form ("14 Feb 1890", "Mar 1867", "1797") – the website sorts by it.
- `summary`: the content in a sentence or two, including godparents/witnesses (`tools/godparents.py` reads them).
- `link`: permalink to the image on the portal (the image you really read from).
- `read_by`: who read and wrote the entry; `checked_by`: list of independent checks. Models always as
  `"AI model Claude <Model> <version> (<date>)"`, humans as `"genealogist <Name> (<source>, <year>)"`; a professional
  genealogist's transcription counts as a check. Shown on the record page ("Read by" / "Checked by").
- `crop`: optional, a different image name if the crop is not named after the key.
- `sample: true` marks the invented records of the sample family (`new_project.py --sample`); `check.py` reports them
  when they are left in a real project.

## `volumes.json`
`{"1a0b2337": {"archive": "Regional archive X – Collection of registers", "portal": "<portal>", "title": "B Holice
1880–1900, ref. …", "description": "villages…", "url": "link to the volume", "images": 412, "orientation": {…}}}`
– portal tools write it themselves (e.g. `aron_img.py <apu> volume`), otherwise `tools/write.py volumes`.
`orientation` (optional) records what you learned about the book's structure so that you and helpers need not find
it again: e.g. `{"years": {"1746": 104, "1760": 151}, "sections": [["Lhota", 1, 48], ["Ves", 49, 82]],
"offset": "image = folio + 3 (images 10–200)", "note": "index at the end, images 380–405"}`. Update it whenever a
helper reports a new anchor.

## `transcripts.json`
`{"<key>": {"orig": "[Date] 14 February 1890\n[House] 112\n[Father] …", "translation": "Plain translation…"}}`
- `orig` a faithful transcription by columns, `[Column name]` in square brackets, uncertain "(?)", illegible "[…]",
  abbreviations kept, original language and spelling.
- `translation` a readable translation for the family, in the family's language; explain old terms (cottager,
  lodger).

## `highlights.json`
`{"<key>": {"boxes": [[x0, y0, x1, y1]], "status": "ok", "note": ""}}` – fractions of the width/height of
`crops/<key>.jpg`. Written by `frame.py`. The frame must enclose the whole entry being read (not just the name).

## `places.json`
`{"Holice": {"re": "Holic", "query": "Holice, Czechia", "lat": 50.066, "lon": 15.986}}` – `re` is a regular
expression searched in the people's facts (a word stem, so that inflected forms match). Managed by `places.py`.
Watch for collisions (`(?<!Nový )Hradec` – negative look-behind; short names like `\bBuku?\b`). Hypothesis:
`"hypothesis": true, "line": 8`. When OpenStreetMap does not find a place (small hamlets), give a third parameter –
a query: `places.py add "Žár" "Žár" "Žár, Zdíkov, Prachatice"` or a query with a bigger town or district. For
**ambiguous names** (Podolí, Lhota, Sint-Martens-…, Saint-Martin) OpenStreetMap takes any village – check the
district/province in the last column of the output and give a query with a neighbouring place. The family knows the
geography best – when unsure, ask. `places.py` searches only settlements and warns below the list when it found
something else (a bar, a street) or when the new point is more than 50 km from all other places (probably another
village of the same name). Moving a wrong point: correct `lat`/`lon` in `places.json` by `tools/write.py places`.

## `documents.json` – family photos and documents on the website
`[{"img": "photo_wedding_1919", "caption": "Wedding of Jan and Josefa, Holice 1919.", "people": [8, 9],
"type": "photo", "date": "20 Jun 1919", "source": "photo and caption: aunt Maria (family album)"}]`
- `caption` is shown on the website – always fill it (like `t` for side relatives).
- `type`: `certificate`, `photo`, `map`, `register_copy`, `document`, `screenshot`, `other` (the Documents page
  filters by it).
- `source`: **who made the photo, wrote the caption or told the story** – credit the real author, not whoever
  forwarded it.
- Save the image with `crop.py documents/<scan>.jpg photo_wedding_1919` (creates `crops/` and `sources/`); rename
  with `write.py documents <old> --rename <new>` (`--preview` first shows what would change).
- Blur personal ID numbers and causes of death on recent certificates before publishing (`privacy.md`).

## `memories.json` – memories and anecdotes per person
`{"8": [{"kind": "memory", "text": "He always whistled while shoeing horses.", "source": "told by granddaughter
Maria, 2026"}]}` – `kind` is `anecdote`, `curiosity` or `memory`. Shown on the person's page under "Memories and
stories". Always with a source.

## `lines.json` – short story of each line
`{"Novák": {"story": ["paragraph", "paragraph"], "unknown": "What we do not know yet about this line."}}` – shown on
the line's page. Same style as stories (`stories.md`).

## `website.json` – website settings
See `web.md`. Besides the website texts and the gate it holds `country` (the main country, used by `places.py` for
map queries, e.g. `"Belgium"`) and optionally `ai_models` (`{"Opus": "Claude Opus 5.5", "Fable": "Claude Fable 5.2"}` –
short model names in the data are shown on the website as "AI model <full name>").

## `maps.json` – optional
Crops of old maps (cadastral sketches, town plans) with the family's houses, `[{"img": "<image key in crops/>", …}]`;
made from a map image with `crop.py` (see the country guide, e.g. `cuzk_maps.py`). `write.py documents --rename`
checks image keys against it.

## `variants.json` – optional site variants
See `web.md` → Site variants.

## `watched.json` – optional
What `tools/news_watch.py` watches: `{"github": ["owner/repo"], "aron": {"<search term>": "<why>"}, "pages": {"<url>":
"<why>"}}` – repositories, Czech ARON searches where a book is still missing, web pages. Empty by default; the state of
the last run is in `data/watch_state.json`. `news_watch.py --github-only` skips archive requests.

## Markdown notes
- `research_log.md` – table `| # | date | source | range | searched | result | citation |`, new rows at the end, also
  negative ones; in the range say **"with evidence"** or **"orientation only"**. Shown on the website as "Research
  log" – no living people with full birth dates there (`check.py` warns).
- `curiosities.md` – `## Heading` + text, links `[Name](/person/<slug>/)`, a `Sources:` line under each section.
- `story.md` – the main line's story: front matter `title`, `lead` + chapters `##`, each ending with `Sources:`;
  further lines in `story_<line>.md`. If the file does not exist, the menu item is hidden. How to write: `stories.md`.
- `proof_summary.md` – proof summaries of disputed links (`methodology.md` → Competing candidates and proof).
- `sensitive_review.md` – sensitive findings and the user's decisions (`privacy.md`).
- `archive_requests.md` – what can only be found on site or on request, and the e-mails sent (one per institution).
- `offline_sources.md` – sources that exist only physically (archive, library), for a visit or a hired genealogist.
- `family_info.md` – who in the family said what, documents received.
- `rounds_history.md` – older "In progress" points moved out of `STATUS.md` so that it stays short.
- Notes for Claude inside Markdown are written as `<!-- … -->` – they do not go to the website.
- `cases/<case>.json` – competing candidates (`tools/cases.py`); research state only, the website does not read it.

## Links to people (slug)
Slug = name without diacritics + year, e.g. `jan-novak-1890`; on a collision the person's number is added. Exact
slugs after `npm run data` in `web/src/data/site.json` (`people`). Renaming a person changes the slug – fix the links
in the texts. Family pages join two slugs with `-and-` (`jan-novak-1890-and-josefa-pokorna-1895`).

## Importing a family tree (Phase 1)
- **GEDCOM** (`.ged`, export from MyHeritage/Geni/FamilySearch/Ancestry/Gramps):
  `python3 -I tools/ged_import.py documents/tree.ged "Given Surname"` lists the ancestors with numbers, all events and
  notes, and a **queue of records** (the most recent known event for each ancestor and whether it is already in an
  archive). `--people` gives a skeleton for `people.py`; `--limits B,M,D` sets the closing periods (years) used to say whether
  a record can already be in an archive (default: the Czech 100,75,30 – set your country's, see `countries/README.md`). Notes in trees are often full of family stories – read them
  and extract them into `family_info.md`.
- Older trees from **Brother's Keeper** (ANSI encoding and Czech dates like "SRPEN 1945" are converted by the tool);
  places may be in an inflected form – write them in the base form in `people.py`. The root of such a tree is often
  not the user but their children (both lines) – choose the starting person by name.
- **MyHeritage tree backup** (ZIP with `<tree>.ftb` and a folder `Photos/` – a database, not GEDCOM): unzip into its
  own folder in `documents/` (often large – put it into `.gitignore`), then
  `python3 -I tools/ftb_export.py <tree.ftb> documents/tree.ged "Given Surname" <birth year> work/direct_line.md <Photos folder>`.
  (`--lang <code>` chooses the tree's data language when it has several – a MyHeritage language code.)
  You get a GEDCOM for `ged_import.py` (without addresses, e-mails and phones) and an overview of the direct line with
  **the origin of each fact** – for each person, from which other people's trees (Smart Match) or sources the data
  came. A person without an external citation = `fam`, documented only by other people's trees = `mh`. The overview
  also lists attached scans (register copies, death notices, certificates) – read them, they are often the most
  valuable family documents.
- Data from trees (also Smart Matches) are only a guide to the entry – the date and house lead you to the page, but
  **always verify the names in the entry** (a real mistake: a "marriage" from a Smart Match was another couple from the
  same house).
