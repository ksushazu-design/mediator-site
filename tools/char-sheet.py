#!/usr/bin/env python3
"""Сравнительный лист вариантов образа медиатора: 3 колонки на 2 ряда, подписи снизу."""
import os, glob
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "img", "characters")
CREAM = (251, 242, 224, 255)
INK = (43, 42, 40, 255)
LABELS = {
    "char-01-woman": "1. Женщина",
    "char-02-dove": "2. Птица",
    "char-03-guy": "3. Парень",
    "char-04-bridge": "4. Мостик",
    "char-05-colorful-monk": "5. Яркий монах",
    "char-06-cartoon": "6. Мультяшный",
}
FONT_DIR = os.path.join(HERE, "..", "..", "telegram-assets", "fonts")


def font(size):
    for pat in ("Nunito*Bold*.ttf", "Nunito*.ttf", "*.ttf"):
        found = sorted(glob.glob(os.path.join(FONT_DIR, "**", pat), recursive=True))
        if found:
            return ImageFont.truetype(found[0], size)
    return ImageFont.load_default()


def cell(path, size=700, pad=40, label=""):
    tile = Image.new("RGBA", (size, size), CREAM)
    if os.path.exists(path):
        im = Image.open(path).convert("RGBA")
        box = size - pad * 2 - 70
        im.thumbnail((box, box), Image.LANCZOS)
        tile.alpha_composite(im, ((size - im.width) // 2, pad + (box - im.height) // 2))
    d = ImageDraw.Draw(tile)
    f = font(38)
    w = d.textbbox((0, 0), label, font=f)[2]
    d.text(((size - w) // 2, size - 78), label, font=f, fill=INK)
    return tile


if __name__ == "__main__":
    names = list(LABELS)
    sheet = Image.new("RGBA", (2100, 1400), CREAM)
    for i, name in enumerate(names):
        tile = cell(os.path.join(SRC, name + ".png"), label=LABELS[name])
        sheet.alpha_composite(tile, ((i % 3) * 700, (i // 3) * 700))
    d = ImageDraw.Draw(sheet)
    for x in (700, 1400):
        d.line([(x, 20), (x, 1380)], fill=(43, 42, 40, 40), width=2)
    d.line([(20, 700), (2080, 700)], fill=(43, 42, 40, 40), width=2)
    out = os.path.join(SRC, "characters-sheet.png")
    sheet.convert("RGB").save(out, optimize=True)
    print("ok", os.path.normpath(out), os.path.getsize(out) // 1024, "KB")
