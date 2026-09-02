#!/usr/bin/env python3
"""Walks every index.html and 404.html under the site root and reports broken href/src targets.
Usage: python3 tools/check-links.py [ROOT]"""
import io, os, re, sys

ATTR_RE = re.compile(r'''(?:href|src)\s*=\s*"([^"]*)"''')
SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.\-]*:')
SKIP_SCHEMES = ('mailto:', 'tel:', 'data:')


def targets(src):
    return ATTR_RE.findall(src)


def is_skippable(href):
    href = href.strip()
    if not href or href.startswith('#'):
        return True
    if href.startswith('//'):
        return True
    if href.startswith(SKIP_SCHEMES):
        return True
    if SCHEME_RE.match(href) and not href.startswith('/'):
        return True
    return False


def resolve(root, file_path, href):
    href = href.split('#', 1)[0].split('?', 1)[0]
    if not href:
        return None
    if href.startswith('/'):
        target = os.path.join(root, href.lstrip('/'))
    else:
        target = os.path.join(os.path.dirname(file_path), href)
    return os.path.normpath(target)


def target_exists(target):
    if os.path.isfile(target):
        return True
    if os.path.isdir(target) and os.path.isfile(os.path.join(target, 'index.html')):
        return True
    return False


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
    broken = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            if name not in ('index.html', '404.html'):
                continue
            path = os.path.join(dirpath, name)
            with io.open(path, encoding='utf-8') as f:
                src = f.read()
            for href in targets(src):
                if is_skippable(href):
                    continue
                target = resolve(root, path, href)
                if target is None:
                    continue
                if not target_exists(target):
                    broken.append((os.path.relpath(path, root), href))
    if broken:
        for path, href in broken:
            print(f'{path}: broken link {href}')
        print(f'{len(broken)} broken link(s)')
        sys.exit(1)
    print('ok: no broken links')
    sys.exit(0)


if __name__ == '__main__':
    main()
