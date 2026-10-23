# Kleine Schritte

Ein Arbeitsheft für mutige Experimente gegen soziale Angst: vorher aufschreiben, was du befürchtest, nachher festhalten, was wirklich passiert ist, und beides vergleichen.

Die App liegt im Ordner `docs/` und läuft als Web-App (PWA) direkt im Browser. Alle Einträge bleiben auf dem Gerät.

## Aufs iPhone

1. Link in **Safari** öffnen.
2. Teilen-Symbol → **Zum Home-Bildschirm** → Hinzufügen.

## Veröffentlichen (GitHub Pages)

Repo auf *public* stellen, dann *Settings → Pages → Deploy from a branch*, den Branch wählen, Ordner `/docs`, *Save*.

Nach Änderungen in `docs/sw.js` den Wert `const CACHE = ...` ändern, sonst zeigt das Handy die alte Fassung.

## Tischler-Karte

Unter `docs/tischler/` liegt eine Karte der Tischlereien aus dem Praktikums-Ranking (mit GitHub Pages: `…/tischler/`). Die Zahl im Pin ist der inhaltliche Fit (0–10). Ein Klick öffnet die Karteikarte mit Logo, Website-Vorschau, Kriterien, Praktikum-Status und Kontakt.

Neu bauen, wenn sich die Tabelle ändert:

```
pip install openpyxl
python3 tools/tischler-karte/build.py Tischler-Praktikum_Hamburg_Ranking.xlsx
```

Website-Vorschau und Logos neu holen (braucht Node mit Playwright und Pillow):

```
node tools/tischler-karte/previews.mjs tools/tischler-karte/sites.json roh/
python3 tools/tischler-karte/images.py roh/
python3 tools/tischler-karte/build.py Tischler-Praktikum_Hamburg_Ranking.xlsx
```

`sites.json` schreibt `build.py`. Logos, die die Erkennung falsch greift, stehen in `images.py` unter `WRONG_LOGO`.

Die Grundkarte (`tools/tischler-karte/basemap.json`) erzeugt `basemap.py` aus OpenStreetMap-Vektorkacheln; das ist nur nötig, wenn sich der Kartenausschnitt ändern soll.
