#!/usr/bin/env python3
"""Стикер-иллюстрация для истории в стиле сайта (gpt-image-1, палитра и обводка как у остальных).

Использование из корня репозитория:
  OPENAI_API_KEY=... python3 tools/gen-illu.py <имя> "<сцена по-английски>"
Пример:
  python3 tools/gen-illu.py illu-08 "Two friends sitting on a bench, one looks away hurt, the other holds out a phone with a message"
Результат: img/<имя>.png, 900x900, прозрачный фон, около 150 КБ.
Если на macOS ругается на SSL: export SSL_CERT_FILE=$(python3 -m certifi)
"""
import base64, io, json, os, sys, urllib.request
from PIL import Image, ImageChops

STYLE = ("Die-cut sticker style flat vector illustration, isolated on a fully transparent background: "
         "the PNG alpha channel must be empty everywhere except the sticker itself. "
         "The whole group of characters is enclosed by ONE thick warm-cream #FAF8F5 die-cut sticker outline, like a physical sticker. "
         "NO backdrop, NO background color, NO glow, NO vignette, NO floor shadow outside the sticker. "
         "Modern editorial tech-illustration style: thin dark ink outlines, simple rounded characters with minimal faces "
         "(dot eyes, tiny line mouth), flat color fills, no gradients, absolutely no text. "
         "Strict palette: warm cream #FAF8F5, sage green #7A9E7E, light sage #A8C4AB, muted clay terracotta #C4916E, "
         "warm dark charcoal #1A1918 for outlines and hair. ")


def generate(scene, key):
    body = json.dumps({"model": "gpt-image-1", "prompt": STYLE + scene, "size": "1024x1024", "quality": "medium",
                       "background": "transparent", "output_format": "png", "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    return base64.b64decode(data["data"][0]["b64_json"])


def clean(png_bytes):
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    a = im.getchannel("A"); lum = im.convert("L")
    partial = a.point(lambda v: 255 if 0 < v < 255 else 0)
    dark = lum.point(lambda v: 255 if v < 150 else 0)
    a2 = ImageChops.subtract(a, ImageChops.multiply(partial, dark)).point(lambda v: 0 if v < 40 else v)
    im.putalpha(a2)
    im = im.crop(im.getbbox())
    w, h = im.size; side = int(max(w, h) / 0.88)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2))
    canvas = canvas.resize((900, 900), Image.LANCZOS)
    return canvas.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("Нужна переменная OPENAI_API_KEY")
    name, scene = sys.argv[1], sys.argv[2]
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "img", name + ".png")
    clean(generate(scene, key)).save(out, optimize=True)
    print("ok", os.path.normpath(out), os.path.getsize(out) // 1024, "KB")
