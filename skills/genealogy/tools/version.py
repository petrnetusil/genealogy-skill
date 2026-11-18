#!/usr/bin/env python3
"""Version check at the start of a conversation: installed skill × project × latest release on GitHub.
Usage: python3 -I <skill>/tools/version.py [<project folder>]

It asks GitHub at most once per 24 hours (cache ~/.cache/genealogy_version.json, on Windows %LOCALAPPDATA%);
without network or on an error it simply does not ask. The last line starts with "→" and a keyword for Claude:
  NEW_SKILL_VERSION  GitHub has a newer version than the installed skill – the user should update the skill
                     (the project is then updated from the new skill, not from GitHub)
  UPDATE_PROJECT     the installed skill is newer than the project – offer new_project.py
  PROJECT_NEWER      the project was created by a newer skill than the installed one (old copy of the skill) –
                     do not change the project
  SKILL_NOT_FOUND    run from the copy in the project and the installed skill was not found – skill version unchecked
  UP_TO_DATE         everything matches
The copy in the project's tools/ finds the installed skill itself (Claude Code plugin registry,
~/.claude/skills/genealogy, Claude desktop).
The exit code is always 0 (the check must never stop the work).
Environment (for tests): GENEALOGY_VERSION_URL (release API URL), GENEALOGY_CACHE (cache folder).
"""
import glob, json, os, re, sys, time, urllib.request
if sys.argv[1:2] in (["-h"], ["--help"]):   # help instead of the check (otherwise "--help" would be taken as a folder)
    print(__doc__.strip())
    sys.exit(0)   # always 0, see above
if len(sys.argv) > 1 and (sys.argv[1].startswith("-") or not os.path.isdir(sys.argv[1])):
    print(f"version.py: \"{sys.argv[1]}\" is not a project folder – give the path to the project folder (or nothing).")
    sys.exit(0)

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/petrnetusil/genealogy-skill"
URL = os.environ.get("GENEALOGY_VERSION_URL", "https://api.github.com/repos/petrnetusil/genealogy-skill/releases/latest")
CACHE = os.path.join(os.environ.get("GENEALOGY_CACHE") or os.environ.get("LOCALAPPDATA")
                     or os.path.join(os.path.expanduser("~"), ".cache"), "genealogy_version.json")
PLUGIN = "genealogy@genealogy-skill"   # plugin id in the Claude Code registry (plugin@marketplace)
DAY = 24 * 3600


def number(v):
    """"v0.10.0" → (0, 10, 0); an unintelligible version → None."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def github():
    """Latest release on GitHub (version text) or None; at most one request per 24 hours."""
    try:
        with open(CACHE, encoding="utf-8") as f:
            c = json.load(f)
        if time.time() - c.get("time", 0) < DAY and number(c.get("version")):
            return c["version"]
    except (OSError, ValueError, AttributeError):
        pass
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "genealogy-skill", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            version = json.load(r).get("tag_name", "").lstrip("v")
    except Exception:
        return None
    if not number(version):
        return None
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump({"time": time.time(), "version": version}, f)
    except OSError:
        pass
    return version


def installed(project_dir):
    """The copy in the project's tools/ has no VERSION next to it – find the installed skill: a plugin from the
    Claude Code registry (for this project, else for the user), a manually copied ~/.claude/skills/genealogy, the
    usual plugin folder ~/.claude/plugins/cache/genealogy-skill/genealogy/<version> or Claude desktop.
    Returns (version, path)."""
    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    project = os.path.realpath(project_dir) if project_dir else None
    try:
        with open(os.path.join(cfg, "plugins", "installed_plugins.json"), encoding="utf-8") as f:
            entries = json.load(f).get("plugins", {}).get(PLUGIN, [])
    except (OSError, ValueError, AttributeError):
        entries = []
    order = []
    for z in entries if isinstance(entries, list) else []:
        pp = z.get("projectPath")
        if pp and project and os.path.realpath(pp) == project:
            order.insert(0, z)                      # an install for this project wins
        elif z.get("scope") == "user":
            order.append(z)
    for z in order:
        path = os.path.join(z.get("installPath", ""), "skills", "genealogy")
        version = read(os.path.join(path, "VERSION")) or z.get("version")
        if number(version):
            return version, path
    manual = os.path.join(cfg, "skills", "genealogy")
    version = read(os.path.join(manual, "VERSION"))
    if number(version):
        return version, manual
    # registry missing or unreadable: the usual plugin cache folder – the highest version found
    found = []
    for d in glob.glob(os.path.join(cfg, "plugins", "cache", "genealogy-skill", "genealogy", "*", "skills", "genealogy")):
        v = read(os.path.join(d, "VERSION"))
        if number(v):
            found.append((number(v), v, d))
    if found:
        _, v, d = max(found)
        return v, d
    return desktop()


def desktop():
    """Skill of an account in the Claude desktop app (Windows %LOCALAPPDATA%\\Claude-Data\\claude_…\\rpm\\…\\plugin_…\\
    skills\\genealogy, similarly on macOS) – the highest version found, else (None, None)."""
    bases = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Claude-Data"),
             os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Claude-Data")]
    found = []
    for b in bases:
        if not os.path.isdir(b):
            continue
        for pattern in ("*/rpm/plugin_*", "*/rpm/*/plugin_*", "*/rpm/*/*/plugin_*"):
            for d in glob.glob(os.path.join(b, pattern, "skills", "genealogy")):
                v = read(os.path.join(d, "VERSION"))
                if number(v):
                    found.append((number(v), v, d))
    if not found:
        return None, None
    _, v, d = max(found)
    return v, d


def main():
    global SKILL
    skill = read(os.path.join(SKILL, "VERSION"))
    if skill is None:   # run from the copy in the project's tools/
        skill, located = installed(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(SKILL))
        if located:
            SKILL = located
    project_dir = sys.argv[1] if len(sys.argv) > 1 else None
    project = read(os.path.join(project_dir, ".skill_version")) if project_dir else None
    gh = github()

    print(f"Skill (installed): {skill}")
    if project_dir:
        print(f"Project: {project or 'no .skill_version (created by a very old skill)'}")
    print(f"GitHub (latest release): {gh or 'unknown (no network or GitHub did not answer)'}")

    s, p, g = number(skill), number(project), number(gh)
    if g and s and g > s:
        if os.sep + "plugins" + os.sep in SKILL:   # installed as a plugin (…/.claude/plugins/…)
            how = ("as a plugin: `claude plugin marketplace update genealogy-skill` and `claude plugin update\n"
                   f"  {PLUGIN}`, then restart Claude Code (permanently: turn on automatic updates in /plugin;\n"
                   "  when the `claude` command cannot be run, the same commands work in Claude Code via /plugin)")
        else:                                       # copied by hand (~/.claude/skills/genealogy …)
            how = (f"manually copied skill ({SKILL}): download the new version from {REPO}\n"
                   "  (Code → Download ZIP), replace the current folder with skills/genealogy and restart Claude")
        print(f"→ NEW_SKILL_VERSION: version {gh} is out, the installed skill is {skill}. Tell the user in one sentence and\n"
              f"  explain how to update the skill – {how}. Update the project only from the new skill.")
    elif project_dir and p and s and p > s:
        print(f"→ PROJECT_NEWER: the project is from version {project}, the installed skill is older ({skill}). Do not update\n"
              "  the project (you would take it back to an older version); the user should update the skill (README, Installation).")
    elif project_dir and s and (not p or s > p):
        print(f"→ UPDATE_PROJECT: skill {skill} is newer than the project. Offer to update the project:\n"
              f"  python3 -I {os.path.join(SKILL, 'tools', 'new_project.py')} <project folder>")
    elif not s:
        print("→ SKILL_NOT_FOUND: the installed skill was not found, the skill version is not compared. Run the check from\n"
              "  the skill's folder: python3 -I SKILL_DIR/tools/version.py <project folder>")
    else:
        print("→ UP_TO_DATE")


if __name__ == "__main__":
    main()
