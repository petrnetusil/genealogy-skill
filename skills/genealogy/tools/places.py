#!/usr/bin/env python3
"""Ancestors' places for the map on the website (data/places.json).

Usage:
  places.py add "Name" ["regular expression"] ["search query"]
      adds a place; the expression is searched for in people's facts (default = the first 5 letters of the name, so
      that inflected forms match too); the query for OpenStreetMap (default = "Name, <country>" with the country from
      data/website.json "country", otherwise just "Name"; when nothing is found, it retries without the country);
      enter a historical part of a village that the map does not know as the whole village; for ambiguous names
      (Podolí, Dub, Sint-Martens…) add a neighbouring place: "Podolí, Odlochovice" – and always check the district
      in the listing
  places.py
      looks up coordinates of places that do not have them yet (OpenStreetMap Nominatim, 1 query per second)
      and prints the list. If a point is wrong, fix lat/lon in data/places.json by hand.

Searches only settlements (featuretype=settlement); if it finds none, it takes anything and below the list writes
"WARNING: not a settlement" (a bar, street, island, nature reserve). It also warns below the list about a new point
farther than FAR_KM from all other places – probably another place of the same name. Emigrants (Chicago, Vienna)
get the warning too, only once when added; just check the address.

An entry may have "hypothesis": true and "line": <Ahnentafel 8–15> – then it shows on the map as a hypothesis
without people.
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request
if sys.argv[1:2] in (["-h"], ["--help"]):   # help instead of a crash
    sys.exit(__doc__.strip())
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402,F401 – network brake against being blocked (shared rate limit, tools/polite.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output even on Windows without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "places.json")
WEBSITE = os.path.join(ROOT, "data", "website.json")


FAR_KM = 50   # a new point farther than this from all other places of the project = probably another place of that name


def country():
    """Default country for queries: data/website.json "country" (e.g. "Belgium", "Česko"), or none."""
    try:
        c = json.load(open(WEBSITE, encoding="utf-8-sig")).get("country", "")
    except (OSError, ValueError, AttributeError):
        return ""
    return c.strip() if isinstance(c, str) else ""


def default_query(name):
    c = country()
    return f"{name}, {c}" if c else name


def nominatim(par):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(par)
    req = urllib.request.Request(url, headers={"User-Agent": "genealogy-skill/1.0 (family genealogy map, occasional geocoding)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)
    time.sleep(1.1)
    return res


SETTLEMENTS = {"city", "town", "village", "hamlet", "suburb", "quarter", "neighbourhood", "isolated_dwelling", "farm",
               "municipality", "borough", "cadastral_community"}   # types in class place; from boundary only administrative
# place=locality is missing on purpose: in OSM it is a named uninhabited place (field, area), not a settlement


def is_settlement(r):
    if r.get("class") == "place":
        return r.get("type") in SETTLEMENTS
    if (r.get("class"), r.get("type")) != ("boundary", "administrative"):
        return False
    if r.get("addresstype"):   # a municipality has "municipality", "village"…; a region "state", a district "county"
        return r["addresstype"] in SETTLEMENTS | {"city_district"}
    return int(r.get("place_rank") or 0) >= 16


def pick(res):
    """The first settlement as (result, True); without a settlement the first result (bar, island…) with False."""
    found = [r for r in res if is_settlement(r)]
    return (found[0], True) if found else (res[0], False) if res else None


def geocode(q):
    """(lat, lon, OSM address, is_settlement); settlements first (featuretype=settlement), if none, anything."""
    hit = None
    for only in ({"featuretype": "settlement"}, {}):
        par = {"q": q, "format": "json", "limit": 5} | only
        v = pick(nominatim(par))
        if v and v[1]:
            hit = v
            break
        hit = hit or v
    return (round(float(hit[0]["lat"]), 4), round(float(hit[0]["lon"]), 4), hit[0]["display_name"], hit[1]) if hit else None


def distance_km(a, b):
    """Great-circle distance of two points (lat, lon) in km (haversine)."""
    (f1, l1), (f2, l2) = [(math.radians(x), math.radians(y)) for x, y in (a, b)]
    h = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin((l2 - l1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def point(e):
    """(lat, lon) as numbers, or None when coordinates are missing, unreadable or out of range ("50.1" passes)."""
    try:
        lat, lon = float(e["lat"]), float(e["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None   # NaN and infinity fail the range too


def nearest(name, cache):
    """(km, name) of the nearest other place with usable coordinates, or None."""
    a = point(cache[name])
    d = [(distance_km(a, b), n) for n, o in cache.items() if n != name and (b := point(o))] if a else []
    return min(d) if d else None


def main():
    cache = json.load(open(OUT, encoding="utf-8-sig")) if os.path.exists(OUT) else {}
    if len(sys.argv) > 2 and sys.argv[1] == "add":
        name = sys.argv[2]
        stem = re.escape(name.split()[0][:5]) if len(name.split()) == 1 else re.escape(name)
        old = cache.get(name, {})
        query = sys.argv[4] if len(sys.argv) > 4 else old.get("query", default_query(name))
        cache[name] = dict(old, re=sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else old.get("re", stem),
                           query=query)
        if "lat" in old and query != old.get("query", default_query(name)):   # another query = a fix of the place → search again
            for k in ("lat", "lon", "osm"):
                cache[name].pop(k, None)
            print(f"recomputing: {name} (new query \"{query}\")")
    warnings, new = [], []   # warnings are printed below the list so they do not get lost in it
    for name, e in cache.items():
        if "lat" not in e:
            q = e.get("query") or default_query(name)
            g = geocode(q)
            if not g and q == default_query(name) and q != name:   # default query with a country: try without it
                g = geocode(name)
                if g:
                    warnings.append(f"OUTSIDE {country().upper()}: {name} → {g[2][:80]} – check that it is the right one")
            if g:
                e["lat"], e["lon"], e["osm"] = g[:3]
                if not g[3]:
                    warnings.append(f"WARNING: not a settlement – check: {name} → {g[2][:80]}")
                new.append(name)
            else:
                warnings.append(f"NOT FOUND: {name} – change 'query' or add lat/lon by hand")
    for name in new:   # only after the whole batch, so the order of places does not matter
        n = nearest(name, cache)
        if n and n[0] > FAR_KM:
            warnings.append(f"WARNING: {name} is {n[0]:.0f} km from the nearest place ({n[1]}) – is it the right one? "
                            f"{cache[name]['osm'][:80]}")
    json.dump(cache, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    for n, e in cache.items():
        print(f"{n:28} {str(e.get('lat', '?')):>8} {str(e.get('lon', '?')):>8}  matches \"{e.get('re')}\"  {e.get('osm', '')[:60]}")
    for w in warnings:
        print(w)


if __name__ == "__main__":
    main()
