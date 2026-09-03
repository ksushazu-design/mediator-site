#!/usr/bin/env python3
"""Красочный набор иллюстраций: тот же плоский вектор, но палитра шире, а медиатор с лицом.

  OPENAI_API_KEY=... python3 tools/gen-rich.py [имена без .png]
Результат: img/rich/<имя>.png, 900x900, прозрачный фон. Оригиналы не трогаем.
"""
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("genillu", os.path.join(HERE, "gen-illu.py"))
genillu = importlib.util.module_from_spec(spec); spec.loader.exec_module(genillu)

STYLE = (
    "Flat vector editorial illustration in the style of modern tech-startup websites: clean, thin, even black ink "
    "outlines of uniform thickness; flat solid color fills; no gradients, no shadows, no sticker outline, no backdrop "
    "(fully transparent PNG). Simplified, slightly exaggerated proportions; simple expressive faces with open eyes, "
    "small noses and small line mouths. Warm peach skin. "
    "Cheerful, saturated palette, every scene must use at least four of these colors: sage green #7A9E7E, "
    "light sage #A8C4AB, terracotta #C4703F, amber yellow #E8B04B, dusty blue #6E8CA0, coral #E8836A, "
    "cream #FBF2E0, warm charcoal #1A1918 for outlines and hair. Clothes are color blocks, stripes or two-tone, "
    "never a single flat tone. Scatter a few small decorative dots and short dashes in these colors around the "
    "figures to add life. Colorful and lively, not muted. "
    "Square composition, the whole scene centered with generous margin. Absolutely no text or letters. "
)

MEDIATOR = (
    "The mediator character is a serene bald person with warm peach skin, open friendly eyes and a soft smile, "
    "wearing a sweater made of color blocks in amber yellow, coral, sage green and dusty blue, with small "
    "decorative dots and dashes around them. "
)

SCENES = {
    "illu-hero": MEDIATOR + "In the upper half two large round outlined bubbles side by side: in the left bubble a "
        "woman with a dark bob shouting and pointing a finger, in the right bubble a man with dark hair shouting with "
        "a raised fist, both in colorful striped clothes. Below and between the bubbles the mediator sits cross-legged, "
        "calm, one hand raised in a light welcoming gesture, head slightly overlapping the bubbles.",
    "illu-01": MEDIATOR + "The mediator sits in the centre, smaller than the others, holding up two separate colored "
        "threads, one in each raised hand; each thread runs clearly through the empty air to one of two people who had "
        "a fight, standing far to the left and far to the right, turned away from each other with arms crossed. The "
        "threads must not cross the mediator body.",
    "illu-02": "Two people sitting back to back on the floor, each with their own phone and their own rounded speech "
        "bubble above their head, clothes in contrasting colors.",
    "illu-03": "A person sitting calmly and untangling a big ball of yarn, the loose end of the thread finishing in a "
        "small heart shape.",
    "illu-04": "A thick closed hardcover book lying flat on a table, seen from a slight angle, its stacked paper "
        "pages clearly visible along the edge, with a ribbon tied in a neat bow across the cover, like closing a chapter. "
        "Two people stand behind the table, hands resting near the book, smiling gently at each other. Two cups of tea "
        "on the same table. There is no wrapping paper, no gift box, no parcel and no present in the scene.",
    "illu-05": "One person holding out a paper heart to another; the second person slowly unclenching their fists, "
        "shoulders softening.",
    "illu-06": "Two people at a small round table with two cups of tea and an hourglass, a straight thread without any "
        "knots stretched between them.",
    "illu-07": MEDIATOR + "A large phone in the centre with the mediator shown on its screen, holding two threads that "
        "run out of the screen to two small people standing on either side with their own phones.",
    "illu-08": "Cross-section of two apartments, one above the other: in the upper flat a person in headphones dancing "
        "with a lamp and a plant; in the lower flat a person lying in bed pressing a pillow over their ears.",
    "illu-09": "Top down slightly tilted view of a parking lot: one empty parking bay clearly marked with thick white "
        "painted lines on grey asphalt, one car parked in the neighbouring bay. Two neighbours stand on either side of "
        "the empty bay, facing each other, one gesturing at the bay with an open palm.",
    "illu-10": "Two flatmates in a small kitchen, a tall stack of dirty dishes in the sink, a chore list pinned to the "
        "fridge, one of them gesturing at the sink.",
    "illu-11": "Two friends on a park bench, one turned away with arms crossed, the other holding out two paper cups "
        "of coffee, a tree and a few leaves around them.",
    "illu-12": "Two colleagues at a shared desk, a tall stack of folders sliding from one side of the desk to the "
        "other, the person receiving them raising an open palm.",
    "illu-13": "An adult daughter and her mother sitting at a kitchen table with a teapot, both looking down into "
        "their cups, a thread stretching between the two cups.",
    "illu-cta": "Two people walking toward each other with open posture, a loose colored thread lying between them "
        "with no knots.",
    "illu-lock": "Two phones side by side, each with its own closed padlock and its own rounded chat bubble above it, "
        "no people.",
}

if __name__ == "__main__":
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("Нужна переменная OPENAI_API_KEY")
    genillu.STYLE_FLAT = STYLE
    out_dir = os.path.join(HERE, "..", "img", "rich")
    os.makedirs(out_dir, exist_ok=True)
    wanted = [a for a in sys.argv[1:] if a in SCENES] or list(SCENES)
    for name in wanted:
        out = os.path.join(out_dir, name + ".png")
        try:
            img = genillu.clean(genillu.generate(SCENES[name], key, quality="medium", style="flat"))
            img.save(out, optimize=True)
            print("ok", name, os.path.getsize(out) // 1024, "KB", flush=True)
        except Exception as e:
            print("fail", name, repr(e)[:160], flush=True)
