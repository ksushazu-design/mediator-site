#!/usr/bin/env python3
"""Листы для приёмки нового набора: общая сетка и сравнение «было и стало»."""
import os, glob
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "img")
NEW = os.path.join(IMG, "rich")
CREAM = (251, 242, 224, 255)
INK = (43, 42, 40, 255)
FONT_DIR = os.path.join(HERE, "..", "..", "telegram-assets", "fonts")
ORDER = ["illu-hero", "illu-01", "illu-07", "illu-cta", "illu-lock", "illu-02", "illu-03", "illu-04",
         "illu-05", "illu-06", "illu-08", "illu-09", "illu-10", "illu-11", "illu-12", "illu-13"]


def font(size):
    f = sorted(glob.glob(os.path.join(FONT_DIR, "**", "Nunito*.ttf"), recursive=True))
    return ImageFont.truetype(f[0], size) if f else ImageFont.load_default()


def tile(path, size, label="", pad=26, lab_h=44):
    t = Image.new("RGBA", (size, size), CREAM)
    if os.path.exists(path):
        im = Image.open(path).convert("RGBA")
        box = size - pad * 2 - lab_h
        im.thumbnail((box, box), Image.LANCZOS)
        t.alpha_composite(im, ((size - im.width) // 2, pad + (box - im.height) // 2))
    if label:
        d = ImageDraw.Draw(t); f = font(26)
        w = d.textbbox((0, 0), label, font=f)[2]
        d.text(((size - w) // 2, size - lab_h - 4), label, font=f, fill=INK)
    return t


def grid(names, cols, size, labels=None):
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * size, rows * size), CREAM)
    for i, n in enumerate(names):
        lab = labels[i] if labels else n.replace("illu-", "")
        sheet.alpha_composite(tile(os.path.join(NEW, n + ".png"), size, lab), ((i % cols) * size, (i // cols) * size))
    return sheet


if __name__ == "__main__":
    sheet = grid(ORDER, 4, 520)
    out1 = os.path.join(NEW, "rich-sheet.png")
    sheet.convert("RGB").save(out1, optimize=True)
    print("ok", os.path.normpath(out1), os.path.getsize(out1) // 1024, "KB")

    pairs = ["illu-hero", "illu-01", "illu-08", "illu-cta"]
    size = 480
    ba = Image.new("RGBA", (size * len(pairs), size * 2), CREAM)
    for i, n in enumerate(pairs):
        ba.alpha_composite(tile(os.path.join(IMG, n + ".png"), size, "было: " + n.replace("illu-", "")), (i * size, 0))
        ba.alpha_composite(tile(os.path.join(NEW, n + ".png"), size, "стало: " + n.replace("illu-", "")), (i * size, size))
    d = ImageDraw.Draw(ba)
    d.line([(10, size), (size * len(pairs) - 10, size)], fill=(43, 42, 40, 50), width=2)
    out2 = os.path.join(NEW, "rich-before-after.png")
    ba.convert("RGB").save(out2, optimize=True)
    print("ok", os.path.normpath(out2), os.path.getsize(out2) // 1024, "KB")
