"""Tests of the project update via tools/new_project.py: three-way decision from the stored template (.skill_template/).

The script builds a small fake skill in a temporary folder (template/ and tools/ with a copy of new_project.py),
creates a project from it, changes the template and the project and runs the update. Downloads nothing, needs only
Python (and git for merging).
From the repository root:
  python3 -I tests/update/test_update.py skills/genealogy
On Windows `python -I -X utf8`. Exits with code 1 when a case fails.
"""
import glob, os, shutil, subprocess, sys, tempfile, time, traceback

SKILL = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy")
LINES = [f"line {i}" for i in range(1, 21)]
COUNT = 20   # number of cases in cases()
SKIPPED = "skipped: "   # a case that cannot be tried here (counted separately)


def write(p, text, nl="\n"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline=nl) as f:
        f.write(text)


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def text(lines):
    return "\n".join(lines) + "\n"


def change(lines, i, new):
    r = list(lines)
    r[i] = new
    return r


def fake_skill(root):
    s = os.path.join(root, "skill")
    os.makedirs(os.path.join(s, "tools"))
    shutil.copy2(os.path.join(SKILL, "tools", "new_project.py"), os.path.join(s, "tools"))
    write(os.path.join(s, "VERSION"), "9.9.9\n")
    write(os.path.join(s, "tools", "tool.py"), text(LINES))
    write(os.path.join(s, "tools", "script.sh"), "#!/bin/sh\necho hello\n", nl="\r\n")   # a skill from Windows with CRLF
    write(os.path.join(s, "template", "web", "src", "style.css"), text(LINES))
    write(os.path.join(s, "tools", "old.py"), "print('remove me')\n")
    for n in ("index.astro", "home.astro", "drop.astro", "map.astro", os.path.join("folder", "x.astro")):
        write(os.path.join(s, "template", "web", "src", n), text(LINES))
    write(os.path.join(s, "template", "web", "node_modules", "x.js"), "do not copy\n")
    write(os.path.join(s, "template", "data", "STATUS.md"), "# Status\n")
    for n in ("CLAUDE.md", ".gitignore", ".gitattributes", "notes_for_skill.md", os.path.join(".claude", "launch.json")):
        write(os.path.join(s, "template", n), "{}\n" if n.endswith(".json") else "x\n")
    return s


def run(skill, project, *opts, env=None):
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(skill, "tools", "new_project.py"), project,
                        *opts], capture_output=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def section(output, start):
    """Files listed under the line starting with `start` (indented lines up to the next unindented one)."""
    lines, inside, out = output.splitlines(), False, []
    for r in lines:
        if r.startswith(start):
            inside = True
        elif inside and r.startswith("  "):
            out.append(r.strip())
        else:
            inside = False
    return out


def backups(project, *path):
    return sorted(glob.glob(os.path.join(project, "work", "backup_*", *path)))   # the last one is the newest


def cases(root):
    s = fake_skill(root)
    p = os.path.join(root, "project")
    tpl = lambda *c: os.path.join(s, "template", "web", *c)
    proj = lambda *c: os.path.join(p, *c)

    # 1. new project: exact copies of the template are stored, without node_modules and new_project.py; .sh has LF
    run(s, p)
    assert read(proj(".skill_template", "web", "src", "style.css")) == text(LINES)
    assert read(proj(".skill_template", "tools", "tool.py")) == text(LINES)
    assert not os.path.exists(proj(".skill_template", "web", "node_modules"))
    assert not os.path.exists(proj(".skill_template", "tools", "new_project.py"))
    assert not os.path.exists(proj("tools", "new_project.py"))
    assert read(proj("tools", "script.sh")) == "#!/bin/sh\necho hello\n"
    assert read(proj(".skill_template", "tools", "script.sh")) == "#!/bin/sh\necho hello\n"
    for d in ("crops", "sources", "documents", "work"):
        assert os.path.isdir(proj(d)), d
    assert read(proj(".skill_version")) == "9.9.9\n"
    yield "a new project stores the template in .skill_template/"

    # 2. unmodified file, the template changed → overwrite without a backup
    new = change(LINES, 0, "line 1 from the new template")
    write(tpl("src", "style.css"), text(new))
    out = run(s, p)
    assert read(proj("web", "src", "style.css")) == text(new), out
    assert "web/src/style.css" in section(out, "Overwritten"), out
    assert not backups(p, "*", "web", "src", "style.css"), out
    assert read(proj(".skill_template", "web", "src", "style.css")) == text(new)
    yield "an unmodified file is overwritten by the new template"

    # 3. modified file, template unchanged → keep
    own = change(new, 10, "line 11 own change")
    write(proj("web", "src", "style.css"), text(own))
    out = run(s, p)
    assert read(proj("web", "src", "style.css")) == text(own), out
    assert "web/src/style.css" in section(out, "Kept"), out
    yield "an own change stays when the template did not change"

    # 4. modified file, template changed elsewhere → merge both changes
    new2 = change(new, 19, "line 20 from the next template")
    write(tpl("src", "style.css"), text(new2))
    out = run(s, p)
    assert read(proj("web", "src", "style.css")) == text(change(own, 19, "line 20 from the next template")), out
    assert "web/src/style.css" in section(out, "Merged"), out
    yield "non-overlapping changes are merged"

    # 5. modified file, template changed on the same line → keep the project, new version to the backup, report it
    before = read(proj("web", "src", "style.css"))
    write(tpl("src", "style.css"), text(change(new2, 10, "line 11 different in the template")))
    out = run(s, p)
    assert read(proj("web", "src", "style.css")) == before, out
    assert "web/src/style.css" in section(out, "To check"), out
    nb = backups(p, "new_template", "web", "src", "style.css")
    assert nb and read(nb[-1]) == text(change(new2, 10, "line 11 different in the template")), out
    yield "a conflict keeps the project, saves the new version to the backup and reports it"

    # 6. an unresolved conflict is reported again on the next run (the stored template does not move)
    out = run(s, p)
    assert read(proj("web", "src", "style.css")) == before, out
    assert "web/src/style.css" in section(out, "To check"), out
    assert read(proj(".skill_template", "web", "src", "style.css")) == text(new2), out
    yield "an unresolved conflict is reported again"

    # 6b. --resolved after a manual merge stores as the base the proposal the user got (A), not a newer template (B)
    #     meanwhile; the next update then adds the change from B
    proposal = change(new2, 10, "line 11 different in the template")
    write(tpl("src", "style.css"), text(change(proposal, 14, "line 15 template B")))   # the skill moved on meanwhile
    manual = change(change(own, 19, "line 20 from the next template"), 10, "line 11 own + different")
    write(proj("web", "src", "style.css"), text(manual))
    out = run(s, p, "--resolved", "web/src/style.css")
    assert read(proj("web", "src", "style.css")) == text(manual), out
    assert read(proj(".skill_template", "web", "src", "style.css")) == text(proposal), out
    pending = proj(".skill_template", "pending.json")   # an empty record is deleted
    assert not os.path.exists(pending) or "web/src/style.css" not in read(pending), out
    out = run(s, p)
    assert "web/src/style.css" not in section(out, "To check"), out
    assert "web/src/style.css" in section(out, "Merged"), out
    assert read(proj("web", "src", "style.css")) == text(change(manual, 14, "line 15 template B")), out
    yield "--resolved stores the recorded proposal, a newer template is then merged"

    # 7. without git in PATH not even non-overlapping changes are merged; with git they are on the next run
    own_home = change(LINES, 2, "line 3 own")
    write(proj("web", "src", "home.astro"), text(own_home))
    write(tpl("src", "home.astro"), text(change(LINES, 17, "line 18 new")))
    out = run(s, p, env={**os.environ, "PATH": os.path.dirname(sys.executable)})
    assert read(proj("web", "src", "home.astro")) == text(own_home), out
    assert "web/src/home.astro" in section(out, "To check"), out
    out = run(s, p)
    assert read(proj("web", "src", "home.astro")) == text(change(own_home, 17, "line 18 new")), out
    assert "web/src/home.astro" in section(out, "Merged"), out
    yield "without git: file to check, with git it is merged later"

    # 8. a file added by the user and by the new template → keep the user's, template version to the backup, report again
    write(proj("web", "src", "photos.astro"), "my photos\n")
    write(tpl("src", "photos.astro"), "photos from the template\n")
    for _ in range(2):
        out = run(s, p)
        assert read(proj("web", "src", "photos.astro")) == "my photos\n", out
        assert any(f.startswith("web/src/photos.astro") for f in section(out, "To check")), out
    nb = backups(p, "new_template", "web", "src", "photos.astro")
    assert nb and read(nb[-1]) == "photos from the template\n", out
    yield "a new file in the template and in the project: the user's stays"

    # 8b. --resolved for a file added by the project and by the template
    run(s, p, "--resolved", "web/src/photos.astro")
    out = run(s, p)
    assert not any(f.startswith("web/src/photos.astro") for f in section(out, "To check")), out
    assert read(proj("web", "src", "photos.astro")) == "my photos\n", out
    yield "--resolved for a file added by the project and by the template"

    # 9. a file deleted in the project: do not bring it back; if the template changes, new version only to the backup
    os.remove(proj("web", "src", "home.astro"))
    out = run(s, p)
    assert not os.path.exists(proj("web", "src", "home.astro")), out
    assert "web/src/home.astro" in section(out, "Deleted in the project"), out
    write(tpl("src", "home.astro"), text(change(LINES, 0, "line 1 after deletion")))
    out = run(s, p)
    assert not os.path.exists(proj("web", "src", "home.astro")), out
    assert any(f.startswith("web/src/home.astro") for f in section(out, "To check")), out
    nb = backups(p, "new_template", "web", "src", "home.astro")
    assert nb and read(nb[-1]) == text(change(LINES, 0, "line 1 after deletion")), out
    yield "a deleted file does not come back"

    # 10. the template removed a file: delete or move nothing, only report (unmodified and modified)
    write(proj("web", "src", "drop.astro"), text(change(LINES, 4, "line 5 own")))
    os.remove(os.path.join(s, "tools", "old.py"))
    os.remove(tpl("src", "drop.astro"))
    for _ in range(2):
        out = run(s, p)
        assert read(proj("tools", "old.py")) == "print('remove me')\n", out
        assert os.path.isfile(proj(".skill_template", "tools", "old.py")), out
        assert read(proj("web", "src", "drop.astro")) == text(change(LINES, 4, "line 5 own")), out
        assert {"tools/old.py", "web/src/drop.astro"} <= set(section(out, "No longer in the template")), out
    assert not backups(p, "removed"), out
    yield "a file removed from the template stays and is reported"

    # 10b. --resolved for a file the template no longer has deletes only the base; without a conflict record it stores
    #      the current template
    out = run(s, p, "--resolved", "web/src/drop.astro", "--resolved", "tools/old.py")
    assert not os.path.exists(proj(".skill_template", "web", "src", "drop.astro")), out
    assert not os.path.exists(proj(".skill_template", "tools", "old.py")), out
    out = run(s, p)
    assert not set(section(out, "No longer in the template")) & {"tools/old.py", "web/src/drop.astro"}, out
    assert read(proj("web", "src", "drop.astro")) == text(change(LINES, 4, "line 5 own")), out
    assert os.path.isfile(proj("tools", "old.py")), out
    out = run(s, p, "--resolved", "web/src/index.astro")
    assert "not recorded" in out, out
    yield "a removal from the template is reported until it is resolved"

    # 10c. a folder in the project where the new template has a file: do not crash, overwrite nothing, report
    os.remove(tpl("src", "folder", "x.astro"))
    os.rmdir(tpl("src", "folder"))
    write(tpl("src", "folder"), "now a file\n")
    out = run(s, p)
    assert "WARNING" in out, out
    assert os.path.isfile(proj("web", "src", "folder", "x.astro")), out
    assert any(f.startswith("web/src/folder") for f in section(out, "To check")), out
    yield "a folder in place of a file is reported"

    # 10d. a rename only in letter case (Windows, macOS): one file, do not write twice, report
    if os.name == "nt" or sys.platform == "darwin":
        os.remove(tpl("src", "map.astro"))
        write(tpl("src", "Map.astro"), text(change(LINES, 0, "line 1 Map")))
        out = run(s, p)
        assert os.path.isfile(proj("web", "src", "map.astro")), out
        assert read(proj("web", "src", "map.astro")) == text(LINES), out
        assert os.path.isfile(proj(".skill_template", "web", "src", "map.astro")), out
        assert any(f.lower().startswith("web/src/map.astro") for f in section(out, "To check")), out
        yield "a rename only in letter case is reported"
    else:
        yield SKIPPED + "letter case (the file system distinguishes it)"

    # 11. a project with CRLF (git on Windows), the same content as the template → counted as unmodified
    write(proj("web", "src", "index.astro"), text(LINES), nl="\r\n")
    write(tpl("src", "index.astro"), text(change(LINES, 5, "line 6 new")))
    out = run(s, p)
    assert read(proj("web", "src", "index.astro")) == text(change(LINES, 5, "line 6 new")), out
    assert "web/src/index.astro" in section(out, "Overwritten"), out
    yield "CRLF line endings do not count as an own change"

    # 12. an old project without .skill_template/: overwrite as before, but back up tools/ as well
    shutil.rmtree(proj(".skill_template"))
    write(proj("tools", "tool.py"), text(change(LINES, 3, "line 4 own")))
    write(os.path.join(s, "tools", "tool.py"), text(change(LINES, 15, "line 16 new")))
    out = run(s, p)
    assert read(proj("tools", "tool.py")) == text(change(LINES, 15, "line 16 new")), out
    bk = backups(p, "original", "tools", "tool.py")
    assert bk and read(bk[-1]) == text(change(LINES, 3, "line 4 own")), out
    assert "tools/tool.py" in section(out, "Overwritten, the original version"), out
    assert os.path.isfile(proj(".skill_template", "tools", "tool.py"))
    yield "an old project without a stored template: tools/ are backed up"

    # 12b. package-lock.json is changed by npm install: changed only in the project it stays, changed in the template
    #      too it is replaced (no merge)
    write(tpl("package-lock.json"), text(LINES))
    run(s, p)
    write(proj("web", "package-lock.json"), text(change(LINES, 5, "line 6 from npm")))
    out = run(s, p)
    assert read(proj("web", "package-lock.json")) == text(change(LINES, 5, "line 6 from npm")), out
    write(tpl("package-lock.json"), text(change(LINES, 18, "line 19 new template")))
    out = run(s, p)
    assert read(proj("web", "package-lock.json")) == text(change(LINES, 18, "line 19 new template")), out
    assert not any("package-lock" in f for f in section(out, "To check")), out
    bk = backups(p, "original", "web", "package-lock.json")
    assert bk and read(bk[-1]) == text(change(LINES, 5, "line 6 from npm")), out
    yield "package-lock.json is not merged: new from the template, old in the backup"

    # 13. .skill_template/tools as a link (symlink, on Windows a junction) outside the project: delete or write nothing
    outer = os.path.join(root, "outside")
    write(os.path.join(outer, "notes.txt"), "foreign\n")
    shutil.rmtree(proj(".skill_template", "tools"))
    link = proj(".skill_template", "tools")
    try:
        os.symlink(outer, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        try:
            import _winapi
            _winapi.CreateJunction(outer, link)
        except (ImportError, OSError):
            link = None
    if link:
        try:
            out = run(s, p)
            assert read(os.path.join(outer, "notes.txt")) == "foreign\n", out
            assert sorted(os.listdir(outer)) == ["notes.txt"], out
            assert "WARNING" in out, out
        finally:
            os.unlink(link) if os.path.islink(link) else os.rmdir(link)
        yield "a link from .skill_template/ outside the project is refused"
    else:
        yield SKIPPED + "a folder link cannot be created (no permission)"

    # 14. backup of an old project: the backup target is a link outside beforehand (file symlink, else junction) →
    #     do not write, do not overwrite
    shutil.rmtree(proj(".skill_template"))
    write(proj("tools", "tool.py"), text(change(LINES, 6, "line 7 own")))
    write(os.path.join(s, "tools", "tool.py"), text(change(LINES, 8, "line 9 new")))
    target = os.path.join(outer, "target.txt")
    write(target, "foreign target\n")
    links, kind = [], None
    for z in backups(p):   # backups of the earlier cases (may have the same second)
        shutil.rmtree(z)
    now = time.time()
    for t in range(-1, 15):   # the backup name has the time in seconds – prepare links for the nearest seconds
        leaf = proj("work", "backup_" + time.strftime("%Y%m%d-%H%M%S", time.localtime(now + t)),
                    "original", "tools", "tool.py")
        os.makedirs(os.path.dirname(leaf), exist_ok=True)
        try:
            if kind != "junction":
                os.symlink(target, leaf)
                kind = "symlink"
            else:
                raise OSError
        except (OSError, NotImplementedError):
            try:
                import _winapi
                _winapi.CreateJunction(outer, leaf)
                kind = "junction"
            except (ImportError, OSError):
                break
        links.append(leaf)
    if links:
        out = run(s, p)
        for leaf in links:
            os.unlink(leaf) if os.path.islink(leaf) else os.rmdir(leaf)
        assert read(target) == "foreign target\n", out
        assert sorted(os.listdir(outer)) == ["notes.txt", "target.txt"], out
        assert "WARNING" in out, out
        assert read(proj("tools", "tool.py")) == text(change(LINES, 6, "line 7 own")), out
        yield f"a backup target as a link ({kind}) is refused"
    else:
        yield SKIPPED + "a link in the backup's place cannot be created (no permission)"


def main():
    root = tempfile.mkdtemp(prefix="test_update_")
    ok = skipped = 0
    try:
        for desc in cases(root):
            if desc.startswith(SKIPPED):
                skipped += 1
                print("  [SKIPPED]", desc[len(SKIPPED):])
            else:
                ok += 1
                print("  [OK]", desc)
    except Exception:   # a missing file is a failed case too
        print("  [FAIL] case", ok + skipped + 1, "\n", traceback.format_exc())
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"== update: {ok} of {COUNT} correct, skipped {skipped}")
    sys.exit(0 if ok + skipped == COUNT else 1)


if __name__ == "__main__":
    main()
