# Where to look when the registers are silent

<!-- Adapted (MIT) from:
     - micl79/rodokmen-skill, skills/rodokmen/reference/souvislosti.md (Jindřich Šaršon, Michal Kos) – sections on
       context from the data, other sources, the manor, Napoleonic and military sources;
     - zbysekvoda/rodokmen-plus, skills/rodokmen-plus/reference/portaly.md and metodika.md (Zbyšek Voda) – older
       sources, land registers, mills, cadastres, WWI soldiers, Matricula/Vienna, Slovakia/Hungary, expulsion,
       hand-downloaded books, dead ends, milestones;
     - the experience of a long family project (about 400 log entries), generalised.
     Rule: everything outside the registers is a CLUE – a person becomes `doc` in data/people.py only from an entry
     read on an image; otherwise prob/fam. -->

How to read this: sections follow a **question**. For each source: **where** · **what it gives** · **online or
offline**. Concrete archives, portals and reference numbers are in `reference/countries/<country>.md`. Offline sources
go into `data/offline_sources.md`, questions to an archive into `data/archive_requests.md` (**one e-mail per
institution; until it replies, no further e-mail** – collect new points for the reply).

---

## 0. Before you start – context from the data you already have (no new archive)
1. **Network of godparents and witnesses** (`python3 -I tools/godparents.py`) – godparents were often relatives. The
   godparents of a baptism can prove that a man recorded under a farm name is the same as a man recorded under his
   surname.
2. **The house as a thread** – list all entries of one house number by year; whoever lived in the house before the
   ancestor is often the father-in-law. Beware of **renumbering** (keep a table house → holder by year).
3. **Siblings as a shortcut** – a sibling's marriage or death often states what your entry left out.
4. **Age as a filter, not a fact** – at deaths of old people it is often exaggerated by 5–15 years; look for the
   baptism from −10 to +3 years, at marriage ±3.
5. **Farm names** – surnames were written after the holding ("X or Prima", *vulgo*, *dit*): look for all aliases and
   the list of holders of the farm (tax rolls, cadastres).
6. **Contradictions as a clue** – two different mothers' names among siblings = a second marriage, or another couple
   with the same names. Do not merge silently; open a case (`tools/cases.py`).
7. **The whole parish at once** – read the index under the letter completely and reconstruct families; an index line
   is only a candidate.
8. **What has been searched** – `python3 -I tools/searched_books.py <surname>` and `--book <ref>`, so nothing is
   searched twice.

---

## 1. "Who was the father, when the register is silent?" (baptism not found, the register starts late, a leaf is illegible)
| Source | Where | What it gives | Online / offline |
|---|---|---|---|
| **Neighbouring and mother parishes, chapels of ease** | the country's register portal | parish membership changed (new parishes, filial churches); a village was sometimes recorded by another parish | online |
| **Separate indexes** | register portals, FamilySearch | summary over decades, often into the 17th century; may survive where the book did not | online |
| **Burial or marriage of a child** | D and M registers | the father's name at a child's burial, "daughter of the late X" at a bride's marriage | online |
| **Illegitimate sections and legitimations** | special sections of books, margin notes | the father added later, godparents | online |
| **Registers at the edge of legibility** | full-resolution image | – | online, then **the original under a UV lamp** in the archive. Try `tools/enhance.py --strips` (blur + division by the background of a downscaled copy + levels per strip); for show-through only raise levels. List the leaves in `offline_sources.md` |
| **Land / manorial books** | manorial or court collections | transfer of the holding "bought from his father", marriage contracts, siblings with shares | mostly **offline**; parts on FamilySearch (catalog → Land and property) |
| **Orphans' books and guardianship records** | manorial / court collections, orphan chambers | guardians, children with ages, paternity | offline |
| **Marriage protocols, banns books** | parish collections in district archives | parents, residence, the father's consent | offline |
| **Other people's trees: FamilySearch Family Tree, Geni, MyHeritage** | the user's account | only a hint, never proof | online with login; MyHeritage without a paid plan hides places and parents – useless for verification |

---

## 2. "Who held the farm?" (sequence on the holding, retirement, marrying in)
| Source | Where | What it gives | Online / offline |
|---|---|---|---|
| **Land books of the manor** | collections "great estate / manor <name>" in regional archives | transfers father → son, marriage contracts, retirement contracts, debts | often offline; some scanned, some on FamilySearch |
| **Collections of court land books** (after the manorial era) | regional archives | land books of district courts | finding aids often typewritten, books offline |
| **Urbaria and urbarial surveys** | manorial collections | farmers by village with their obligations | offline; some on FamilySearch |
| **Tax cadastres** (18th century) | national archives | the holder of every farm and its size | mostly offline (finding aids online) |
| **Revisions of tax rolls** | national archives | "instead of X now Y" – who took over a farm | offline |
| **Cadastral maps of the 19th century** (stable / Napoleonic / Franciscan cadastre) | national survey offices' map archives, regional archives | house and plot numbers, sometimes owners' names; plot protocols with owners | maps often online, written protocols offline |
| **Mills** | national mill databases (where they exist) | holders of a mill over centuries | online |
| **Land registers of the nobility** | national archives | only noble/free estates; sales sometimes list the subjects by name | indexes sometimes online |
| **Town books** (deeds of sale, wills, marriage contracts) | town and district archives | burghers | partly online |

---

## 3. "Before about 1650" (before the registers, or the register starts late)
| Source | Where | What it gives | Online / offline |
|---|---|---|---|
| **Lists of subjects / of faith, early censuses** (e.g. Bohemia 1651) | editions as PDF from national archives, digital libraries | whole households with ages, servants | often online (sometimes only for logged-in library readers – read only) |
| **Tax rolls** (e.g. Bohemian *berní rula* 1654, hearth taxes, *Schatzungen*) | editions by region | farmers with land size | editions online / in libraries |
| **Land-tax visitations and confiscation estimates** | national archives | names of subjects | offline |
| **Confession lists** (late 17th–early 18th century) | editions, diocesan archives | farmers by village | partly in libraries only (digitisation on demand, e.g. EOD – books2ebooks.eu) |
| **Visitation reports of parishes** | editions in digital libraries | parishes, chapels, numbers of Catholics / Protestants | online |
| **Theses** | university repositories | editions of urbaria, demography of manors | sometimes online, sometimes only for university login |
| **Literature about the lordship** | digital libraries | who owned the village → where the books are | online |
| **Medieval and early modern editions** | national source editions | land register entries | online |

**The key to the 17th–18th century: through the lordship, not the parish.** For each branch write down the manor (who
owned the village in which year) – that tells you in which collection to look for land books, urbaria and lists.

---

## 4. Soldiers (Napoleonic wars, 19th century, World War I)
| Source | Where | What it gives | Online / offline |
|---|---|---|---|
| Notes in the register ("miles", "Soldat", "invalide", "Regiment") | registers | soldier, regiment | online |
| **Personnel and muster records** | national military archives (e.g. Kriegsarchiv Vienna for Austria-Hungary; parts on FamilySearch microfilm) | birthplace, parents, service | online (FamilySearch) / offline |
| **Casualty lists 1914–18** | ANNO (`tools/anno.py --losses`, search the **home municipality in German/Hungarian**), national digital libraries | wounded, captured, killed; regiment | online |
| **Databases of the fallen, legionnaires** | national military history institutes | record of the fallen | online |
| **War graves and memorials** | war graves registers, memorial databases | names of the fallen of a village | online |
| **Military death registers** | military archives' digital reading rooms | the soldier's death entry | partly online |

## 5. "The 20th century" (records younger than 100 years, living people)
| Source | Where | What it gives | Online / offline |
|---|---|---|---|
| **Civil registry offices** | the municipality | younger births, marriages, deaths – for the family | in writing |
| **Censuses** (19th–20th century) | archive portals, FamilySearch, national portals | the whole household with dates and places of birth | online |
| **Population registers** (Belgium, Netherlands, Italy…) | municipal and state archives | households over decades, moves | partly online |
| **Contemporary press, directories** | digital libraries (full text, proximity search `"a b"~N`), ANNO, Delpher, BelgicaPress | trades, deaths, associations | online |
| **Village and school chronicles** | district/municipal archives | events, the fallen, copies of land books | mostly offline |
| **Family documents, memories** | the family | dates, photos, stories – credit the author | – |
| **Oral history archives** | national memory projects | memories of the 20th century | online |
| **Victims and prisoners of WWII** | national victim databases, Arolsen | imprisonment, fate | online (terms accepted by the user) |

## 6. "They moved away" (big cities, abroad, expulsion)
- **Big cities:** city parishes and civil registers, police registration records, Matricula for Austrian dioceses
  (`reference/portals.md`), city archives (often only on paid request).
- **Former Hungary, other multilingual regions:** FamilySearch (church books, indexes with Hungarian/Latin names);
  catalogs are often inaccurate (wrong religion, filial parishes in the mother parish's film). Archive inventories as
  PDF on the archives' websites. Some portals (Hungaricana, Arcanum) are browser only.
- **Expulsion and displacement after 1945:** registers stayed in the country of origin; transport lists, expellee card
  files and compensation files in the receiving country (country guide).
- **Emigration overseas:** passenger lists, naturalisations, emigrant associations; the original spelling of the
  village is the key.
- **Books downloaded by hand** – when an archive does not allow scripts: the user downloads the book with the portal's
  button into `work/<key>_<name>_manual/` with a `contents.txt`; anchors year → image go straight into the volume's
  `orientation`.

## 7. Requests and orders (when nothing is online)
- **National archives** – requests for reproductions with the exact reference (finding aid, inventory number). One
  e-mail with all points; wait for the reply (and the price) before writing again.
- **Regional archives** – usually no research for you; the reading room has fixed days, order books in advance
  (collection + inventory number).
- **District / municipal archives** – parish collections, chronicles, municipal records; some collections are closed.
- **Libraries** – works under reading-only licences: the user reads while logged in (no downloading, no printing);
  works available only on a library terminal → `offline_sources.md`; digitisation on demand.
- **A professional genealogist** – when online sources are exhausted, prepare a list for an on-site visit
  (`offline_sources.md`: what, collection and number, whom it concerns, what it would decide). A genealogist's
  transcription counts as a check (`checked_by`); where it conflicts with your reading, the independent review decides
  and the user is told.

## 8. Dead ends – order of what to try
- **Before detailed registers:** whole older B/M/D books (not only the index) → land books → orphans' books, marriage
  contracts → tax cadastres → early lists of subjects and tax rolls. The realistic bottom for farmers is around 1650.
- **The book has not survived:** duplicates, separate indexes, censuses, military conscription lists.
- **Illegitimate child:** legitimation in the margin → the mother's later marriage → godparents → court file → land
  books.
- **Identification:** two independent characteristics; list the other candidates of the same name and what would
  overturn the conclusion (`reference/methodology.md` → Competing candidates and proof).

## 9. Before writing "not online"
List where and how you searched, checked by two routes (the country's portal and the FamilySearch catalog), and go
through the checklist of source types: registers and indexes, duplicates, censuses, land books, urbaria, tax rolls and
cadastres, orphans' records, notarial deeds, military records, newspapers and directories, local histories and
chronicles, editions and their indexes. Only then write it into `archive_requests.md` / `offline_sources.md`.
