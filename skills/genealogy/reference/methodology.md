# Methodology – linking records, identity, competing candidates, proof, dead ends

Read as needed: when you are unsure whether two records are the same person, when a search gets stuck (dead end),
when two candidates compete for one place in the tree, or before you declare a disputed link proven. Reading
registers and the glossary: `registers.md`; portals: `portals.md` and `countries/`; data format: `data.md`; sources
beyond the registers: `methodology/beyond_registers.md`.

## Linking records – what connects the generations
- **House number / farm / address.** Jan Novák at no. 12 in a death entry of 1820 (aged 70) and Jan Novák at
  no. 12 in a marriage of 1788 are probably the same holding. **Renumbering** (after fires, new building, reforms;
  in towns and suburbs) splits a village; one house may have two numbers over time. Check doubtful cases on
  a cadastral map of the period (country guide) and keep a table house → holder by year.
- **Farm name (*vulgo*, *genannt*, *dit*, *alias*).** "Wenzel Schmid vulgo Bauer" – the name of the holding outlives
  a change of holder and passes even to a son-in-law who married in. **It is not a surname:** when a "surname"
  changes when a farm is taken over, the land records explain it.
- **Godparents and witnesses (the circle of family and neighbours).** The same three godparent couples at eight
  baptisms 1790–1810 = one family; a change of godparents may mean a new marriage. But: godparents often came from
  established "godparent families", not necessarily relatives. `python3 -I tools/godparents.py` lists people who
  appear in several records.
- **Status in the entry.** Farmer → retired farmer in the same house = the old farmer handed over the holding.
  **The retired man is not automatically the father** of the new farmer (he may be the father-in-law, stepfather,
  an unrelated seller) – the land record states the relationship. A cottager ≠ a farmer of the same name; status
  can rise by marrying onto a farm.
- **Land records as proof of descent.** "Wenceslas sells to his son John … inheritance shares to brother Matthew,
  sister Anna" – one record names parents, child and siblings. Land records are often more careful than registers
  ("it was about money"). Payouts of shares were recorded even decades later – date each separately.
- **Orphans' records** give the ages of orphans → a window for baptisms (ages rounded).
- **Marriage contracts:** the bride's dowry "from her father George, farmer in X" shows her home parish. They are
  in town books and notarial records, not only in manorial books.
- **Probate records** name heirs, also in other districts and big cities. Collections are often incomplete.
- **Naming patterns:** the first son often after a grandfather. Weak evidence on its own.
- **Names in other languages** of persons and places (Kováč → Kovács, Šimek → Schimek, Gent = Gand, Mechelen =
  Malines, Bytča = Nagybiccse); in Hungarian sources the surname comes before the given name, Polish -owa instead of
  Czech -ová. Search all language forms.
- **Gazetteers:** use historical gazetteers of the country (country guide) to find old names and parish membership.
  Take parish membership as of the year of the event.
- **Legitimation in the margin** ("legitimised by subsequent marriage on …") identifies the father – the note may
  also be in another book (the parents' marriage entry, a later copy).
- **Right of settlement / home parish** (Habsburg *Heimatrecht*, Belgian *domicile de secours* and similar):
  police registrations, soldiers' records and settlement certificates give the home municipality → home parish.
  **Home municipality ≠ place of birth** (the right was also acquired by residence or marriage).

## Identity – when it is the same person
- **Default rule:** link two people of the same name only by **two independent characteristics** – house number,
  both parents, spouse, the same circle of godparents, exact birth date. Each characteristic from a different record
  (different clerk / informant). One characteristic or just name and period = `prob` with a `note` why;
  contradictions into `ISSUES`.
- **Cousins of the same name in one village:** the house alone is not enough (they lived next door or in one house) –
  require the parents **and** the wife.
- **A remarried widow** appears under two husbands' surnames: link by **maiden name and father's name** in both
  marriage entries.
- **Contradictions between sources:** the original beats a copy; weigh who reported the fact and how long after the
  event (a birth date in a death entry reported by a neighbour is weaker than the baptism). Write the contradiction
  into `ISSUES`.
- **Step-families:** the retired man may be a step-parent; the land record states the relationship.
- **Foundlings:** no parents – link via the foundling number (foundling hospital) and the wet nurse's village.
- **Soldiers:** the two characteristics are **regiment and home municipality**, not just the place of birth.
- Before recording "same person", **list the other candidates** of the same name in the parish and why each does
  not fit (in the `note` or in the log). And write what new evidence would overturn the conclusion.

## Competing candidates and proof
When two or more people could fill one place in the tree (two couples "Wenceslas × Catherine" baptising children in
one village at the same time; two possible fathers), do not decide by gut feeling.
1. **Open a case:** `python3 -I tools/cases.py new <case> "goal" [--person N]` (case file `data/cases/<case>.json`,
   belongs in git, the website does not read it). Add each candidate (`cases.py candidate <case> <id> "description"`).
2. **Read layer by layer** (breadth first): layer 1 = the candidate's own baptism, marriage, death; layer 2 = their
   children, godparents, witnesses, siblings; layer 3 = parents, parents-in-law. Record each entry read
   (`cases.py record <case> work/x.json`) and tasks (`cases.py task …`, `cases.py done …` – also "searched, found
   nothing", which is a result too).
3. **Look for overlaps:** `cases.py intersect <case>` shows where the people and houses of each candidate meet what is
   already documented about the ancestor ("anchors"); `cases.py families <case>` groups children by parents (order,
   gaps, repeated names, stable godparents); `cases.py overview <case>` shows what is next.
4. **Decide by evidence, not by the number of matches:** `cases.py state <case> <id> open|excluded|confirmed
   "reason"`. Only a confirmed candidate goes into `data/people.py`. The tool compares names loosely (Latin/German
   forms, w/v…) – its matches are suggestions; check each in the entry.
5. **Proof summary** (`data/proof_summary.md`) for every disputed or important link, following the Genealogical
   Proof Standard in five points:
   1. **What was searched** (by type of source – registers, indexes, land records, censuses, family documents),
      with ranges, so nobody searches again;
   2. **Sources and their reliability** (original / copy / index / family memory; informant and distance in time);
   3. **Conflicts and how they are resolved**;
   4. **Conclusion** in words (proven / probable / possible) and the resulting status (`doc`/`prob`);
   5. **What would change the conclusion** and where to look for it.
   Update it after every new finding that touches the case. On the website, uncertainty is told in words (see
   `stories.md`), never with percentages.
6. **Checks:** `python3 -I tools/check.py` runs the family checks (`family_checks.py`: a child's record names the
   parent but the parent does not cite it; a fact dated after the person's death; living people with full birth
   dates in the log; the same ancestor twice without `SAME`) and the evidence check (`evidence_check.py`: impossible
   chronology – child before the parents' marriage, after a parent's death, mother younger than 14 or older than 50;
   sections without `Sources:`). Each warning is checked, not just silenced.

## Independent review by a second model
Independent of who read an entry first, the uncertain and key readings get a second, independent reading (rules in
SKILL.md → Checking readings): Claude Fable when available, otherwise another model or a fresh session without the
project's context. Prepare the material with `python3 -I tools/audit.py brief <key> … [--round N]`; the reviewer
works from enhanced crops (contrast, zoom, strips via `tools/enhance.py`) and compares letter shapes elsewhere on
the same page; load the answer with `audit.py load <answer.json>`. Then **you** check the result on the image and
write it into the data (`checked_by`, corrections, `ISSUES`). Automatically after about every 8 rounds and whenever
readings conflict – also with a professional genealogist's report. Experience: a second reading of 88 entries found
one wrong crop and two errors in a date or name; a review of disputed identifications found a baptism of a child
who died young wrongly assigned to an adult ancestor.

## Mistakes to watch for
(In addition to "Typical traps" in `registers.md`.)
- **Two men of the same name merged into one** – you notice it by children of the "same" couple born 10 months
  apart. The marriage entries of both and the house numbers decide.
- **The father of an illegitimate child guessed** without a legitimation note – look for the note, the mother's later
  marriage, the godparents.
- **Wrong parish because of parish reorganisations** (new parishes founded) – the village is missing from the
  expected book; check when the parish was founded and look for older entries in the mother parish.
- **Renumbered house** – same family, different number.
- **Age at death taken without tolerance** – "baptism not found"; widen the window, old people's ages tend to grow.
- **Place of marriage = origin of the bride** is not certain – banns (a note about banns in another parish) and land
  records show where she came from.
- **A Latin name converted wrongly** (Joannes ≠ Joachim).
- **A foreign-language place name not matched** – the village "does not exist"; find it in a historical gazetteer.
- **A godparent taken for a relative, a retired farmer for the father** – see above.
- **A soldier's place of birth confused with his home municipality.**
- **Jewish surnames:** often fixed only around 1787–1810 (by state decree), before that patronymics.
- **A convert:** the former identity disappears; an adult baptism often has a note on the conversion → look in the
  Jewish or other register.
- **A Protestant looked for only in the Protestant register:** in many Catholic countries the Catholic priest also
  recorded non-Catholics for decades – try both.
- **A death in a big city looked for in the home parish** – the entry is in the city parish (or the city's civil
  register).
- **A name anglicised (or otherwise changed) abroad** – in home records it "does not exist"; passenger lists and
  naturalisations give the original form.
- **A soldier's child "missing"** – it may be in a military register of the regiment, not in the parish.
- **Double counting:** a duplicate register and the original are not two independent sources – one is a copy of the
  other.

## Dead ends – what to try, in this order
- **Before the registers become detailed (often before ~1780) or before they start:** 1. read the older combined
  B/M/D books completely (not just the index) → 2. land/manorial records → 3. orphans' records, marriage contracts →
  4. tax and cadastral surveys → 5. early censuses and lists of subjects. They connect via the **holding/house and the
  sequence of holders**. For farmers with surviving land records the realistic bottom is **around 1650**.
- **The book has not survived:** duplicates and separate indexes, land records, censuses, for men military
  conscription lists. They connect via the house number.
- **Illegitimate child:** legitimation in the margin → the mother's later marriage → godparents → paternity court
  file → land records. They connect via the mother and the child's house.
- **Moved to a big city:** the city parish or civil register → police registration records → probate → home
  municipality.
- **Emigrated (e.g. to the USA):** passenger lists → naturalisation → church and emigrant associations → margin notes
  in the home parish. They connect via **the place name in its original spelling**.
- **Soldier:** first the **regiment** (by home municipality) → conscription and muster lists → personnel records →
  military registers of the regiment → casualty lists 1914–18 (`portals.md` → Newspapers) and casualty card files.
  Country specifics (e.g. Austro-Hungarian records in Vienna and Prague) are in the country guides.
- **Foundling:** foundling hospital records → the wet nurse's parish. Connect via the foundling number.
- **20th-century record not yet public:** the civil registry office (relatives usually have access), police
  registrations, family documents and gravestones. Into `archive_requests.md`.
- **Expelled or displaced family after 1945:** the expellee card files and compensation files of the receiving
  country (country guide), Arolsen Archives for displaced persons (`portals.md`).
- **Name change, language forms:** all forms of the person and place (above).
- **Online trees** (FamilySearch Family Tree, Geni, MyHeritage): only hints – status `mh`, never a solution of a
  dead end; but their sources can point to a volume you missed.

## Milestones of record keeping (examples – details in the country guides)
| year | what changed | what it means for the search |
|---|---|---|
| 1563 | Council of Trent: Catholic baptism and marriage registers required | registers start in many Catholic regions 1580–1650 (often later after wars) |
| 1582 | Gregorian calendar (Catholic countries); Protestant regions often only 1700 | dates may differ by 10–11 days |
| 1618–1648 | Thirty Years' War | many registers in Central Europe start after 1650; lists of subjects and tax rolls fill the gap |
| 1770s | numbering of houses (Habsburg lands 1770/71) | the house number becomes the key link; beware of later renumbering |
| 1784 | Habsburg lands: separate B/M/D books with printed columns | uniform columns, parents' parents named in baptisms |
| 1792–1811 | French civil registration (France 1792, Belgium 1796, Netherlands 1811, Rhineland, Luxembourg) | civil registers with ten-year indexes (*tables décennales*); Republican calendar 1793–1805 |
| 1850 | end of manorial administration in the Habsburg lands | land and orphans' records move from manorial to court collections |
| 1874–1876 | Prussia / German Empire: civil registration (*Standesamt*) | civil records for families who moved to Germany |
| 1895 | Hungary (incl. Slovakia): civil registration | parallel state series, church books continue |
| 1914–18 | casualty lists, casualty card files | main substitute for lost military records |
| 1939 / 1950 | Austria / Czechoslovakia: civil registration | church books stop being official records |
