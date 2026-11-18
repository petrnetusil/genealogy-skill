# Family website – building, settings, publishing

The website is static (Astro + Pagefind search) and takes its data from `data/` via `tools/export_web.py`.
UI language is English; all texts written by you (titles, stories, summaries, captions, curiosities) are in the
family's language.
Pages: home (teaser, statistics, curiosities, map, lines, fan), story/stories (`/stories`), curiosities
(`/curiosities`), lines (`/lines`) and each line (`/line/<slug>`), map (`/map`, OpenStreetMap), full-screen fan
chart with search (`/fan`), list of ancestors (`/ancestors`), records (`/records`) and each source with crop, frame,
transcription, translation and "Read by / Checked by" (`/source/<key>`), person page with summary, timeline,
memories and collapsible research notes (`/person/<slug>`), families (`/family/<id>`), "How are we related?"
(`/relationship`), statistics (`/statistics`), documents and photos (`/documents`), open questions
(`/open-questions`), research log (`/log`), what's new (`/news`), search (`/search`).

## Commands (in the `web/` folder)
| command | what it does |
|---|---|
| `npm install` | once at the beginning (downloads libraries, ~1 minute) |
| `npm run data` | converts the data for the website (always after data changes; `scripts/data.mjs` finds a working Python 3 itself) |
| `npm run build` | builds the website into `dist/` |
| `npm run preview` | data + build + preview at http://localhost:4321 (Ctrl+C stops it) |
| `npm run dev` | development mode when changing the design |
| `npm run deploy-cloudflare` | data + build + upload to Cloudflare (default) + check |
| `npm run deploy` | data + build + upload to Netlify + check |
| `npm run verify` | check the deployed website without logging in (family question × Netlify team protection / Cloudflare page) |

Run the preview in the background and send the user the link. Check the look yourself (screenshot via the browser,
if available).

## `data/website.json`
```json
{
 "title": "The Novák family tree",
 "description": "Description for search engines and sharing (the website is noindex anyway).",
 "footer": "Researched in the digitised registers of …",
 "contact": {"name": "Peter", "email": "peter@example.org"},
 "gate": {"intro": "This website is for the family only.", "question": "What was the name of grandma's dog in Holice?", "answer": "Rex"},
 "home": {"heading": "An enticing heading", "paragraphs": ["2–3 sentences that grip"], "photo": "image_key_in_crops", "photo_caption": "…"},
 "story": {"menu": "The story of the Nováks", "line": 8, "button": "Read the story of the Nováks"},
 "home_curiosities": [{"heading": "The oldest ancestor", "text": "Blacksmith Jan, c. 1825."}],
 "sensitive_approved": [],
 "portraits": {"jan-novak-1890": "photo_jan_novak_1930"},
 "cloudflare": {"subdomain": "novak-family"},
 "country": "Czechia",
 "ai_models": {"Opus": "Claude Opus 5.5", "Fable": "Claude Fable 5.2"}
}
```
- `contact.name` is shown in the sentence "Do you know more about …? Write to <name>" on each person's page.
- **Gate:** a question only the family knows the answer to (not easy to find on social networks). The answer is
  compared without diacritics and case and must contain Latin letters or digits (Cyrillic and symbols only do not
  work). Only its fingerprint (SHA-256) is stored on the server and in the browser cookie, never the answer itself.
  A short or common answer (a name, a village) can still be guessed from the fingerprint by trying, so the user must
  not use it as a password elsewhere. Without an answer the deploy (`npm run deploy-cloudflare`, `deploy`,
  `deploy-caprover`) ends with an error; an open website only explicitly via `"open": true` in `gate`.
  It is light protection against random visitors, not bank-grade security – sensitive things do not belong on the
  website.
- `home.photo` = key of an image in `crops/` (save it via `crop.py`). `portraits` maps a person's slug to an image key
  (the medallion on the person's page).
- `story`: `menu` and `button` named after the main line, `line` = line number (8–15). Without `home` the home page
  shows at least the story's title and `lead`. See `stories.md`.
- The template's `website.json` is empty – set the title as soon as you know the starting person's surname
  (`check.py` reports leftovers of the sample).
- `sensitive_approved`: a list of text snippets the user approved for the website (`privacy.md`).
- `country`: the main country (used by `places.py` for map queries). `ai_models`: short model name → full name;
  short names in the data ("checked by Opus") are shown on the website as "AI model Claude Opus 5.5". Neither `gate`
  nor `ai_models` goes into the website's data.

## Publishing in batches, news and versions
- **Deploy in larger batches** – at most about once an hour, preferably after a coherent piece of work (several
  rounds, a big discovery, a finished branch) or when the user asks. In between update only the local preview.
  Frequent deploys burden the servers, cost tokens and (on Netlify) credits.
- **Every deploy is a new version** shown on the "What's new" page. Before deploying add an entry at the top of
  `web/src/news.json`:
  ```json
  {"version": 7, "date": "18 Nov 2026", "title": "The blacksmiths go back to 1702",
   "points": ["Three new generations of the Novák line, found in the parish registers of Holice.",
              "New photos from aunt Maria's album.", "The story of the Nováks has a new first chapter."]}
  ```
  `version` = previous + 1, `date` from the `date` command, `points` in plain words for the family (no image numbers,
  no "round"). `python3 -I tools/news_people.py` adds `people` (`{"k": number, "new": true/false, "records": [keys]}`)
  by comparing the data with the previous version (state in `data/news_state.json`); `deploy_all.sh` runs it itself.
- If the user wants fewer entries, older versions can be merged into one (keep a backup of the old `news.json` in `work/`).

## Site variants (optional)
One family often wants separate websites, e.g. **one per parent's side** (the father's relatives see only his
ancestors), or one per branch. Variants are made from the same data – nothing is copied by hand.
- `data/variants.json` (not `website.json`, which goes into the website data) – a list:
  ```json
  [{"name": "father", "root": 2, "title": "The Novák family tree",
    "gate": {"question": "…", "answer": "…"}, "domain": "novak.example.org"},
   {"name": "mother", "root": 3, "title": "The Dvořák family tree", "gate": {"question": "…", "answer": "…"},
    "story": "story_dvorak.md", "story_config": {"menu": "The story of the Dvořáks", "line": 8, "button": "Read it"}}]
  ```
  `root` = the Kekulé number that becomes person 1 of the variant (2 = father, 3 = mother); people are renumbered
  (2 → 1, 4 → 2, …) and the lines become the eight great-grandparent lines of that person. Optional: `domain` (custom
  domain, otherwise a workers.dev address), `worker` (Cloudflare worker name, default `<main worker>-<name>`), `story`
  and `story_config` (the variant's own story), `home_curiosities`, `lines` (names/descriptions of the variant's new lines 8–15) and
  `hide_words` (extra words – typical places of the other branches – that mark texts to leave out of the variant). Full format:
  `python3 -I tools/site_variants.py --help`. Open questions and hypotheses stay on the main website only.
- `python3 -I tools/site_variants.py <name>|--all [--deploy]` builds (`--list` lists the variants, `--urls` their
  addresses, `--deploy-main` deploys the main site); the result is `variants/<name>/` (trimmed data: people, records, images,
  documents, memories, curiosities, story chapters and news of the other side are left out; web copied).
  Check a variant's preview before the first deploy – especially that no text of the other side slipped in.
- `bash tools/deploy_all.sh` deploys the main website and every variant from `data/variants.json` (`bash tools/deploy_all.sh [all|main|<variant>|check]`;
  `check` only runs the gate check through `polite.py curl`), and at the end **checks that every gate answers HTTP 401** without the cookie.
  If any address does not return 401, stop and fix it before telling the user the site is live.

## Publishing on Cloudflare (default, free)
Deploys and traffic are free without limit; the gate runs in front of every file and counts towards 100,000 requests
a day (a page is about 20–40 requests → thousands of page views a day; when exhausted the website returns error 429
until midnight UTC).
1. **Account:** if the user has no Cloudflare account, they create one **first** at dash.cloudflare.com (free, an
   e-mail is enough) and confirm the e-mail – registration does not fit into the two minutes of the login. When they
   are logged in to the dashboard, continue.
2. **Login:** run in the background `cd web && npx -y wrangler@4 login` – it opens the browser. Tell the user: "A
   Cloudflare page opens – click **Allow**, you have about 2 minutes." Check: `npx -y wrangler@4 whoami`.
   - "Application authorization failed / Authentication error, please login": the browser is not logged in to
     Cloudflare (typically right after registration, or another / private window). "Retry authorization" does not
     help when the login has expired. The user logs in at dash.cloudflare.com in that browser, then run
     `wrangler login` again (new link). Link without opening a browser: `npx -y wrangler@4 login --browser=false`.
   - "Timed out waiting for authorization code" = the 2 minutes expired, run login again.
3. **Address:** the website will run at `https://<worker>.<subdomain>.workers.dev` (`<worker>` = the website's name on
   the account, default `genealogy`; `<subdomain>` = the account's subdomain). Think of 2–3 names after the family (lowercase, no diacritics,
   hyphens: `novak`, `novak-family`, `novak-holice`), check them with
   `cd web && node scripts/deploy_cloudflare.mjs --check-free novak novak-family novak-holice` (asks Cloudflare's DNS,
   does not "scare" the address) and offer the user only the free ones. Write the chosen one into
   `data/website.json` as `"cloudflare": {"subdomain": "novak-family"}`. The name is the subdomain of the whole Cloudflare
   account (created on the first deploy, changeable only in the dashboard); if it is taken after all, the deploy tries
   a variant with a number and says so. **If the user already has a Cloudflare account**, its existing subdomain is used
   and `subdomain` is ignored – the deploy tells the address. **A second family tree on the same account** needs another
   website name, otherwise it would overwrite the first: ask for one, write `"cloudflare": {"worker": "dubois-tree"}`
   and show the full address. The deploy guards this: when a website of that name exists on the account and was not
   deployed from this folder, it stops with advice (same project from another computer:
   `node scripts/deploy_cloudflare.mjs --overwrite`). A custom domain: `"cloudflare": {"domain": "tree.example.org"}`.
4. **Deploy:** `cd web && npm run deploy-cloudflare` (run it yourself; it exports with `npm run data -- --deploy`, which
   refuses to continue without a gate answer). It prints the address and runs the check
   `scripts/verify.mjs`. For a new address the check waits until it propagates (a few minutes); if the computer does
   not know it yet, it says so and ends without error – check later with `npm run verify`. Until then do not open the
   address in a browser: the computer or router would remember it does not exist and might not see it for up to
   30 minutes (elsewhere, e.g. a phone on mobile data, the site already works). Tell the user so they do not worry.
5. Check yourself in a private window: family question, after the right answer the website.
   The gate (`web/cloudflare/worker.js`) and `web/wrangler.jsonc` are generated by the export – do not edit by hand.
   The gate must run before every file (`run_worker_first`), otherwise pages and photos could be downloaded without
   logging in.
Further updates = just `npm run deploy-cloudflare` (or `bash tools/deploy_all.sh` with variants).

**Traps:**
- "You need to verify your email address to use Workers" (403) on a new account: Cloudflare wants a verified e-mail –
  verification in the dashboard (bar at the top / My Profile), confirm the link in the mail, deploy again (the
  subdomain stays).
- Safari with a content blocker shows an empty 403 page instead of Cloudflare's verification page – try another
  browser (the check recognises it).
- Do not use `wrangler pages project create/deploy` or "Import a repository" in the dashboard – they create another
  type of project or rewrite `astro.config`/`package.json`. Deploy only with `npm run deploy-cloudflare`.
- In a cloud environment (claude.ai), where the browser login does not return to the terminal, use Netlify
  (`login --request`).

## Publishing on Netlify (second option)
For users who already have their site on Netlify. A free account is enough for only about 20 deploys a month (see
credits below).
1. The user creates an account at netlify.com (login via Google/GitHub is enough) – they do it themselves.
2. CLI login (opens the browser) – give the user: `! cd web && npx -y netlify-cli@latest login`.
   When `!` does not work (cloud environment): `npx -y netlify-cli@latest login --request "Family tree"` prints a link
   and a ticket number – the user opens and approves the link, then `npx -y netlify-cli@latest login --check <ticket>`.
3. Create the site and link the folder (interactive, once) – give the user:
   `! cd web && npx -y netlify-cli@latest sites:create` (chooses team and name → address `https://<name>.netlify.app`),
   or `npx netlify-cli link` if the site already exists. If the user is logged in, you can create it without questions:
   `cd web && npx -y netlify-cli@latest sites:create --name <name> --account-slug <team>`.
   **Windows:** when `!` runs in Windows PowerShell 5.1 (`&&` does not work there and `npx` is blocked by the Execution
   Policy), the user opens PowerShell 7 or Command Prompt, goes to `web` and runs `npx -y netlify-cli@latest login`
   (and `sites:create`).
   **A new site is often "Private" (team protection)** – the family would see a Netlify login instead of the family
   question and the owner would not notice (they are logged in). Say so in advance; the check after the deploy
   (step 4) detects it. Turn it off with the user's consent:
   `npx -y netlify-cli@latest api updateSite --data '{"site_id":"<siteId from web/.netlify/state.json>","body":{"sso_login":false}}'`
   (in the dashboard: Project configuration → Access & security → Visitor access → Project visibility → Public).
4. Deploy: `cd web && npm run deploy` (you can run it yourself; prints the address). At the end `scripts/verify.mjs`
   runs (manually `npm run verify`): it opens the site without login and recognises the family question, Netlify team
   protection (and prints how to turn it off) and a site without a gate. If it fails, fix it and run `npm run verify`
   again.
5. Check yourself in a **private window** → family question, after the right answer the website.
   The login is handled by the Netlify Edge Function `web/netlify/edge-functions/gate.js` (generated by the export).
Further updates = just `npm run deploy`. A custom domain can be set in the Netlify dashboard.

**Netlify credits (free account):** 300 credits a month, not carried over. Each deploy costs 15 (a failed one
nothing), 1 GB of traffic 20 → about 20 deploys a month, or fewer when the family downloads large crops from
`sources/`. When exhausted, Netlify pauses deploys and `npm run deploy` ends with "Forbidden" – exhausted credits, not
a website error (credit status in the Netlify dashboard). Tell the user at the first publication.

**Warning:** "Netlify Drop" (dragging a folder in the browser) cannot do Edge Functions → the site would be without
a gate. Do not use it.

## Preview in Claude desktop
The project has `.claude/launch.json` – the website preview in Claude desktop runs `npm --prefix web run dev` (port
4321). Export the data first (`cd web && npm run data`). If the preview does not start (e.g. on Windows, where `npm`
is `npm.cmd`), try in `launch.json` `"runtimeExecutable": "node"` and
`"runtimeArgs": ["web/node_modules/astro/bin/astro.mjs", "dev", "--root", "web"]`. The server runs only on this
computer – do not add `--host`.

## Own server (advanced)
- Docker: `web/Dockerfile` (Astro build → nginx with `nginx.conf` from `nginx.template.conf`). Always run
  `npm run data` before building the image. Without Node.js on the computer:
  `python3 -I tools/export_web.py --deploy`, then `docker build` in `web/` (Astro is built inside the image).
- Rebuilding leaves an untagged old image on disk (hundreds of MB). After `docker build` delete only this website's
  old image:
  ```
  OLD=$(docker images -q family-web:latest); docker build -t family-web .
  docker rm -f family-web; docker run -d --name family-web --restart unless-stopped -p 8080:80 family-web
  [ -n "$OLD" ] && [ "$OLD" != "$(docker images -q family-web:latest)" ] && docker image rm "$OLD"
  ```
  Do not use `docker system/image/builder prune` – it applies to the whole server and deletes other projects' items.
- The website expects to run at the root of a domain (links, login cookie and search from `/`) – behind a reverse
  proxy give it a subdomain (`tree.example.org`), not a subdirectory (`example.org/tree/`).
- **Only over https** (a reverse proxy with Let's Encrypt, Synology DSM, CapRover can do it): the login page computes
  the answer's fingerprint in the browser, which plain http (outside localhost) does not allow.
- CapRover: `npm run deploy-caprover` (needs the `caprover` CLI installed and logged in).

## Changing the design
Styles in `web/src/styles/global.css` (colours in `:root`), layout in `web/src/layouts/Base.astro`, pages in
`web/src/pages/`. Line colours are in `tools/export_web.py` (`LINE_COLORS`) and `tools/fan_chart.py` (`BASE`). Change
them only at the user's request and check the website on a phone and a computer afterwards.

## Fan chart as a poster
`python3 -I tools/fan_chart.py output/` → SVG and HTML (and PNG if Google Chrome is installed, on Windows also
Microsoft Edge) for printing.

## Updating an older project
Run `python3 -I SKILL_DIR/tools/new_project.py <project folder>` again. Data (`data/`, crops) stay. The project's
skill version is recorded in `.skill_version` (compared by `version.py` with the skill's `VERSION`). The project keeps
in `.skill_template/` a copy of the template's `web/` and `tools/` it was created from (commit it with the project),
and the script decides about each file and prints a list:
- **Overwritten**: the project had not changed the file, the new version replaced it.
- **Kept**: your own change, the template did not change.
- **Merged**: both your change and the template changed, each in a different place; `git merge-file` combined them.
  Check that the file makes sense.
- **To check**: your change and the template changed the same places, `git` is missing, both the project and the new
  template added the file, or the project deleted it and the template changed it. The file stayed as it was; the new
  version is in `work/backup_<date>/new_template/` (on a merge conflict with `git` also a proposal with `<<<<<<<`
  markers as `.conflict`). Take over the template's changes by hand and then run
  `python3 -I SKILL_DIR/tools/new_project.py <project folder> --resolved web/src/…` (can be repeated). It stores
  exactly the proposal from the backup as the base (remembered in `.skill_template/pending.json`), so later template
  changes come with the next update; it does not change the file in the project. Until then the file is reported at
  every update. A folder in place of a file (or vice versa) and paths differing only in letter case also go here; the
  script does not change them.
- **Deleted in the project**: the project deleted the file and the template did not change it – it stays deleted.
- **No longer in the template**: the file stayed (the script deletes nothing) and is reported at every update. Check
  whether the website still needs it; if not, delete it by hand and run `--resolved` with its path.
- **Overwritten, original in the backup**: a project from an older version without `.skill_template/`. Changed files
  were replaced by the new version and the originals are in `work/backup_<date>/original/`; take your changes from
  there (compare the files).

A link (symlink, junction) in `web/`, `tools/`, `.skill_template/` or `work/` that leads outside the project, and
a link or folder in place of a backup, are refused with a WARNING and the files behind them are skipped (nothing is
overwritten without a backup).

`web/package-lock.json` (changed by `npm install`) is not merged: if the template changed it, the new one is taken
and the old one goes to the backup.

**After an update go through the list with the user** (the script handles only mechanical cases):
1. **To check:** compare what the template changed (`.skill_template/<file>` vs. `new_template/<file>` in the backup)
   and what the project changed (`.skill_template/<file>` vs. the file in the project). Tell the user in two sentences
   what is new and what is their change, propose a merge and after consent do it and run `--resolved`.
2. **Overwritten, original in the backup:** compare `original/<file>` with the new version. If it contains your own
   changes (not just an older state of the template), offer to take them over into the new version.
3. **Merged:** look at the result (`git diff`) to see whether it makes sense.
4. In `web/` run `npm install`, `npm run data` and `npm run build`, then `python3 -I tools/check.py`.
An old login template is refused by `export_web.py` with a request to update.

A project that has been deliberately customised a lot (its own pages and tools) may prefer **not** to be updated
from the template; respect that and take over new features by hand, piece by piece, as the user wishes.
