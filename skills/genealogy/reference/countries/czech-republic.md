# Czech Republic (Bohemia, Moravia, Czech Silesia) – archives, portals and tools

The best-equipped country of this skill: the skill grew up here, and many tools are written for Czech portals.
General reading of registers: `../registers.md`; international portals: `../portals.md`; Slovakia (shared history
until 1993, Hungarian until 1918) at the end of this guide.

Czech portal labels are quoted in Czech with an English explanation. Czech words you will meet constantly:
*matrika* = register, *svazek* = volume, *snímek* = image, *farnost / fara* = parish, *obec* = municipality/village,
*čp.* (číslo popisné) = house number (`no.` in the data), *rejstřík / index* = index, *N / O / Z* = births (narození) /
marriages (oddaní) / deaths (zemřelí), *SOA* = state regional archive, *SOkA* = district archive, *badatelna* = reading
room.

## Which archive
Registers are online at eight state archives – according to **where the ancestors lived** (today's regions roughly
match):

| Archive | Area | Portal with registers | Works with the skill |
|---|---|---|---|
| SOA Zámrsk | east Bohemia (Hradec Králové and Pardubice regions) | ARON – aron.vychodoceskearchivy.cz | **yes – ready tools** |
| SOA Praha | central Bohemia | eBadatelna – ebadatelna.soapraha.cz | **browser only** – the archive forbids tools since 2 Nov 2026 (procedure below; also urbaria and land books) |
| SOA Plzeň | west Bohemia | Porta fontium – portafontium.eu | **yes – `portafontium.py`** |
| SOA Třeboň | south Bohemia | digi.ceskearchivy.cz | **browser only** – the archive rejects tools since 2 Nov 2026 (procedure below) |
| SOA Litoměřice | north Bohemia | Digitální badatelna – digi.soalitomerice.cz | **partly – `soal_zoomify.py`** (find the book in the browser) |
| AHMP | the city of Prague | katalog.ahmp.cz (Pragapublica) | **yes – `ahmp_search.sh`, `ahmp_scan.py`** |
| MZA Brno | south Moravia, part of Vysočina | Acta Publica – www.mza.cz/actapublica | **browser only** – screenshot of the zoomed entry (procedure below) |
| ZA Opava | north Moravia and Silesia, Olomouc and Litovel areas | Digitální badatelna – digi.archives.cz/da/ | **browser only, best Playwright** – full image from the tiles the browser loads (procedure below; the user solves the CAPTCHA) |
| National Archives (NA) | Jewish registers (HBMa), lists; Prague police registrations 1850–1914 | HBMa: VadeMeCum NA – vademecum.nacr.cz (Digitální badatelna → Matriky židovských náboženských obcí; the old address badatelna.eu no longer belongs to the archive); digi.nacr.cz/prihlasky2 | registrations **yes – `prague_police.py`** |

Check the addresses of untested portals on first use (portals change). Overview of all archive collections with
finding aids: Národní archivní portál (NARP, portal.nacr.cz) – check there before writing to an archive. A cross-archive
index of registers including those only in reading rooms: matriky.online (default filter "to 1900").
FamilySearch has most Czech church books too ("Czech Republic, Church Books, 1552–1981") – a good backup when a portal
blocks (`../portals.md` → FamilySearch).

**Certificate check on macOS/Windows** (Phase 0):
`python3 -I -c "import urllib.request; urllib.request.urlopen('https://aron.vychodoceskearchivy.cz')"`.

## Czech registers – what is special
- **Kinds:** N (births), O (marriages), Z (deaths), I (index); in the data they are `B`, `M`, `D`.
- **1784 – Josephine patent:** separate books with printed columns; baptisms then name the parents' parents and
  residence. Before ~1780 Latin or Czech, then much German (Kurrent), from ~1860 often Czech, in the 20th century Czech.
- **House numbers** since the conscription of 1770/71 – the key link between generations; renumbering around 1805 and
  1857–1880 ("alt/neu"), after fires and in towns.
- **Duplicates** (druhopisy, e.g. "T" volumes in ZA Opava) hold N, O, Z of one year together.
- **Protestant registers:** after the Toleration Patent (1781) Lutheran (a. v.) and Calvinist (h. v.) congregations
  kept their own registers, one congregation covering dozens of villages; in ARON they have reference codes "R …" and
  `aron_search.py` finds them by village. Common in east Bohemia. The Catholic priest also recorded non-Catholics until
  about 1849 – try both. **Mixed marriages:** from 1868 sons followed the father, daughters the mother, unless the
  parents agreed otherwise; before 1868 all children of a Catholic father were Catholic.
- **Old Catholics** (recognised 1877) may be missing from Catholic books after that year.
- **Civil registers (1920–1945) of people without religion** are in the books of district offices (e.g. Tábor) – a good
  route when the parish register is silent. They do not show under the village (they belong to the district) – look
  under the district town.
- **State civil registers from 1950** (Czechoslovakia); parish books stop being official.
- **Names:** Czech names in German/Latin: Johann/Joannes = Jan, Wenzel/Wenceslaus = Václav, Joseph = Josef,
  Franz/Franciscus = František, Maria = Marie, Katharina = Kateřina, Barbara = Barbora, Magdalena = Majdalena/Magdaléna,
  Theresia = Terezie, Ludmilla = Lidmila, Dorothea = Dorota, Apollonia = Apolena, Georg/Georgius = Jiří,
  Matthias = Matěj, Adalbert = Vojtěch. Women's surnames in German without "-ová" (Maria Novak = Marie Nováková).
  Surnames are phonetic and change (Šaršon/Scharschon/Šaršoun, Kroupa/Kraupa).
- **Indexes follow German spelling:** Czech names on O and V also under W (Otava = Wotawa, Vávra = Wawra); in
  17th–18th-century indexes Š is written as "St" / "Sſt" (Sſtiepanek = Štěpánek). Place names have old forms with a
  prefixed "V" ("Volešnice" = Olešnice) and German names (Trutnov = Trautenau, Vrchlabí = Hohenelbe, so "Langenau … bey Hohenelbe"
  = the Langenau near Vrchlabí). Find the German name of every village before searching an index.
- **Farm names:** surnames were written after the holding ("X neb Prima" = "X or Prima") – look for all aliases.
- **Parish reorganisation after 1784** (new parishes and *lokálie*): a village may be missing from the expected book;
  older entries are in the mother parish.

## Access periods (Act 301/2000 Coll.)
A volume goes to the archive (and online) only when, since its **last** entry, there have passed: births **100 years**,
marriages **75**, deaths **30**. Younger books are at the registry office of the municipality with extended
competence. **The registry office, however, counts the period for each entry separately** (§ 25b of Act 301/2000
Coll.): an entry older than 100 / 75 / 30 years (birth / marriage / death) is issued to **anyone** even from a volume
still at the office, and one may look into the book. A younger entry is given only to the person concerned or a family
member (spouse, partner, parents, children, siblings, grandparents, grandchildren, great-grandchildren) with proof of
relationship. Ask for a **literal extract** (*doslovný výpis*) – unlike a birth or marriage certificate it includes the
margin notes (later marriage, death, legitimation). The same periods apply to the collection of documents and
duplicates up to 1958. Write it into `archive_requests.md`.
Archive catalogues list **also volumes still at the office**: in the detail "Technická poznámka: MATRIKA JE DOSUD
ULOŽENA NA MATRIČNÍM ÚŘADĚ" (technical note: the register is still kept at the registry office), "Místo uložení:
Obecní úřad X" (place of storage: municipal office X) and 0 attachments (images). Read that note before looking for
images; write the volume into `archive_requests.md` with the place of storage (that is where to ask for an extract).
Try a **separate index** (I-N, I-O, I-Z) over the same years or a **duplicate** (it may end earlier than the original
and thus already be in the archive) – often online, it gives at least the date and house number. Tell the user in
advance that births after roughly 1910 are often not online (the book continues past 1926, and the period runs from the
last entry).

## ARON (SOA Zámrsk) – ready tools
- **Finding volumes:** `python3 -I tools/aron_search.py "Holice"` → lines `apu_id | reference, years | kind, villages`.
  The description contains the kind of book (NAROZENÝCH / ODDANÝCH / ZEMŘELÝCH = births / marriages / deaths, index)
  and all villages of the parish.
- **Volume info:** `python3 -I tools/aron_img.py <apu_id> info` → title and number of images.
- **Downloading an image:** `python3 -I tools/aron_img.py <apu_id> <image> 1 work/holice_b_57.jpg`
  (level 1 = half resolution – enough for orientation; 0 = full resolution – for reading and the crop).
  Only part of the page at full resolution: `… <image> 0 work/detail.jpg 0.0,0.4,1.0,0.7`.
  The tool downloads the whole scan in one request (like the download button in ARON) and makes reductions and crops
  from disk; further crops of the same page do not go to the archive. Tiles (dozens of slow requests) only as a
  fallback. Output only inside the project (outside it the tool fails silently). ARON level 0 is the true maximum and
  scans are grey (R=G=B) – colour channels add nothing.
- **Permalink to the image** (`link` in `records.json`): `python3 -I tools/aron_img.py <apu_id> link <image>`.
- **Volume into the data:** `python3 -I tools/aron_img.py <apu_id> volume` (key = first 8 characters of the apu_id →
  the `volume` field of the record).
- ARON also has other collections (censuses, some land books, chronicles, town books) –
  `aron_search.py "Village" "collection name"`. Censuses 1857–1921 can be found by the unit type "sčítací operát"; in
  the district archives of Hradec Králové and Chrudim the house number is in the image file name.
  Only digitised units: the ARON filter "pouze s digitalizáty" (only with digital copies).
- Villages of the same name are frequent (Vinice near Hořice × Vinice near Velká Jesenice). Results are sorted by
  parish; narrow them with more words separated by a comma, all of which must be in the description:
  `aron_search.py "Vinice,Hořice"` (or search a neighbouring village or the parish village).
- For old parishes look first for **summary indexes** (description "index NAROZENÝCH…" over many years), often reaching
  into the 17th century.
- Village not found? Try the name **without an attribute** ("Lhota" instead of "Horní Lhota") and the old name. Older
  registers (before ~1784) are often in the parish of a neighbouring town; parish indexes have sections by village
  ("Copulati Gross Lhota").
- Be considerate to the server: download only what you read; no bulk downloads of whole volumes.
- `book_map.py aron <apu> <from> <to> [step]` and `contact_sheet.py aron …` work for ARON; check the number of images
  first (`aron_img.py <apu> info`) – a range past the end of the volume fails.
- **ARON of MZA** (www.mza.cz/aron/) is the same platform for Moravia, with scanned collections of district archives
  (town books, land books from the 16th century, wills, marriage contracts, land-tax rolls 1656–79 in fond D 1). MZA does
  not allow scripts – browser only.

## SOA Třeboň (digi.ceskearchivy.cz) – browser only
- **Since 2 Nov 2026 the archive rejects tools** (HTTP 403 by User-Agent) and the brake stops scripts on
  digi.ceskearchivy.cz. Do not work around it (other User-Agent, own script). Read the registers in the browser (best
  Playwright) as with MZA: zoom into the entry, save a screenshot, `crop.py`. Pace 5–10 s between pages (SKILL.md, Being
  gentle with archives), only pages you read, no helpers. Without a browser the user sends screenshots.
- Village: `https://digi.ceskearchivy.cz/<Village>` (without diacritics and spaces, e.g. `RatiborskeHory`) → the place
  page, on the left "Matriční knihy" (register books; the page is inside the frame `ram_obsah`) → list of books with
  years and villages; a click opens the book in a new tab. **Check the name and district**: for villages of the same
  name the portal picks another (Buk → Bukovka), for towns also the district or synagogue. The portal does not know small
  hamlets – search the parish or a neighbouring village and the hamlet in the book descriptions.
- Image: `https://digi.ceskearchivy.cz/<book>/<image>` (also the permalink). Books often have a volunteer name index
  (place page → "Rejstříky") – a huge saving; not every book has one.
- **Every display of an image downloads all tiles again** – even the back arrow to the image just shown (the frame
  reloads with a new token; the browser cache does not help). So do everything on one image at once: zoom into and read
  all entries you may need before moving on.
- The viewer is Zoomify inside the frame `ram_obsah`. Procedure: window screenshot (scale css) → read off the corners of
  the entry → the snippet below (`browser_evaluate`) hides the Navigator and Thumbnails panels, zooms into the entry and
  returns a link `/<book>/<image>/<x>/<y>/<zoom>/0` directly to the entry (into `link`) → window screenshot at device
  resolution into `work/trebon_<book>_<image>.png` → `crop.py` (cut off the bars at top and bottom):
  ```js
  async () => {
    const [x0, y0, x1, y1] = [185, 688, 590, 795];   // corners of the entry on the window screenshot (CSS px)
    const f = document.querySelector('iframe[name=ram_obsah]'), d = f.contentDocument, vp = f.contentWindow.Z.Viewport;
    if (!d.getElementById('genealogy-hide')) d.head.insertAdjacentHTML('beforeend',
      '<style id="genealogy-hide">#navigat_b,#thumbs_b{display:none!important}</style>');
    const r = f.getBoundingClientRect(), z = vp.getZoom(), c = vp.calculateCurrentCenterCoordinates();
    const W = vp.getViewW(), H = vp.getViewH();
    const img = (x, y) => ({x: (x - r.left - W / 2) / z + c.x, y: (y - r.top - H / 2) / z + c.y});
    const a = img(x0, y0), b = img(x1, y1);
    vp.zoomAndPanToView((a.x + b.x) / 2, (a.y + b.y) / 2, Math.min(W / (b.x - a.x), H / (b.y - a.y)));
    await new Promise(ok => setTimeout(ok, 6000));
    return location.href;
  }
  ```
  Always take the coordinates from the current window screenshot (after loading the page or `vp.reset()`), not from an
  older one.
- Volume into `volumes.json` via `write.py` (`../portals.md` → Other portals, step 4, key `trebon_<book>`).
- Some parishes have books by village that are not in the place's list of books – search by the titles of the parish's
  books.
- **Civil registers (1920–1945)** of people without religion are in the books of district offices (e.g. Tábor, book
  12304) with a volunteer index.
- **Land books of the great estates** are also here (place page → "Pozemkové knihy"; a book is visible only under the
  village it is assigned to – look also under the seat of the manor).

## SOA Plzeň (Porta fontium, portafontium.eu) – `tools/portafontium.py`, no browser
- **Village → books:** `portafontium.py village "<village>"` → all books with the village in the description, grouped by
  parish and sorted by years (book | villages | years and kinds: `*` B, `oo` M, `+` D, `i` index | description). It also
  shows a village moving between parishes and civil registers of district offices. The portal also searches historical
  and similar names – exclude villages of the same name in other parishes by the villages column. Nothing found? Try
  another form (Stajanovice × Stojanovice, the German name) or a neighbouring village.
- `portafontium.py parish <parish>` → all books of the parish in the same form. `<parish>` is a name ("Dolní Bělá",
  "Mýto" – the tool removes diacritics) or part of the parish's address (`dolni-bela`); parishes of the same name have
  a district suffix (`plana-ps`, `radnice-ro`) – `village` shows the right address.
- `portafontium.py info <book>` (`dolni-bela-17`) → reference, kind, cover text and **contents** – for books written by
  village it lists which folios hold which village ("Village X 1862–1901 = fol. 121–200").
- `portafontium.py image <book> <image> work/x.jpg [preview] [x0,y0,x1,y1]` → the whole page at full resolution in one
  request (IIIF), `preview` = 1/4. The image number = the order of the thumbnail in the viewer; files carry the folio
  number (`dolni-bela-17_0951` = fol. 95), so for books with continuous foliation **image ≈ folio**. A link from someone
  else's tree (MyHeritage) with `…_0450` in the address is therefore folio 45, not image 45 – download the neighbouring
  image too.
- `link <book> <image>` → permalink, `volume <book>` → `volumes.json` (key `pf_<book>`).
- **Pace:** the portal asks for 10 s between requests (robots.txt "Crawl-delay: 10") – the brake keeps it, also for
  images.
- Without a browser User-Agent the portal returns 403 (the tool sends one). The portal has no name search – indexes are
  only inside the books (`*i`, `ooi`, `+i` in the parish's list).
- `book_map.py pf …` and `contact_sheet.py pf …` work here.

## SOA Praha (eBadatelna, ebadatelna.soapraha.cz) – browser only
- **Since November 2026 the archive also limits automated traffic** (notice on the home page about automated security
  measures and limits). Reading in the browser at a human pace still works (tested 13 Nov 2026 in Playwright). If you hit
  a limitation page, "Forbidden" or an image that does not load, stop:
  `python3 -I tools/polite.py stop ebadatelna.soapraha.cz "limited in browser"` and hand the reading over to the user.
- **Since 2 Nov 2026 the archive forbids tools** (robots.txt disallows the skill's User-Agent, HTTP 403): `ebadatelna.py`
  must not download (`link`, `a-link` and `image` from images saved by the browser still work) and the brake stops
  scripts on soapraha.cz. Do not work around it (other User-Agent, own script, fetch). Read the registers in the browser
  (best Playwright). Pace 5–10 s between pages, only pages you read, no helpers. Without a browser the user sends
  screenshots.
- Search: Matriky (registers) → fill the field "lokalita" with the village minus the last letter (`browser_type`) and
  type the last letter with `slowly` (only that shows the suggestions; typing letter by letter into an empty field
  appends to the placeholder "lokalita"). Choose the full name (`.ui-menu-item`, "Obec - obec X - okres Y"), Vyhledat
  (search). The list of books with one `browser_evaluate`:
  `[...document.querySelectorAll('table tr')].map(r => [...r.cells].map(c => c.innerText.trim()).join(' | ') + ' | ' + (r.querySelector('a')?.getAttribute('href') ?? ''))`
  (book | creator | district | places | years B, M, D, indexes | images | `/pages/MatrikaPage/matrikaId/<id>`).
- Book description: `https://ebadatelna.soapraha.cz/pages/MatrikaPage/matrikaId/<id>` (archival documents
  `…/pages/ArchivaliePage/archivalieId/<id>`) – `document.body.innerText`. "Obecný popis matriky" (general description)
  gives for books written by village the **page layout** ("1–48 Village A, 49–82 Village B …", each village may have
  its own pagination) – do not estimate the image by year but by the village's pages; if there is an index, start with
  it. The archive truncates the description at about 250 characters (the end of the layout is missing) – the complete
  list of villages is in the field "Lokality"; the rest see `../registers.md` (Books arranged by village).
- Image: `https://ebadatelna.soapraha.cz/d/<matrikaId>/<image>` (archival documents `/a/<archivalieId>/<image>`; also
  the permalink, into `link`; the "<" and ">" arrows in the viewer go to this address too). The browser loads the whole
  image at full resolution. **Save it once into the cache and work from disk** – the archive then gets no further
  request. When paging, save every displayed image at once (saving costs the archive nothing) and before the next step
  check whether you already have the next image – then read it from disk and in the browser go directly to the address
  of one you do not have:
  1. Already have it? `python3 -I tools/cache.py find <image address> --preview work/preview.jpg` – prints the path and
     makes a preview (1600 px); then do not open the browser.
  2. Otherwise open the address, wait for loading (a few s) and save it (`browser_evaluate` with
     `filename: "work/ebad.json"`):
     ```js
     () => {
       const im = document.getElementById('scanImage');
       if (!im || !im.complete || !im.naturalWidth) return 'image still loading – try again in a moment';
       const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
       c.getContext('2d').drawImage(im, 0, 0);
       return JSON.stringify({w: c.width, h: c.height, url: location.origin + new URL(im.src).pathname.split(';')[0],
                              data: c.toDataURL('image/jpeg', 0.92)});
     }
     ```
     and `python3 -I tools/cache.py save work/ebad.json --preview work/preview.jpg` (stores the image, makes a 1600 px
     preview for reading the page and deletes the .json file).
  3. Another preview or a crop from the stored image without network: `python3 -I tools/ebadatelna.py image <matrikaId>
     <image> work/x.jpg [preview] [x0,y0,x1,y1]` (archival documents `a-image`), then `crop.py` as with other archives.
  Without Playwright (Claude in Chrome cannot save the result to a file) the user saves the image (screenshot).
- Older images are often from microfilm or strongly faded – crop with `--contrast` (`crop.py`, `verify.py`; see
  `../registers.md`, Reading the script) and note it in the transcription.
- Volume into `volumes.json` via `write.py` (key `ebad_<matrikaId>`, archival documents `ebad_a_<id>`).
  Daily maintenance around 4:44 (about 2 minutes); in the evening and at night often unavailable (roughly 22:45–0:45 and
  around 2:00). Urbaria and land books are also in eBadatelna.

## AHMP Prague – `tools/ahmp_search.sh`, `tools/ahmp_scan.py`
- `bash tools/ahmp_search.sh "Smíchov"` → volumes of the register collection: description | parish | (XID, id, number of
  images).
- `python3 -I tools/ahmp_scan.py <XID> <image> work/x.jpg [1] [x0,y0,x1,y1]` → image (1 = half resolution).
- Permalink `https://katalog.ahmp.cz/pragapublica/permalink?xid=<XID>&scan=<N>`.
- The new portal digi.ahmp.cz has bot protection – do not use it. Prague registers 1890–1940 mostly **have no indexes**
  and there are many parishes – without an exact date and parish (from a death/marriage or from the family) the search
  is very expensive. Use the police registrations below first.

## SOA Litoměřice (north Bohemia) – `tools/soal_zoomify.py`
The same software as ZA Opava (Digitální badatelna; Opava no longer lets tools in) – the same traps apply (`vysledekDetail`
by direct address shows another volume; JavaScript output without parameters in Claude in Chrome).
- `https://digi.soalitomerice.cz/digitalnibadatelna/` has an automatic check at the entrance (about 15 s of
  "computing", passes by itself) → find the book and the image paths in the browser (Playwright or Claude in Chrome),
  download images with the tool.
- **Search:** the Registers icon and the village in the field **"Místo / Lokalita"** (place; the main full-text search
  returns all ~18,000 registers), Enter. All results at once (switch the number per page with one selection, do not page
  through). Open the volume by clicking in the results and **check the reference code on the detail**. The book's
  description gives "Územní rozsah" (territorial scope – the book's villages) – read it first. Books are often **split by
  village** with their own pagination and an index at the end.
- **Image addresses** (images tab, `actualDetailTab=attachmentsImg`) – get them with a snippet only for images you read
  (at most a few at a time), sequentially with a 3 s pause (`browser_evaluate`; on the page of the same volume, otherwise
  showZoomify returns an empty answer):
  ```js
  async () => {
    const images = [1, 50, 120];   // only images you really read
    const ent = document.querySelector('[entityuuid]').getAttribute('entityuuid');
    const ids = Object.fromEntries([...document.querySelectorAll('select.getScanSelect option')].map(o => o.value.split('%20')));
    const out = [];
    for (const n of images) {
      if (!ids[n]) { out.push(`${n}: image not in the book`); continue; }
      const h = await (await fetch(`/digitalnibadatelna/showZoomify/${ent}/${ids[n]}`)).text();
      if (h.trim().length < 300 && !/images\//.test(h)) { out.push(`${n}: BLOCKED ("${h.trim().slice(0, 20)}") – stop for 35 minutes`); break; }
      const m = h.match(/https?:\/\/images\.[^"'\s]+?\/images\/[^"'\s]+?\.jpe?g/i);
      out.push(`${n}: ${m ? m[0] : 'address not found in the answer'}`);
      await new Promise(ok => setTimeout(ok, 3000));
    }
    return out.join('\n');
  }
  ```
  The folder in the path (`…/images/0046/…`, `…/NAD-856/dao/images/0701/…`) differs between books and even within one
  book – never build the address yourself, always take it whole from the output.
- Download images with the tool: `python3 -I tools/soal_zoomify.py "<full address>" 0 work/x.jpg` (0 = full resolution,
  1 = half, 2 = quarter for orientation). The image server images.soalitomerice.cz does not limit and needs no cookies.
- **WARNING – the application blocks** (images do not): after only 25–100 fast steps (paging results, Back, quick
  `fetch`). It shows a page "!" with **HTTP 200** (about 116 bytes) – check the content, not the status code. Requests
  only sequentially (no `Promise.all`), pause at least 3 s, only one loop at a time; after a block nothing for 35 minutes
  (further attempts extend it). Put this into helper briefs.
- Collection NAD 240 has land books of manors also from other regions (a manorial collection lies where its last owner
  had his seat).

## ZA Opava (north Moravia, Silesia, Olomouc, Litovel) – browser only, best Playwright
- Mind the border: villages around Litovel and Olomouc belong to **ZA Opava**, not to MZA Brno.
- **It does not work without a browser.** The reading room `https://digi.archives.cz/da/` (the old address
  matriky.archives.cz only redirects) has bot protection (Radware) and since November 2026 does not let tools reach even
  the images (robots.txt "Disallow: /", images.archives.cz returns 403/404 to scripts) – `soal_zoomify.py`, curl and
  WebFetch are stopped by the brake. The archive warns on its home page that non-standard work with the application
  leads to blocking: work like a human, one image after another.
  **Recommended browser: Playwright** – only there can an image be saved whole (below). Claude in Chrome also works
  (the user connects it with `/chrome`), but only with screenshots of the zoomed entry. Without a browser the user finds
  the book and saves images.
  **The built-in browser of the Claude app** (desktop, Code) is rejected at once ("Anomaly detected") – do not use it.
  The entry check passes by itself, but only in a foreground tab. Set the window to at least 1400×900, in a narrower one
  the filters and image do not show. **A CAPTCHA typically comes already at the first search**, then about every hour
  and always in a new browser session: **the user solves it** in the browser window, never you.
- Search the village and filter Registers (icon, then the magnifier again). The search also returns civil registers
  (hundreds of volumes for a village) – the filter "Datum od – do" (date from–to, by the start of the volume, e.g.
  1680–1873) leaves only church books. Books are often arranged by village with an index at the end. Next to parish books
  there are often **duplicates** ("T" in the reference). When the field "Signatura" (reference) "freezes" and returns the
  previous book, type the village into the main full-text field (Enter) or choose it in "Územní rozsah" from the
  suggestions.
- **Never open a volume detail by the direct address `vysledekDetail/<id>`.** The reading room keeps search results in
  the session and such an address shows the N-th (without `page` the first) result of the last search, or the images of
  the last opened volume – not the volume from the address. Open a volume by the permalink
  `https://digi.archives.cz/da/permalink?xid=<id>` (the id is the end of the result link `vysledekDetail/<id>`) – it
  shows the volume by id regardless of the last search, but only in a browser that has passed the check. Otherwise click
  in the results (the images icon in the row, or the results mosaic and a double click on the thumbnail). **Always check
  the reference and title on the page** before reading anything.
- **Save the list of volumes and image IDs at once** into `work/<volume>/` – the session expires after a few hours and
  search results are valid only within it. On a volume's detail: entity
  `document.querySelector('[entityuuid]').getAttribute('entityuuid')` (for volumes stored in another archive it is not
  a UUID – do not look for it by regex), image IDs are the values of `select.getScanSelect option` (form "N%20uuid").
  An image can then be opened any time without searching (the only direct address independent of the session):
  `/da/showZoomifySeparate?imageNumberSeparate=N&myEntityUuid=<entity>&myImageUuid=<uuid>`.
- **The whole image (Playwright)** – the reading room has no download and sends images only as 256 px tiles; images have
  no CORS, so the page cannot assemble them into a file. But Playwright can capture the tiles the viewer itself loads
  while zooming – the archive gets no extra request and you then read from disk (tested 13 Nov 2026):
  1. Already have it? `python3 -I tools/cache.py find "<showZoomifySeparate… address>" --preview work/preview.jpg` (prints
     path and size) – then do not open the image.
  2. Open the image **by its address** `showZoomifySeparate…` (not with the viewer's arrows – the address is the cache
     key), wait for loading and run `browser_run_code_unsafe`; it zooms the viewer and goes through the page view by view
     (2.5 s per view, like a person scrolling):
     ```js
     async (page) => {
       const z = 0.5;   // 0.5 = half resolution, enough for reading; 1 = full (4× more tiles) only for a hard spot
       const img = await page.evaluate(() => Z.imagePath);
       const tiles = await page.evaluate(() => window.__tiles || {});   // a repeat only adds missing ones
       const h = async (r) => { const m = r.url().match(/TileGroup\d+\/(\d+-\d+-\d+)\.jpg/);
         if (m && r.url().startsWith(img) && r.status() === 200) try { tiles[m[1]] = (await r.body()).toString('base64'); } catch {} };
       page.on('response', h);
       const [W, H, vw, vh] = await page.evaluate(() => [Z.imageW, Z.imageH, Z.viewerW, Z.viewerH]);
       const sx = vw / z, sy = vh / z, nx = Math.ceil(W / sx), ny = Math.ceil(H / sy);
       const centre = (n, i, s, D) => n === 1 ? D / 2 : Math.min(D - s / 2, s / 2 + i * s);
       for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
         await page.evaluate(([x, y, zz]) => Z.Viewport.zoomAndPanToView(x, y, zz), [centre(nx, i, sx, W), centre(ny, j, sy, H), z]);
         await page.waitForTimeout(2500);
       }
       page.off('response', h);
       await page.evaluate((t) => { window.__tiles = t; }, tiles);
       return `${Object.keys(tiles).length} tiles, ${nx * ny} views`;
     }
     ```
  3. Assemble the image (`browser_evaluate` with `filename: "work/zaopava.json"`):
     ```js
     async () => {
       const t = window.__tiles || {}, T = 256, dims = [];
       for (let w = Z.imageW, h = Z.imageH; ; w = Math.ceil(w / 2), h = Math.ceil(h / 2)) { dims.unshift([w, h]); if (w <= T && h <= T) break; }
       const L = Math.max(...Object.keys(t).map(k => +k.split('-')[0])), [W, H] = dims[L];
       const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d');
       let missing = 0;
       for (let y = 0; y < Math.ceil(H / T); y++) for (let x = 0; x < Math.ceil(W / T); x++) {
         const b = t[`${L}-${x}-${y}`]; if (!b) { missing++; continue; }
         const i = new Image(); i.src = 'data:image/jpeg;base64,' + b; await i.decode(); g.drawImage(i, x * T, y * T);
       }
       return JSON.stringify({w: W, h: H, missing, url: location.href, data: missing ? '' : c.toDataURL('image/jpeg', 0.92)});
     }
     ```
     and `python3 -I tools/cache.py save work/zaopava.json work/x.jpg --preview work/preview.jpg` (stores the image in the
     cache and in `work/x.jpg`, makes a preview). If tiles are missing, repeat step 2 (adds only the missing ones). Then
     `crop.py` as with other archives. Full resolution (`z = 1`) replaces half resolution in the cache, not vice versa.
  Only images you read – no batches of whole volumes and no helpers on this archive.
- **Claude in Chrome** cannot capture responses: zoom into the entry (`Z.Viewport.zoomAndPanToView(x, y, 0.6)` on the
  page `showZoomifySeparate`, coordinates of the original, size in `Z.imageW`/`Z.imageH`) and save a screenshot; do not
  download or assemble tiles with your own `fetch`/`new Image()` – those are extra requests the browser would not make.
- **WARNING – blocking:** fast requests → CAPTCHA, "operations evaluated as non-standard" or "Access blocked" for 30
  minutes. Pause at least 5 s between pages, do not page through results quickly and do not run background loops or
  batches of whole volumes. **No `fetch`** (on `showZoomify`, permalinks or anything else) – the bot protection catches it,
  for permalinks immediately; get image numbers and addresses only by normal navigation, one at a time.
  - **Daily limit:** not stated officially; by experience about **50 images** (and 200–300 application pages) a day.
    Then "Server Exception" in the image window, "Přístup zablokován!" (access blocked) even on the home page. After the
    first refusal stop for the day (`python3 -I tools/polite.py stop digi.archives.cz "daily limit"`) – a second refusal
    extends the block.
  - **"Server Exception" right after a CAPTCHA** (redirect via `/da/human/verify`) is not the limit: open
    `https://digi.archives.cz/da/` or the image address again; if that does not help, close and reopen the browser once
    (Playwright `browser_close`) – the check then usually passes by itself. Only then treat the error as the limit.
- **The same on FamilySearch:** ZA Opava registers (collection "Czech Republic, Church Books, 1552–1981", references
  `217000010-…`) and the land and manorial books of Opava and Olomouc ("Land Records, 1450–1889") are on FamilySearch at
  full resolution and without CAPTCHA – a good substitute when Opava blocks or the daily limit is reached
  (`../portals.md` → FamilySearch). Pair the volume via "vol. NNNN" in the FS catalog = inventory number of ZA Opava
  (year labels in FS are often wrong). **Image numbers differ book by book** (0, ±1, sometimes +7 to +8, elsewhere another
  order of leaves): before reading from FS compare the page with the archive (folio or page, year, at least two names),
  never rely on a guessed offset. Put into `link` the image you really read from.

## MZA Brno (south Moravia, Acta Publica) – browser only
- Portal `https://www.mza.cz/actapublica/`, no login. **Since 2 Nov 2026 MZA blocks download scripts** (Altcha check,
  tile addresses with a token) and makes no exceptions. By script only the book search (below, brake 1 request per 4 s;
  other MZA addresses are stopped by the brake). Images only in their viewer: zoom into the entry and save a screenshot.
  No downloading, `fetch` or assembling tiles, no helpers. **Browser: Playwright** (saves the screenshot to a file); Claude
  in Chrome also works without CAPTCHA (useful as a second browser while Playwright is busy with FamilySearch).
  **Do not use the built-in browser of Claude desktop for MZA** – by user reports it gets 403 on images even after a
  day's pause, while a normal browser gets through. Without Playwright the user opens the image in their browser and
  sends screenshots (the whole double page for orientation, then the zoomed entry – mouse wheel, macOS Cmd+Shift+4,
  Windows Win+Shift+S); save them into `work/`.
- Book: `python3 -I tools/polite.py curl -s "https://www.mza.cz/actapublica/matrika/hledani?typ=obec&search_by_obec=<village>&page=<n>"`
  → HTML table (book number, creator, years B/M/D, number of images, link `matrika/detail/<id>`; book number ≠ id).
  Results by 20 – go through further pages before saying the village is not there. Large parishes have separate index
  volumes (B/M/D) – start with them. Parishes founded around 1784 have older entries in the mother parish. The check on the
  book detail passes by itself in a few seconds.
- The book detail has "Části matriky" (parts of the register) with image ranges (births 1–43, index of births 43–93, for
  books of several villages by village). Estimate the image with the wanted year (images ÷ years). Indexes give the page,
  not the image: read the page numbers on 1–2 images and compute (the relation is usually linear, different book by book).
  If the index's pages "do not fit", look for the ink page numbers at the top corner or a second series of the same years
  (e.g. a German "Sterb Register" after a Latin series).
- **Page within the open page** (`viewer.goToPage(n-1)`, arrows) – returning to an image already shown comes from the
  browser cache and costs MZA nothing. Do not reload the page or reopen the image address: a reload gets a new token and
  downloads all tiles again.
- The viewer is OpenSeadragon in the variable `viewer`: `viewer.goToPage(n-1)`, `viewer.viewport.goHome(true)` and a window
  screenshot (scale css) – year and month in the header. At a found entry read off its corners on the current window
  screenshot and zoom in with the snippet (`browser_evaluate`); then save a screenshot of the first element
  `.openseadragon-container` (in Playwright `.openseadragon-container >> nth=0`; the second is the navigator) at device
  resolution into `work/mza_<book>_<image>.png` (Playwright saves only into the project folder) and continue with
  `crop.py`:
  ```js
  async () => {
    const [x0, y0, x1, y1] = [145, 435, 595, 500];   // corners of the entry on the window screenshot (CSS px)
    const vp = viewer.viewport, e = viewer.container.getBoundingClientRect();
    const P = (x, y) => vp.pointFromPixel(new OpenSeadragon.Point(x - e.left, y - e.top));
    const a = P(x0, y0), b = P(x1, y1);
    vp.fitBounds(new OpenSeadragon.Rect(a.x, a.y, b.x - a.x, b.y - a.y), true);
    await new Promise(ok => setTimeout(ok, 5000));
    return location.href;
  }
  ```
  A window of 1500×1500 gives a container of about 1468×1200 where a whole double page is often readable even without
  zooming (fewer displays).
- Do not show the whole page at full resolution (large window) – hundreds of tiles at once and MZA returns 503. Pace
  5–10 s between pages, only pages you really read. If the check does not pass or MZA reports an error, stop and tell the
  user. 503 on tiles after about 30 images a day = slow down.
- **Image block (403):** after roughly 45–60 images a day (each zoom counts – it loads new tiles) MZA stops serving
  images: the page and the check pass, but the image stays white and tiles return 403. **It is not slow loading – stop at
  once**, do not retry and tell the user. The block lasted into the next day; the next day try at most one image.
- A tile returning **410** is not a block – the token in the address expired; reopen the same image address
  (`?image=…jp2`).
- Permalink = the address in the browser `…/matrika/detail/<id>?image=<file>.jp2` (the file ends with image number × 10:
  image 16 → `…-00160.jp2`). Volume into `volumes.json` via `write.py`.
- The domain actapublica.eu does not belong to MZA (MZA confirmed it) – do not use it, only www.mza.cz/actapublica. If MZA
  does not load even in the browser, the user may try without VPN or another network.
- **Censuses (1857–1921) are not in Acta Publica** but in a separate portal
  `https://www.mza.cz/scitacioperaty/digisada/search` – browser only (the brake does not allow other MZA addresses), the
  same rules as for registers: no downloading or assembling tiles. Search the village (field "Město/obec nebo část obce/
  osada"); a set = one village and one year (often only some years, e.g. only 1921), with the range of house numbers. The
  detail `…/digisada/detail/<id>` has the same `viewer` as the registers. Image 1 is the list with metadata (house
  numbers, notes like "no. 134 has 2 sheets"), then sheets by house. 1857 gives only the year of birth, 1869 and 1880
  place and date; the column of birth dates is often written vertically – rotate the zoomed crop by 90°.
- Stable cadastre maps of Moravia open in the MZA viewer (fond D 9, often two sheets: the original from the 1830s and a
  revision from the 1870s; the written records in D 10) – zoom and screenshot only, as with registers.

## Prague police registrations 1850–1914 (National Archives) – `tools/prague_police.py`
- Cards of Prague families: head of family, wife with year and place of birth, children with years, addresses, sometimes
  place of marriage. Excellent when the family lived in Prague and you do not know the parish (Prague registers have no
  indexes).
- `python3 -I tools/prague_police.py Kolar [Jan] [1850] [1870]` – surname without diacritics (start of the name), given
  name and birth years optional. Without a browser it returns only the first 20 results, so search as narrowly as
  possible. Download the card with `prague_police.py card <no.> work/card.jpg Kolar [Jan] [1850] [1870]` (same search; also
  numbers above 20) – it prints the citation and permalink.
- **It does not cover Smíchov, Vinohrady, Žižkov, Karlín and other suburbs before 1922** (they were separate towns).
  Cards do not state religion.

## Newspapers, books and printed sources – Kramerius, DNNT
- **Kramerius** (Czech digital libraries): `python3 -I tools/kramerius.py 'text_ocr:"Jan Novák" AND datum_begin:[1900 TO 1910]'`
  (default the National Library; another library with `--server https://<library>`). Exact phrases often fail – use
  proximity `"word1 word2"~N`. Regional libraries (e.g. Hradec Králové, Kraj Vysočina at kramerius.kkvysociny.cz,
  Moravian Library) have regional press; some return 403 for OCR text of non-public pages – then take the snippet from
  the search highlight only.
- **DNNT** (out-of-commerce works, most print 1900–2000): readable only by a logged-in reader of the National Library on
  **ndk.cz without www** – the user registers and logs in themselves; after loading, the page shows "no access" for
  8–10 s before it checks the login. **Read only – no downloading, no printing**; take notes with page references.
  `python3 -I tools/dnnt.py search '<solr query>'` (pages with hits and access type), `dnnt.py context <pid> '<words>'`
  (snippets from a non-public page without login; a snippet from OCR is a clue, not `doc`). Full-text search inside a
  volume: `https://ndk.cz/view/<uuid>?fulltext=Word*`.
- Useful printed sources: trade directories (Adresář ČSR 1930–38 only in the National Library), yearbooks of teachers and
  clergy (schematisms), regional homeland books (*Heimatkunde*) for German-speaking areas, military schematisms on
  archive.org.
- Austrian newspapers and casualty lists 1914–19: ANNO (`../portals.md`). Fallen soldiers are often missing from the
  home death register; the card file of the fallen of the Military History Archive (VÚA) is in the Ministry of Defence's
  digital reading room after registration; war graves: evidencevh.mo.gov.cz, vets.cz; VHA databases of the fallen and of
  legionnaires: vuapraha.cz.

## Older sources (17th–18th century)
- **List of subjects by faith 1651** (*Soupis poddaných podle víry*) – whole families with ages, by region; editions as
  PDF from the National Archives (nacr.cz, publications → e-books; "Soupis poddaných podle víry" + region) and in NDK
  (DNNT). Full text in the PDF; surnames often without diacritics / other spelling (Šaršoun → "Šaroun", long ſ as f).
  The village is listed within its manor; note the edition's page. The introduction says which manors survived.
- **Berní rula 1654** (tax roll) – only farmers with land; editions and indexes in libraries (Kramerius/DNNT; some volumes
  only at the National Library terminal). **Revisitations of the berní rula** (NA, NAD 53, 1670s–80s: "instead of X now
  Y") – offline.
- **Land (manorial) books** (*gruntovní / pozemkové knihy*) – transfers of houses from father to son; online only partly:
  SOA Plzeň almost all, SOA Praha part, **SOA Třeboň** land books of great estates (browser only, see above), **ZA Opava**
  urbaria and land books in the Digitální badatelna. Parts of Třeboň and Opava books and the **east Bohemian urbaria of
  SOA Zámrsk** (search the FamilySearch catalog for "Urbarios Zamrsk"; the catalog's village is often wrong – read the card
  on image 1) are on FamilySearch ("Czech Republic, Land Records, 1450–1889"; `../portals.md` → the land records trick).
  Other archives mostly reading room only. Collection "Velkostatek <manor>" (great estate). A collection of land books of
  district courts (e.g. NAD 192 at SOA Zámrsk, 1551–1886) – finding aids typewritten, books offline.
- **Theresian cadastre** (NA, NAD 54: declarations 1713, visitations 1715–26, *fasse* 1748–57) – the holder of every
  rustic holding; offline (VadeMeCum has the finding aid). **Josephine cadastre 1785–89** (NA, NAD 55) – landholders by
  village. **Land-tax rolls (lánové rejstříky) 1656–79** for Moravia (MZA D 1).
- **Confession lists 1671–1725** (ed. J. V. Šimák) – farmers by village around 1700; some volumes only in libraries.
- **Land registers (zemské desky)** – only noble and free estates; the index from 1541 is public in Kramerius.
- **Town books** (deeds of sale, wills, marriage contracts) – ARON has some scanned (filter digital = yes), ARON of MZA
  many.
- **Mills:** vodnimlyny.cz (holders of a mill from 1651 to the 20th century; browser, scripts only through the brake).
- **Village and school chronicles** (district archives; ARON has some scanned) – copies of land books with holders of
  house numbers, lists of families, the fallen.
- **Theses** (theses.cz, is.muni.cz full texts) about manors often edit urbaria or name books the catalogue hides.
- **Stable cadastre maps (1824–43)** – where the house with a given number stood: Archive of ČÚZK, ags.cuzk.gov.cz/archiv
  (the old address archivnimapy.cuzk.cz no longer works). `python3 -I tools/cuzk_maps.py sheets "<village> <no.>" | lat,lon`
  (which sheets cover a place, the cadastral community of 1827), `cuzk_maps.py rasters <service> "<pattern>"`,
  `cuzk_maps.py export <service> <id> work/x.jpg [x0,y0,x1,y1] [width_px]` (a sheet or a crop at full resolution).
  On the **imperial copies** (*císařské otisky*) colours and house numbers are missing on some sheets. Better are the
  **indication sketches** (*indikační skici*): they have house numbers and for plots the owner's name ("N. 13" = belongs to
  house no. 13). A house without land outside the village = a cottager without fields. The owner of the house itself is
  often only in the written records (archive, not online). Map crops belong on the website with the family.
  - **Browser procedure** (the services are behind a token that the page obtains itself – do not print it): on
    ags.cuzk.gov.cz/archiv find the cadastral area, click the village on the map → "Indikační skici" (or "Císařské povinné
    otisky") → raster ID (e.g. `HRA235018400`; the ID contains the year). A sketch can then be opened directly:
    `https://ags.cuzk.gov.cz/archiv/openmap.html?typ=skicic&idrastru=<ID>` (imperial copy `typ=cioc`); it loads in about
    20 s. A hamlet often has no cadastre of its own – search by the neighbouring village.
  - **Reading:** inside a building the **house number in red** and the **building plot number in black** (land plots have
    red numbers); mixing them up reads the whole village backwards. When in doubt check a few houses: the land cadastre
    layer with today's address points (RÚIAN) shows on which plot today's house number stands. "N° 35 Surname" on a plot =
    belongs to house no. 35. Yellow buildings are wooden, pink brick. Labels are often upside down (rotate the crop by
    180°). In towns the built-up area is often empty. Put a crop with the house circled on the website (old maps are
    very popular with families).
- **Today's address of a house** by house number: RÚIAN (ČÚZK, layer AdresniMisto). The old centre often has the same
  numbers since the 19th century, but suburbs and villages renumbered. Good for a "walk in the ancestors' footsteps".
  nahlizenidokn.cuzk.gov.cz finds a building by village and house number; the owner is behind a CAPTCHA and is data about
  a living person – do not look it up.
- **The key to the 17th–18th century is the manor, not the parish:** for each branch note who owned the village in which
  year – that tells you in which collection to look for land books, urbaria and lists.

## Military records (Habsburg army)
- First the **regiment** (by home municipality; recruiting districts in Wrede's overview) → until 1820 muster lists
  (*Musterlisten*, by regiment and year) / from 1820 personnel sheets (*Grundbuchblätter*) → military registers of the
  regiment (Vienna, closed for 100 years) → casualty lists 1914–18 and the casualty card file in Vienna.
- Personnel sheets of men with a home municipality in Bohemia, Moravia and Silesia: years of birth about 1865–1886 in the
  VÚA–VHA Prague (paid search), older ones in Vienna (Kriegsarchiv; about 1820–1864 also on FamilySearch microfilm,
  catalog 489271), **years 1887–1898 largely destroyed** – use casualty lists and registers.
- The Austrian death card file of the fallen (*Totenkartei*) of World War I is on FamilySearch.

## Victims of persecution 1938–1945
- **holocaust.cz** (Terezín Initiative): `python3 -I tools/holocaust_victims.py search --surname … [--given …]` and
  `holocaust_victims.py detail <link|number>` – victims of the Nazi persecution (Jews and Roma from the Czech lands). The
  user must first accept the database's terms personally: `! python3 -I tools/holocaust_victims.py consent`.
- **Památník Terezín** (pamatnik-terezin.cz/databaze): Czech prisoners of concentration camps, the Small Fortress, Pankrác…
  `python3 -I tools/persecuted.py search --surname …`, `persecuted.py detail <link>`; consent as above
  (`! python3 -I tools/persecuted.py consent`).
- Arolsen Archives and Mauthausen: `../portals.md`. Paměť národa (pametnaroda.cz) – memories of the 20th century.
- Sensitive – on the website only with the family's consent (`../privacy.md`).

## Sudeten Germans and the border regions
- Registers stayed in Czech archives. After 1945: the **Heimatortskartei Sudetendeutsche (HOK)** – card file by residence
  on 1 Sep 1939 with the post-war address; today Bundesarchiv Bayreuth (fond B 530), written request only. There also the
  **Lastenausgleich** files (compensation of expellees, from 1949) and the **Gemeindeseelenlisten /
  Gemeindevermisstenlisten** (lists of inhabitants and missing persons by village, 1950s). The Kirchlicher Suchdienst
  (Passau, Regensburg) closed in 2015 – older guides sending people there are out of date.
- Transport lists of 1946: district archives by place of departure (ONV/MNV collections 1945–48).
- German homeland books (*Heimatbücher*, DNB, GenWiki) often list families by house.

## Surnames today
kdejsme.cz – number of bearers of a surname by district: shows quickly whether a surname is rare and where its "nests" are.

## Archives on site and genealogists
- State regional archives do not do research for you; the reading room (*badatelna*) has fixed days, books must be
  ordered in advance (collection + inventory number). District archives (SOkA) hold parish collections (marriage
  protocols, chronicles), municipal archives; some collections are "not accessible".
- The National Archives orders reproductions by e-mail with the exact reference (finding aid number from VadeMeCum).
- When the online sources are exhausted, prepare for the user a list of what to check on site (`data/offline_sources.md`:
  collection, inventory number, whom it concerns, what it would decide) – for their own visit or for a hired genealogist.
  One e-mail per institution, then wait for its reply (SKILL.md).

## Slovakia (until a separate guide exists)
Part of Hungary until 1918; place names have Hungarian (and German) forms – look them up in the Helységnévtár 1877/1913.
- **Church registers** (Roman Catholic, Greek Catholic, Lutheran, Reformed, Jewish) from 1592, today in state archives
  (Zbierka cirkevných matrík). Images and an incomplete index (mainly baptisms) on FamilySearch ("Slovakia Church and
  Synagogue Books, 1592–1935"; account needed), usually to ~1895. Some films are locked ("Image Restricted") – only at the
  archive. The FamilySearch catalog is often inaccurate for Slovak films (a Lutheran film listed as Catholic; filial
  parishes in the mother parish's film; more years than the catalog says) – probe first. Inventories of the state archives
  are PDFs on minv.sk (search "minv.sk <village> inventár").
  1. **Parish:** catalog `https://www.familysearch.org/search/catalog/results?q.keywords=Farský úrad <village>` (also
     "Grécko-katolícka …", "Evanjelická …"). It finds the parishes of the whole area – the village in brackets after the
     parish is the one the catalog files it under. Search by place (`q.place`) and Hungarian names often find nothing or a
     Czech village of the same name.
  2. **Filmed years:** read the film table (`../portals.md` → FamilySearch). "Cirkevná matrika, 1762–1927" may have
     baptisms, marriages and deaths only to **1895** (to 1927 only confirmations). After ~1895 the state kept civil
     registers – younger entries are in the state archive or at the registry office, not online.
  3. **The index is incomplete** and names mangled; search via the parents and without the given name, otherwise page
     through the film (first the index "Zoznam krstov A–Z", often at the start of the book).
  4. **1900–1940:** family documents (children's birth certificates also name grandparents), gravestones and grave
     registers. Rusyns registered as Orthodox after 1950 have older entries in Greek Catholic books.
- **Civil (state) registers** from 1 Oct 1895 (Hungarian law), at the registry office; to the archive only after 100 years.
  While at the office (100 years from the last entry) an extract is given only to the person concerned or a family member
  (spouse, parents, children, grandchildren, great-grandchildren, great-great-grandchildren, siblings and their children) –
  regardless of the entry's age (Act 154/1994 Coll., § 18). Church books in the state archive are archival documents –
  personal data accessible 90 years after the entry (Act 395/2002 Coll., § 13).
- **Census 1869** on FamilySearch ("Slovakia, Census, 1869"): whole households with years and places of birth, religion
  and occupation; images only, no name index, only from the archives Bytča, Banská Bystrica and Nitra.
- **Census 1930 (and 1940)** on Slovakiana (slovakiana.sk), free, by village and house number:
  `python3 -I tools/slovakiana.py search "Village" [--year 1930]` (index of sheets, saved into `work/slovakiana/`),
  `slovakiana.py sheet <id>`, `slovakiana.py image <id> <side> work/x.jpg`. Whole images often return 502; the tool uses
  IIIF tiles (1–2 minutes per sheet). Names are not indexed.
- Hungaricana and Arcanum return 403 to scripts – browser only.
- Grave registers: e.g. Košice gisplan.kosice.sk; cintoriny.sk covers part of the villages.
- Austro-Hungarian casualty lists (ANNO) work for Slovakia too – search the Hungarian name of the village.
