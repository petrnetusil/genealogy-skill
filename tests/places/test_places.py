"""Tests of tools/places.py (choosing a settlement from the Nominatim answer, warning about a distant point) and of the
hint in the map check of tools/check.py.

From the repository root:
  python3 -I tests/places/test_places.py
  (Windows: python -I -X utf8 tests/places/test_places.py)
Downloads nothing: the Nominatim answers are written into the test, nominatim() is replaced. The check runs in a
temporary project. The country for default queries is set by a temporary data/website.json ("country": "Česko").
"""
import contextlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(REPO, "skills", "genealogy", "tools")
os.environ.setdefault("POLITE_STATE", tempfile.mkdtemp(prefix="places_polite_"))   # the brake does not touch the real state
spec = importlib.util.spec_from_file_location("places", os.path.join(TOOLS, "places.py"))
places = importlib.util.module_from_spec(spec)
spec.loader.exec_module(places)
_site = tempfile.mkdtemp(prefix="places_site_")
places.WEBSITE = os.path.join(_site, "website.json")
json.dump({"country": "Česko"}, open(places.WEBSITE, "w", encoding="utf-8"), ensure_ascii=False)

BAR = {"class": "amenity", "type": "bar", "lat": "50.7741", "lon": "15.0632",
       "display_name": "Andelka;Herna Bar, Letná, Liberec III-Jeřáb, Liberec, okres Liberec, Liberecký kraj, Česko"}
VILLAGE = {"class": "place", "type": "village", "lat": "50.9890", "lon": "15.1076",
           "display_name": "Andělka, Višňová, okres Liberec, Liberecký kraj, Česko"}
MUNI = {"class": "boundary", "type": "administrative", "addresstype": "municipality", "place_rank": 14,
        "lat": "49.9606", "lon": "13.9622",
        "display_name": "Korycany, okres Beroun, Středočeský kraj, Česko"}

results = []


def ok(name, condition, detail=""):
    results.append(bool(condition))
    print(("OK   " if condition else "FAIL "), name, "" if condition else detail)


def run_places(cache, argv, answers):
    """main() in a temporary folder; answers = {query: list of Nominatim results (without featuretype, with settlement)}."""
    d = tempfile.mkdtemp(prefix="places_")
    out = os.path.join(d, "places.json")
    json.dump(cache, open(out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False)
    queries = []

    def nominatim(par):
        queries.append(par)
        settlements = par.get("featuretype") == "settlement"
        return [r for r in answers.get(par["q"], []) if not settlements or r["class"] in ("place", "boundary")]

    original = places.OUT, places.nominatim, sys.argv
    places.OUT, places.nominatim, sys.argv = out, nominatim, ["places.py"] + argv
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            places.main()
    finally:
        places.OUT, places.nominatim, sys.argv = original
    return output.getvalue(), json.load(open(out, encoding="utf-8")), queries


# pick(): the first settlement, otherwise the first result with a flag
ok("pick: skips the bar, takes the village", places.pick([BAR, VILLAGE]) == (VILLAGE, True), places.pick([BAR, VILLAGE]))
ok("pick: boundary is a municipality", places.pick([MUNI]) == (MUNI, True))
ok("pick: only a bar = result with a flag", places.pick([BAR]) == (BAR, False))
ok("pick: nothing = None", places.pick([]) is None)

# distance_km(): Prague – Brno as the crow flies about 185 km
km = places.distance_km((50.0755, 14.4378), (49.1951, 16.6068))
ok("distance_km Prague–Brno", 180 < km < 190, km)
ok("distance_km same point", places.distance_km((50, 15), (50, 15)) < 1e-9)

# nearest(): another place with coordinates, not itself, not places without coordinates
c = {"A": {"lat": 50.0, "lon": 15.0}, "B": {"lat": 50.1, "lon": 15.0}, "C": {"lat": 49.0, "lon": 15.0}, "D": {}}
n = places.nearest("A", c)
ok("nearest: B", n and n[1] == "B" and 10 < n[0] < 12, n)
ok("nearest: a single place = None", places.nearest("A", {"A": {"lat": 50, "lon": 15}, "D": {}}) is None)

# main(): query for settlements, bar refused
output, cache, queries = run_places({"Liberec": {"re": "Libere", "lat": 50.767, "lon": 15.056}},
                                    ["add", "Andělka", "Anděl", "Andělka, Liberec"], {"Andělka, Liberec": [BAR, VILLAGE]})
ok("main: the first query has featuretype=settlement", queries and queries[0].get("featuretype") == "settlement", queries)
ok("main: saves the village, not the bar", cache["Andělka"].get("lat") == 50.989, cache["Andělka"])
ok("main: a village 25 km from Liberec without a warning", "WARNING" not in output, output)

# main(): only a bar → tries without the restriction, saves with a warning
output, cache, queries = run_places({"Liberec": {"re": "Libere", "lat": 50.767, "lon": 15.056}},
                                    ["add", "Andělka", "Anděl", "Andělka, Liberec"], {"Andělka, Liberec": [BAR]})
ok("main: without a settlement the second query has no featuretype", len(queries) == 2 and "featuretype" not in queries[1], queries)
ok("main: bar saved, but reported as not a settlement", "lat" in cache["Andělka"] and "not a settlement" in output, output)

# main(): a point far from the others → warning with the distance and the OSM address
KORYCANY_KM = {"class": "boundary", "type": "administrative", "addresstype": "town", "place_rank": 16,
               "lat": "49.1063", "lon": "17.1645",
               "display_name": "Koryčany, okres Kroměříž, Zlínský kraj, Česko"}
output, cache, _ = run_places({"Beroun": {"re": "Beroun", "lat": 49.9638, "lon": 14.0720}},
                              ["add", "Korycany"], {"Korycany, Česko": [KORYCANY_KM]})
ok("main: a distant place reports km and the district", "WARNING" in output and " km " in output and "Kroměříž" in output, output)
output, cache, _ = run_places({"Beroun": {"re": "Beroun", "lat": 49.9638, "lon": 14.0720}},
                              ["add", "Korycany"], {"Korycany, Česko": [MUNI]})
ok("main: a near place without a warning", "WARNING" not in output, output)
output, cache, _ = run_places({}, ["add", "Korycany"], {"Korycany, Česko": [KORYCANY_KM]})
ok("main: the first place of the project without a warning", "WARNING" not in output, output)

# pick(): an island or a nature reserve is no settlement, a municipal boundary is
ISLAND = {"class": "place", "type": "island", "lat": "50.0", "lon": "15.0", "display_name": "Ostrov, Česko"}
RESERVE = {"class": "boundary", "type": "protected_area", "lat": "50.0", "lon": "15.0", "display_name": "CHKO, Česko"}
ok("pick: island before a village – takes the village", places.pick([ISLAND, VILLAGE]) == (VILLAGE, True),
   places.pick([ISLAND, VILLAGE]))
ok("pick: nature reserve = with a flag", places.pick([RESERVE]) == (RESERVE, False), places.pick([RESERVE]))
ok("pick: hamlet is a settlement", places.pick([dict(VILLAGE, type="hamlet")])[1] is True)

# nearest(): coordinates as text, missing lon, None, nonsense – no crash, unusable places skipped
c = {"A": {"lat": 50.0, "lon": 15.0}, "B": {"lat": "50.1", "lon": "15.0"}, "C": {"lat": 49.0},
     "D": {"lat": None, "lon": None}, "E": {"lat": "?", "lon": 15.0}}
try:
    n = places.nearest("A", c)
except Exception as e:  # noqa: BLE001
    n = e
ok("nearest: text, missing lon, None", isinstance(n, tuple) and n[1] == "B" and 10 < n[0] < 12, n)
try:
    output, cache, _ = run_places({"Beroun": {"lat": "49.9638", "lon": "14.0720"}, "Broken": {"lat": 50.0, "lon": None}},
                                  ["add", "Korycany"], {"Korycany, Česko": [MUNI]})
    ok("main: with broken coordinates of other places the new place is saved", cache["Korycany"].get("lat") == 49.9606, cache)
except Exception as e:  # noqa: BLE001
    ok("main: with broken coordinates of other places the new place is saved", False, repr(e))

# main(): the distance is computed only after the whole batch, independent of the order
A = [{"class": "place", "type": "village", "lat": "50.0", "lon": "15.0", "display_name": "A, Česko"}]
B = [{"class": "place", "type": "village", "lat": "50.009", "lon": "15.0", "display_name": "B, Česko"}]
for order in (("A", "B"), ("B", "A")):
    cache0 = {"C": {"re": "C", "lat": 49.0, "lon": 15.0}, **{x: {"re": x} for x in order}}
    output, _, _ = run_places(cache0, [], {"A, Česko": A, "B, Česko": B})
    ok(f"main: order {'+'.join(order)} – neither A nor B is far (they have each other)", "WARNING" not in output, output)

# pick(): a region or district (boundary/administrative above municipality level) is no settlement
REGION = {"class": "boundary", "type": "administrative", "addresstype": "state", "place_rank": 8,
          "lat": "50.6", "lon": "15.0", "display_name": "Liberecký kraj, Česko"}
DISTRICT = dict(REGION, addresstype="county", place_rank=12, display_name="okres Liberec, Liberecký kraj, Česko")
ok("pick: region before a village – takes the village", places.pick([REGION, VILLAGE]) == (VILLAGE, True),
   places.pick([REGION, VILLAGE]))
ok("pick: only a region = with a flag", places.pick([REGION]) == (REGION, False), places.pick([REGION]))
ok("pick: only a district = with a flag", places.pick([DISTRICT]) == (DISTRICT, False), places.pick([DISTRICT]))
ok("pick: municipal boundary without addresstype, place_rank 16 is a settlement",
   places.pick([{"class": "boundary", "type": "administrative", "place_rank": 16}])[1] is True)
FIELD = {"class": "place", "type": "locality", "lat": "50.0", "lon": "15.0", "display_name": "Na Vinici, Česko"}
ok("pick: named place (locality) before a village – takes the village", places.pick([FIELD, VILLAGE]) == (VILLAGE, True),
   places.pick([FIELD, VILLAGE]))
ok("pick: only locality = with a flag", places.pick([FIELD]) == (FIELD, False), places.pick([FIELD]))

# point(): infinity, NaN and coordinates out of range are unusable; the batch is saved
for bad in ({"lat": "Infinity", "lon": "15"}, {"lat": "NaN", "lon": "15"}, {"lat": 50, "lon": "-inf"},
            {"lat": 91, "lon": 15}, {"lat": 50, "lon": 181}):
    ok(f"point: {bad} = None", places.point(bad) is None, places.point(bad))
try:
    output, cache, _ = run_places({"Beroun": {"lat": 49.9638, "lon": 14.0720}, "Inf": {"lat": "Infinity", "lon": "15"},
                                   "Nan": {"lat": "NaN", "lon": "15"}}, ["add", "Korycany"], {"Korycany, Česko": [MUNI]})
    ok("main: with Infinity/NaN at other places the new place is saved without a warning",
       cache["Korycany"].get("lat") == 49.9606 and "WARNING" not in output, output)
except Exception as e:  # noqa: BLE001
    ok("main: with Infinity/NaN at other places the new place is saved without a warning", False, repr(e))

# check.place_words(): multi-word names after "in/from"
spec = importlib.util.spec_from_file_location("check", os.path.join(TOOLS, "check.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
for fact, wanted in (("in Horní Počernice", "Horní Počernice"), ("from Dolní Břežany", "Dolní Břežany")):
    ok(f"place_words: {fact}", check.place_words([fact]) == [wanted], check.place_words([fact]))

# check.py: for a person without a place it shows the words from the facts that look like a place
d = tempfile.mkdtemp(prefix="check_")
os.makedirs(os.path.join(d, "tools"))
os.makedirs(os.path.join(d, "data"))
shutil.copy(os.path.join(TOOLS, "check.py"), os.path.join(d, "tools"))
with open(os.path.join(d, "data", "people.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write("P = {1: {'n': 'Jan Novák', 'st': 'doc', 'r': ['k'], 'f': ['* 3 May 1850 Přesece no. 4', 'farmer in Nová Ves near Klikov',"
            " '† 1900 Ostrovec']},\n     2: {'n': 'Josef Novák', 'st': 'doc', 'r': ['k'], 'f': ['* 1820 Holice']}}\n")
json.dump({"Holice": {"re": "Holic", "lat": 50.0, "lon": 15.9}, "Přesek": {"re": "Přesek", "lat": 49.0, "lon": 14.8}},
          open(os.path.join(d, "data", "places.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False)
p = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(d, "tools", "check.py")],
                   capture_output=True, text=True, encoding="utf-8")
line = next((l for l in p.stdout.splitlines() if "map:" in l), "")
ok("check: reports person 1 without a place", "1 Jan Novák" in line and "2 Josef" not in line, p.stdout + p.stderr)
ok("check: shows the words Přesece, Nová Ves, Klikov, Ostrovec",
   all(s in line for s in ("Přesece", "Nová Ves", "Klikov", "Ostrovec")), line)
shutil.rmtree(d, ignore_errors=True)
shutil.rmtree(_site, ignore_errors=True)

print(f"\n{sum(results)} of {len(results)} correct")
sys.exit(0 if all(results) else 1)
