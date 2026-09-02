#!/usr/bin/env python3
"""Типографский проход по HTML: висячие предлоги и частицы, число и единица,
последние два слова блока склеиваются неразрывным пробелом (чтобы одно слово не оставалось на строке).
Использование: python3 tools/typograf.py index.html istorii/index.html ...  (идемпотентно)"""
import re, sys, io

NBSP = ' '
SHORT3 = 'что|как|для|при|про|без|над|под|все|всё|вот|уже|ещё|или|так|там|тут|где|кто|чем|тем|его|её|их|мне|нам|вам|ему|ей|им|это|эта|тот|эти|нет|да|ну|бы|же|ли'
HANG = re.compile(r'(?<![\w-])((?:[а-яёА-ЯЁ]{1,2})|(?:' + SHORT3 + r'))[ \t]+(?=[«"(]?[а-яёА-ЯЁa-zA-Z0-9«(])')
PARTICLE = re.compile(r'[ \t]+(же|ли|бы|б|ж)(?=[\s.,;:!?»)])')
UNIT = re.compile(r'(\d+)[ \t]+(звёзд\w*|дней|дня|день|минут\w*|секунд\w*|час\w*|раз\w*|человек\w*|шаг\w*|правил\w*|верси\w*|процент\w*|лет|год\w*|недел\w*)')
TAG = re.compile(r'(<[^>]+>)')
BLOCK_CLOSE = {'p', 'h1', 'h2', 'h3', 'h4', 'li', 'summary', 'small', 'span', 'figcaption', 'div', 'b', 'strong', 'em', 'a'}
SKIP_OPEN = ('script', 'style', 'title', 'svg', 'pre', 'code')

def widont(text):
    m = re.match(r'^(.*?)(\s*)$', text, re.S)
    body, tail = m.group(1), m.group(2)
    words = re.split(r'[ \t]+', body.strip())
    if len(words) < 3: return text
    last = words[-1]
    if len(last) > 14 or re.fullmatch(r'[\d.,%]+', last): return text
    idx = body.rstrip().rfind(' ')
    if idx < 0: return text
    lead = body[:idx]; rest = body[idx + 1:]
    return lead + NBSP + rest + tail

def process(html):
    parts = TAG.split(html)
    skip = None
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            name = re.match(r'</?\s*([a-zA-Z0-9]+)', part)
            tag = name.group(1).lower() if name else ''
            if skip:
                if part.startswith('</') and tag == skip: skip = None
            elif not part.startswith('</') and tag in SKIP_OPEN and not part.endswith('/>'):
                skip = tag
            elif part.startswith('</') and tag in BLOCK_CLOSE and out and (i - 1) % 2 == 0:
                prev = out[-1]
                if prev.strip(): out[-1] = widont(prev)
            out.append(part)
        else:
            if skip or not part.strip():
                out.append(part); continue
            t = HANG.sub(lambda m: m.group(1) + NBSP, part)
            t = PARTICLE.sub(lambda m: NBSP + m.group(1), t)
            t = UNIT.sub(lambda m: m.group(1) + NBSP + m.group(2), t)
            out.append(t)
    return ''.join(out)

if __name__ == '__main__':
    for f in sys.argv[1:]:
        s = io.open(f, encoding='utf-8').read(); t = process(s)
        if t != s:
            io.open(f, 'w', encoding='utf-8').write(t)
        print(f, 'nbsp:', t.count(NBSP))
