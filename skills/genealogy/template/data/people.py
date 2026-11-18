# Direct ancestors by Kekulé (Ahnentafel) number: 1 = the root person (the one the family tree is made for),
# the father of person n has number 2n, the mother 2n+1. So 2 = father, 3 = mother, 4–7 grandparents,
# 8–15 great-grandparents …
#
# Each person:  number: dict(n="First Surname", y="1850–1910", st="doc", f=[...], r=[...], note="...")
#   n        name; women under their birth surname ("Anna Dvořáková", "Marie Dubois"), uncertain readings with a
#            question mark ("Marie Peeters (?)")
#   y        years of life for overviews: "* 1931" (living / death unknown), "1850–1910", "c. 1720–1785",
#            "1680 – before 1740"
#   st       evidence status:  doc  = documented in a register (read directly from the image)
#                              prob = probable (details agree, but no direct proof)
#                              fam  = from the family / a family document
#                              mh   = only from someone else's online tree (MyHeritage, Geni, FamilySearch tree…) – unverified
#                              unk  = unknown (just a place in the tree)
#   f        facts as short phrases: "* 12 Mar 1873 Hořice no. 477", "blacksmith", "× 28 Jan 1897 Anna Stejskalová",
#            "† 14 May 1902", "† 3 Jun 1850 Ghent (aged 64)"
#            (* birth/baptism, × marriage, † death/burial – the website uses these symbols to find marriages and map places)
#            Dates: "12 Mar 1873" (day, English 3-letter month, year), "Mar 1873" or "1873"; approximate:
#            "c. 1720", "before 1740", "after 1801", "between 1680 and 1685". House number: "no. 47".
#            A dated milestone ends with the year in brackets: "took over the mill (1873)".
#   r        keys of records in data/records.json that document the person
#   note     research note: why a detail is uncertain, contradictions, where it came from
#   summary  optional short summary for the website (shown as "Research notes"; then `note` folds into details)
#   sex      only for person 1: "M" or "F" (for everyone else it follows from the number: even = male, odd = female)
# Living people: only name and year of birth (privacy), note="Living – basic details only."
# Unknown father of an illegitimate child: dict(n="father unknown", st="unk", f=[], note="…")

P = {
}

# Family lines = eight branches after the great-grandparents (numbers 8–15). Fill them in once known:
# 8: ("Novák", "One sentence on who they were and where they came from – shown on the website with the line."),
LINES = {
}

# Relatives outside the direct line (siblings, uncles…): k = number of the ancestor they belong to.
# Start the text with "Brother of <first name>" / "Sister of <first name>" so the website can work out the relationship.
# dict(k=16, n="Josef Novák (1865–1920)", t="Brother of Jan. Blacksmith in …", r=["record_key"])
SIDE = [
]

# Contradictions and open questions (on the website under "Open questions") as pairs (question, answer). Start the
# answer with "Resolved: …" (hidden on the website), "Hypothesis: …" or "Open: …". It goes on the website – nothing sensitive.
# ("When was Jan Novák born?", "Open: the family says 1850, not found in Holice 1848–1852.")
ISSUES = [
]

# Hypotheses about the origin of a line beyond the documented line (shown on the line's page):
# dict(line=8, title="Hypothesis: the Nováks from Lhota", text="…", items=[("Jan Novák", "godfather 1681…")], records=["key"])
HYPOTHESES = [
]

# An ancestor appearing in the tree more than once (related parents): {alias: main number}, e.g. {350: 140}
SAME = {}
