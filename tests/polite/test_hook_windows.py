"""Guard hook on Windows: .claude/settings.json gets the full path to Python, not "python" from PATH.

Claude Code hooks run with a different PATH than the command that set the project up – "python" may lead to a broken
Microsoft Store shortcut (WindowsApps) there and the guard would silently not run. The test imitates Windows
(os.name, shutil.which). From the repository root:
  python3 -I tests/polite/test_hook_windows.py skills/genealogy
Contract with new_project.py: guard_hook() returns {"command": <python>, "args": ["-I", …]} on Windows.
"""
import os, shutil, sys

sys.path.insert(0, os.path.join(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "skills/genealogy"), "tools"))
import new_project  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{'' if ok else '  ' + str(detail)}", flush=True)


original_name, original_which = os.name, shutil.which
try:
    new_project.os.name = "nt"
    for in_path in ("C:/Users/x/AppData/Local/Programs/Python/Python312/python.exe",
                    "C:/Users/x/AppData/Local/Microsoft/WindowsApps/python.exe", None):
        new_project.shutil.which = lambda _n, v=in_path: v
        h = new_project.guard_hook()
        check(f"Windows, python in PATH = {in_path}: full path to the Python of the setup",
              h.get("command") == sys.executable and h.get("args", [None])[0] == "-I", h)
finally:
    new_project.os.name, new_project.shutil.which = original_name, original_which

print(f"\n{sum(results)} of {len(results)} right")
sys.exit(0 if all(results) else 1)
