#!/usr/bin/env python3
"""Old maps from the ČÚZK archive (Czech Office for Surveying, Mapping and Cadastre, ags.cuzk.gov.cz/archiv) without a
browser: stable cadastre (1820s–1840s), indication sketches, land cadastre.

The ČÚZK archive is a web application on top of ArcGIS services. The token for them is issued by a public ČÚZK service
(just like in the application); the tool obtains it itself and keeps it for an hour in work/.cuzk_token.

Usage (from the project root):
  cuzk_maps.py sheets "Horní Lhota 12" | lat,lon
      which sheets of the stable cadastre cover the place: the cadastral municipality in 1827 (often different from
      today – a small village used to belong to a neighbouring one), the original map (om_SIGN_INV, year of
      re-survey, sheets om_SOUB), the imperial imprint (cio_SIGN_INV) and the indication sketch (S0X = prefix of the
      rasters in the service skici).
  cuzk_maps.py rasters <service> "pattern"
      rasters (sheets) in a service: stable = original maps and imperial imprints (pattern e.g. B2_a_4C_518),
      skici = indication sketches (pattern = S0X without "c|", e.g. BUD286018270), nonstable = others.
      (Service names are the server's Czech names.) Prints id | name | sheet size (in sheet units).
  cuzk_maps.py export <service> <id> <output.jpg> [x0,y0,x1,y1] [width_px]
      a sheet in full resolution or a crop of it. Crop as in crop.py: fractions 0–1 from the top left corner
      (whole sheet = 0,0,1,1; default). Default width 4000 px, max. about 15000. First download the whole sheet
      smaller (width 1500), find the village, then the crop in large size.
  cuzk_maps.py map <layer> "Horní Lhota 12" | lat,lon <output.jpg> [radius_m] [px]
      georeferenced (merged) layer around the place: pk = land cadastre (~1900–1950, in S-JTSK, fits today's
      houses), originalni_mapy (original maps), cisarske_otisky (imperial imprints). Merged layers often do not cover
      small villages (white image) – then sheets + export. Default radius 150 m, 1500 px.
An address is looked up in RÚIAN (the Czech address register) – Czech addresses only; elsewhere give lat,lon.
Be considerate to the server: download only sheets and crops you read. Store the result as a document and continue
with crop.py + data/maps.json.

Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted: network through our brake
tools/polite.py (1 request per 2 s), no retries after an error (project rule), the project's User-Agent.
"""
import json, math, os, sys, time, urllib.parse, urllib.request
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # shared rate limit for archive websites (polite.py)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(os.path.join(ROOT, "data", "STATUS.md")):   # run from the skill folder: no project data there, writes would go into the skill
    sys.exit(f"{os.path.basename(__file__)}: {ROOT} is not a project folder (data/STATUS.md is missing). "
             f"Run the project copy from the project root: python3 -I tools/{os.path.basename(__file__)} …")
REFERER = "https://ags.cuzk.gov.cz/archiv/"
ARCHIV = "https://ags.cuzk.gov.cz/arcgis4/rest/services/Archiv"
GEN = "https://ags.cuzk.gov.cz/arcgis2/rest/services/GenerateToken/Token/GPServer/GenerateToken"
RUIAN = "https://ags.cuzk.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer"
TOKEN = os.path.join(ROOT, "work", ".cuzk_token")


def get(url, params=None, binary=False):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Referer": REFERER, "User-Agent": polite.UA})
    try:   # one attempt – not repeated (the brake watches 429/503 and failed connections itself)
        with urllib.request.urlopen(req, timeout=120) as r:
            d = r.read()
            return d if binary else json.loads(d)
    except OSError as e:
        sys.exit(f"ČÚZK did not answer ({type(e).__name__}: {str(e)[:120]}). Try again later, do not retry in a loop.")


def token():
    if os.path.exists(TOKEN) and time.time() - os.path.getmtime(TOKEN) < 50 * 60:
        return open(TOKEN).read().strip()
    job = get(f"{GEN}/submitJob", {"GenerateTokenURL": "https://ags.cuzk.gov.cz/arcgis4/tokens/", "referer": REFERER,
                                   "parametr": "", "expiration": 60, "f": "json"})["jobId"]
    for _ in range(20):
        time.sleep(1)
        if get(f"{GEN}/jobs/{job}", {"f": "json"}).get("jobStatus") == "esriJobSucceeded":
            break
    else:
        sys.exit("ČÚZK did not issue a token within 20 s – try again in a while")
    t = get(f"{GEN}/jobs/{job}/results/Token", {"f": "json"})["value"]
    os.makedirs(os.path.dirname(TOKEN), exist_ok=True)
    open(TOKEN, "w").write(t)
    return t


def archive(path, params, binary=False):
    d = get(f"{ARCHIV}/{path}", dict(params, token=token()), binary)
    if not binary and "error" in d:
        sys.exit(f"ČÚZK: {d['error']}")
    return d


def save_jpeg(img, out):
    if not img.startswith(b"\xff\xd8"):
        sys.exit("ČÚZK did not return an image: " + img[:300].decode("utf-8", "replace"))
    open(out, "wb").write(img)


def place(m):
    """'lat,lon' or an address for RÚIAN ('Horní Lhota 12') → (lat, lon)."""
    try:
        lat, lon = (float(x) for x in m.split(","))
        return lat, lon
    except ValueError:
        f = get(f"{RUIAN}/1/query", {"where": f"adresa LIKE '{m.replace(chr(39), '')},%'", "outFields": "adresa",
                                     "outSR": 4326, "f": "json"}).get("features", [])
        if not f:
            sys.exit(f"RÚIAN does not know \"{m}\" – give lat,lon (e.g. from data/places.json) or another form of the address")
        print("place:", f[0]["attributes"]["adresa"])
        return f[0]["geometry"]["y"], f[0]["geometry"]["x"]


def sheets(m):
    lat, lon = place(m)
    d = archive("klady/MapServer/identify", {
        "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": 4326, "layers": "all:3",
        "tolerance": 0, "mapExtent": f"{lon - .01},{lat - .01},{lon + .01},{lat + .01}",
        "imageDisplay": "1000,1000,96", "returnGeometry": "false", "f": "json"})
    if not d.get("results"):
        print("stable cadastre: no sheet (try another place)")
    for r in d.get("results", []):
        a = {k: v for k, v in r["attributes"].items() if v and v.strip() and v != "Null"}
        print(f"cadastral municipality 1827: {a.get('NAZ_PUV_CS', '?')} ({a.get('NAZ_PUV_NE', '')})")
        print(f"  original map: {a.get('om_NAZEV_JEDNOTKY', '–')}, ref. {a.get('om_SIGNATURA', '?')}, "
              f"inv. no. {a.get('om_INV_CISLO', '?')}, surveyed {a.get('om_ROZPIS_DAT', '?')}, "
              f"re-survey {a.get('om_REAMBULACE', '–')}")
        print(f"     → rasters stable \"{a.get('om_SIGN_INV', '')}\", sheets {a.get('om_SOUB', '?')}")
        print(f"  imperial imprint: ref. {a.get('cio_SIGNATURA', '?')}, inv. no. {a.get('cio_INV_CISLO', '?')}, "
              f"{a.get('cio_DAT_OD', '?')}, sheets {a.get('cio_LISTU_CELK', '?')} → rasters stable \"{a.get('cio_SIGN_INV', '')}\"")
        s0x = a.get("S0X", "").split("|")[-1]
        print("  indication sketch: " + (f"→ rasters skici \"{s0x}\"" if s0x else "not in the sheet index"))


def rasters(service, pattern):
    d = archive(f"archiv_nespojene_{service}/ImageServer/query", {
        "where": f"Name LIKE '{pattern.replace(chr(39), '')}%'", "outFields": "OBJECTID,Name",
        "returnGeometry": "true", "f": "json"})
    feats = [f for f in d.get("features", []) if f["attributes"]["Name"].startswith(pattern)
             and not f["attributes"]["Name"][len(pattern):len(pattern) + 1].isdigit()]   # 518 ≠ 5180
    for f in feats:
        r = f["geometry"]["rings"][0]
        xs, ys = [p[0] for p in r], [p[1] for p in r]
        print(f"{f['attributes']['OBJECTID']} | {f['attributes']['Name']} | {max(xs) - min(xs):.1f} × {max(ys) - min(ys):.1f}")
    if not feats:
        print("nothing – try a shorter pattern")


def export(service, rid, out, crop="0,0,1,1", width=4000):
    d = archive(f"archiv_nespojene_{service}/ImageServer/query", {"objectIds": rid, "outFields": "OBJECTID",
                                                                "returnGeometry": "true", "f": "json"})
    r = d["features"][0]["geometry"]["rings"][0]
    X0, X1 = min(p[0] for p in r), max(p[0] for p in r)
    Y0, Y1 = min(p[1] for p in r), max(p[1] for p in r)
    a, b, c, e = (float(x) for x in crop.split(","))
    bbox = (X0 + a * (X1 - X0), Y1 - e * (Y1 - Y0), X0 + c * (X1 - X0), Y1 - b * (Y1 - Y0))   # y grows upwards
    width = int(width)
    height = round(width * (bbox[3] - bbox[1]) / (bbox[2] - bbox[0]))
    img = archive(f"archiv_nespojene_{service}/ImageServer/exportImage", {
        "f": "image", "bbox": ",".join(f"{v:.4f}" for v in bbox), "size": f"{width},{height}", "format": "jpg",
        "compressionQuality": 92,
        "mosaicRule": json.dumps({"ascending": True, "lockRasterIds": [int(rid)], "mosaicMethod": "esriMosaicLockRaster"})},
        binary=True)
    save_jpeg(img, out)
    print(f"{out} {width}×{height}")


def map_layer(layer, m, out, radius=150, px=1500):
    lat, lon = place(m)
    dlat = float(radius) / 111320
    dlon = dlat / math.cos(math.radians(lat))
    img = archive(f"archiv_spojene_{layer}/MapServer/export", {
        "bbox": f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}", "bboxSR": 4326, "imageSR": 5514,
        "size": f"{px},{px}", "format": "jpg", "dpi": 96, "f": "image"}, binary=True)
    save_jpeg(img, out)
    print(f"{out} – check that it is not white (the layer may not cover this place)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "sheets":
        sheets(a[1])
    elif len(a) >= 3 and a[0] == "rasters":
        rasters(a[1], a[2])
    elif len(a) >= 4 and a[0] == "export":
        export(*a[1:6])
    elif len(a) >= 4 and a[0] == "map":
        map_layer(*a[1:6])
    else:
        sys.exit(__doc__)
