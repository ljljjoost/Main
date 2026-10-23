"""Baut die Tischler-Karte aus der Ranking-Tabelle.

Aufruf: python3 build.py <Tischler-Praktikum_Hamburg_Ranking.xlsx> [fragment.html]

Schreibt docs/tischler/index.html (vollständige Seite für GitHub Pages) und sites.json
(Startseite je Betrieb, Eingabe für previews.mjs). Website-Vorschau und Logo werden eingebunden,
wenn previews.mjs sie unter docs/tischler/img/ abgelegt hat.
Mit zweitem Argument zusätzlich eine Fassung ohne <html>/<head>/<body>-Gerüst (für ein Claude-Artifact).
basemap.json muss vorher mit basemap.py erzeugt worden sein.
"""
import json, os, re, sys, time
from urllib.parse import urlsplit

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "docs", "tischler", "index.html")
IMG = os.path.join(os.path.dirname(OUT), "img")
# Links auf Börsen statt auf die eigene Seite; dann wird die Domain der E-Mail-Adresse genommen.
NOT_OWN_SITE = {"www.lehrstelle-handwerk.de", "lehrstelle-handwerk.de"}
MAIL_HOSTERS = {"web.de", "gmx.de", "gmail.com", "t-online.de", "hamburg.de", "freenet.de", "outlook.de"}

# Spaltenüberschrift (ohne Zeilenumbruch) -> Schlüssel im Seiten-JSON
COLS = {
    "Rang": "r", "Betrieb": "n", "Inhaltl. Fit (0–10)": "fit", "Entfernung Winterhude (km)": "km",
    "Praktikum-Status": "st", "Chance (0–3)": "ch", "Typ": "typ", "Ähnlich wie": "aw", "Stadtteil": "ort",
    "Schwerpunkt": "sp", "Einschätzung": "ein", "Praktikum – Details": "det", "Telefon": "tel",
    "E-Mail": "mail", "Website / Quelle-Link": "web", "Adresse": "adr", "Restaurierung (0–3)": "c0",
    "Entwurf & Möbelbau (0–3)": "c1", "Feinarbeit & Gestaltung (0–2)": "c2", "Hand + Maschine (0–2)": "c3",
    "Quelle(n)": "src", "Breite (OSM)": "lat", "Länge (OSM)": "lng",
}


def slug(name):
    s = name.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return "-".join(re.sub(r"[^a-z0-9]+", "-", s).strip("-").split("-")[:4])


def home_page(d):
    host = urlsplit(d["href"]).netloc if d.get("href") else ""
    if host and host not in NOT_OWN_SITE:
        return "https://" + re.sub(r"^(karriere|jobs)\.", "", host) + "/"
    domain = d.get("mail", "").rpartition("@")[2].lower()
    return f"https://{domain}/" if domain and domain not in MAIL_HOSTERS else None


def read_rows(path):
    ws_f = openpyxl.load_workbook(path)["Ranking"]               # Hyperlinks
    ws_v = openpyxl.load_workbook(path, data_only=True)["Ranking"]  # berechnete Werte
    head = [re.sub(r"\s*\n\s*", " ", str(c.value or "")).strip() for c in ws_v[1]]
    idx = {COLS[h]: i for i, h in enumerate(head) if h in COLS}
    missing = set(COLS.values()) - set(idx)
    if missing:
        sys.exit(f"Spalten fehlen in der Tabelle: {sorted(missing)}")
    rows = []
    for vals, cells in zip(ws_v.iter_rows(min_row=2, values_only=True), ws_f.iter_rows(min_row=2)):
        if not vals[idx["n"]]:
            continue
        d = {k: vals[i] for k, i in idx.items()}
        code, _, label = str(d["st"]).partition("·")
        d["st"], d["stl"] = int(code), label.strip()
        link = cells[idx["web"]].hyperlink
        d["href"] = link.target if link else (("https://" + d["web"]) if d["web"] else None)
        d["c"] = [d.pop(f"c{i}") for i in range(4)]
        if d["aw"] in (None, "–", "-"):
            d["aw"] = None
        d["slug"] = slug(d["n"])
        d["site"] = home_page(d)
        for kind in ("shot", "logo"):
            f = f"{d['slug']}-{kind}.webp"
            if os.path.exists(os.path.join(IMG, f)):
                d[kind] = f"img/{f}"
                d["shotd"] = time.strftime("%d.%m.%Y", time.localtime(os.path.getmtime(os.path.join(IMG, f))))
        rows.append({k: v for k, v in d.items() if v is not None})
    rows.sort(key=lambda d: d["r"])
    return rows


def read_stand(path):
    ws = openpyxl.load_workbook(path, data_only=True)["Legende"]
    for row in ws.iter_rows(max_row=5, values_only=True):
        for v in row:
            m = re.search(r"Stand:\s*([\d.]+)", str(v or ""))
            if m:
                return m.group(1)
    return "–"


def main():
    rows = read_rows(sys.argv[1])
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    css = open(os.path.join(HERE, "vendor", "leaflet-1.9.4.css"), encoding="utf-8").read()
    base = open(os.path.join(HERE, "basemap.json"), encoding="utf-8").read()
    js = lambda s: s.replace("</", "<\\/")
    page = (tpl.replace("/*LEAFLET_CSS*/", css)
               .replace("__STAND__", read_stand(sys.argv[1]))
               .replace("__DATA__", js(json.dumps(rows, ensure_ascii=False, separators=(",", ":"))))
               .replace("__BASEMAP__", js(base)))
    head, body = page.split("<!--/HEAD-->")
    head = head.replace("<!--HEAD-->", "").strip()
    full = ("<!doctype html>\n<html lang=\"de\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            f"{head}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n")
    sites = [{"slug": d["slug"], "url": d["site"]} for d in rows if d.get("site")]
    json.dump(sites, open(os.path.join(HERE, "sites.json"), "w"), indent=1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(full)
    print(f"{len(rows)} Betriebe -> {os.path.normpath(OUT)} ({len(full) // 1024} KB)")
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(head + "\n" + body.strip() + "\n")
        print("Fragment ->", sys.argv[2])


if __name__ == "__main__":
    main()
