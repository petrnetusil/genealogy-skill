#!/usr/bin/env python3
"""The user's consent to the terms of portals with sensitive data on victims and prisoners (holocaust_victims.py,
arolsen.py, persecuted.py).

These portals ask on entry to confirm their terms (personal responsibility for handling data on victims). A tool has
no browser, so without this module it would skip the confirmation. Therefore a tool downloads nothing without recorded
consent and exits with code 4. Only the user may record the consent: the `consent` command of the respective tool shows
the text and requires the answer "yes" typed by hand in the terminal. Claude does not run it and never confirms it on
the user's behalf (in Claude Code the user runs it with the prefix `!`).

NOTE: this is a safeguard against accidents, not technical protection – anyone who may write to the home folder can
write the state file (or redirect CONSENT_STATE). That Claude does not confirm the consent is held by a rule, not by code.

Consent is valid for 30 days on this computer and only for the given wording of the terms (if it changes, it asks again).
State: ~/.cache/genealogy_consent/<portal>.json (Windows %LOCALAPPDATA%\\genealogy_consent), only a small JSON file.
`python3 -I tools/consent.py status` lists which consents are valid.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), code unchanged apart from translation.
Originally taken over and adapted from a fork (MIT licence, © srameko):
  https://github.com/srameko/rodokmen-skill/blob/5f25edb9a201f8ac03b79293bbcb79b5109d022e/skills/rodokmen/tools/souhlas.py
"""
import hashlib, json, os, sys, time

VALIDITY = 30 * 24 * 3600
EXIT_CODE = 4


def _folder():
    return os.environ.get("CONSENT_STATE") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache"), "genealogy_consent")


def _fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def has_consent(key, text):
    try:
        with open(os.path.join(_folder(), key + ".json"), encoding="utf-8") as fh:
            d = json.load(fh)
        return d.get("fingerprint") == _fingerprint(text) and -300 < time.time() - float(d.get("time", 0)) < VALIDITY
    except (OSError, ValueError, TypeError):
        return False


def require(key, name, text, command):
    """Exit (code 4) unless the user has recorded consent. `command` = how to record it (e.g. "tools/arolsen.py consent")."""
    if has_consent(key, text):
        return
    sys.stderr.write(
        f"{name} asks for consent to its terms on entry (sensitive data on victims). The tool downloads nothing without it.\n"
        f"The user must confirm the consent personally: run `python3 -I {command}` in the terminal (in Claude Code with\n"
        "the prefix `!`), read the text and answer \"yes\" by hand. Claude never confirms consent on the user's behalf.\n")
    sys.exit(EXIT_CODE)


def _is_terminal():
    return sys.stdin.isatty() and sys.stdout.isatty()


def confirm(key, name, text, url, command):
    """Show the text and record the consent only when the user answers "yes" by hand in the terminal."""
    if not _is_terminal():
        sys.stderr.write("Consent can only be recorded in an interactive terminal where the user types. Run the command "
                         f"yourself (in Claude Code `!python3 -I {command}`); Claude must not confirm it for you.\n")
        sys.exit(EXIT_CODE)
    print(f"{name} – terms of entry:\n\n{text}\n\nTerms and rules: {url}\n")
    answer = input("Do you agree and take responsibility for handling this data? Type \"yes\": ").strip().lower()
    if answer != "yes":
        print("Consent not recorded.")
        sys.exit(EXIT_CODE)
    os.makedirs(_folder(), exist_ok=True)
    target = os.path.join(_folder(), key + ".json")
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"portal": name, "time": time.time(), "date": time.strftime("%Y-%m-%d"),
                   "fingerprint": _fingerprint(text)}, fh)
    os.replace(tmp, target)
    print(f"Consent recorded (valid for 30 days on this computer): {target}")


def main(a):
    """`consent.py status` – which consents are recorded and until when they are valid (confirmed by the tool's `consent`)."""
    if a != ["status"]:
        sys.exit("Usage: consent.py status   (to record consent: python3 -I tools/<tool>.py consent – only the user personally)")
    try:
        files = sorted(f for f in os.listdir(_folder()) if f.endswith(".json"))
    except OSError:
        files = []
    if not files:
        print("No consent is recorded.")
    for f in files:
        try:
            with open(os.path.join(_folder(), f), encoding="utf-8") as fh:
                d = json.load(fh)
            until = time.strftime("%Y-%m-%d", time.localtime(float(d["time"]) + VALIDITY))
            print(f"{f[:-5]}: {d.get('portal', '?')} – confirmed {d.get('date', '?')}, valid until {until}")
        except (OSError, ValueError, KeyError, TypeError):
            print(f"{f[:-5]}: unreadable record")


if __name__ == "__main__":
    main(sys.argv[1:])
