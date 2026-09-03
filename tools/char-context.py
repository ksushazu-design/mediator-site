#!/usr/bin/env python3
"""Примерка образа в композицию главной: два пузыря ссоры сверху, новый персонаж снизу.

  python3 tools/char-context.py char-01-woman char-02-dove
"""
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "img")
SRC = os.path.join(IMG, "characters")
CREAM = (251, 242, 224, 255)


def bubbles():
    """Верхняя часть текущего героя: два круга со ссорящимися."""
    hero = Image.open(os.path.join(IMG, "illu-hero.png")).convert("RGBA")
    w, h = hero.size
    return hero.crop((0, 0, w, int(h * 0.46)))


def panel(name, size=900):
    tile = Image.new("RGBA", (size, size), CREAM)
    top = bubbles()
    top.thumbnail((int(size * 0.92), int(size * 0.46)), Image.LANCZOS)
    tile.alpha_composite(top, ((size - top.width) // 2, int(size * 0.04)))
    ch = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    ch.thumbnail((int(size * 0.52), int(size * 0.52)), Image.LANCZOS)
    tile.alpha_composite(ch, ((size - ch.width) // 2, int(size * 0.46)))
    return tile


if __name__ == "__main__":
    names = sys.argv[1:] or ["char-01-woman", "char-02-dove"]
    sheet = Image.new("RGBA", (900 * len(names), 900), CREAM)
    for i, n in enumerate(names):
        sheet.alpha_composite(panel(n), (900 * i, 0))
    out = os.path.join(SRC, "characters-in-context.png")
    sheet.convert("RGB").save(out, optimize=True)
    print("ok", os.path.normpath(out), os.path.getsize(out) // 1024, "KB")
