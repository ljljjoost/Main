"""Wandelt die Roh-Screenshots von previews.mjs in kleine WebP-Bilder für docs/tischler/img/ um.

Aufruf: python3 images.py <roh-ordner> [kontaktbogen.png]
"""
import glob, os, sys

from PIL import Image, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "..", "docs", "tischler", "img")


# Von der Erkennung gegriffen, aber kein Firmenlogo (Siegel, Fahne, Bildausschnitt)
WRONG_LOGO = {"tiko-moebeltischlerei", "elbdoerfer-glas-und-fensterbau"}
# Die Logo-Datei ist nur das Zeichen, der Ausschnitt zeigt Zeichen und Namen
PREFER_CROP = {"zywietz-gmbh"}


def tile(im):
    """Logo auf eine eigene Fläche setzen: helle Logos auf dunkel, alle anderen auf weiß.
    So bleibt es in hellem wie dunklem Seitenthema lesbar."""
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] < 250:
        im = im.crop(alpha.getbbox())
        r, g, b = ImageStat.Stat(im.convert("RGB"), mask=im.getchannel("A").point(lambda a: 255 if a > 128 else 0)).mean
        lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        bg = (31, 37, 35, 255) if lum > 0.8 else (255, 255, 255, 255)
        im.thumbnail((336, 72), Image.LANCZOS)
        out = Image.new("RGBA", (im.width + 24, im.height + 24), bg)
        out.alpha_composite(im, (12, 12))
        return out.convert("RGB")
    im.thumbnail((360, 96), Image.LANCZOS)  # Ausschnitt der Seite: Hintergrund ist schon dabei
    return im.convert("RGB")


def main():
    raw = sys.argv[1]
    os.makedirs(IMG, exist_ok=True)
    made = []
    for p in sorted(glob.glob(os.path.join(raw, "*.png"))):
        name = os.path.basename(p)[:-4]
        if name.endswith("-logo-crop"):
            continue
        if name.endswith("-logo") and (name[:-5] in PREFER_CROP or not Image.open(p).convert("RGBA").getchannel("A").getbbox()):
            p = p[:-4] + "-crop.png"  # Logo-Datei ließ sich nicht einzeln darstellen
            if not os.path.exists(p):
                continue
        im = Image.open(p).convert("RGB")
        if name.endswith("-shot"):
            im = im.resize((640, 400), Image.LANCZOS)
            im.save(os.path.join(IMG, name + ".webp"), "WEBP", quality=72, method=6)
        else:
            if name[:-5] in WRONG_LOGO:
                continue
            tile(Image.open(p)).save(os.path.join(IMG, name + ".webp"), "WEBP", quality=88, method=6)
        made.append(name)
    print(len(made), "Bilder ->", os.path.normpath(IMG))
    if len(sys.argv) > 2:  # Kontaktbogen zum Durchsehen
        shots = [n for n in made if n.endswith("-shot")]
        cols, w, h = 6, 320, 200
        sheet = Image.new("RGB", (cols * w, ((len(shots) + cols - 1) // cols) * (h + 60)), "white")
        for i, n in enumerate(shots):
            x, y = (i % cols) * w, (i // cols) * (h + 60)
            sheet.paste(Image.open(os.path.join(IMG, n + ".webp")).resize((w - 6, h - 6)), (x + 3, y + 3))
            lp = os.path.join(IMG, n[:-5] + "-logo.webp")
            if os.path.exists(lp):
                lg = Image.open(lp); lg.thumbnail((w - 6, 54)); sheet.paste(lg, (x + 3, y + h + 2))
        sheet.save(sys.argv[2])


if __name__ == "__main__":
    main()
