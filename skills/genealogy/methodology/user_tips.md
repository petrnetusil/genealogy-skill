# Tips from other users of the skill

A digest of practical notes that users of the original `rodokmen` skill reported (GitHub issues of
sarsonj/rodokmen-skill, state November 2026) and of experience from a long family project – only what is general
enough to help anyone. Country-specific details are in `reference/countries/`.

## New sources and routes
- **The FamilySearch catalog by place** (not just browsing collections) finds manorial land books, urbaria, tax rolls
  and court records the archives themselves have not put online. Books are usually filed under the seat of the manor;
  the catalog's place is often wrong – read the card on the first image (`reference/portals.md` → the land records trick).
- **FamilySearch register collections** as a backup when a national portal blocks or a daily limit is reached.
- **Cross-archive indexes of registers** (where they exist, e.g. matriky.online for Czech archives) show also volumes
  that are only in reading rooms. Watch default filters (e.g. "to 1900").
- **Published editions** of early tax and census lists (17th century) are often available as PDF from national archives
  or in digital libraries; the edition's introduction says which manors survived.
- **War dead:** casualty lists (ANNO for Austria-Hungary), death card files (e.g. the Austrian *Totenkartei* on
  FamilySearch), war graves registers and memorials of the village.
- **Village chronicles** – copies of land books with the holders of house numbers, family lists.
- **Theses** about manors and villages edit urbaria and name books that catalogues hide.
- **Marriage contracts and books of instruments** of manors and towns – the bride's father and house; good for the
  website.

## Method
- **Children "missing" in the mother's parish → search the father's home parish** in the years after the marriage.
- **Marriages within the manor:** when a marriage is missing, search the neighbouring parishes of the same manor.
- **Necronym** – a child named after a dead sibling; two baptisms of the same name = the elder probably died.
- **Legitimation notes** give the date and place of the parents' marriage.
- **Second reading of "(?)"** at 4–6× zoom (`-filter Lanczos -resize 400%`), comparing with letters of the same clerk.
- **Kurrent confusions:** N×R, Tr×Pe, Č×G, D×B, Sch×Ch, W×St, S×B/P/D, Z×P.
- **"Not online" only with a list of where and how it was searched**, checked by two routes; use a checklist of source
  types (tax rolls, cadastres, censuses, urbaria, military records, local histories, directories, indexes of editions).
- ***Hujus / ejusdem*** in a date = the month of the previous entry.
- **House renumbering** (e.g. ~1805 and 1857–1880 in the Habsburg lands, "alt/neu").
- **Indexes normalise names** – search variants; "not in the index" is weak evidence.
- **An independent second reading pays off:** a second model re-reading 88 entries found one wrong crop and two errors
  in a date or name; a review of disputed identifications found a dead child's baptism assigned to an adult ancestor.
  Make it a standard step (SKILL.md → Checking readings).
- **Record who read what** (model, version, date) on every record (`read_by`, `checked_by`).
- **Typewritten indexes** have wrong lines too – always verify in the book.

## Ideas for the website and checks (already in the skill or worth considering)
- "How are we related?", statistics, a "worth verifying" page, a "names" overview, a printable pedigree / "book of
  ancestors" PDF, a timeline "who could have met whom".
- Checks: a record names a parent, but the parent does not cite it; facts out of order; living people in the log
  (`family_checks.py` covers these).
- Shared public indexes of already-read books (where a community runs one): check before reading a book again; offer
  the user to contribute readings back – only with their consent.
- OCR of whole books without an index (e.g. PERO OCR with the user's own account) as a search aid instead of paging
  image by image – the OCR text is a finding aid, never `doc`.
