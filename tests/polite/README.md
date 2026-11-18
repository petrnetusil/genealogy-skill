# Tests of the brake against being blocked by an archive

Regression tests for `skills/genealogy/tools/polite.py` (the brake), `skills/genealogy/tools/cache.py` (shared image
cache) and `skills/genealogy/tools/net_guard.py` (the optional guard). They are not inside the skill folder so that
they are not copied to users. They download nothing from the internet: the brake is tested against local servers
(127.0.0.2 and 127.0.0.3 – localhost is deliberately not braked), the guard only receives JSON as from Claude Code.

From the repository root, through the wrapper (the tests themselves contain commands with curl):

    python3 -I skills/genealogy/tools/polite.py tests/polite/test_polite.py skills/genealogy/tools/polite.py
    python3 -I skills/genealogy/tools/polite.py tests/polite/test_net_guard.py skills/genealogy
    python3 -I skills/genealogy/tools/polite.py tests/polite/test_cache.py skills/genealogy/tools   # cache: whole images only
    python3 -I tests/polite/test_curl.py skills/genealogy/tools/polite.py   # curl: URL without https://, several URLs, ranges, own -w
    python3 -I tests/polite/test_browser_images.py skills/genealogy/tools   # cache.py save/find: images from the browser (eBadatelna, FamilySearch)
    python3 -I tests/polite/test_hook_windows.py skills/genealogy    # guard hook on Windows: full path to Python

On Windows use `python -I -X utf8` and run them from Git Bash and from PowerShell. `EXTENDED=0` runs only the basic
brake tests (no heredoc, no stop extension, no subprocesses, no repeated thread races).

On macOS 127.0.0.2 needs an alias on lo0 (`sudo ifconfig lo0 alias 127.0.0.2 up`, the same for .3, .4 and .5);
without it run `test_polite.py` and `test_cache.py` in Docker (`python:3.12-bookworm`).

`test_net_guard.py` and `test_hook_windows.py` use `new_project.py` (`GUARD`, `CODE`, `guard_hook()`):
on Windows `new_project.py --guard` writes the hook without a shell (`command` + `args`), so it does not matter
whether hooks run in Git Bash or PowerShell. `test_net_guard.py` always tries the form without a shell, the shell
form only outside Windows.

History (from the Czech original `rodokmen-skill`): in version 0.6.1 (2 Nov 2026) the brake tests passed 24 of 24 on
Windows 11 (Git Bash and PowerShell) and Linux (Docker), the guard tests 69 of 69 through bash and without a shell.
