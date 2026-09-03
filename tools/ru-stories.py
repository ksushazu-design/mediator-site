#!/usr/bin/env python3
"""Генерирует раздел историй сайта (страницы историй, хаб, блок на главной) из JSON-данных.
Использование: python3 tools/ru-stories.py [--check] [--root DIR] [--home slug1,slug2,...]"""
import argparse, glob, html, io, json, os, re, sys

BASE = 'https://askmediator.com/'
EN_BASE = BASE + 'en/'
BOT = 'https://t.me/mediator_help_bot?start=ref_seo'
TODAY = '2026-09-03'
CSSV_FALLBACK = 'tm15'
GENERATED_MARKER = '<!-- ru-stories: generated -->'

DEFAULT_HOME = ['muzh-molchit-posle-ssory', 'sosed-shumit-po-nocham', 'possorilas-s-podrugoy',
                'kollega-perekladyvaet-rabotu', 'possorilas-s-mamoy', 'postoyanno-ssorimsya']

STORY_KEYS = ('slug', 'tag', 'mins', 'img', 'cls', 'scene', 'card', 'title', 'desc', 'h1',
              'alt', 'tldr', 'body', 'chat', 'try', 'after', 'faq', 'more')
BODY_TAGS = {'p', 'h2', 'h3', 'ul', 'li', 'strong', 'em', 'a', 'div', 'small'}
DASH_RE = re.compile('[–—]')
TAG_RE = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^<>]*)?)>')
HOME_CARD_RE = re.compile(r'      <a class="story-card" href="([a-z0-9-]+)/">\n.*?\n      </a>\n', re.S)
HUB_CARD_RE = re.compile(r'      <a class="story-card" href="\.\./([a-z0-9-]+)/">\n.*?\n      </a>\n', re.S)


def strip(t):
    return html.unescape(re.sub(r'<[^>]+>', '', t)).strip()


def attr(attrs_str, name):
    m = re.search(name + r'\s*=\s*"([^"]*)"', attrs_str)
    return m.group(1) if m else None


def story_href_ok(slugs):
    allowed_exact = {'../istorii/', '../#faq', '../#how', '../'}

    def ok(href):
        if href in allowed_exact:
            return True
        m = re.fullmatch(r'\.\./([a-z0-9-]+)/', href)
        if m and m.group(1) in slugs:
            return True
        return href.startswith('https://')
    return ok


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


def check_dashes(value, path, problems):
    if isinstance(value, str):
        if DASH_RE.search(value):
            problems.append(f'{path}: contains an em or en dash')
    elif isinstance(value, list):
        for i, v in enumerate(value):
            check_dashes(v, f'{path}[{i}]', problems)
    elif isinstance(value, dict):
        for k, v in value.items():
            check_dashes(v, f'{path}.{k}', problems)


def check_len(value, fname, slug, key, lo, hi, problems):
    if not isinstance(value, str):
        problems.append(f'{fname}: {slug}: {key}: expected a string')
        return
    n = len(value)
    if not (lo <= n <= hi):
        problems.append(f'{fname}: {slug}: {key}: length {n} not in [{lo},{hi}]')


def validate_story(st, fname, all_slugs, root, problems):
    slug = st.get('slug', '?')

    def p(key, msg):
        problems.append(f'{fname}: {slug}: {key}: {msg}')

    for key in STORY_KEYS:
        if key not in st:
            p(key, 'missing')
    if any(k not in st for k in STORY_KEYS):
        return

    if not isinstance(st['slug'], str) or not re.fullmatch(r'[a-z0-9-]+', st['slug']):
        p('slug', 'must be a non-empty string of lowercase letters, digits and hyphens')
    if not isinstance(st['tag'], str) or not st['tag']:
        p('tag', 'must be a non-empty string')
    if not isinstance(st['mins'], int) or isinstance(st['mins'], bool) or st['mins'] <= 0:
        p('mins', 'must be a positive integer')
    if not isinstance(st['img'], str) or not st['img']:
        p('img', 'must be a non-empty string')
    if not isinstance(st['cls'], str):
        p('cls', 'must be a string')
    if not isinstance(st['scene'], str) or not st['scene']:
        p('scene', 'must be a non-empty string')
    check_len(st['card'], fname, slug, 'card', 40, 70, problems)
    check_len(st['title'], fname, slug, 'title', 50, 60, problems)
    check_len(st['desc'], fname, slug, 'desc', 120, 160, problems)
    if not isinstance(st['h1'], str) or not st['h1']:
        p('h1', 'must be a non-empty string')
    else:
        if len(re.findall(r'<em class="ac">', st['h1'])) != 1:
            p('h1', 'must contain exactly one <em class="ac">')
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

    check_dashes(st, f'{fname}: {slug}', problems)

    if isinstance(st['slug'], str) and re.fullmatch(r'[a-z0-9-]+', st['slug']):
        existing = os.path.join(root, st['slug'], 'index.html')
        if os.path.isfile(existing):
            try:
                content = io.open(existing, encoding='utf-8').read()
            except OSError:
                content = ''
            if GENERATED_MARKER not in content:
                p('slug', f'conflicts with an existing folder not generated by this tool: {st["slug"]}/')


def check_img(root, st, fname, problems):
    img = st.get('img')
    if isinstance(img, str) and img:
        if not os.path.isfile(os.path.join(root, 'img', img)):
            problems.append(f'{fname}: {st.get("slug", "?")}: img: file not found: img/{img}')


def load_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def load_stories(root, problems):
    files = sorted(glob.glob(os.path.join(root, 'tools', 'ru-stories-*.json')))
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
        problems.append('tools/ru-stories-*.json: no files found')
    return stories, origin


def existing_page_slugs(root):
    slugs = set()
    if os.path.isdir(root):
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if os.path.isdir(full) and os.path.isfile(os.path.join(full, 'index.html')):
                slugs.add(name)
    return slugs


def load_en_ru_map(root):
    mapping = {}
    for fp in sorted(glob.glob(os.path.join(root, 'tools', 'en-stories-*.json'))):
        try:
            data = load_json(fp)
        except (OSError, ValueError):
            continue
        if not isinstance(data, list):
            continue
        for st in data:
            if isinstance(st, dict) and isinstance(st.get('ru_slug'), str) and isinstance(st.get('slug'), str):
                mapping[st['ru_slug']] = st['slug']
    return mapping


def read_css_version(root):
    src = io.open(os.path.join(root, 'index.html'), encoding='utf-8').read()
    m = re.search(r'styles\.css\?v=([^"]+)"', src)
    return m.group(1) if m else CSSV_FALLBACK


def read_shared(root):
    src = io.open(os.path.join(root, 'index.html'), encoding='utf-8').read()
    icon = re.search(r'<link rel="icon"[^>]+>', src).group(0)
    fonts = re.search(r'<link href="https://fonts.googleapis.com[^>]+>', src).group(0)
    yandex = re.search(r'<!-- Yandex\.Metrika counter -->.*?<!-- /Yandex\.Metrika counter -->', src, re.S).group(0)
    tg_click = re.search(r"<script>\ndocument\.addEventListener\('click'.*?</script>", src, re.S).group(0)
    return icon, fonts, yandex, tg_click


def read_footer(root):
    src = io.open(os.path.join(root, 'istorii', 'index.html'), encoding='utf-8').read()
    return re.search(r'<footer>.*?</footer>', src, re.S).group(0)


def write_if_changed(path, content):
    if os.path.isfile(path):
        with io.open(path, encoding='utf-8') as f:
            if f.read() == content:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def hreflang_block(ru_canonical, en_slug):
    if en_slug:
        en_url = EN_BASE + 'stories/' + en_slug + '/'
        return (f'<link rel="alternate" hreflang="ru" href="{ru_canonical}">\n'
                f'<link rel="alternate" hreflang="en" href="{en_url}">\n'
                f'<link rel="alternate" hreflang="x-default" href="{en_url}">\n')
    return f'<link rel="alternate" hreflang="ru" href="{ru_canonical}">\n'


def resolve_more_meta(root, slug, by_slug):
    if slug in by_slug:
        return by_slug[slug]['tag'], by_slug[slug]['card']
    path = os.path.join(root, slug, 'index.html')
    src = io.open(path, encoding='utf-8').read()
    tag_m = re.search(r'<p class="meta">([^·<]+)·', src)
    h1_m = re.search(r'<h1>(.*?)</h1>', src, re.S)
    tag = tag_m.group(1).strip() if tag_m else ''
    card = strip(h1_m.group(1)) if h1_m else slug
    return tag, card


def story_page(st, hreflang, footer, css_version, icon, fonts, yandex, tg_click, more_html):
    slug = st['slug']
    canonical = BASE + slug + '/'
    img = BASE + 'img/' + st['img']
    faq_html = ''.join(f'<details>\n  <summary>{q}</summary>\n  <p>{a}</p>\n</details>\n' for q, a in st['faq'])
    tldr = '<div class="tldr"><small>Коротко</small><ul>' + ''.join(f'<li>{i}</li>' for i in st['tldr']) + '</ul></div>'
    chat = f'''<div class="chat" aria-label="Пример переписки с ботом">
  <div class="bubble user">{st['chat'][0]}</div>
  <div class="bubble bot">{st['chat'][1]}</div>
  <div class="bubble bot">{st['chat'][2]}</div>
  <div class="chat-caption">Второй участник эту переписку не видит, у него своя</div>
</div>'''
    graph = [
      {"@type": "BlogPosting", "headline": strip(st['h1']), "description": st['desc'], "inLanguage": "ru",
       "datePublished": TODAY, "dateModified": TODAY, "image": [img],
       "author": {"@type": "Organization", "name": "Медиатор", "url": BASE},
       "publisher": {"@type": "Organization", "name": "Медиатор", "url": BASE},
       "mainEntityOfPage": {"@type": "WebPage", "@id": canonical}},
      {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Медиатор", "item": BASE},
        {"@type": "ListItem", "position": 2, "name": "Истории", "item": BASE + 'istorii/'},
        {"@type": "ListItem", "position": 3, "name": strip(st['h1']), "item": canonical}]},
      {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": strip(q), "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in st['faq']]}
    ]
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{st['title']}</title>
<meta name="description" content="{st['desc']}">
<link rel="canonical" href="{canonical}">
{hreflang}<meta property="og:title" content="{st['title']}">
<meta property="og:type" content="article">
<meta property="og:locale" content="ru_RU">
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
<link rel="stylesheet" href="../styles.css?v={css_version}">
<script type="application/ld+json">
{ld}
</script>
{yandex}
{GENERATED_MARKER}
</head>
<body>
<a class="skip" href="#main">К содержанию</a>

<div class="wrap-wide">
  <nav class="topbar">
    <a class="brand" href="../">Медиатор<span>.</span></a>
    <div class="nav-links">
      <a href="../istorii/">Истории</a>
      <a href="../#faq">Вопросы</a>
    </div>
    <a class="btn btn-ghost" href="{BOT}">Открыть в Telegram</a>
  </nav>
</div>

<article class="article" id="main">
<div class="wrap">
<p class="crumbs"><a href="../istorii/">Истории</a></p>
<h1>{st['h1']}</h1>
<p class="meta">{st['tag']} · {st['mins']} минут на чтение</p>

<figure class="story-hero {st['cls']}"><img src="../img/{st['img']}" alt="{st['alt']}" width="900" height="900" loading="eager"></figure>
{tldr}

{st['body']}

{chat}

<div class="try-box">
  <h3>{st['try'][0]}</h3>
  <p>{st['try'][1]}</p>
  <a class="btn" href="{BOT}">{st['try'][2]}</a>
</div>

{st['after']}

<h2>Частые вопросы</h2>
{faq_html}
<h2>Другие истории</h2>
<div class="more">
{more_html}</div>
<p class="more-all"><a href="../istorii/">Все истории</a></p>
</div>
</article>

{footer}

{tg_click}

</body>
</html>
'''


def hub_card(st):
    return f'''      <a class="story-card" href="../{st['slug']}/">
        <span class="thumb contain"><img src="../img/{st['img']}" alt="" loading="lazy" width="900" height="900"></span>
        <span class="story-meta">{st['tag']} · {st['mins']} минут</span>
        <span class="story-title">{st['card']}</span>
        <span class="story-teaser">{st['desc']}</span>
      </a>
'''


def landing_card(st):
    return f'''      <a class="story-card" href="{st['slug']}/">
        <span class="thumb contain"><img src="img/{st['img']}" alt="" loading="lazy" width="900" height="900"></span>
        <span class="story-meta">{st['tag']} · {st['mins']} минут</span>
        <span class="story-title">{st['card']}</span>
      </a>
'''


def resolve_hub_name(root, slug, existing_names):
    if slug in existing_names:
        return existing_names[slug]
    path = os.path.join(root, slug, 'index.html')
    try:
        src = io.open(path, encoding='utf-8').read()
    except OSError:
        return slug
    m = re.search(r'<h1>(.*?)</h1>', src, re.S)
    return strip(m.group(1)) if m else slug


def update_hub(root, by_slug, new_slugs_order):
    path = os.path.join(root, 'istorii', 'index.html')
    original = io.open(path, encoding='utf-8').read()
    s = original

    existing_order, existing_raw = [], {}
    for m in HUB_CARD_RE.finditer(s):
        existing_order.append(m.group(1))
        existing_raw[m.group(1)] = m.group(0)

    ld_m = re.search(r'<script type="application/ld\+json">\n(.*?)\n</script>', s, re.S)
    graph = json.loads(ld_m.group(1))['@graph']
    existing_names = {}
    for node in graph:
        if node.get('@type') == 'ItemList':
            for item in node['itemListElement']:
                item_slug = item['url'].rstrip('/').rsplit('/', 1)[-1]
                existing_names[item_slug] = item['name']

    final_order = list(existing_order)
    for slug in new_slugs_order:
        if slug not in final_order:
            final_order.append(slug)

    cards_html = []
    item_list = []
    for i, slug in enumerate(final_order):
        if slug in by_slug:
            st = by_slug[slug]
            cards_html.append(hub_card(st))
            name = strip(st['h1'])
        else:
            cards_html.append(existing_raw[slug])
            name = resolve_hub_name(root, slug, existing_names)
        item_list.append({"@type": "ListItem", "position": i + 1, "url": BASE + slug + '/', "name": name})

    for node in graph:
        if node.get('@type') == 'ItemList':
            node['itemListElement'] = item_list
    new_ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    s = s[:ld_m.start()] + '<script type="application/ld+json">\n' + new_ld + '\n</script>' + s[ld_m.end():]

    matches = list(HUB_CARD_RE.finditer(s))
    if matches:
        cards_block = ''.join(cards_html)
        s = s[:matches[0].start()] + cards_block + s[matches[-1].end():]

    if s != original:
        io.open(path, 'w', encoding='utf-8').write(s)
        print('written', 'istorii/index.html')


def update_home(root, by_slug, home_slugs):
    path = os.path.join(root, 'index.html')
    original = io.open(path, encoding='utf-8').read()
    s = original

    start_marker = '<!-- ru-stories:home -->\n'
    end_marker = '<!-- /ru-stories:home -->\n'
    existing_block_re = re.compile(re.escape(start_marker) + r'(.*?)' + re.escape(end_marker), re.S)

    em = existing_block_re.search(s)
    search_scope = em.group(1) if em else s

    existing_raw = {}
    for m in HOME_CARD_RE.finditer(search_scope):
        existing_raw[m.group(1)] = m.group(0)

    cards = []
    for slug in home_slugs:
        if slug in existing_raw:
            cards.append(existing_raw[slug])
        elif slug in by_slug:
            cards.append(landing_card(by_slug[slug]))
        else:
            raise RuntimeError(f'--home slug not found in existing cards or data: {slug}')
    block_content = ''.join(cards)

    if em:
        s2 = s[:em.start(1)] + block_content + s[em.end(1):]
    else:
        matches = list(HOME_CARD_RE.finditer(s))
        if not matches:
            raise RuntimeError('no story cards found in index.html to anchor the home section')
        s2 = s[:matches[0].start()] + start_marker + block_content + end_marker + s[matches[-1].end():]

    if s2 != original:
        io.open(path, 'w', encoding='utf-8').write(s2)
        print('written', 'index.html')


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
        print('written', 'sitemap.xml')


def generate(root, stories, home_arg):
    by_slug = {st['slug']: st for st in stories}
    en_ru_map = load_en_ru_map(root)
    footer = read_footer(root)
    css_version = read_css_version(root)
    icon, fonts, yandex, tg_click = read_shared(root)

    new_slugs_order = [st['slug'] for st in stories]
    for st in stories:
        slug = st['slug']
        canonical = BASE + slug + '/'
        hreflang = hreflang_block(canonical, en_ru_map.get(slug))
        more_parts = []
        for s in st['more']:
            tag, card = resolve_more_meta(root, s, by_slug)
            more_parts.append(f'  <a href="../{s}/"><small>{tag}</small>{card}</a>\n')
        more_html = ''.join(more_parts)
        page = story_page(st, hreflang, footer, css_version, icon, fonts, yandex, tg_click, more_html)
        out_path = os.path.join(root, slug, 'index.html')
        if write_if_changed(out_path, page):
            print('written', slug + '/index.html')

    update_hub(root, by_slug, new_slugs_order)
    home_slugs = home_arg.split(',') if home_arg else DEFAULT_HOME
    update_home(root, by_slug, home_slugs)
    update_sitemap(root, [(BASE + slug + '/', '0.7') for slug in new_slugs_order])


def main():
    ap = argparse.ArgumentParser(description='Generate the Russian stories section of the site from JSON data.')
    ap.add_argument('--check', action='store_true', help='validate the data only, do not write files')
    ap.add_argument('--root', default='.', help='site root to read from and write into')
    ap.add_argument('--home', default='', help='comma-separated slugs for the home page stories section')
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    problems = []
    stories, origin = load_stories(root, problems)
    data_slugs = {st.get('slug') for st in stories if isinstance(st, dict) and isinstance(st.get('slug'), str)}
    all_slugs = data_slugs | existing_page_slugs(root)

    for st in stories:
        if isinstance(st, dict):
            fname = origin.get(st.get('slug'), '?')
            validate_story(st, fname, all_slugs, root, problems)
            check_img(root, st, fname, problems)

    if problems:
        for msg in problems:
            print(msg)
        print(f'{len(problems)} problem(s) found')
        sys.exit(1)

    if args.check:
        print('ok: no problems found')
        sys.exit(0)

    generate(root, stories, args.home)
    print('done')


if __name__ == '__main__':
    main()
