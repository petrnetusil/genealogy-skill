# Curiosities, stories and person summaries

This is why the family reads the website. A table of names and dates grips nobody, but "great-great-grandfather
was born 267 days after the wedding" or "the family lived in one house for a hundred years" does. Do not wait with
it until the end of the research.

## The basic rules for every text on the website
- **Write for relatives, not for genealogists.** Storytelling in the family's language: who these people were,
  where they lived, what they did, what happened to them.
- **No research apparatus in the text:** no percentages, image numbers, folio references, "round 12", "log
  no. 47", "revision", "Kekulé 256", "doc/prob". These belong in the data, the research log and the collapsible
  research notes.
- **Uncertainty in words:** "probably", "most likely", "the family remembers that…", "we have not yet found…".
  Never invent anything for the sake of a smooth story.
- **Sources under each section:** every chapter and every curiosity ends with a line
  `Sources: [baptism of Jan Novák 1890](/source/holice_baptism_jan_novak_1890/), family album (aunt Maria), …`
  – record links, documents, books with page. A source that is not a register image (a book, a land record without
  a scan) can be recorded as a record of kind `O`, so it has its own source page. `tools/evidence_check.py` (run by
  `check.py`) reports sections without `Sources:` and claims ("died of cholera", "because of the war") whose sources
  are only interpretation.
- **Credit the authors** of photos, captions and memories by name ("told by grandmother Anna", "photo and caption:
  aunt Maria").
- **Sensitive content** (illegitimacy, crime, illness, suicide, causes of death of the recently deceased, politics,
  persecution, family conflicts) only after the user's approval (`privacy.md`, `data/sensitive_review.md`).

## After every new finding: check the texts
A new record or a correction can make a story wrong ("baptism not yet found", the wrong house, a death "still to be
verified"). After writing a finding into the data, search `data/story*.md`, `data/curiosities.md`,
`data/lines.json`, `data/memories.json`, the home texts in `website.json` and the `summary` of the people concerned
(grep the name, place and year) and update them – in the storytelling style above. Tell the user in one sentence
what you changed in the texts.

## Person summaries
Each ancestor with more than a few facts gets a `summary` in `data/people.py`: 2–5 readable sentences about their
life (where, trade, marriage, children, something human), in the family's language. It is the first thing on the
person's page. The long research `note` (sources searched, contradictions, reasoning) is shown collapsed under
"Research notes" – it can stay technical. Write or update summaries with `tools/person.py <n> summary="…"`, whenever
a person gets new facts.

## Curiosities ("fun facts") – collect continuously
Whenever you come across something unusual while reading an entry, write it **at once** into
`data/curiosities.md` as a short paragraph and tell the user as a story. After each bigger round run
`python3 -I tools/ideas.py`. The tool goes through the data and lists ideas (weddings shortly before a birth,
a family in one house, marriages between relatives, longevity, epidemics…). Check each idea in the entry before you
write it.

What tends to be interesting (all from one real family tree):
| Type | Example of how to write it |
|---|---|
| Weddings just in time | a table: wedding – child – after how many days (compute exactly); "a perfect hit": born 267 days after the wedding – probably conceived on the wedding night |
| Illegitimate children, legitimation | "The name survived thanks to a single mother" – the surname came from the mother; a legitimation note in the margin |
| A hundred years in one house | the same house over 3–5 generations, who was born and died there |
| An ancestor in the tree several times | grandfather and grandmother were distant relatives (`SAME`) – where the branches met |
| Unusual names | a first name after a saint (and how the registers mangled it) |
| Notable witnesses and godparents | a councillor, mayor, priest or manorial official at an ordinary craftsman's wedding |
| Dispensations | a wedding with the bishop's permission (kinship, no banns, Advent) |
| Trades in the family | tailors, gunsmiths, a barber-surgeon, a brewer… as one paragraph across all lines |
| Women's fates | twice widowed within ten years; a maid who married a widower 25 years older |
| Children who lost their parents early | the mother died after childbirth, the father in an epidemic – who raised the children |
| Epidemics and wars | cholera 1831/1849/1866, wars, the Spanish flu 1918 (cause of death in the entry!) |
| Modern times | a civil wedding and court permission for an under-age bride; moving after 1945 |
| Family story vs. register | "the family said Marie, actually Anna"; a confirmed family legend ("grandma came from a farm") |
| A lost beginning | where a line ends and why (burnt books, an illegitimate child without a father) |
| Newspapers | a clipping about an appointment, award, retirement, death notice – add the image to `documents.json` |
| Maps and houses | a cadastral map crop with the family house circled; the same house on a today's map |

Style: heading `## Short and curious`, 2–5 sentences, concrete dates and places, links to people
`[Name](/person/<slug>/)`, `Sources:` line. Put the best 2–4 also on the home page (`website.json` →
`home_curiosities`).

## The main line's story
**The main line** is the starting person's line (birth surname, usually line no. 8 in `LINES`). If the user wants
another one, set `website.json` → `story.line`. The story is called **"The story of the <family>"** (in the
family's language: "Het verhaal van de familie Dubois", "L'histoire des Dubois", "Příběh Novákových"). It has its own
menu item and is the main thing on the home page. Further lines can get their own story in `data/story_<line>.md`
(listed on the Stories page).

**When to write:** as soon as the main line has about 5 generations documented by registers. Do not wait until it
is "finished" – the story can be extended later. `check.py` reminds you. Offer it to the user even if they earlier
said "when there is more data".

**Procedure:**
1. Collect the material: facts, summaries and notes of the people of the main line, `SIDE`, curiosities,
   `memories.json`, `family_info.md`, family memoirs and documents, newspaper clippings, land records and maps.
2. Write a **draft in the chat** and get it approved (length, tone, what yes/no). Below the draft say what comes
   from registers and what from the family, and what you left out as sensitive. Save it only after approval.
3. Save it into `data/story.md`:
   ```markdown
   ---
   title: The story of the Nováks
   lead: One sentence that grips – from whom to whom the story leads.
   ---

   ## Prologue in the mist (1700–1750)
   …
   Sources: [baptism of Jakub Novák 1702](/source/holice_baptism_jakub_novak_1702/), land register of the manor (page 14)

   ## The blacksmiths of no. 112 (1777–1874)
   …
   Sources: …
   ```
4. Set `website.json` → `"story": {"menu": "The story of the Nováks", "line": 8, "button": "Read the story of the
   Nováks"}` and the home page (`home.heading`, 2–3 enticing paragraphs, a photo). Without `home` the home page shows at
   least the story's title and `lead`.

**What it should look like** (a proven form, about 800–1500 words):
- Chapters by generation, from the oldest ancestor to today. Heading = the person or their role + years
  ("The tailor of Holice (c. 1756–1812)", "The maid who saved the name").
- Each chapter 1–3 short paragraphs: where they lived, how they earned a living, marriage, children, something human
  (an entry, a witness, an accident, a move). End with `Sources:`.
- Concretely: dates, places, house numbers, quotations from the entry in quotation marks. Links to people
  `[Name](/person/<slug>/)` (slugs in `web/src/data/site.json`).
- Place names: archives and OpenStreetMap may spell a place differently from the family and today's official form.
  Ask which form the family uses and keep it throughout the text.
- Honestly: what we do not know, write as a question or a supposition ("probably", "according to the family").
- At the end a chapter about today: only names and relationships of the living, no details.
- The other lines get their space on the line pages (`LINES`, `lines.json`, `HYPOTHESES`), in their own stories and in
  the curiosities.
