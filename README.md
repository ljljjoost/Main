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

Unter `docs/tischler/` liegt eine Karte der Tischlereien aus dem Praktikums-Ranking (mit GitHub Pages: `…/tischler/`). Ein Klick auf einen Pin öffnet die Karteikarte des Betriebs mit Fit, Kriterien, Praktikum-Status und Kontakt.

Neu bauen, wenn sich die Tabelle ändert:

```
pip install openpyxl
python3 tools/tischler-karte/build.py Tischler-Praktikum_Hamburg_Ranking.xlsx
```

Die Grundkarte (`tools/tischler-karte/basemap.json`) erzeugt `basemap.py` aus OpenStreetMap-Vektorkacheln; das ist nur nötig, wenn sich der Kartenausschnitt ändern soll.
