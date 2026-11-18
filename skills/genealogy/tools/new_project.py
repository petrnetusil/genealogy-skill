#!/usr/bin/env python3
"""Creates a new genealogy project from the skill's template, or updates an existing one.

Usage: python3 <skill>/tools/new_project.py <target folder> [--sample] [--guard | --no-guard]
  --sample        also copies the invented sample data (the Novák family), so the website can be tried right away
  --guard         turns on the network guard (hook in .claude/settings.json, tools/net_guard.py): it refuses commands
                  that go to an archive website outside the brake tools/polite.py; --no-guard turns it off
       python3 <skill>/tools/new_project.py <project folder> --resolved <file> [--resolved <file> …]
  --resolved      after taking over template changes by hand (a file "to check", e.g. web/src/pages/index.astro) saves
                  the new template version as the base; the project file is not changed and later updates stop
                  reporting it

Creates: data/ (empty skeletons or the sample), web/ (Astro website), tools/ (copy of the skill's tools),
crops/, sources/, documents/, work/, CLAUDE.md, notes_for_skill.md, .gitignore, .gitattributes (LF line endings even
on Windows) and .claude/launch.json (preview in Claude desktop). Adds a ban on direct curl/wget to
.claude/settings.json (downloads from archives go through the brake tools/polite.py); other settings in the file stay
unchanged. Existing data are never overwritten.
It stores a copy of the template's web/ and tools/ the project was created from in .skill_template/ (it belongs in git
with the project) and the skill version in .skill_version.
Updating an older project (run again on the same folder) decides about every file in web/ and tools/ from three
versions (stored template, project, new template): an unmodified file is overwritten, an own modification is kept
when the template did not change, otherwise the two are merged line by line (git merge-file). On a conflict, without
git, for a file added by both the project and the template and for a file deleted in the project that the template
changed, the file stays and the new version is saved to work/backup_<date>/new_template/ (on a git merge conflict
also the proposal with conflict markers) and recorded in .skill_template/pending.json; it is reported until you
resolve it (--resolved stores exactly this proposal as the base).
A file the template no longer has is not deleted: it is reported until you delete it by hand and run --resolved.
Links (symlink, junction) leading outside the project or placed where a backup goes, a folder in place of a file and
paths differing only in letter case are reported and skipped.
A project without .skill_template/ (from an older version) is overwritten and the original versions of changed files
are saved to work/backup_<date>/original/.
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF = "new_project.py"   # not copied into the project


def copy(src, out):
    if os.path.islink(out):   # never write through a symlink leading outside the project
        os.remove(out)
    shutil.copy2(src, out)


SKIP = ("node_modules", "dist", ".astro", "__pycache__")
TEMPLATE = ".skill_template"   # copy of the template the project was created from (base of the three-way update)
PENDING = "pending.json"       # in .skill_template/: proposals from conflicts waiting for --resolved
ALWAYS_TEMPLATE = {"web/package-lock.json"}   # changed by npm install, not by the user: no merge, take the new one (old to backup)
CASE_INSENSITIVE = os.name == "nt" or sys.platform == "darwin"   # the disk usually ignores letter case


def copy_tree(src, dst):
    """Copies the missing files."""
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP]
        rel = os.path.relpath(base, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for f in files:
            new, out = os.path.join(base, f), os.path.join(dst, rel, f)
            if not os.path.lexists(out):
                copy(new, out)


def files_of(src):
    """Relative paths of the template's files (without dependencies and build output)."""
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            yield os.path.relpath(os.path.join(base, f), src)


def read(p):
    with open(p, "rb") as f:
        return f.read()


def write(p, data, mode_from=None):
    if os.path.islink(p):   # never write through a symlink leading outside the project
        os.remove(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    if mode_from:
        shutil.copymode(mode_from, p)


def lf(data):
    """LF line endings – CRLF from git on Windows does not count as a modification (binary files unchanged)."""
    return data if b"\0" in data else data.replace(b"\r\n", b"\n")


def merge(ours, base, new):
    """Merges line by line via `git merge-file`. Returns (result, without conflict); without git or on error (None, False)."""
    git = shutil.which("git")
    if not git:
        return None, False
    d = tempfile.mkdtemp(prefix="merge_")
    try:
        paths = [os.path.join(d, n) for n in ("project", "original_template", "new_template")]
        for p, data in zip(paths, (ours, base, new)):
            write(p, data)
        r = subprocess.run([git, "merge-file", "-p", "-L", "project", "-L", "original_template", "-L", "new_template",
                            *paths], capture_output=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if not 0 <= r.returncode <= 127:   # error (e.g. a binary file); 1–127 = number of conflicts
        return None, False
    return r.stdout, r.returncode == 0


def outside(dst, *paths):
    """Does some path lead through a link (symlink, junction) outside the project? The last element does not count –
    write() just replaces a symlink in place of a file. Such a path is reported and the caller skips it."""
    root = os.path.normcase(os.path.realpath(dst)) + os.sep
    for p in paths:
        real = os.path.join(os.path.realpath(os.path.dirname(p)), os.path.basename(p))
        if not os.path.normcase(real).startswith(root):
            print(f"WARNING: {p} leads outside the project (link) – skipping.")
            return True
    return False


def new_version(new):
    data = read(new)
    return data.replace(b"\r\n", b"\n") if new.endswith(".sh") else data   # a skill from Windows (core.autocrlf) has CRLF


def backup(dst, p, data=None, src=None):
    """Writes data, or a copy of the file src, into the backup. Not through a link or folder in the backup's place and
    not outside the project."""
    if os.path.islink(p) or os.path.isdir(p):   # isdir also catches a junction (islink does not see it in Python 3.9)
        print(f"WARNING: in the place of the backup {p} there is a link or a folder – the backup is not written.")
        return False
    if outside(dst, os.path.realpath(p)):
        return False
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if src:
        shutil.copy2(src, p)
    else:
        write(p, data)
    return True


def collision(dst, p):
    """Is there a folder in the file's place, or is some parent folder in the project a file?"""
    if os.path.isdir(p) and not os.path.islink(p):
        return True
    d = os.path.dirname(p)
    while len(d) > len(dst):
        if os.path.lexists(d) and not os.path.isdir(d):
            return True
        d = os.path.dirname(d)
    return False


def load_pending(dst):
    """Conflicts waiting for --resolved: path → fingerprint (sha256) and backup of the template proposal the user got."""
    try:
        with open(os.path.join(dst, TEMPLATE, PENDING), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_pending(dst, pend):
    p = os.path.join(dst, TEMPLATE, PENDING)
    if outside(dst, p):
        return
    if pend:
        write(p, (json.dumps(pend, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    elif os.path.isfile(p):
        os.remove(p)


def propose(dst, pend, name, new_bak, new):
    """Conflict: saves the new version into the backup and remembers it for --resolved."""
    if backup(dst, new_bak, new):
        pend[name] = {"sha256": hashlib.sha256(new).hexdigest(),
                      "backup": os.path.relpath(new_bak, dst).replace(os.sep, "/")}


def update(src, dst, part, names, bak, res, legacy, pend):
    """Updates dst/part from three versions: the original template (dst/.skill_template/part), the project and the new
    template (files `names` from src). Files the new template no longer has are only reported. The stored template
    moves forward only where the new version got into the project; conflict proposals are written to pend.
    legacy=True: project without .skill_template/. The result is added to res[category]."""
    original = os.path.join(dst, TEMPLATE, part)
    if outside(dst, os.path.join(original, "x"), os.path.join(dst, part, "x")):   # the whole folder is a link outside
        return
    groups = {}
    for rel in sorted(set(names) | set(files_of(original) if os.path.isdir(original) else ())):
        groups.setdefault(rel.lower() if CASE_INSENSITIVE else rel, []).append(rel)
    for variants in groups.values():
        if len(variants) > 1:   # differ only in letter case – one file on this disk: write nothing
            res["conflict"].append(", ".join(part + "/" + v.replace(os.sep, "/") for v in variants)
                                   + " (differ only in letter case)")
            continue
        rel = variants[0]
        new, out, orig = os.path.join(src, rel), os.path.join(dst, part, rel), os.path.join(original, rel)
        new_bak = os.path.join(bak, "new_template", part, rel)   # on a conflict the new version goes here, the project stays
        orig_bak = os.path.join(bak, "original", part, rel)
        name = part + "/" + rel.replace(os.sep, "/")
        if outside(dst, out, orig, new_bak, orig_bak):
            continue
        newdata = new_version(new) if rel in names else None
        if collision(dst, out) or collision(dst, orig):
            print(f"WARNING: {name} – the project has a folder in place of a file (or the other way round), skipping.")
            res["conflict" if newdata is not None else "removed"].append(name + " (folder in place of a file)")
            continue
        pend.pop(name, None)
        ours = lf(read(out)) if os.path.isfile(out) and not os.path.islink(out) else None
        base = lf(read(orig)) if os.path.isfile(orig) else None
        if (name in ALWAYS_TEMPLATE and newdata is not None and ours is not None and base is not None
                and ours not in (base, lf(newdata)) and base != lf(newdata)):   # changed by npm and by the template
            if not backup(dst, orig_bak, src=out):   # no overwrite without a backup
                res["conflict"].append(name + " (the backup could not be written, the file stayed)")
                continue
            write(out, newdata, new)
            write(orig, newdata, new)
            res["overwritten"].append(name + " (generated by npm, the old one is in the backup original/)")
            continue
        if newdata is None:   # the template removed the file: delete nothing, report until --resolved takes it over
            if os.path.lexists(out):
                res["removed"].append(name)
            continue
        if os.path.islink(out) or (ours is None and base is None):   # a symlink is just replaced; a new file is added
            if os.path.lexists(out):
                res["overwritten"].append(name)
            write(out, newdata, new)
        elif ours is None:   # deleted in the project
            if base == lf(newdata):
                res["deleted"].append(name)
                continue
            propose(dst, pend, name, new_bak, newdata)
            res["conflict"].append(name + " (deleted in the project)")
            continue
        elif ours == lf(newdata):
            pass
        elif ours == base:   # no own modifications
            res["overwritten"].append(name)
            write(out, newdata, new)
        elif base == lf(newdata):   # template unchanged
            res["kept"].append(name)
            continue
        elif base is None and legacy:   # project from an older version without a stored template: overwrite, back up
            if not backup(dst, orig_bak, src=out):   # no overwrite without a backup
                res["conflict"].append(name + " (the backup could not be written, the file stayed)")
                continue
            write(out, newdata, new)
            res["backed_up"].append(name)
        elif base is None:   # the file was added by both the project and the new template
            propose(dst, pend, name, new_bak, newdata)
            res["conflict"].append(name + " (new in the template and in the project)")
            continue
        else:
            merged, ok = merge(ours, base, lf(newdata))
            if not ok:
                propose(dst, pend, name, new_bak, newdata)
                if merged is not None:
                    backup(dst, new_bak + ".conflict", merged)   # with git also the proposal with conflict markers
                res["conflict"].append(name)
                continue
            write(out, merged)
            res["merged"].append(name)
        if base != lf(newdata) or not os.path.isfile(orig):   # the new version is in the project: move the stored template
            write(orig, newdata, new)


def resolve(dst, path):
    """--resolved: stores as the base the template proposal the user got with the conflict (entry in pending.json),
    without an entry the current template version; leaves the project file alone. If the template no longer has the
    file, the base is deleted and the file belongs to the project only. Returns False when there is nothing to resolve."""
    if not os.path.isdir(os.path.join(dst, TEMPLATE)):
        print(f"WARNING: the project has no {TEMPLATE}/ – update it first (run the script without --resolved).")
        return False
    rel = os.path.normpath(os.path.relpath(path, dst) if os.path.isabs(path) else path).replace(os.sep, "/")
    part, _, rest = rel.partition("/")
    src = {"web": os.path.join(SKILL, "template", "web"), "tools": os.path.join(SKILL, "tools")}.get(part)
    if not src or not rest:
        print(f"WARNING: {path} – give a path in the project's web/ or tools/ (e.g. web/src/pages/index.astro).")
        return False
    new, orig = os.path.join(src, rest), os.path.join(dst, TEMPLATE, part, rest)
    if outside(dst, orig) or collision(dst, orig):
        print(f"WARNING: {rel} – the base cannot be written (a link outside or a folder in place of a file).")
        return False
    if part == "web":
        in_template = os.path.isfile(new) and not set(rest.split("/")) & set(SKIP)
    else:
        in_template = os.path.isfile(new) and "/" not in rest and rest.endswith((".py", ".sh")) and rest != SELF
    pend = load_pending(dst)
    entry = pend.get(rel)
    if isinstance(entry, dict):
        z = os.path.join(dst, str(entry.get("backup", "")))
        data = read(z) if os.path.isfile(z) and not outside(dst, os.path.realpath(z)) else None
        if data is None or hashlib.sha256(data).hexdigest() != entry.get("sha256"):
            print(f"WARNING: {rel} – the stored proposal {entry.get('backup')} is missing or changed; not resolved. Run"
                  " the update again (it stores a new proposal) and then --resolved.")
            return False
        write(orig, data)
        del pend[rel]
        save_pending(dst, pend)
        print(f"Resolved: {rel} – the proposal {entry['backup']} is stored as the base, the project file is unchanged.")
    elif in_template:
        write(orig, new_version(new), new)
        print(f"Resolved: {rel} – the conflict proposal is not recorded, the current template version is stored as the"
              " base; the project file is unchanged.")
    elif os.path.isfile(orig):
        os.remove(orig)
        print(f"Resolved: {rel} – the template no longer has it, the project file stays and belongs to the project only.")
    else:
        print(f"WARNING: {rel} is neither in the template nor in {TEMPLATE}/ – nothing to resolve.")
        return False
    return True


NET_DENY = ["Bash(curl:*)", "Bash(wget:*)"]   # downloads from archives only through tools/polite.py (curl goes through it)
# Run the guard only when the file exists: a missing script would make Python exit with code 2, which would block
# every command. Not a path with a version number outside Windows (it would vanish after a Python update); on Windows
# forward slashes (work in Git Bash and cmd).
CODE = ("import os,runpy;p=os.path.join(os.environ.get('CLAUDE_PROJECT_DIR','.'),'tools','net_guard.py');"
        "os.path.isfile(p) and runpy.run_path(p,run_name='__main__')")
PY = sys.executable.replace("\\", "/") if os.name == "nt" else "python3"
GUARD = f'"{PY}" -I -c "{CODE}"'   # shell form (macOS, Linux)
MATCHER = "Bash|PowerShell|Monitor"   # Monitor runs a command in bash just like Bash
GUARD_FILES = ("net_guard.py", "hlidac_site.py")   # current name, and the name in projects of the Czech original


def _python_windows():
    """Python for the hook on Windows: always the full path of the Python running the update. Claude Code hooks have
    another PATH and "python" may lead to a broken Microsoft Store alias there – the guard would silently not run.
    A project shared via OneDrive on two computers is fixed by an update run on the second one (the hook is
    rewritten every time)."""
    return sys.executable


def guard_hook():
    """The guard's hook. On Windows without a shell (command + args): hooks run there in Git Bash, or in PowerShell when
    Git Bash is missing – and there a command with quotes would be a syntax error and Claude Code would refuse every
    command."""
    if os.name == "nt":
        return {"type": "command", "command": _python_windows(), "args": ["-I", "-X", "utf8", "-c", CODE], "timeout": 10}
    return {"type": "command", "command": GUARD, "timeout": 10}


def settings(dst, guard):
    """Adds the curl/wget ban to .claude/settings.json; guard=True/False turns the hook on/off, None leaves it as is."""
    path = os.path.join(dst, ".claude", "settings.json")
    data = {}
    if os.path.exists(path):
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
        except ValueError:
            print(f"WARNING: {path} is not valid JSON – the brake settings were not added. Fix it and run again.")
            return
    before = json.dumps(data, sort_keys=True)
    deny = data.setdefault("permissions", {}).setdefault("deny", [])
    deny += [r for r in NET_DENY if r not in deny]
    pre = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    ours = [h for h in pre if any(g in json.dumps(h) for g in GUARD_FILES)]
    for h in ours:   # project update: renew the hook (the Python path and the form may have changed)
        h["matcher"] = MATCHER
        h["hooks"] = [guard_hook()]
    if guard is True and not ours:
        pre.append({"matcher": MATCHER, "hooks": [guard_hook()]})
    elif guard is False:
        pre[:] = [h for h in pre if h not in ours]
    if not pre:
        del data["hooks"]["PreToolUse"]
    if not data["hooks"]:
        del data["hooks"]
    if json.dumps(data, sort_keys=True) != before:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    on = any("net_guard.py" in json.dumps(h) for h in data.get("hooks", {}).get("PreToolUse", []))
    print("Network guard:", "on" if on else "off (turn on: --guard)")


def _version(text):
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def check_version(dst):
    """Never update a project created by a newer skill with an older copy of the skill – it would take it back."""
    try:
        with open(os.path.join(dst, ".skill_version"), encoding="utf-8") as f:
            project = f.read().strip()
        with open(os.path.join(SKILL, "VERSION"), encoding="utf-8") as f:
            skill = f.read().strip()
    except OSError:
        return
    p, s = _version(project), _version(skill)
    if p and s and p > s:
        sys.exit(f"ERROR: the project is from skill version {project}, this skill is older ({skill}). The update would take\n"
                 "the project back to an older version, so nothing is changed. Update the skill first (README, Installation)\n"
                 "and then try again.")


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        sys.exit(__doc__)
    dst = os.path.abspath(os.path.expanduser(sys.argv[1]))
    if "--resolved" in sys.argv:   # only mark files resolved by hand, nothing else
        paths = [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == "--resolved"]
        if not paths:
            sys.exit(__doc__)
        sys.exit(0 if all([resolve(dst, c) for c in paths]) else 1)
    check_version(dst)
    demo = "--sample" in sys.argv
    os.makedirs(dst, exist_ok=True)
    copy_tree(os.path.join(SKILL, "template", "sample" if demo else "data"), os.path.join(dst, "data"))
    if demo:
        for sub in ("crops", "sources"):
            src = os.path.join(SKILL, "template", "sample_" + sub)
            if os.path.isdir(src):
                copy_tree(src, os.path.join(dst, sub))
    bak = os.path.join(dst, "work", "backup_" + time.strftime("%Y%m%d-%H%M%S"))
    res = {k: [] for k in ("overwritten", "backed_up", "merged", "kept", "deleted", "removed", "conflict")}
    legacy = not os.path.isdir(os.path.join(dst, TEMPLATE))   # project from an older version (or a new one)
    pend = load_pending(dst)
    web_template = os.path.join(SKILL, "template", "web")
    update(web_template, dst, "web", sorted(files_of(web_template)), bak, res, legacy, pend)
    tools = os.path.join(dst, "tools")
    os.makedirs(tools, exist_ok=True)
    tool_files = sorted(f for f in os.listdir(os.path.join(SKILL, "tools"))
                        if f.endswith((".py", ".sh")) and f != SELF)
    update(os.path.join(SKILL, "tools"), dst, "tools", tool_files, bak, res, legacy, pend)
    save_pending(dst, pend)
    for f in tool_files:   # also a kept own .sh with CRLF: Git Bash would not run the script
        p = os.path.join(tools, f)
        if f.endswith(".sh") and os.path.isfile(p) and not os.path.islink(p) and not outside(dst, p):
            data = read(p)
            if b"\r\n" in data:
                write(p, data.replace(b"\r\n", b"\n"))
    for d in ("crops", "sources", "documents", "work"):
        os.makedirs(os.path.join(dst, d), exist_ok=True)
    os.makedirs(os.path.join(dst, ".claude"), exist_ok=True)
    for name in ("CLAUDE.md", ".gitignore", ".gitattributes", "notes_for_skill.md", os.path.join(".claude", "launch.json")):
        out, src = os.path.join(dst, name), os.path.join(SKILL, "template", name)
        if not os.path.lexists(out) and os.path.isfile(src):
            copy(src, out)
    settings(dst, True if "--guard" in sys.argv else False if "--no-guard" in sys.argv else None)
    with open(os.path.join(dst, ".skill_version"), "w", encoding="utf-8") as f:   # SKILL.md offers an update by it
        f.write(open(os.path.join(SKILL, "VERSION"), encoding="utf-8").read())
    print("Project ready:", dst)
    for k, title in (("overwritten", "Overwritten with the new version (no own modifications)"),
                     ("backed_up", "Overwritten, the original version is in " + os.path.join(bak, "original")
                      + " (the project had no stored template – take your own modifications over from the backup)"),
                     ("merged", "Merged (own modifications and template changes)"),
                     ("kept", "Kept (own modifications, template unchanged)"),
                     ("deleted", "Deleted in the project, left deleted (template unchanged)"),
                     ("removed", "No longer in the template – check it, delete it by hand if you like and run --resolved"),
                     ("conflict", "To check (the file stayed unchanged, the new version is in "
                      + os.path.join(bak, "new_template") + "; on a git merge conflict also the proposal with"
                      " conflict markers next to it as .conflict)")):
        if res[k]:
            print(f"{title}, {len(res[k])}:")
            for f in res[k]:
                print("  " + f)
    if res["conflict"] or res["removed"]:
        print("They are reported on every update until you resolve them. After taking the changes over by hand run:\n"
              f"  python3 -I {os.path.abspath(__file__)} {dst} --resolved <file> [--resolved <file> …]")
    if any(f.startswith("web/") for k in ("overwritten", "backed_up", "merged") for f in res[k]):
        print("Then run `npm install` and `npm run data` in web/.")


if __name__ == "__main__":
    main()
