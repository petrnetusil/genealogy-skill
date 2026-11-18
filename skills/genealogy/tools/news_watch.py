#!/usr/bin/env python3
"""News watch: what is new in the archives and in watched repositories since the last run.

Usage:  python3 -I tools/news_watch.py                – compares with the state of the last run, prints only changes
        python3 -I tools/news_watch.py --github-only  – only GitHub (fast, no archive requests)

What it watches – data/watched.json (empty by default; add what you need):
  {
    "github": ["owner/repo", …],
        latest commit of each repository (git ls-remote) – e.g. other genealogy skills whose ideas you follow
    "aron":   {"<search term>": "<why we watch it>", …},
        Czech ARON portal (e.g. SOA Zámrsk): for each search term (village/parish where a book is missing) new
        volumes and volumes that got their scans (scans 0 → n); via tools/aron_search.py and tools/aron_img.py
    "pages":  {"<url>": "<why we watch it>", …}
        any web page (e.g. an archive's "newly digitised" list or a search result): reports when its content changes
  }
Archive requests go through the network brake (tools/polite.py), like every other tool.
The state of the last run is in data/watch_state.json (saved after every run).
"""
import datetime, hashlib, json, os, re, subprocess, sys
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
CFG = os.path.join(ROOT, "data", "watched.json")
STATE = os.path.join(ROOT, "data", "watch_state.json")
EMPTY = {"github": [], "aron": {}, "pages": {}}
STOPPED = 3   # exit code of the network brake when the archive is stopped (tools/polite.py)


def brake_stopped(r):
    return r.returncode == STOPPED or re.search(r"\bstopped\b", r.stderr or "", re.I)


def scans(apu):
    r = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "aron_img.py"), apu, "info"],
                       capture_output=True, text=True, cwd=ROOT)
    if brake_stopped(r):
        sys.exit("polite: ARON is stopped – the watch ends, try again later.")
    m = re.search(r"scans:\s*(\d+)", r.stdout)
    if m:
        return int(m.group(1))
    return 0 if re.search(r"scans: 0|not in ARON|no published images", r.stderr + r.stdout) else None


def page_hash(url):
    r = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "polite.py"), "curl", "-sL", url],
                       capture_output=True, cwd=ROOT)
    if r.returncode == STOPPED:
        sys.exit("polite: the site is stopped – the watch ends, try again later.")
    if r.returncode != 0 or not r.stdout:
        return None
    text = re.sub(rb"\s+", b" ", r.stdout)   # whitespace changes do not count
    return hashlib.sha256(text).hexdigest()[:16]


def main():
    if sys.argv[1:2] in (["-h"], ["--help"]):
        print(__doc__)
        return
    try:
        cfg = dict(EMPTY, **json.load(open(CFG, encoding="utf-8-sig"))) if os.path.exists(CFG) else dict(EMPTY)
    except ValueError as e:
        sys.exit(f"data/watched.json is not valid JSON: {e}")
    if not any(cfg.get(k) for k in EMPTY):
        print("Nothing to watch – data/watched.json is empty or missing. Add GitHub repositories, ARON search terms\n"
              "or web pages (see python3 -I tools/news_watch.py --help).")
        return
    old = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    new = {"date": datetime.date.today().isoformat(), "aron": dict(old.get("aron", {})), "github": {},
           "pages": dict(old.get("pages", {}))}
    changes = []

    for repo in cfg.get("github", []):
        r = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}", "HEAD"], capture_output=True, text=True)
        sha = r.stdout.split()[0][:7] if r.stdout else None
        new["github"][repo] = sha
        if sha and old.get("github", {}).get(repo) not in (None, sha):
            changes.append(f"GitHub {repo}: new commit {old['github'][repo]} → {sha}")
        elif sha and repo not in old.get("github", {}):
            changes.append(f"GitHub {repo}: recorded for the first time ({sha})")
        elif not sha:
            changes.append(f"GitHub {repo}: not reachable (typo, private repository or no network?)")

    if "--github-only" not in sys.argv:
        for term, why in cfg.get("aron", {}).items():
            r = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "aron_search.py"), term],
                               capture_output=True, text=True, cwd=ROOT)
            if brake_stopped(r):
                sys.exit("polite: ARON is stopped – the watch ends, try again later.")
            for line in r.stdout.splitlines():
                parts = line.split(" | ")
                if len(parts) < 2 or not re.match(r"^[0-9a-f-]{36}$", parts[0].strip()):
                    continue
                apu, name = parts[0].strip(), parts[1].strip()
                prev = old.get("aron", {}).get(apu)
                if prev and prev.get("scans"):            # already has scans – no need to check again
                    new["aron"][apu] = prev
                    continue
                s = scans(apu)
                new["aron"][apu] = {"name": name, "term": term, "scans": s}
                if prev is None and old.get("aron"):
                    changes.append(f"ARON [{term}] NEW volume: {name} ({s} scans) – {apu}  ← {why}")
                elif prev is not None and not prev.get("scans") and s:
                    changes.append(f"ARON [{term}] SCANS ADDED ({s}): {name} – {apu}  ← {why}")
        for url, why in cfg.get("pages", {}).items():
            h = page_hash(url)
            prev = old.get("pages", {}).get(url)
            if h is None:
                changes.append(f"Page {url}: could not be read this time  ← {why}")
                continue
            new["pages"][url] = h
            if prev is None:
                changes.append(f"Page {url}: recorded for the first time  ← {why}")
            elif prev != h:
                changes.append(f"Page {url}: CHANGED since the last run  ← {why}")

    with open(STATE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
    print(f"News watch {new['date']} (last run {old.get('date', 'never')}):")
    print("\n".join("  • " + z for z in changes) if changes else "  nothing new.")


if __name__ == "__main__":
    main()
