# Country guides – index

The core of the skill is country-neutral. Everything that depends on a country – which archive holds what, portals
and their tools, paces and blocks, closing periods, local record types and terms – lives in one guide per country.
Read the guide for every country the family comes from (Phase 0); for international portals (FamilySearch,
Matricula, Arolsen, ANNO, Geneteka) see `../portals.md`.

| Country | Guide | State |
|---|---|---|
| Czech Republic (Bohemia, Moravia, Czech Silesia) – with a section on **Slovakia** | [czech-republic.md](czech-republic.md) | full: many portals with ready tools and browser procedures |
| Belgium (Flanders, Wallonia, Brussels) | [belgium.md](belgium.md) | full guide (AGATHA, civil and parish registers, population registers) |
| Austria, Germany, Poland, Hungary, others | quick notes below | no full guide yet – use `../portals.md` → Other portals and write what you learn |

## Closing periods – overview
How many years after the event (or after the last entry of the volume / the year of the register) records become
publicly accessible. Births / marriages / deaths. Details and the exact rules in the country guides; laws change –
verify on first use.
| country | period | counted from | note |
|---|---|---|---|
| **Czech Republic** | 100 / 75 / 30 | the last entry of the volume (archive); each entry (registry office) | younger entries for the person and close family |
| **Slovakia** | state registers (from 1895): 100 / 100 / 100 | the last entry | until then at the registry office, family only; **church books in the state archive** – personal data 90 years after the entry |
| **Belgium** | 100 / 75 / 75 | the act | population registers 120 years after closing; civil registers online mostly up to 1920 (`belgium.md`) |
| **Austria** | 100 / 75 / 30 | the entry (law) – the Vienna diocesan archive counts from the closing of the book | 100 and 75 years only if the entry does not concern a living person; after 1938 the *Standesamt* |
| **Germany** | 110 / 80 / 30 | the year of the register | earlier only for direct relatives or legal interest |
| **Poland** | 100 / 80 / 80 | the closing of the book | to the state archive within 2 years after the period – online availability lags |
| **Hungary** | 110 / 86 / 30 | the year after the register was opened | special data (religion, illegitimacy, cause of death) only 60 years after death |

Periods counted from the register year or the closing of the book (DE, PL) move once a year. Do not publish sensitive
data (religion, illegitimacy, cause of death) of the recently deceased – see `../privacy.md`.

## Quick notes for countries without a full guide
Most other archives are available only on written request – write into `data/archive_requests.md`.

**Austria (incl. Vienna, Burgenland)**
- **Catholic registers to 1938** in diocesan archives, images on Matricula (Vienna, Linz, St. Pölten, Graz, Tyrol,
  Carinthia, Salzburg, Vorarlberg). Burgenland (Eisenstadt) has its own portal matriken.at (incomplete). Matricula has no
  name search; the GenTeam index (registration by the user) covers many Viennese registers.
- **Protestant registers** (A.C., H.C.) from 1783, partly also on Matricula.
- **Civil registers from 1 Jan 1939** (*Standesamt*); church books after 1938 are church records only.
- **Kriegsarchiv (Vienna), all offline:** military registers 1633–1938 (by regiment, closed for 100 years), personnel
  sheets 1820–1918 (birth years about 1790–1900; years to ~1864 also on FamilySearch microfilm), muster lists 1740–1820,
  casualty card files 1914–18 (about 40 million cards, written request). Over 90 % of the documents are in German
  Kurrent.
- **Wiener Stadt- und Landesarchiv (WStLA):** police registrations (*Meldezettel*) about 1904–1975 (request only, paid
  even for a negative result); for people born before 1897 "Austria, Vienna, Population Cards, 1850–1910" on FamilySearch;
  death inspection protocols (*Totenbeschauprotokolle*), probate files (*Verlassenschaften*), duplicates of Old Catholic
  registers.
- Lower Austria: Franciscan cadastre (~1821) with building plots, owners and house numbers in the NÖ Landesarchiv
  (noela.findbuch.net).

**Germany**
- **Civil registration (*Standesamt*)** from 1 Jan 1876 (Prussia 1874); older civil records in the French-ruled
  Rhineland from 1798. Church books in diocesan and regional church archives, many on Matricula (Catholic) and Archion
  (Protestant, paid).
- Expellee records after 1945 (Heimatortskartei, Lastenausgleich) – Bundesarchiv Bayreuth (see the Czech guide,
  Sudeten Germans).

**Poland (incl. Galicia, Upper Silesia, Těšín/Cieszyn region)**
- **Parish registers (*metryki*)** in diocesan and state archives (AP), part of the images on Matricula, FamilySearch
  and szukajwarchiwach.gov.pl (the state archives' portal – not yet tested with the skill), index Geneteka
  (`../portals.md`).
- **Civil registers (USC):** in the Prussian partition from 1874, uniformly from the decree of 25 Sep 1945; to the state
  archive after the closing period.

**Hungary (also kept registers for Slovakia until 1918)**
- **State civil registers** from 1 Oct 1895; duplicates up to 31 Dec 1980 in the county archives of the MNL, otherwise
  the registry office (*anyakönyvi hivatal*).
- **Church registers** in church archives – each has its own periods (e.g. 90 years from opening the book). FamilySearch
  has filmed most of them. Hungaricana and Arcanum: browser only (scripts get 403).
- In Hungarian sources the surname comes first. Gazetteer: Helységnévtár 1877/1913.

**Netherlands, France, Luxembourg** – civil registration from the French period (1792–1811) with ten-year indexes; good
national indexes (OpenArchieven / WieWasWie for the Netherlands, departmental archives for France). No guide yet; the
Belgian guide's sections on civil registration, the Republican calendar and French/Dutch terms apply largely too.

## Writing a new country guide
When a project researches a country without a guide, collect what works in `notes_for_skill.md` and, once it is
substantial, write `reference/countries/<country>.md` (lowercase English name, hyphens). Suggested outline, following
the existing guides:
1. **In short** – a table: period → main source → where online → account/cost.
2. **How records are organised** – who keeps what (church, municipality, state), when civil registration started,
   duplicates, closing periods with the law, regions and historical borders.
3. **Portals and how to use them** – each portal: what it has, search, image download (tool or browser procedure),
   permalink format for `link`, volume key for `volumes.json`, pace and blocks (status codes, daily limits, CAPTCHA –
   always solved by the user), whether scripts are allowed (`robots.txt`, terms).
4. **Languages, calendar and names** – glossary of terms not in `../registers.md`, name forms, place-name forms,
   gazetteers.
5. **Research workflow** for the country (which record to start from, typical traps).
6. **Beyond registers** – land, tax, census, notarial, military, newspapers, local history (cross-reference
   `../../methodology/beyond_registers.md`).
7. **Societies, reading rooms and help** when online sources end.
8. **Sources** for every claim and a list of unverified points.
Tools for a new portal go into `tools/` (network only through `polite.py`, output into the project, `--help`), and the
portal's pace rules into `polite.py` if it needs a special limit. Add the guide to the table above.
