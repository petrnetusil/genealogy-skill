"""Test of the command portafontium.py village (books by village) – offline on saved result pages of the portal.

From the repository root:
  python3 -I tests/portafontium/test_village.py skills/genealogy/tools
Does not go to the archive: get() is replaced by saved excerpts of pages (search_*.html, state of 5 Nov 2026).
"""
import contextlib, io, os, sys

TOOLS = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import portafontium as pf  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'OK ' if ok else 'FAIL'}] {name}{'' if ok else '  ' + str(detail)[:600]}", flush=True)


def page(n):
    return open(os.path.join(HERE, n), encoding="utf-8").read()


URLS = []


def fake_get(url, binary=False):
    URLS.append(url)
    if "Bu%C4%8D%C3%AD" in url:
        return page("search_buci.html")
    if "Kdyn%C4%9B" in url:
        # page 1 links to the next one, page 2 (page=1) no longer does – any other saved page without the link will do
        return page("search_buci.html") if "page=1" in url else page("search_kdyne_0.html")
    return "<table></table>"


pf.get = fake_get

# Bučí: books of two parishes – Dolní Bělá (until 1787) and Krašovice (from 1787)
books = pf.village("Bučí")
check("search URL has the Czech name encoded", any("search_api_views_fulltext_1=Bu%C4%8D%C3%AD" in u for u in URLS), URLS)
slugs = [k for k, _ in books]
check("finds 28 books", len(books) == 28, len(books))
check("finds books of the parish Krašovice", "krasovice-01" in slugs, slugs)
check("finds older books of the parish Dolní Bělá", any(s.startswith("dolni-bela-") for s in slugs), slugs)

out = io.StringIO()
with contextlib.redirect_stdout(out):
    pf.print_village(books)
t = out.getvalue()
check("output grouped by parish – heading Krašovice with the parish URL part", "Krašovice (parish krasovice)" in t, t[:800])
check("output grouped by parish – heading Dolní Bělá", "Dolní Bělá (parish dolni-bela)" in t, t[:800])
line = next((r for r in t.splitlines() if r.strip().startswith("krasovice-01 ")), "")
check("book line: book | villages | years and kinds", "Bučí" in line and "1787-1828 *" in line, line)
check("the archive is not repeated in the line", "státní archiv" not in line, line)
kr = [r.split()[0] for r in t.split("Krašovice (parish krasovice)")[1].split("\n\n")[0].splitlines()[1:] if r.strip()]
check("books of the parish sorted by start year", kr.index("krasovice-01") < kr.index("krasovice-15"), kr)
check("warning about similar villages and villages of the same name", "same name" in t, t[-400:])

# paging by 40: goes through the next page too
URLS.clear()
books = pf.village("Kdyně")
check("paging: loads page=1 too", any("page=1" in u for u in URLS), URLS)
check("paging: books from both pages", len(books) > 40, len(books))

# nothing found
check("a village without results returns an empty list", pf.village("Neexistujici") == [])

print(f"\n{sum(results)} of {len(results)} right")
sys.exit(0 if all(results) else 1)
