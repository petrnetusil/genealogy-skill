# Preparing the computer and the project (Phase 0)

Read when creating a project or when a tool is missing or fails to install.

## Tools
Check: `python3 --version` (≥ 3.9), `node --version` (≥ 20), `magick -version` (ImageMagick 7; if only version 6 with
the command `convert` is available, the tools use it themselves outside Windows), `git --version`.
Help install what is missing. Let the user confirm installations of system software; give interactive commands to
the user with the prefix `!` so they run them themselves.
- **macOS:** Homebrew `brew install python node imagemagick git`. **Older macOS (13 and below):**
  `brew install imagemagick` may try to compile dozens of dependencies and fail; use MacPorts instead
  (`sudo port install ImageMagick` after installing the MacPorts `.pkg` for the macOS version). It installs
  ImageMagick 6 (`convert`) into `/opt/local/bin`, which is not on Claude's PATH – put
  `export PATH=/opt/local/bin:$PATH` before image commands and write this into the project's `CLAUDE.md`.
- **Windows:** winget or installers from python.org, nodejs.org, imagemagick.org. **winget always with full options**,
  otherwise it stops at the question about the msstore source ("Error reading input in prompt"):
  `winget install --id <package> --source winget --accept-source-agreements --accept-package-agreements`
  (packages `Python.Python.3.12` + `--scope user`, `OpenJS.NodeJS.LTS`, `ImageMagick.ImageMagick`, `Git.Git`).
- **Linux:** the distribution's packages (`python3`, `nodejs`/`npm`, `imagemagick`, `git`).
- Optional: Node via nvm (`web/.nvmrc` gives the version) – then `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh";
  nvm use` before `npm` commands; write that into the project's `CLAUDE.md` too.

## macOS: https and certificates
Check: `python3 -I -c "import urllib.request; urllib.request.urlopen('https://www.familysearch.org')"`.
Python from python.org has no certificates after installation (`CERTIFICATE_VERIFY_FAILED`) – the user runs
`Install Certificates.command` in `/Applications/Python 3.x/`, or use Homebrew's Python (`/opt/homebrew/bin/python3`).

## Windows
- **Python:** `python3` is often only a broken Microsoft Store alias ("Python was not found") – check
  `python --version` (or `py -3 --version`) and in all skill commands use `python -I -X utf8` instead of
  `python3 -I` (if only the launcher works, `py -3 -I -X utf8`). `-I` ignores the `PYTHONUTF8` variable; without
  `-X utf8` piped or redirected output is in the local code page – accented letters break and some tools crash on
  characters like "→".
- Check **which** Python it is (`which -a python`) – it may come bundled with another program (Inkscape, GIMP…) and
  lack certificates. Check https: `python -I -c "import urllib.request; urllib.request.urlopen('https://www.familysearch.org')"`.
  On `CERTIFICATE_VERIFY_FAILED` install a normal Python (winget above) and call it by its full path
  `"$LOCALAPPDATA/Programs/Python/Python312/python.exe"` (it reaches the PATH only after restarting Claude Code).
- **ImageMagick:** `winget install --id ImageMagick.ImageMagick --source winget --accept-source-agreements --accept-package-agreements`;
  it reaches the PATH only after restarting Claude Code (until then put `export PATH="/c/Program Files/ImageMagick-7…:$PATH"`
  with the exact folder from `C:\Program Files` before commands). **Never `convert`** (a Windows system tool), always
  `magick`.
- Run `.sh` scripts through Git Bash (`bash tools/…`). Do not write longer one-off Python scripts as a heredoc
  (`python - <<EOF`), in Git Bash they sometimes fail with "unexpected EOF" – write them into a file in `work/` and run it.
- Write these rules into the project's `CLAUDE.md` right after creating the project, so they apply next time too,
  and put them into helper briefs (more traps: `registers.md` → Technical traps (Windows)).

## A browser for Claude
You need one for archives that do not allow tools (see the country guide: "browser only"), for FamilySearch images,
and for portals whose image addresses are computed by JavaScript (Matricula). If you have no `mcp__…playwright…`
tools, offer the Playwright plugin: `/plugin install playwright@claude-plugins-official` (give it to the user with `!`
as `claude plugin install playwright@claude-plugins-official`), then restart Claude Code. Another option is Claude in
Chrome (`/chrome`) – it works in the user's own Chrome; the procedures in the guides were tested mainly with
Playwright (it can save screenshots and downloads into files). Without a browser, the user sends screenshots.
- **Logins** (FamilySearch, library accounts) are done by the user in the Playwright window or their Chrome; the login
  usually persists for days. Before a round that needs it, check the login with one request (401 or a "Sign in"
  header = logged out, not a block) and ask the user to log in again.
- Playwright is one browser: two helpers in different tabs switch each other's pages. For parallel work on another
  browser-only archive use Claude in Chrome in its own tab.
- Some archives reject the built-in browser of the Claude desktop app – the country guide says so.

## Creating the project
1. Ask where the project should live (suggest `~/Genealogy`) and create it:
   `python3 -I SKILL_DIR/tools/new_project.py <folder>`. If the user first wants to see what the website looks like,
   create a sample next to it: `… new_project.py ~/Genealogy-sample --sample`, then
   `cd web && npm install && npm run preview` (in the background) and send the link http://localhost:4321.
2. Ask whether to turn on the **network guard** (`… new_project.py <folder> --guard`, turn off with `--no-guard`).
   Explain in one sentence: archives block IP addresses after a series of fast requests. The guard is a small script
   in the project (`tools/net_guard.py`) which checks before each command that downloads go through the brake and
   rejects them otherwise. It downloads nothing itself. Without it only the brake rules and the ban on direct
   `curl`/`wget` in `.claude/settings.json` apply.
3. In the project `git init` and a first save (git = history of changes, in case something breaks). Recommend
   continuing in Claude Code **from this folder** (its `CLAUDE.md` makes sure you pick up where you left off).
4. Fill in `data/STATUS.md` → "Who is this for" (starting person, who works with Claude, **the family's language** for
   translations and website texts) and in `data/website.json` the website title ("The Novák family tree", "Stamboom
   Dubois") as soon as you know the starting person's surname (the template is empty).
5. Ask which countries the family comes from and read the matching guides in `reference/countries/`.
