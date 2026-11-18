"""Regression suite for the network guard tools/net_guard.py: commands it must deny and commands it must let through.

The guard is started exactly as `new_project.py --guard` writes it into .claude/settings.json: always without a
shell (command + args – the Windows form) and outside Windows also as a shell command through bash (and PowerShell,
if present). For denials it also checks that the answer is valid UTF-8 (Claude Code reads it that way). The guard
downloads nothing. From the repository root (through the wrapper, the test contains commands with curl):
  python3 -I skills/genealogy/tools/polite.py tests/polite/test_net_guard.py skills/genealogy
Contract with new_project.py: GUARD (shell form), CODE (Python code for -c) and guard_hook() (the hook
dict written into settings.json). The cases come from hook tests on Windows (sarsonj/rodokmen-skill PR #53).
"""
import json, os, shutil, subprocess, sys, tempfile

SKILL = os.path.abspath(sys.argv[1])          # …/skills/genealogy (tools/net_guard.py, tools/new_project.py)
sys.path.insert(0, os.path.join(SKILL, "tools"))
import new_project                             # noqa: E402 – the same hook command that --guard writes

COMMAND = new_project.GUARD
HOOK = new_project.guard_hook()
SHELLS = {   # the form without a shell (command + args) – new_project.py writes it on Windows; elsewhere the same code is tried
    "no shell (args)": [shutil.which(HOOK["command"]) or HOOK["command"], *HOOK["args"]] if "args" in HOOK
    else [sys.executable, "-I", "-X", "utf8", "-c", new_project.CODE]}
if "args" in HOOK:
    pass   # Windows: the shell form is no longer written
elif os.name == "nt" and os.path.isfile(r"C:\Program Files\Git\usr\bin\bash.exe"):
    SHELLS["Git Bash"] = [r"C:\Program Files\Git\usr\bin\bash.exe", "-c", COMMAND]
elif shutil.which("bash"):
    SHELLS["bash"] = [shutil.which("bash"), "-c", COMMAND]
if shutil.which("pwsh") and "args" not in HOOK:
    SHELLS["PowerShell"] = [shutil.which("pwsh"), "-NoProfile", "-Command", COMMAND]

TMP = tempfile.mkdtemp(prefix="test_net_guard_")
BATCH = os.path.join(TMP, "batch.py").replace("\\", "/")          # runs a tool with import polite → allow
OWN = os.path.join(TMP, "own_network.py").replace("\\", "/")      # own script with network → deny
with open(BATCH, "w", encoding="utf-8") as f:
    f.write("import subprocess, sys\nfor n in range(1, 50):\n"
            "    subprocess.run([sys.executable, '-I', 'tools/aron_img.py', '123', str(n), '1', f'work/x{n}.jpg'])\n")
with open(OWN, "w", encoding="utf-8") as f:
    f.write("import json, urllib.request\nprint(1)\n")
GITHUB = os.path.join(TMP, "github_only.py").replace("\\", "/")   # network only to an exempt site (like tools/version.py) → allow
with open(GITHUB, "w", encoding="utf-8") as f:
    f.write("import json, urllib.request\nURL = 'https://api.github.com/repos/x/y/releases/latest'\n")
MIXED = os.path.join(TMP, "github_and_archive.py").replace("\\", "/")  # exempt site and an archive → deny
with open(MIXED, "w", encoding="utf-8") as f:
    f.write("import urllib.request\nA = 'https://api.github.com/x'\nB = 'https://aron.vychodoceskearchivy.cz/'\n")

D, A = "deny", "allow"
CASES = [
    # a network word or curl only inside text (grep, commit, note) – allow; real execution – deny
    ("Bash", 'python3 -I tools/check.py; grep -n "urlopen(" tools/*.py', A),
    ("Bash", 'git commit -m "fix; curl https://www.mza.cz/actapublica"', A),
    ("Bash", 'echo "- guard: curl https://www.mza.cz denied; import requests" >> notes_for_skill.md', A),
    ("Bash", 'echo "$(curl -s https://www.mza.cz/x)"', D),
    ("Bash", "echo `curl -s https://www.mza.cz/x`", D),
    ("Bash", 'eval "curl -s https://www.mza.cz/x"', D),
    ("Bash", 'echo "import urllib.request" | python3 -', D),
    ("Bash", "cat > work/x.py <<'EOF'\nimport urllib.request\nEOF\npython3 work/x.py", D),
    ("Bash", 'python3 -c "print(1)"; curl -s https://www.mza.cz/x', D),
    # Bash – deny
    ("Bash", "python -I -X utf8 -c \"import urllib.request; urllib.request.urlopen('https://aron.vychodoceskearchivy.cz')\"", D),
    ("Bash", "python -I -X utf8 - <<'EOF'\nimport json, urllib.request\nprint(1)\nEOF", D),
    ("Bash", "python -I -X utf8 - <<'EOF'\nimport urllib.request  # Plaňany, Všeruby\nEOF", D),
    ("Bash", "curl -s https://katalog.ahmp.cz/pragapublica/ -o work/x.html", D),
    ("Bash", 'for i in 1 2 3; do curl -s "https://example.cz/api?p=$i"; done', D),
    ("Bash", "x=$(curl -s https://example.com) && echo $x", D),
    ("Bash", "wget https://example.com/a.jpg", D),
    ("Bash", 'bash -c "curl -s https://example.com"', D),
    ("Bash", f"python -I -X utf8 {OWN}", D),
    ("Bash", f"python -I -X utf8 {MIXED}", D),
    ("Bash", f"python3 -I {GITHUB} .", A),
    ("Bash", f"python3 -I {os.path.join(SKILL, 'tools', 'version.py')} .", A),
    ("Bash", 'curl -s "https://www.portafontium.eu/register/soap-pn?q=Plaňany"', D),
    ("Bash", "curl -s https://family-tree.example.net/", D),
    ("Bash", "curl -s https://search.arch.be/en/zoeken-naar-personen", D),
    ("Monitor", "while true; do curl -s https://example.com/status; sleep 1; done", D),
    ("Bash", "sh -c 'wget https://example.cz/a.jpg'", D),
    ("Bash", 'python3 -c "import json, urllib.request; print(1)"', D),
    ("Bash", "python3 -c 'import os; import requests'", D),
    ("Bash", 'python3 -c "import json; print(42)"', A),
    ("Bash", 'echo "import requests" >> work/note.txt', A),
    ("Bash", "python3 - <<'EOF'\nimport os, sys, requests\nEOF", D),
    ("Bash", "python3 - <<'EOF'\nimport json as j, http.client\nEOF", D),
    ("Monitor", "tail -f work/log.txt | grep --line-buffered ERROR", A),
    ("Bash", 'bash -c "python -I -X utf8 tools/check.py"', A),
    ("Bash", "python3 - <<'EOF'\nimport json, os  # no requests here\nEOF", A),
    # Bash – allow (tools brake themselves, the wrapper, localhost, own website)
    ("Bash", 'python -I -X utf8 tools/aron_search.py "Holice"', A),
    ("Bash", 'bash tools/ahmp_search.sh "Švamberk"', A),
    ("Bash", "./tools/ahmp_search.sh Holice", A),
    ("Bash", 'cd work && python -I -X utf8 ../tools/kramerius.py "Švamberk" 1', A),
    ("Bash", "timeout 60 python -I -X utf8 tools/places.py", A),
    ("Bash", f"python -I -X utf8 {BATCH}", A),
    ("Bash", f"python -I -X utf8 tools/polite.py {OWN}", A),
    ("Bash", "python -I -X utf8 tools/polite.py - <<'EOF'\nimport urllib.request\nEOF", A),
    ("Bash", 'python -I -X utf8 tools/polite.py bash tools/ahmp_search.sh "Plaňany"', A),
    ("Bash", "python -I -X utf8 tools/polite.py curl -s https://example.com", A),
    ("Bash", "curl -s https://my-family.netlify.app/", A),
    ("Bash", "curl -s http://localhost:4321/", A),
    ("Bash", "curl --version", A),
    ("Bash", "python -I -X utf8 tools/write.py records key work/x.json", A),
    ("Bash", "python -I -X utf8 tools/check.py", A),
    ("Bash", "python -I -X utf8 tools/export_web.py", A),
    ("Bash", "grep -n urllib tools/aron_img.py && cat tools/ahmp_search.sh", A),
    ("Bash", "git commit -m \"$(cat <<'EOF'\nUse curl https://x.cz and python tools/aron_img.py, it's fine\nEOF\n)\"", A),
    ("Bash", "python -I -X utf8 - <<'EOF'\nimport json\nprint(json.dumps({}))\nEOF", A),
    ("Bash", "python3 - <<'EOF'\ns = open('x.py').read().replace(\"import http.client\", \"import http.client, ssl\")\nEOF", A),
    ("Bash", "python3 - <<'EOF'\nimport os; import http.client\nEOF", D),
    ("Bash", "cd web && npm run data", A),
    ("Bash", 'echo "curl https://example.com" >> work/note.txt', A),
    ("Bash", 'echo "Plaňany, Všeruby, Dolní Bělá" > work/x.txt', A),
    ("Bash", "python -m http.server 8000", A),
    ("Bash", "gh api repos/petrnetusil/genealogy-skill/commits --jq '.[0].sha'", A),
    ("Bash", "magick x.jpg -resize 50% y.jpg 2>&1 && python -I -X utf8 tools/crop.py a.jpg key 0,0,1,1", A),
    # PowerShell – deny
    ("PowerShell", "Invoke-WebRequest https://aron.vychodoceskearchivy.cz/api/aron -OutFile x.json", D),
    ("PowerShell", "iwr $url -OutFile x.jpg", D),
    ("PowerShell", "curl.exe -s https://example.com", D),
    ("PowerShell", '(New-Object System.Net.WebClient).DownloadString("https://example.com")', D),
    ("PowerShell", '1..3 | ForEach-Object { Invoke-RestMethod "https://example.cz/api?p=$_" }', D),
    ("PowerShell", "@'\nimport urllib.request\nprint(1)\n'@ | python -I -X utf8 -", D),
    ("PowerShell", 'Invoke-WebRequest "https://www.portafontium.eu/?q=Plaňany"', D),
    ("PowerShell", f"python -I -X utf8 {OWN}", D),
    # PowerShell – allow
    ("PowerShell", 'python -I -X utf8 tools\\aron_search.py "Holice"', A),
    ("PowerShell", 'bash tools/ahmp_search.sh "Holice"', A),
    ("PowerShell", '& "C:\\Program Files\\Git\\bin\\bash.exe" tools/matricula_dl.sh "https://img.data.matricula-online.eu/x" x.jpg', A),
    ("PowerShell", 'python -I -X utf8 tools/polite.py tools\\aron_search.py "Holice"', A),
    ("PowerShell", "python -I -X utf8 tools/polite.py curl -s https://example.com", A),
    ("PowerShell", 'python -I -X utf8 tools/polite.py bash tools/ahmp_search.sh "Holice"', A),
    ("PowerShell", "Invoke-WebRequest http://localhost:4321/ -UseBasicParsing", A),
    ("PowerShell", "Get-Content tools\\aron_img.py | Select-String urllib", A),
    ("PowerShell", "python -I -X utf8 tools\\check.py", A),
    ("PowerShell", "@'\nimport json\n'@ | python -I -X utf8 -", A),
    ("PowerShell", "git log --oneline -3", A),
    ("PowerShell", "Invoke-WebRequest https://my-family.netlify.app/ -UseBasicParsing", A),
    ("PowerShell", "python -m http.server 8000", A),
    ("PowerShell", "git commit -m 'Use curl https://x.cz'", A),
]

all_ok = True
for shell, argv in SHELLS.items():
    right, errors = 0, []
    for tool, command, expected in CASES:
        data = json.dumps({"tool_name": tool, "tool_input": {"command": command}, "cwd": SKILL,
                           "hook_event_name": "PreToolUse"}, ensure_ascii=False).encode("utf-8")
        r = subprocess.run(argv, input=data, capture_output=True, env={**os.environ, "CLAUDE_PROJECT_DIR": SKILL})
        try:
            out, utf8 = r.stdout.decode("utf-8"), True
        except UnicodeDecodeError:
            out, utf8 = r.stdout.decode("cp1250", "replace"), False
        try:
            decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "allow"
        except (ValueError, KeyError):
            decision = "?"
        result = D if decision == "deny" else A
        ok = result == expected and (utf8 or result == A) and r.returncode in (0, 2)
        right += ok
        if not ok:
            notes = [f"code {r.returncode}"] if r.returncode not in (0, 2) else []
            if not utf8:
                notes.append("answer is not UTF-8")
            errors.append(f"  [FAIL] {tool:10} expected {expected}, got {result}: {command.splitlines()[0][:70]}"
                          + (f"  ({'; '.join(notes)})" if notes else ""))
    all_ok &= right == len(CASES)
    print(f"== guard via {shell}: {right} of {len(CASES)} right")
    print("\n".join(errors))
if not SHELLS:
    print("Found neither bash nor pwsh – nothing tested.")
sys.exit(0 if all_ok and SHELLS else 1)
