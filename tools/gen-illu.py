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
from PIL import Image, ImageChops, ImageFilter

STYLE = ("Die-cut sticker style flat vector illustration, isolated on a fully transparent background: "
         "the PNG alpha channel must be empty everywhere except the sticker itself. "
         "The whole group of characters is enclosed by ONE thick warm-cream #FAF8F5 die-cut sticker outline, like a physical sticker. "
         "NO backdrop, NO background color, NO glow, NO vignette, NO floor shadow outside the sticker. "
         "Modern editorial tech-illustration style: thin dark ink outlines, simple rounded characters with minimal faces "
         "(dot eyes, tiny line mouth), flat color fills, no gradients, absolutely no text. "
         "Strict palette: warm cream #FAF8F5, sage green #7A9E7E, light sage #A8C4AB, muted clay terracotta #C4916E, "
         "warm dark charcoal #1A1918 for outlines and hair. "
         "Crisp uniform ink outlines of equal thickness everywhere. Same character design across the whole series: "
         "simple rounded people with dot eyes, tiny line mouths, small noses, sage or terracotta clothes. ")


def generate(scene, key, size="1024x1024", quality="high"):
    body = json.dumps({"model": "gpt-image-1", "prompt": STYLE + scene, "size": size, "quality": quality,
                       "background": "transparent", "output_format": "png", "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    return base64.b64decode(data["data"][0]["b64_json"])


def clean(png_bytes, ratio=1.0, width=900):
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    # модель рисует "фактуру" полупрозрачными точками в альфа-канале: делаем внутренность стикера
    # непрозрачной (мягкий край сохраняем) и сглаживаем заливки, одинаково для всей серии
    a = im.getchannel("A")
    solid = a.point(lambda v: 255 if v >= 110 else 0).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    rgb = im.convert("RGB").filter(ImageFilter.MedianFilter(7))
    im = Image.merge("RGBA", (*rgb.split(), solid))
    a = im.getchannel("A"); lum = im.convert("L")
    partial = a.point(lambda v: 255 if 0 < v < 255 else 0)
    dark = lum.point(lambda v: 255 if v < 150 else 0)
    a2 = ImageChops.subtract(a, ImageChops.multiply(partial, dark)).point(lambda v: 0 if v < 40 else v)
    im.putalpha(a2)
    im = im.crop(im.getbbox())
    w, h = im.size
    cw = int(max(w, h * ratio) / 0.88); ch = int(cw / ratio)
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    canvas.paste(im, ((cw - w) // 2, (ch - h) // 2))
    canvas = canvas.resize((width, int(width / ratio)), Image.LANCZOS)
    return canvas.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("Нужна переменная OPENAI_API_KEY")
    name, scene = sys.argv[1], sys.argv[2]
    landscape = "--landscape" in sys.argv
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "img", name + ".png")
    if landscape:
        img = clean(generate(scene, key, size="1536x1024"), ratio=1400 / 959, width=1400)
    else:
        img = clean(generate(scene, key))
    img.save(out, optimize=True)
    print("ok", os.path.normpath(out), os.path.getsize(out) // 1024, "KB")
