# International and general portals – and how to get images from them

National and regional archive portals (with their tools, paces and traps) are in `reference/countries/<country>.md`.
This guide covers portals used across countries, and what to do with a portal nobody has described yet.

| Portal | What | Access | Tools |
|---|---|---|---|
| **FamilySearch** (familysearch.org) | images of church and civil registers, land records, censuses from almost all of Europe; indexes; catalog | free account; **the user logs in themselves** | browser (Playwright), `cache.py` |
| **Matricula** (data.matricula-online.eu) | Catholic (and some Protestant) registers of Austria, Germany, Poland, Slovenia, Serbia, Belgium (some dioceses), Luxembourg… | free, no login | `matricula_dl.sh`, `matricula_batch.sh` + browser |
| **Geneteka** (geneteka.genealodzy.pl) | volunteer index of Polish B/M/D | free | web; single API queries |
| **Arolsen Archives** (collections.arolsen-archives.org) | prisoners, forced labourers, displaced persons of the Nazi era | free; terms accepted by the user | `arolsen.py` |
| **ANNO** (anno.onb.ac.at) | Austrian newspapers 1700–1950, Austro-Hungarian casualty lists 1914–19 | free | `anno.py`, `anno_snap.py` |
| Other newspaper portals | Delpher (NL), BelgicaPress (BE, KBR), Gallica / RetroNews (FR), Europeana Newspapers, national digital libraries | mostly free | browser; see country guides |
| **MyHeritage, Geni, Ancestry, FamilySearch Family Tree** | other people's trees, Smart Matches | partly paid | **clues only**, status `mh`, never mass access |
| BillionGraves, Find a Grave | photos of gravestones | free | browser |

Check addresses of untested portals on first use (portals change).

**Claude in Chrome – JavaScript output** (applies to all portals):
- Output containing an address with parameters (`?`, `&`, `=`) or a long hex string is dropped by the extension as
  "[BLOCKED: Cookie/query string data]". Return only the path (`location.pathname`, `new URL(a.href).pathname`) and
  the parameter values separately, or replace `?&=` with spaces; assemble the full address in the shell.
- Output is cut at about 1000 characters (lists at about 30 lines) – print longer lists in parts (`.slice(0, 25)`, …).
- Screenshots of heavy pages time out; read text via `get_page_text` / `read_page` or `innerText`.

## FamilySearch (through the user's logged-in browser)
FamilySearch has digitised microfilms of registers and many other records for most of Europe. Images and indexes
need a free account. **The user logs in themselves** in the Playwright window (or their Chrome); you never type the
password. The login lasts a few days – before a round, check it with one request (header "SIGN IN" or HTTP 401 =
logged out, not a block) and ask the user to log in again.

### Finding the volume: the catalog
- **Catalog by place:** `https://www.familysearch.org/search/catalog/results?q.keywords=<parish or place>` or
  "Places within …" in the catalog. A catalog entry lists films by years and content: read the film table with one
  `browser_evaluate` (text only, no links):
  `[...document.querySelectorAll('tr')].map(r => [...r.cells].map(c => c.innerText.trim()).join(' | '))`
  → note (record types and years) | film | **DGS** number. The entry's title often overstates ("Church records,
  1762–1927" may hold baptisms, marriages and deaths only to 1895). A note "For earlier years see …" points to the
  mother parish's film.
- **Catalog errors are common:** a Protestant film filed as Catholic, a filial parish inside the mother parish's film,
  wrong years, the wrong place of the same name. Before searching, make 2–3 probes on the film (religion column, place
  names, years) and check the record's author via the image-data API (below, `catalogs[].data.author`).
- **The "land records" trick (urbaria, manorial land books, cadastres):** search the catalog by the place (and by the
  seat of the manor – books are usually filed under the manor's seat, not every village) and look under **"Land and
  property"**, "Taxation", "Census" and "Court records". FamilySearch filmed many manorial land registers, urbaria
  (lists of subjects with their obligations), tax rolls and cadastres that the archives themselves have not put online
  (e.g. "Czech Republic, Land Records, 1450–1889"). The catalog's place is often wrong – **read the target card
  (title sheet) on the first images** of the film to learn what it really covers. If the catalog of a village is
  incomplete, search the archive's reference code or collection name in `q.keywords`.
- **Collections of registers** (e.g. "Czech Republic, Church Books, 1552–1981", "Slovakia Church and Synagogue
  Books, 1592–1935", "Belgium, Civil Registration, 1582–1920") are useful backups when a national portal blocks or a
  daily limit is reached. Pair the FamilySearch volume with the archive's volume (reference/volume number) and
  **compare the page with the archive's** (folio, year, at least two names) before reading – image numbers differ
  book by book (0, ±1, +7…). Put into `link` the image you actually read from.

### Indexes
- The search API can be called from the page context (`fetch(…, {credentials: 'include'})`):
  `https://www.familysearch.org/service/search/hr/v2/personas?q.surname=…&q.givenName=…&q.fatherGivenName=…&count=20`;
  results in `entries[].content.gedcomx`; the image ARK is in `sourceDescriptions[].identifiers.Persistent`
  (`3:1:…`). A hit is a clue – verify it in the register.
- Indexes are incomplete (often baptisms only) and names mangled (Latin/Hungarian/German forms, two given names
  reduced to one); `q.anyPlace` only sorts, it does not filter. Search via the parents, with surname variants, without
  the given name; search also by the spouse's name.
- Do not change tabs the user has open (after searching, return to the original address). Do not work around pages
  behind Cloudflare – ask the user to open them and send a screenshot.

### Navigating a film
- Film viewer: `https://www.familysearch.org/search/film/<DGS 9 digits>?i=<n>` opens a grid of thumbnails (index
  from 0, image = index + 1); the "Download" button appears only after "View single image".
- **Prefer ARK addresses** (`https://www.familysearch.org/ark:/61903/3:1:<ARK>`) for data and downloads, not `?i=`:
  in films with several groups ("waypoints") the viewer shows the number within the group while `?i=` counts from the
  start of the film, and the image-number field jumps within whichever film is open. Store the ARK in `link`.
- The list of a film's images: `POST /search/filmdatainfo/image-data` with
  `{"type":"film-data","args":{"dgsNum":"00…","state":{"i":"0"},"locale":"en"}}` (`images[]` = ARKs, in image order);
  `{"type":"image-data", …}` returns the `dgsNum` and catalog data for any ARK. Do not return whole ID lists into the
  context (large) – save them to a file.
- "Image Restricted" = locked by the archive's contract; viewable only in a FamilySearch centre or at the archive.
  Hundreds of 403s on **thumbnails** of locked images in the console are not a block; a 403 on the image you download
  is – stop. Test pages for "Image Restricted|Too Many|403 Forbidden", not just "403" (image numbers can contain it).
- **After ~1000 fast requests HTTP 429 comes** and a block of tens of minutes – download only specific images, at most
  one every few seconds; never browse whole books in bulk.

### Downloading an image into the project (Playwright, user logged in)
Tools get 403 from FamilySearch; only the logged-in browser gets the image. First check the cache:
`python3 -I tools/cache.py find <ARK address> --preview work/preview.jpg` – if the image is already stored, you do not
need the browser. Otherwise run in Playwright (`browser_run_code_unsafe`), at least 5 s between images:
```js
async (page) => {
  const list = [['holice_b_1760_p57', 'XXXX-XXXX-XXX']];   // [file name, ARK after 3:1:]
  const dir = '/absolute/path/to/project/work/fs';           // Playwright saves only where you tell it
  const out = [];
  for (const [name, ark] of list) {
    await page.waitForTimeout(5000);
    await page.goto('https://www.familysearch.org/ark:/61903/3:1:' + ark + '?lang=en');
    await page.waitForTimeout(7000);
    if (/ident\.familysearch|login/.test(page.url())) return out.join('\n') + '\nLOGGED OUT – ask the user to log in';
    const main = await page.locator('main').innerText().catch(() => '');
    if (/Image Restricted|Too Many|403 Forbidden/i.test(main)) { out.push(name + ' STOP: restricted / 403'); break; }
    const single = page.getByRole('button', { name: 'View single image' });
    if (!(await page.getByRole('button', { name: 'Download' }).count()) && (await single.count())) {
      await single.click(); await page.waitForTimeout(3000);
    }
    const dl = page.waitForEvent('download', { timeout: 30000 });
    await page.getByRole('button', { name: 'Download' }).first().click();
    await (await dl).saveAs(`${dir}/${name}.jpg`);
    out.push(name + ' ' + ark);
  }
  return out.join('\n');
}
```
Variables in `globalThis` do not survive between calls – pass the list in each call. Then `crop.py` as with other
archives. Alternative without the Download button: `fetch` of
`https://www.familysearch.org/service/records/storage/deepzoomcloud/dz/v1/<ARK 3:1:…>/$dist` with
`credentials: 'include'` in the page, returned as JSON `{url, data, w, h}` into a file (`browser_evaluate` with
`filename: "work/fs.json"`) and `python3 -I tools/cache.py save work/fs.json work/fs_<ark>.jpg --preview
work/preview.jpg` (stores the full-resolution image in the cache and in `work/`).
**Without Playwright** (Claude in Chrome cannot save to a file): the user downloads the image with the Download button
(or you do it with their consent) – the file arrives in `~/Downloads` as `<image id>.jpg`, briefly with a `.tmp`
suffix. Move **only the file with the expected name**, never "the newest file in Downloads" (there are others). No
local receivers on localhost or other tricks around browser protections.

## Matricula (data.matricula-online.eu) – `tools/matricula_*.sh`
- No login. Austria, Germany (many Catholic dioceses), Poland, Slovenia, Serbia, Luxembourg, parts of Belgium and
  others. List of books: `…/<country>/<diocese>/<parish>/?page=N`; image of a book `…/<id>/?pg=<image>` (also the
  permalink). No search by name.
- The image URL contains `csrf` and `ctrl` computed by JavaScript → a browser is needed (Playwright / Claude in
  Chrome): open the book, click a page (`.docview-pagelink`), take the image URL from
  `performance.getEntriesByType('resource')` and download it with `bash tools/matricula_dl.sh "<url>" work/x.jpg`.
  Several pages: a file of lines "<image> <url>" → `matricula_batch.sh`.
- The index can be found without a browser: the book page's HTML has a list `labels` with image labels
  ("04-Index Taufe_0001").
- Military registers (e.g. of Austro-Hungarian regiments) are not there – they are in the Kriegsarchiv in Vienna
  (offline).

## Poland – Geneteka (geneteka.genealodzy.pl)
- Free volunteer indexes of baptisms, marriages and deaths by parish; search in the web interface (voivodeship →
  parish → surname). The index is a guide – scans are often not online (parish or diocesan archive), then request the
  entry there.
- **Parish membership changed**: a village could belong to a neighbouring parish for a period – search there too.
- No bulk downloads: the society states "we link, we do not harvest data", and after dozens of fast queries the
  server returns unfiltered data. Batch queries with pauses and check the results.
- A single query also works without a browser (through the brake):
  `https://geneteka.genealodzy.pl/api/getAct.php?draw=1&start=0&length=10&bdm=B&rid=B&w=12sl&search_lastname=<surname>&search_name=&search_lastname2=&search_name2=&from_date=1850&to_date=1900&exac=1`
  (`bdm`/`rid` B baptisms, S marriages, D deaths; `w` voivodeship, e.g. 12sl Silesian, 08op Opole) → JSON. Trap:
  `recordsTotal` > 0 and empty `data` – try only one surname without the given name and narrower years. Paging repeats
  rows.
- Scans of some Polish parishes are also on Matricula or FamilySearch.

## Graves and cemeteries
- Where ancestors are buried is known from the family conversation (Phase 1). Photos of gravestones (names, dates,
  maiden names) are a valuable source mainly for the 20th century, where registers are not yet accessible.
- Grave registers: the cemetery administration (who is buried in the grave, who pays the lease – often a living
  descendant); many towns have online grave search. Internationally BillionGraves and Find a Grave.

## Newspapers and yearbooks
**When it pays off:** state and manorial officials, judges, teachers, priests, officers, military doctors, notaries,
postmasters, mayors, entrepreneurs – newspapers printed appointments, transfers, awards, pensions, bankruptcies,
marriage announcements and death notices (from about 1860). That tells **where a person lived when** → where to
look for children's baptisms, the marriage, the death. Also when a person "is missing" from the expected registers
(moved with their job). **Rather not:** farmers and craftsmen in villages.
- **ANNO** (Austrian newspapers 1700–1950, also Prager Zeitung, Wiener Zeitung):
  `python3 -I tools/anno.py '"Johann Nowak"' 1860 1915 [pages] [--snip]` – names **in German**. Crop of the hit:
  `tools/anno_snap.py <docId> "<query>" work/x.jpg`. ALEX and annoshow are behind Cloudflare – do not work around it.
- **Soldiers of World War I – Austro-Hungarian casualty lists** (ANNO, full text):
  `python3 -I tools/anno.py '"Surname Given"' 1914 1919 3 --snip --losses` (only `vll` Verlustliste, `vlv`
  alphabetical index with the list number, `nvv` news about the wounded; other titles via `ANNO_TITLE=ptb,wrz`).
  An entry: rank, regiment, company, **home municipality, year of birth**, wounded/captured/killed – e.g.
  "Hromadko Wenzel, Inft., IR. Nr. 98, 4. Marschkomp., Rokosnitz, 1881, Schuß …". The order is "Surname Given", in
  German (Wenzel, Johann); try without diacritics too; confirm by home municipality and year. Common surnames have
  thousands of hits – search by a rare surname or by the home municipality in its German (or Hungarian) form. Soldiers
  killed at the front are often missing from the home death register.
- Other national newspaper portals: Delpher (Netherlands), BelgicaPress (Belgium, KBR), Gallica and RetroNews
  (France), Europeana Newspapers, the Kramerius libraries (Czech Republic – see its country guide). Details per
  country in the country guides.
- Military yearbooks (Schematismus, army lists): full text on archive.org.
- **Risks:** names repeat and full-text OCR is noisy ("Winter" = also winter, "Nowak" = also "newcomer"). Identify
  only on matching several facts (residence, an office consistent with the register, sequence in time). The source is
  kind `O` (other) – a clue and a story, not a replacement for the register.
- Clippings are great on the website: save into `documents/newspapers/`, via `crop.py` and into `documents.json`.
- Order: registers first; newspapers when a trail is missing because of moves, or for an official/soldier to tell
  the story.

## Victims of persecution and war
- **Arolsen Archives** (collections.arolsen-archives.org): documents on prisoners, forced labourers and displaced
  persons. `python3 -I tools/arolsen.py search "Surname Given [year]"` – the user must first accept the portal's
  declaration personally (`! python3 -I tools/arolsen.py consent`; you never confirm it).
- **Mauthausen – Raum der Namen** (raumdernamen.mauthausen-memorial.org): prisoners who died in Mauthausen, with
  date and place of birth and death.
- National victim and prisoner databases are listed in the country guides.
- Such data are sensitive – on the website only with the family's consent (`privacy.md`, `sensitive_review.md`).

## Online trees: MyHeritage, Geni, Ancestry, FamilySearch Family Tree – clues only
- They can point to a parish, a year or a document you missed. Everything from them is status `mh` until you read the
  entry yourself – **never `doc`**. Smart Matches often mix up couples from the same house.
- **No mass browsing or downloading** – automated access gets accounts blocked (`privacy.md`). Read only what the
  user opens, at a human pace; prefer a GEDCOM export from the user.
- MyHeritage without a paid plan shows names, years and the tree's name but hides places and parents – useless for
  verification. Geni shows places and sources only to logged-in users.
- Other people's trees often carry confident errors (a wrong place of the same name, merged namesakes). Note in the
  log what the tree claims and what the register says.

## Emigration
Passenger lists (e.g. Hamburg and Bremen departures, Antwerp's Red Star Line, Ellis Island arrivals),
naturalisations, emigrant newspapers and associations. The original spelling of the home village is the key; English
forms of names differ. See `methodology.md` → Dead ends.

## Surnames today and DNA
- **Surname distribution today** (national surname maps, Forebears): quickly shows whether a surname is rare and where
  its "nests" are. When looking for distant relatives, exclude the user's own family.
- **DNA** (only if the user wants it – their decision): an autosomal test (MyHeritage, Ancestry, FamilyTreeDNA) finds
  cousins to about the 5th degree. **Y-DNA** (FamilyTreeDNA) passes from father to son unchanged; it shows whether two
  lines of one surname share an ancestor, and for an illegitimate child a match with another surname may reveal the
  father. Contact with living relatives always only through the user.

## Other portals – general procedure
There are no tools for them yet. Proceed as follows and write the result into `STATUS.md` so you know next time:
1. Open the portal in the browser (Claude in Chrome / Playwright, if available; otherwise ask the user). Find the
   collection "registers" / "parish books" / "civil registration" and the volume by place and years.
2. **Image:** most viewers have a button to download the image – save into `work/`. If not, look at the network
   traffic to see where tiles/images load from (IIIF, DeepZoom, Zoomify) and download the whole image that way – one by
   one, only images you read, and only if the archive does not forbid it (`<portal>/robots.txt`, terms of use). Last
   resort: ask the user to save the image into `work/`.
3. **Permalink** to the image ("permalink" button, otherwise volume URL + image number) into `link` of the record.
4. Write the volume via the tool: an object `{"archive": "…", "portal": "…", "title": "B Volary 1784–1820, ref. …",
   "description": "villages…", "url": "<link to the volume>"}` into `work/volume.json` and
   `python3 -I tools/write.py volumes <key> work/volume.json` (never edit `volumes.json` by hand or by a script).
5. Then as usual: `crop.py`, `frame.py`, transcription, people, log.
6. When the procedure works, write a small tool for the portal following an existing one (without a browser, only
   if the archive does not forbid it), record the procedure in `STATUS.md` and in `notes_for_skill.md` (for the skill
   maintainer) – ideally as a new or extended country guide in `reference/countries/`.

Everything that is only available on site goes into `data/archive_requests.md` (archive, collection, reference number,
what to look for) or `data/offline_sources.md`.
