#!/usr/bin/env python3
"""Generates the English section of the site (stories, hub, legal pages) from JSON data.
Usage: python3 tools/en-stories.py [--check] [--root DIR] [--only all|legal|stories]"""
import argparse, glob, html, io, json, os, re, sys

BASE = 'https://askmediator.com/'
EN_BASE = BASE + 'en/'
BOT_SEO = 'https://t.me/mediator_help_bot?start=ref_seo_en'
BOT_SITE = 'https://t.me/mediator_help_bot?start=ref_site_en'
TODAY = '2026-09-02'
CSSV_FALLBACK = 'tm15'

STORY_SLUGS = [
 'husband-silent-after-argument', 'constantly-fighting-over-small-things',
 'how-to-make-up-after-a-big-fight', 'how-to-apologize', 'how-to-fight-fair',
 'ai-mediator-for-couples', 'upstairs-neighbor-noise-at-night', 'neighbor-parking-in-my-spot',
 'roommate-doesnt-clean', 'fight-with-best-friend', 'coworker-dumps-work-on-me', 'fight-with-my-mom',
]
STORY_TAGS = {'Couples', 'Neighbors', 'Friends', 'Work', 'Family', 'How it works'}
STORY_KEYS = ('ru_slug', 'slug', 'tag', 'mins', 'img', 'cls', 'card', 'title', 'desc', 'h1',
              'alt', 'tldr', 'body', 'chat', 'try', 'after', 'faq', 'more')
HUB_KEYS = ('title', 'desc', 'h1', 'lead')
LANDING_KEYS = ('h2', 'lead', 'cards')
LEGAL_KEYS = ('title', 'desc', 'h1', 'body')

BODY_TAGS = {'p', 'h2', 'h3', 'ul', 'li', 'strong', 'em', 'div', 'small', 'a'}
LEGAL_TAGS = {'h2', 'p', 'ul', 'li', 'strong', 'a'}
DASH_RE = re.compile('[–—]')
CYRILLIC_RE = re.compile('[Ѐ-ӿ]')
TAG_RE = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^<>]*)?)>')

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

FOOT_NOTE = ('Mediator helps you talk. It is not a court, a lawyer or a therapist: '
             'the bot makes no rulings and no diagnoses. If you are in danger, call your local emergency number.')


def strip(t):
    return html.unescape(re.sub(r'<[^>]+>', '', t)).strip()


def format_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return f'{MONTHS[m - 1]} {d}, {y}'


def attr(attrs_str, name):
    m = re.search(name + r'\s*=\s*"([^"]*)"', attrs_str)
    return m.group(1) if m else None


def story_href_ok(slugs):
    allowed_exact = {'/en/', '/en/stories/', '/en/privacy/', '/en/terms/'}

    def ok(href):
        if href in allowed_exact:
            return True
        m = re.fullmatch(r'/en/stories/([a-z0-9-]+)/', href)
        if m and m.group(1) in slugs:
            return True
        return href.startswith('https://')
    return ok


def legal_href_ok(href):
    return href.startswith('https://') or href.startswith('mailto:') or href.startswith('/')


def check_markup(src, allowed, href_ok=None):
    problems = []
    for m in TAG_RE.finditer(src):
        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if name not in allowed:
            problems.append(f'disallowed tag <{closing}{name}>')
            continue
        if closing:
            continue
        if name == 'div':
            classes = (attr(attrs, 'class') or '').split()
            if 'phrase' not in classes:
                problems.append('<div> must have class="phrase"')
        if name == 'a' and href_ok is not None:
            href = attr(attrs, 'href')
            if href is None or not href_ok(href):
                problems.append(f'invalid <a href="{href}">')
    return problems


def check_dashes_cyrillic(value, path, problems):
    if isinstance(value, str):
        if DASH_RE.search(value):
            problems.append(f'{path}: contains an em or en dash')
        if CYRILLIC_RE.search(value):
            problems.append(f'{path}: contains Cyrillic text')
    elif isinstance(value, list):
        for i, v in enumerate(value):
            check_dashes_cyrillic(v, f'{path}[{i}]', problems)
    elif isinstance(value, dict):
        for k, v in value.items():
            check_dashes_cyrillic(v, f'{path}.{k}', problems)


def check_len(value, fname, slug, key, lo, hi, problems):
    if not isinstance(value, str):
        problems.append(f'{fname}: {slug}: {key}: expected a string')
        return
    n = len(value)
    if not (lo <= n <= hi):
        problems.append(f'{fname}: {slug}: {key}: length {n} not in [{lo},{hi}]')


def validate_story(st, fname, all_slugs, problems):
    slug = st.get('slug', '?')

    def p(key, msg):
        problems.append(f'{fname}: {slug}: {key}: {msg}')

    for key in STORY_KEYS:
        if key not in st:
            p(key, 'missing')
    if any(k not in st for k in STORY_KEYS):
        return

    if st['slug'] not in STORY_SLUGS:
        p('slug', 'not one of the allowed story slugs')
    if not isinstance(st['ru_slug'], str) or not st['ru_slug']:
        p('ru_slug', 'must be a non-empty string')
    if st['tag'] not in STORY_TAGS:
        p('tag', f'must be one of {sorted(STORY_TAGS)}')
    if not isinstance(st['mins'], int) or isinstance(st['mins'], bool) or st['mins'] <= 0:
        p('mins', 'must be a positive integer')
    if not isinstance(st['img'], str) or not st['img']:
        p('img', 'must be a non-empty string')
    if not isinstance(st['cls'], str):
        p('cls', 'must be a string')
    check_len(st['card'], fname, slug, 'card', 40, 70, problems)
    check_len(st['title'], fname, slug, 'title', 50, 60, problems)
    check_len(st['desc'], fname, slug, 'desc', 120, 160, problems)
    if not isinstance(st['h1'], str) or not st['h1']:
        p('h1', 'must be a non-empty string')
    if not isinstance(st['alt'], str) or not st['alt']:
        p('alt', 'must be a non-empty string')

    if not isinstance(st['tldr'], list) or len(st['tldr']) != 3 or not all(isinstance(x, str) and x for x in st['tldr']):
        p('tldr', 'must be an array of 3 non-empty strings')
    else:
        for i, x in enumerate(st['tldr']):
            check_len(x, fname, slug, f'tldr[{i}]', 20, 220, problems)

    if not isinstance(st['chat'], list) or len(st['chat']) != 3 or not all(isinstance(x, str) and x for x in st['chat']):
        p('chat', 'must be an array of 3 non-empty strings')
    else:
        for i, x in enumerate(st['chat']):
            check_len(x, fname, slug, f'chat[{i}]', 15, 400, problems)

    if not isinstance(st['try'], list) or len(st['try']) != 3 or not all(isinstance(x, str) and x for x in st['try']):
        p('try', 'must be an array of 3 non-empty strings: heading, paragraph, button label')
    else:
        check_len(st['try'][0], fname, slug, 'try[0]', 10, 70, problems)
        check_len(st['try'][1], fname, slug, 'try[1]', 60, 420, problems)
        check_len(st['try'][2], fname, slug, 'try[2]', 5, 40, problems)

    if not isinstance(st['faq'], list) or not st['faq'] or not all(
            isinstance(x, (list, tuple)) and len(x) == 2 and all(isinstance(y, str) for y in x) for x in st['faq']):
        p('faq', 'must be an array of [question, answer] string pairs')

    if not isinstance(st['more'], list) or len(st['more']) != 3 or not all(isinstance(x, str) for x in st['more']):
        p('more', 'must be an array of 3 slugs')
    else:
        for s in st['more']:
            if s not in all_slugs:
                p('more', f'references unknown slug {s!r}')

    if not isinstance(st['body'], str) or not st['body'].strip():
        p('body', 'must be a non-empty HTML string')
    else:
        for issue in check_markup(st['body'], BODY_TAGS, story_href_ok(all_slugs)):
            p('body', issue)

    if not isinstance(st['after'], str):
        p('after', 'must be a string (may be empty)')
    elif st['after'].strip():
        for issue in check_markup(st['after'], BODY_TAGS, story_href_ok(all_slugs)):
            p('after', issue)

    check_dashes_cyrillic(st, f'{fname}: {slug}', problems)


def check_img(root, st, fname, problems):
    img = st.get('img')
    if isinstance(img, str) and img:
        if not os.path.isfile(os.path.join(root, 'img', img)):
            problems.append(f'{fname}: {st.get("slug", "?")}: img: file not found: img/{img}')


def check_ru_slug(root, st, fname, problems):
    rs = st.get('ru_slug')
    if isinstance(rs, str) and rs:
        if not os.path.isfile(os.path.join(root, rs, 'index.html')):
            problems.append(f'{fname}: {st.get("slug", "?")}: ru_slug: no {rs}/index.html found under root')


def validate_hub(hub_data, fname, all_slugs, problems):
    if 'hub' not in hub_data:
        problems.append(f'{fname}: hub: missing "hub" section')
    else:
        h = hub_data['hub']
        for key in HUB_KEYS:
            if key not in h:
                problems.append(f'{fname}: hub: {key}: missing')
        if all(k in h for k in HUB_KEYS):
            check_len(h['title'], fname, 'hub', 'title', 50, 60, problems)
            check_len(h['desc'], fname, 'hub', 'desc', 120, 160, problems)
            if not isinstance(h['h1'], str) or not h['h1']:
                problems.append(f'{fname}: hub: h1: must be a non-empty string')
            if not isinstance(h['lead'], str) or not h['lead']:
                problems.append(f'{fname}: hub: lead: must be a non-empty string')
        check_dashes_cyrillic(h, f'{fname}: hub', problems)

    if 'landing' not in hub_data:
        problems.append(f'{fname}: landing: missing "landing" section')
    else:
        l = hub_data['landing']
        for key in LANDING_KEYS:
            if key not in l:
                problems.append(f'{fname}: landing: {key}: missing')
        if all(k in l for k in LANDING_KEYS):
            if not isinstance(l['h2'], str) or not l['h2']:
                problems.append(f'{fname}: landing: h2: must be a non-empty string')
            if not isinstance(l['lead'], str) or not l['lead']:
                problems.append(f'{fname}: landing: lead: must be a non-empty string')
            if not isinstance(l['cards'], list) or len(l['cards']) != 6 or not all(isinstance(x, str) for x in l['cards']):
                problems.append(f'{fname}: landing: cards: must be an array of 6 slugs')
            else:
                for s in l['cards']:
                    if s not in all_slugs:
                        problems.append(f'{fname}: landing: cards: references unknown slug {s!r}')
        check_dashes_cyrillic(l, f'{fname}: landing', problems)


def validate_legal(legal_data, fname, problems):
    for section in ('privacy', 'terms'):
        if section not in legal_data:
            problems.append(f'{fname}: {section}: missing section')
            continue
        d = legal_data[section]
        for key in LEGAL_KEYS:
            if key not in d:
                problems.append(f'{fname}: {section}: {key}: missing')
        if not all(k in d for k in LEGAL_KEYS):
            continue
        check_len(d['title'], fname, section, 'title', 40, 60, problems)
        check_len(d['desc'], fname, section, 'desc', 100, 160, problems)
        if not isinstance(d['h1'], str) or not d['h1']:
            problems.append(f'{fname}: {section}: h1: must be a non-empty string')
        if not isinstance(d['body'], str) or not d['body'].strip():
            problems.append(f'{fname}: {section}: body: must be a non-empty HTML string')
        else:
            for issue in check_markup(d['body'], LEGAL_TAGS, legal_href_ok):
                problems.append(f'{fname}: {section}: body: {issue}')
        check_dashes_cyrillic(d, f'{fname}: {section}', problems)


def load_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def load_stories(root, problems):
    files = sorted(glob.glob(os.path.join(root, 'tools', 'en-stories-*.json')))
    stories, origin = [], {}
    for fp in files:
        fname = os.path.relpath(fp, root)
        try:
            data = load_json(fp)
        except (OSError, ValueError) as e:
            problems.append(f'{fname}: cannot read/parse: {e}')
            continue
        if not isinstance(data, list):
            problems.append(f'{fname}: expected a JSON array')
            continue
        for st in data:
            if not isinstance(st, dict):
                problems.append(f'{fname}: story entry is not an object')
                continue
            slug = st.get('slug')
            if slug in origin:
                problems.append(f'{fname}: {slug}: duplicate slug (also defined in {origin[slug]})')
                continue
            origin[slug] = fname
            stories.append(st)
    if not files:
        problems.append('tools/en-stories-*.json: no files found')
    return stories, origin


def load_optional(path, root, problems):
    rel = os.path.relpath(path, root)
    if not os.path.isfile(path):
        problems.append(f'{rel}: file not found')
        return None
    try:
        return load_json(path)
    except (OSError, ValueError) as e:
        problems.append(f'{rel}: cannot read/parse: {e}')
        return None


def read_css_version(root):
    src = io.open(os.path.join(root, 'en', 'index.html'), encoding='utf-8').read()
    m = re.search(r'styles\.css\?v=([^"]+)"', src)
    return m.group(1) if m else CSSV_FALLBACK


def read_shared(root):
    src = io.open(os.path.join(root, 'en', 'index.html'), encoding='utf-8').read()
    icon = re.search(r'<link rel="icon"[^>]+>', src).group(0)
    fonts = re.search(r'<link href="https://fonts.googleapis.com[^>]+>', src).group(0)
    yandex = re.search(r'<!-- Yandex\.Metrika counter -->.*?<!-- /Yandex\.Metrika counter -->', src, re.S).group(0)
    tg_click = re.search(r"<script>\ndocument\.addEventListener\('click'.*?</script>", src, re.S).group(0)
    return icon, fonts, yandex, tg_click


def write_if_changed(path, content):
    if os.path.isfile(path):
        with io.open(path, encoding='utf-8') as f:
            if f.read() == content:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def build_footer(ru_href, bot, show_stories=True):
    stories_line = '        <p><a href="/en/stories/">Stories</a></p>\n' if show_stories else ''
    return f'''<footer>
  <div class="inner">
    <p class="foot-note">{FOOT_NOTE}</p>
    <div class="foot-grid">
      <a class="brand" href="/en/">Mediator<span>.</span></a>
      <div>
        <h3>Product</h3>
        <p><a href="/en/#how">How it works</a></p>
{stories_line}        <p><a href="/en/#faq">FAQ</a></p>
        <p><a href="{ru_href}" hreflang="ru" lang="ru" onclick="try{{localStorage.setItem('lang','ru')}}catch(e){{}}">Русская версия</a></p>
      </div>
      <div>
        <h3>Bot in Telegram</h3>
        <p><a href="{bot}">@mediator_help_bot</a></p>
        <p>One free analysis a month; your partner joins via your link at no cost.</p>
      </div>
    </div>
    <div class="foot-bottom">
      <p>© 2026 Mediator. All rights reserved.</p>
      <p><a href="/en/privacy/">Privacy</a><span class="sep">|</span><a href="/en/terms/">Terms</a></p>
    </div>
  </div>
</footer>'''


def add_hreflang(path, en_url):
    s = io.open(path, encoding='utf-8').read()
    if 'hreflang="ru"' in s:
        return False
    m = re.search(r'<link rel="canonical" href="([^"]+)">\n', s)
    if not m:
        raise RuntimeError('no canonical link found in ' + path)
    ru_url = m.group(1)
    block = (f'<link rel="alternate" hreflang="ru" href="{ru_url}">\n'
             f'<link rel="alternate" hreflang="en" href="{en_url}">\n'
             f'<link rel="alternate" hreflang="x-default" href="{en_url}">\n')
    s2 = s[:m.end()] + block + s[m.end():]
    io.open(path, 'w', encoding='utf-8').write(s2)
    return True


def update_sitemap(root, entries):
    path = os.path.join(root, 'sitemap.xml')
    s = io.open(path, encoding='utf-8').read()
    added = False
    for loc, priority in entries:
        if f'<loc>{loc}</loc>' in s:
            continue
        line = f'  <url><loc>{loc}</loc><lastmod>{TODAY}</lastmod><priority>{priority}</priority></url>\n'
        s = s.replace('</urlset>', line + '</urlset>')
        added = True
    if added:
        io.open(path, 'w', encoding='utf-8').write(s)


def upsert(s, key, content, pattern, mode):
    start = f'<!-- en-stories:{key} -->'
    end = f'<!-- /en-stories:{key} -->'
    block = f'{start}\n{content}\n{end}'
    existing = re.compile(re.escape(start) + r'.*?' + re.escape(end), re.S)
    if existing.search(s):
        return existing.sub(lambda m: block, s)
    m = re.search(pattern, s)
    if not m:
        raise RuntimeError('anchor not found for ' + key)
    if mode == 'before':
        return s[:m.start()] + block + '\n' + s[m.start():]
    if mode == 'replace':
        return s[:m.start()] + block + s[m.end():]
    raise ValueError(mode)


def landing_card(st):
    return f'''      <a class="story-card" href="/en/stories/{st['slug']}/">
        <span class="thumb contain"><img src="/img/{st['img']}" alt="" loading="lazy" width="900" height="900"></span>
        <span class="story-meta">{st['tag']} · {st['mins']} min</span>
        <span class="story-title">{st['card']}</span>
      </a>
'''


def update_en_index_legal(root):
    path = os.path.join(root, 'en', 'index.html')
    s = io.open(path, encoding='utf-8').read()
    old = ('      <p><a href="../privacy/">Privacy (in Russian)</a><span class="sep">|</span>'
           '<a href="../terms/">Terms (in Russian)</a></p>')
    new_line = '      <p><a href="/en/privacy/">Privacy</a><span class="sep">|</span><a href="/en/terms/">Terms</a></p>'
    s2 = upsert(s, 'footer-legal', new_line, re.escape(old), 'replace')
    if s2 != s:
        io.open(path, 'w', encoding='utf-8').write(s2)


def update_en_index_stories(root, hub, landing_cards):
    path = os.path.join(root, 'en', 'index.html')
    original = io.open(path, encoding='utf-8').read()
    s = original
    s = upsert(s, 'nav-stories', '      <a href="/en/stories/">Stories</a>',
               re.escape('      <a href="#faq">FAQ</a>'), 'before')
    l = hub['landing']
    cards = ''.join(landing_card(st) for st in landing_cards)
    section = f'''<section class="stories-section reveal" id="stories">
  <div class="inner">
    <div class="stories-head">
      <div>
        <p class="eyebrow">#Stories</p>
        <h2>{l['h2']}</h2>
        <p>{l['lead']}</p>
      </div>
      <a class="btn btn-ghost" href="/en/stories/">All stories</a>
    </div>
    <div class="stories">
{cards}    </div>
  </div>
</section>'''
    section_pattern = re.escape('<section class="band">\n  <div class="band-inner cta reveal">')
    s = upsert(s, 'stories-section', section, section_pattern, 'before')
    s = upsert(s, 'footer-stories', '        <p><a href="/en/stories/">Stories</a></p>',
               re.escape('        <p><a href="#faq">FAQ</a></p>'), 'before')
    if s != original:
        io.open(path, 'w', encoding='utf-8').write(s)


def legal_page(section, data, ru_href, css_version, icon, fonts, yandex, tg_click, show_stories):
    canonical = EN_BASE + section + '/'
    ru_canonical = BASE + ('privacy/' if section == 'privacy' else 'terms/')
    updated = format_date(TODAY)
    og_image = f'{BASE}img/og.jpg'
    nav_stories = '      <a href="/en/stories/">Stories</a>\n' if show_stories else ''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{data['title']}</title>
<meta name="description" content="{data['desc']}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="ru" href="{ru_canonical}">
<link rel="alternate" hreflang="en" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:title" content="{data['title']}">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_US">
<meta property="og:description" content="{data['desc']}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{og_image}">
{icon}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fonts}
<link rel="stylesheet" href="/styles.css?v={css_version}">
{yandex}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<div class="wrap-wide">
  <nav class="topbar">
    <a class="brand" href="/en/">Mediator<span>.</span></a>
    <div class="nav-links">
{nav_stories}      <a href="/en/#faq">FAQ</a>
    </div>
    <a class="btn btn-ghost" href="{BOT_SITE}">Open in Telegram</a>
  </nav>
</div>

<article class="article" id="main">
<div class="wrap">
<h1>{data['h1']}</h1>
<p class="meta">Updated {updated}</p>
{data['body']}

</div>
</article>

{build_footer(ru_href, BOT_SITE, show_stories)}

{tg_click}

</body>
</html>
'''


def generate_legal(root, legal, css_version, icon, fonts, yandex, tg_click, show_stories):
    pages = {'privacy': ('/privacy/', legal['privacy']), 'terms': ('/terms/', legal['terms'])}
    for section, (ru_href, data) in pages.items():
        out_path = os.path.join(root, 'en', section, 'index.html')
        page = legal_page(section, data, ru_href, css_version, icon, fonts, yandex, tg_click, show_stories)
        if write_if_changed(out_path, page):
            print('written', 'en/' + section + '/index.html')
    add_hreflang(os.path.join(root, 'privacy', 'index.html'), EN_BASE + 'privacy/')
    add_hreflang(os.path.join(root, 'terms', 'index.html'), EN_BASE + 'terms/')
    update_en_index_legal(root)
    update_sitemap(root, [(EN_BASE + 'privacy/', '0.3'), (EN_BASE + 'terms/', '0.3')])


def hub_card(st):
    return f'''      <a class="story-card" href="/en/stories/{st['slug']}/">
        <span class="thumb contain"><img src="/img/{st['img']}" alt="" loading="lazy" width="900" height="900"></span>
        <span class="story-meta">{st['tag']} · {st['mins']} min</span>
        <span class="story-title">{st['card']}</span>
        <span class="story-teaser">{st['desc']}</span>
      </a>
'''


def hub_page(hub, ordered_stories, css_version, icon, fonts, yandex, tg_click):
    h = hub['hub']
    canonical = EN_BASE + 'stories/'
    og_image = f'{BASE}img/og.jpg'
    cards_html = ''.join(hub_card(st) for st in ordered_stories)
    graph = [
        {"@type": "CollectionPage", "name": strip(h['h1']), "url": canonical, "inLanguage": "en",
         "description": h['desc']},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Mediator", "item": EN_BASE},
            {"@type": "ListItem", "position": 2, "name": "Stories", "item": canonical}]},
        {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": EN_BASE + 'stories/' + st['slug'] + '/',
             "name": strip(st['h1'])} for i, st in enumerate(ordered_stories)]}
    ]
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h['title']}</title>
<meta name="description" content="{h['desc']}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="ru" href="{BASE}istorii/">
<link rel="alternate" hreflang="en" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:title" content="{h['title']}">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_US">
<meta property="og:description" content="{h['desc']}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{og_image}">
{icon}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fonts}
<link rel="stylesheet" href="/styles.css?v={css_version}">
<script type="application/ld+json">
{ld}
</script>
{yandex}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<div class="wrap-wide">
  <nav class="topbar">
    <a class="brand" href="/en/">Mediator<span>.</span></a>
    <div class="nav-links">
      <a href="/en/#how">How it works</a>
      <a href="/en/#faq">FAQ</a>
    </div>
    <a class="btn btn-ghost" href="{BOT_SEO}">Open in Telegram</a>
  </nav>
</div>

<main class="hub" id="main">
  <div class="wrap-wide">
    <p class="eyebrow">#Stories</p>
    <h1>{h['h1']}</h1>
    <p class="hub-lede">{h['lead']}</p>
    <div class="stories hub-grid">
{cards_html}    </div>
    <div class="try-box hub-try">
      <h3>Didn't find your situation?</h3>
      <p>Tell the bot what's going on. It works through your specific fight, not a typical one: what hurt, what's happening with the other person, and what line to open with. The first analysis is free.</p>
      <a class="btn" href="{BOT_SEO}">Sort out the fight for free</a>
    </div>
  </div>
</main>

{build_footer(BASE + 'istorii/', BOT_SEO)}

{tg_click}

</body>
</html>
'''


def story_page(st, by_slug, css_version, icon, fonts, yandex, tg_click):
    slug = st['slug']
    canonical = EN_BASE + 'stories/' + slug + '/'
    ru_canonical = BASE + st['ru_slug'] + '/'
    img = BASE + 'img/' + st['img']
    faq_html = ''.join(f'<details>\n  <summary>{q}</summary>\n  <p>{a}</p>\n</details>\n' for q, a in st['faq'])
    more_html = ''.join(
        f'  <a href="/en/stories/{s}/"><small>{by_slug[s]["tag"]}</small>{by_slug[s]["card"]}</a>\n'
        for s in st['more'])
    tldr = '<div class="tldr"><small>In short</small><ul>' + ''.join(f'<li>{i}</li>' for i in st['tldr']) + '</ul></div>'
    chat = f'''<div class="chat" aria-label="Example of a chat with the bot">
  <div class="bubble user">{st['chat'][0]}</div>
  <div class="bubble bot">{st['chat'][1]}</div>
  <div class="bubble bot">{st['chat'][2]}</div>
  <div class="chat-caption">The other person doesn't see this conversation. They have their own.</div>
</div>'''
    graph = [
        {"@type": "BlogPosting", "headline": strip(st['h1']), "description": st['desc'], "inLanguage": "en",
         "datePublished": TODAY, "dateModified": TODAY, "image": [img],
         "author": {"@type": "Organization", "name": "Mediator", "url": EN_BASE},
         "publisher": {"@type": "Organization", "name": "Mediator", "url": EN_BASE},
         "mainEntityOfPage": {"@type": "WebPage", "@id": canonical}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Mediator", "item": EN_BASE},
            {"@type": "ListItem", "position": 2, "name": "Stories", "item": EN_BASE + 'stories/'},
            {"@type": "ListItem", "position": 3, "name": strip(st['h1']), "item": canonical}]},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": strip(q), "acceptedAnswer": {"@type": "Answer", "text": strip(a)}}
            for q, a in st['faq']]}
    ]
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{st['title']}</title>
<meta name="description" content="{st['desc']}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="ru" href="{ru_canonical}">
<link rel="alternate" hreflang="en" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:title" content="{st['title']}">
<meta property="og:type" content="article">
<meta property="og:locale" content="en_US">
<meta property="og:description" content="{st['desc']}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="900">
<meta property="og:image:height" content="900">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{img}">
<meta property="article:published_time" content="{TODAY}">
<meta property="article:modified_time" content="{TODAY}">
{icon}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fonts}
<link rel="stylesheet" href="/styles.css?v={css_version}">
<script type="application/ld+json">
{ld}
</script>
{yandex}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<div class="wrap-wide">
  <nav class="topbar">
    <a class="brand" href="/en/">Mediator<span>.</span></a>
    <div class="nav-links">
      <a href="/en/stories/">Stories</a>
      <a href="/en/#faq">FAQ</a>
    </div>
    <a class="btn btn-ghost" href="{BOT_SEO}">Open in Telegram</a>
  </nav>
</div>

<article class="article" id="main">
<div class="wrap">
<p class="crumbs"><a href="/en/stories/">Stories</a></p>
<h1>{st['h1']}</h1>
<p class="meta">{st['tag']} · {st['mins']} min read</p>

<figure class="story-hero {st['cls']}"><img src="/img/{st['img']}" alt="{st['alt']}" width="900" height="900" loading="eager"></figure>
{tldr}

{st['body']}

{chat}

<div class="try-box">
  <h3>{st['try'][0]}</h3>
  <p>{st['try'][1]}</p>
  <a class="btn" href="{BOT_SEO}">{st['try'][2]}</a>
</div>

{st['after']}

<h2>Common questions</h2>
{faq_html}
<h2>More stories</h2>
<div class="more">
{more_html}</div>
<p class="more-all"><a href="/en/stories/">All stories</a></p>
</div>
</article>

{build_footer(ru_canonical, BOT_SEO)}

{tg_click}

</body>
</html>
'''


def generate_stories(root, stories, origin, hub, css_version, icon, fonts, yandex, tg_click):
    by_slug = {st['slug']: st for st in stories}
    ordered = [s for s in STORY_SLUGS if s in by_slug] + [s for s in by_slug if s not in STORY_SLUGS]
    for slug in ordered:
        st = by_slug[slug]
        out_path = os.path.join(root, 'en', 'stories', slug, 'index.html')
        page = story_page(st, by_slug, css_version, icon, fonts, yandex, tg_click)
        if write_if_changed(out_path, page):
            print('written', 'en/stories/' + slug + '/index.html')
        add_hreflang(os.path.join(root, st['ru_slug'], 'index.html'), EN_BASE + 'stories/' + slug + '/')
    hub_html = hub_page(hub, [by_slug[s] for s in ordered], css_version, icon, fonts, yandex, tg_click)
    if write_if_changed(os.path.join(root, 'en', 'stories', 'index.html'), hub_html):
        print('written', 'en/stories/index.html')
    add_hreflang(os.path.join(root, 'istorii', 'index.html'), EN_BASE + 'stories/')
    landing_cards = [by_slug[s] for s in hub['landing']['cards'] if s in by_slug]
    update_en_index_stories(root, hub, landing_cards)
    update_sitemap(root, [(EN_BASE + 'stories/', '0.8')] +
                    [(EN_BASE + 'stories/' + s + '/', '0.7') for s in ordered])


def main():
    ap = argparse.ArgumentParser(description='Generate the English section of the site from JSON data.')
    ap.add_argument('--check', action='store_true', help='validate the data only, do not write files')
    ap.add_argument('--root', default='.', help='site root to read from and write into')
    ap.add_argument('--only', choices=['all', 'legal', 'stories'], default='all')
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    need_stories = args.only in ('all', 'stories')
    need_legal = args.only in ('all', 'legal')

    problems = []
    stories, origin, hub, legal = [], {}, None, None

    if need_stories:
        stories, origin = load_stories(root, problems)
        hub = load_optional(os.path.join(root, 'tools', 'en-hub.json'), root, problems)
    if need_legal:
        legal = load_optional(os.path.join(root, 'tools', 'en-legal.json'), root, problems)

    all_slugs = {st.get('slug') for st in stories if isinstance(st.get('slug'), str)}

    if need_stories:
        for st in stories:
            fname = origin.get(st.get('slug'), '?')
            validate_story(st, fname, all_slugs, problems)
            check_img(root, st, fname, problems)
            check_ru_slug(root, st, fname, problems)
        if hub is not None:
            validate_hub(hub, 'tools/en-hub.json', all_slugs, problems)
    if need_legal and legal is not None:
        validate_legal(legal, 'tools/en-legal.json', problems)

    if problems:
        for msg in problems:
            print(msg)
        print(f'{len(problems)} problem(s) found')
        sys.exit(1)

    if args.check:
        print('ok: no problems found')
        sys.exit(0)

    css_version = read_css_version(root)
    icon, fonts, yandex, tg_click = read_shared(root)
    if need_legal:
        stories_available = need_stories or os.path.isfile(os.path.join(root, 'en', 'stories', 'index.html'))
        generate_legal(root, legal, css_version, icon, fonts, yandex, tg_click, stories_available)
    if need_stories:
        generate_stories(root, stories, origin, hub, css_version, icon, fonts, yandex, tg_click)
    print('done')


if __name__ == '__main__':
    main()
