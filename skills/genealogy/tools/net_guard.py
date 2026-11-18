#!/usr/bin/env python3
"""Network command guard (optional PreToolUse hook in the project's .claude/settings.json).

Switched on by `new_project.py <project> --guard`, off by `--no-guard`.
Before Claude runs a command in Bash or PowerShell, the guard checks whether it goes to an archive website outside
the brake (tools/polite.py): curl/wget with a URL, a Python script with a network import, a shell script with curl,
Invoke-WebRequest and similar in PowerShell. It denies such a command and tells Claude how to run it through the brake.
It downloads nothing and sends nothing anywhere. It is a text heuristic, not bullet-proof protection.
On any error of its own it lets the command through – a broken guard must not block the work.
"""
import json, os, re, sys

CMD = r"(?:^|[;&|(\n`]|\$\(|\b(?:then|do|else|exec|env|time|nohup|xargs|sudo)\s|\b(?:bash|sh|zsh)\s+-c\s+[\"']|\beval\s+[\"']?)\s*"
CURL = re.compile(CMD + r"(curl|wget)(?:\.exe)?(?=\s|$)", re.I)
PYTHON = re.compile(CMD + r"(?:\S*/)?(?:python3?|py)(?:\.exe)?(?:\s+-3)?(?=\s|$)", re.I)
SHELL = re.compile(CMD + r"(?:(?:bash|sh|zsh)\s+|\./)(\S+\.sh)\b")
NET_MOD = r"(?:requests|httpx|aiohttp|urllib3|pycurl|socket|urllib\.request|http\.client)\b"
START = r"(?:^|[;\"'])\s*"   # start of a line, of a command after a semicolon or of code in python -c "…"
BRAKE = "polite.py"          # the wrapper; tools that `import polite` brake themselves


def _net_py(start):
    return re.compile(start + r"from\s+" + NET_MOD +
                      "|" + start + r"import\s+(?:[\w.]+(?:\s+as\s+\w+)?\s*,\s*)*" + NET_MOD +   # also "import json, urllib.request"
                      "|" + start + r"from\s+urllib\s+import\s+.*\brequest\b|urllib\.request\.|urlopen\(", re.M)


NET_PY = _net_py(START)
NET_PY_LINE = _net_py(r"(?:^|;)\s*")   # code in a heredoc: import only at a line start, not "import http.client" in a string
HEREDOC = re.compile(r"<<-?\s*['\"]?\w+|@['\"]\s*\n")   # bash <<EOF, PowerShell @' … '@
PS = re.compile(r"\b(Invoke-WebRequest|Invoke-RestMethod|iwr|irm|curl\.exe|wget|Start-BitsTransfer|Net\.WebClient|"
                r"HttpClient|DownloadString|DownloadFile)\b", re.I)
URL = re.compile(r"https?://([^/\s\"'`:;)]+)", re.I)
EXEMPT = ("localhost", "127.0.0.1", "0.0.0.0", "netlify.app", "netlify.com", "workers.dev", "cloudflare.com", "github.com",
          "githubusercontent.com", "npmjs.org", "pypi.org", "pythonhosted.org")
ADVICE = ("Network access to archive websites only through the brake against being blocked (tools/polite.py), "
          "helpers included:\n"
          "  python3 -I tools/polite.py curl …            instead of curl/wget\n"
          "  python3 -I tools/polite.py work/x.py …       instead of python3 work/x.py (a script using the network)\n"
          "  python3 -I tools/polite.py bash work/x.sh …\n"
          "The tools in tools/ have the brake built in, run them normally. Do not work around the brake (another "
          "command, the browser).")


def exempt(host):
    host = host.lower().rstrip(".")
    return any(host == v or host.endswith("." + v) for v in EXEMPT)


def only_exempt(text):
    hosts = URL.findall(text)
    return bool(hosts) and all(exempt(h) for h in hosts)


def read(path, cwd):
    try:
        with open(os.path.join(cwd, os.path.expanduser(path)), encoding="utf-8", errors="replace") as f:
            return f.read(500_000)
    except OSError:
        return ""


STRING = re.compile(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'')
RUNS_STRING = re.compile(r"(?:-c|\beval)\s*$")
HEREDOC_BODY = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)^\s*\1\s*$", re.S | re.M)
PY_C = re.compile(r"""^((?:\s+-[IuBEsSOqvbdx]+|\s+-X\s+\S+|\s+-W\s+\S+)*)\s+-c\s*("(?:[^"\\]|\\.)*"|'[^']*'|\S+)""")


def without_text(cmd):
    """The command with the content of quoted strings blanked out ('git commit -m "…; curl …"' runs nothing) – except
    strings that really run: after `-c` (bash/sh -c) or `eval`, and double-quoted ones containing `$(…)` or `…`."""
    def replace(m):
        t = m.group(0)
        if RUNS_STRING.search(cmd[:m.start()]) or (t[0] == '"' and ("$(" in t or "`" in t)):
            return t
        return t[0] + " " * (len(t) - 2) + t[-1]
    return STRING.sub(replace, cmd)


def python_code(cmd, pos):
    """Code that Python started at position `pos` really executes: the text after -c (only Python options before it)
    and the bodies of heredocs in the command (also a heredoc the script is only writing – the file does not exist yet)."""
    m = PY_C.match(cmd[pos:])
    return ([m.group(2).strip("\"'")] if m else []), [t for _, t in HEREDOC_BODY.findall(cmd)]


def judge(tool, cmd, cwd):
    """Return the reason for denying, or None (let it through)."""
    if tool == "Monitor":   # runs a command in bash just like Bash
        tool = "Bash"
    if tool == "PowerShell":
        if PS.search(cmd) and BRAKE not in cmd and not only_exempt(cmd):
            return "PowerShell downloads from the web outside the brake"
        tool = "Bash"   # judge python and curl.exe in PowerShell the same way
    if tool != "Bash":
        return None
    bare = without_text(cmd)   # curl/wget/script only where it really runs, not in quoted text
    for m in CURL.finditer(bare):
        rest = re.split(r"[;&|\n]", cmd[m.end():], maxsplit=1)[0]
        if (URL.search(rest) or "$" in rest) and not only_exempt(rest):
            return f"{m.group(1)} straight to the web"
    for m in PYTHON.finditer(cmd):
        rest = re.split(r"[;&|]", cmd[m.end():], maxsplit=1)[0].split()
        args = [a for a in rest if a not in ("-I", "-u", "-X", "utf8", "-B", "-E", "-s")]
        if args and args[0].strip("\"'").endswith(BRAKE):
            continue
        if args and args[0] == "-m":
            continue
        if args and args[0].strip("\"'").endswith(".py"):
            content = read(args[0].strip("\"'"), cwd)
            if "import polite" in content:          # tools in tools/ brake themselves
                continue
            if NET_PY.search(content) and not only_exempt(content):   # network only to exempt sites (version.py → GitHub) passes
                return f"Python script {args[0]} uses the network"
        c_code, heredocs = python_code(cmd, m.end())   # only code Python really runs, not the rest of the command
        if args and args[0] == "-" and not heredocs:   # code through a pipe ("echo … | python -"): judge the whole command
            c_code.append(cmd)
        if any(NET_PY.search(k) and not only_exempt(k) for k in c_code) or \
                any(NET_PY_LINE.search(t) and not only_exempt(t) for t in heredocs):
            return "Python with a network import right in the command"
    for m in SHELL.finditer(bare):
        content = read(m.group(1), cwd)
        if BRAKE not in content and CURL.search(content) and not only_exempt(content):
            return f"shell script {m.group(1)} calls curl/wget"
    return None


def main():
    try:
        if hasattr(sys.stdin, "reconfigure"):   # Claude Code sends UTF-8; on Windows it would be read as cp1250
            sys.stdin.reconfigure(encoding="utf-8-sig")
        data = json.load(sys.stdin)
        tool = data.get("tool_name", "")
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        reason = judge(tool, cmd, data.get("cwd") or os.getcwd())
    except Exception:          # a broken guard lets the command through
        return 0
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": f"Network guard: {reason}.\n{ADVICE}"}}))   # \uXXXX escapes: safe in any code page
    return 0


if __name__ == "__main__":
    sys.exit(main())
