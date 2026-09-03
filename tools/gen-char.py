#!/usr/bin/env python3
"""Варианты образа медиатора: та же плоская вектор-графика, но палитра шире и живее.

  OPENAI_API_KEY=... python3 tools/gen-char.py [номера через пробел]
Результат: img/characters/char-NN-<имя>.png, 900x900, прозрачный фон.
"""
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("genillu", os.path.join(HERE, "gen-illu.py"))
genillu = importlib.util.module_from_spec(spec); spec.loader.exec_module(genillu)

STYLE = (
    "Flat vector editorial illustration in the style of modern tech-startup websites: clean, thin, even black ink "
    "outlines; flat solid color fills; no gradients, no shadows, no sticker outline, no backdrop (fully transparent "
    "PNG). Simplified, slightly exaggerated proportions; expressive but simple faces with open eyes and a small warm "
    "smile. Rich, cheerful palette, use at least four of these on the character itself: sage green #7A9E7E, light "
    "sage #A8C4AB, terracotta #C4703F, amber yellow #E8B04B, dusty blue #6E8CA0, coral #E8836A, cream #FBF2E0, "
    "warm charcoal #1A1918 for outlines and hair. Colorful and lively, not muted. Single character centered, square "
    "composition, generous margin around the figure, visible hands. Absolutely no text or letters. "
)

VARIANTS = {
    1: ("char-01-woman",
        "A warm woman mediator in her thirties with a short dark bob, open eyes and a small genuine smile, wearing an "
        "amber yellow sweater with a sage green collar and dusty blue trousers, sitting cross-legged and holding a cup "
        "of tea with both hands, leaning slightly forward as if listening closely."),
    2: ("char-02-dove",
        "A friendly dove character standing upright on two coral feet, cream body with sage green wing tips and an "
        "amber beak, large expressive open eyes, one wing extended forward as if offering a hand, holding a small "
        "folded paper note in the other wing. Charming and memorable, not babyish."),
    3: ("char-03-guy",
        "A young man mediator with dark wavy hair, warm skin, open eyes and a relaxed smile, wearing a sweater with "
        "wide horizontal stripes in amber yellow, coral and dusty blue, both hands raised in an open calming gesture, "
        "sitting on a simple sage green cushion."),
    4: ("char-04-bridge",
        "An abstract mediator figure built from two large overlapping rounded shapes, one sage green and one "
        "terracotta, that together form one body with a simple friendly face with open eyes, two small cream hands "
        "reaching out to the left and to the right, a solid amber yellow circle behind the head like a halo."),
    5: ("char-05-colorful-monk",
        "A serene bald mediator sitting cross-legged, warm peach skin, open friendly eyes and a soft smile, wearing a "
        "sweater made of color blocks in amber yellow, coral, sage green and dusty blue, one hand raised in a light "
        "welcoming gesture while the other rests on the knee, small decorative dots and short dashes scattered around "
        "the figure."),
    6: ("char-06-cartoon",
        "A round cartoon companion mascot with a slightly oversized head and big expressive eyes, wearing a bright "
        "coral hoodie with amber drawstrings and dusty blue sleeves, waving with one hand and holding a rounded speech "
        "bubble shape in the other, energetic and playful, like a modern app mascot."),
}

if __name__ == "__main__":
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("Нужна переменная OPENAI_API_KEY")
    genillu.STYLE_FLAT = STYLE
    out_dir = os.path.join(HERE, "..", "img", "characters")
    os.makedirs(out_dir, exist_ok=True)
    wanted = [int(a) for a in sys.argv[1:] if a.isdigit()] or sorted(VARIANTS)
    for n in wanted:
        name, scene = VARIANTS[n]
        out = os.path.join(out_dir, name + ".png")
        try:
            img = genillu.clean(genillu.generate(scene, key, quality="medium", style="flat"))
            img.save(out, optimize=True)
            print("ok", name, os.path.getsize(out) // 1024, "KB", flush=True)
        except Exception as e:
            print("fail", name, repr(e)[:160], flush=True)
