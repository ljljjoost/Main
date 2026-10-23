"""Baut basemap.json (Wasser, Wald, Straßen, Bahn, Landesgrenze, Ortsnamen) für die Tischler-Karte.

Quelle: Vektorkacheln von OpenFreeMap (OpenMapTiles-Schema, Daten © OpenStreetMap-Mitwirkende).
Aufruf: python3 basemap.py <ordner-für-kacheln> [zoom]
"""
import gzip, json, math, os, sys, time, urllib.request

import mapbox_vector_tile as mvt
from shapely.geometry import box, shape, mapping, LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union, linemerge

W, E, S, N = 9.45, 10.75, 53.30, 53.86
TILES = "https://tiles.openfreemap.org/planet"
UA = {"User-Agent": "tischler-karte-build/1.0"}


def tile_x(lon, z): return int((lon + 180) / 360 * 2 ** z)
def tile_y(lat, z):
    r = math.radians(lat)
    return int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** z)
def lon_of(x, z): return x / 2 ** z * 360 - 180
def lat_of(y, z): return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / 2 ** z))))


def fetch(cache, z):
    tj = json.load(urllib.request.urlopen(urllib.request.Request(TILES, headers=UA), timeout=30))
    url = tj["tiles"][0]
    os.makedirs(cache, exist_ok=True)
    for x in range(tile_x(W, z), tile_x(E, z) + 1):
        for y in range(tile_y(N, z), tile_y(S, z) + 1):
            p = f"{cache}/{z}_{x}_{y}.pbf"
            if not os.path.exists(p):
                req = urllib.request.Request(url.format(z=z, x=x, y=y), headers=UA)
                open(p, "wb").write(urllib.request.urlopen(req, timeout=30).read())
                time.sleep(0.1)
            yield x, y, p


def to_lonlat(geom, x, y, z, extent):
    def conv(c):
        px, py = c[0], c[1]
        return (lon_of(x + px / extent, z), lat_of(y + 1 - py / extent, z))
    g = geom
    t = g["type"]
    if t == "Point": return {"type": t, "coordinates": conv(g["coordinates"])}
    if t in ("LineString",): return {"type": t, "coordinates": [conv(c) for c in g["coordinates"]]}
    if t in ("MultiLineString", "Polygon"): return {"type": t, "coordinates": [[conv(c) for c in r] for r in g["coordinates"]]}
    if t == "MultiPolygon": return {"type": t, "coordinates": [[[conv(c) for c in r] for r in p] for p in g["coordinates"]]}


def main():
    cache = sys.argv[1]
    z = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    polys = {"water": [], "wood": []}
    lines = {"river": [], "motorway": [], "trunk": [], "primary": [], "rail": [], "border": []}
    places = {}
    for x, y, p in fetch(cache, z):
        b = open(p, "rb").read()
        if b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
        tile = mvt.decode(b)
        clip = box(lon_of(x, z), lat_of(y + 1, z), lon_of(x + 1, z), lat_of(y, z))
        for lname, layer in tile.items():
            ext = layer.get("extent", 4096)
            for f in layer["features"]:
                pr, g = f["properties"], f["geometry"]
                cls = pr.get("class")
                target = None
                if lname == "water" and cls in ("lake", "river", "ocean", "dock", "pond"): target = polys["water"]
                elif lname == "landcover" and cls == "wood": target = polys["wood"]
                elif lname == "waterway" and cls == "river": target = lines["river"]
                elif lname == "transportation" and cls in ("motorway", "trunk", "primary"): target = lines[cls]
                elif lname == "transportation" and cls in ("rail", "transit") and pr.get("subclass") in ("rail", "light_rail") and not pr.get("service"): target = lines["rail"]
                elif lname == "boundary" and pr.get("admin_level") == 4 and not pr.get("maritime"): target = lines["border"]
                elif lname == "place" and cls in ("city", "town", "suburb", "village"):
                    name = pr.get("name:de") or pr.get("name")
                    if name:
                        lon, lat = to_lonlat(g, x, y, z, ext)["coordinates"]
                        if W <= lon <= E and S <= lat <= N:
                            places[(name, cls)] = (round(lon, 4), round(lat, 4), cls, pr.get("rank") or 99)
                    continue
                if target is None: continue
                geom = shape(to_lonlat(g, x, y, z, ext)).buffer(0) if g["type"].endswith("Polygon") else shape(to_lonlat(g, x, y, z, ext))
                geom = geom.intersection(clip)
                if not geom.is_empty: target.append(geom)

    out = {"bbox": [W, S, E, N], "z": z}

    def rings(geom, tol, min_area):
        geom = unary_union(geom).simplify(tol, preserve_topology=True)
        parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom] if isinstance(geom, Polygon) else [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]
        res = []
        for pg in parts:
            if pg.area < min_area: continue
            rs = [pg.exterior] + [i for i in pg.interiors if Polygon(i).area >= min_area]
            res.append([[[round(c[1], 4), round(c[0], 4)] for c in r.coords] for r in rs])
        return res

    def paths(geom, tol):
        merged = linemerge(unary_union(geom))
        merged = merged.simplify(tol)
        parts = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
        return [[[round(c[1], 4), round(c[0], 4)] for c in ln.coords] for ln in parts if ln.length > tol * 4]

    out["water"] = rings(polys["water"], 0.0002, 8e-6)
    out["wood"] = rings(polys["wood"], 0.0008, 1.5e-4)
    for k, tol in (("river", 0.0002), ("motorway", 0.0003), ("trunk", 0.0003), ("primary", 0.0006), ("rail", 0.0004), ("border", 0.0003)):
        out[k] = paths(lines[k], tol)
    def delta(path):
        flat, plat, plng = [], 0, 0
        for lat, lng in path:
            a, b = round(lat * 1e4), round(lng * 1e4)
            flat += [a - plat, b - plng]
            plat, plng = a, b
        return flat

    for k in ("water", "wood"):
        out[k] = [[delta(r) for r in poly] for poly in out[k]]
    for k in ("river", "motorway", "trunk", "primary", "rail", "border"):
        out[k] = [delta(pth) for pth in out[k]]
    out["places"] = sorted([[n, lon, lat, cls, rk] for (n, cls), (lon, lat, cls, rk) in places.items()], key=lambda r: (r[3], r[4]))
    s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "basemap.json"), "w").write(s)
    print({k: len(v) for k, v in out.items() if isinstance(v, list)}, len(s) // 1024, "KB")


if __name__ == "__main__":
    main()
