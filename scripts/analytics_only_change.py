"""Recognize ONLY the exact approved GA4 snippet on existing pages.

A measurement-ID correction is not a republication of the historic archive.
No arbitrary marker content, script, editorial, image, date, layout, or new
page is exempt. All bytes outside these exact snippets must stay identical.
"""
import argparse
import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = 'G-C3C0CEYX8Q'
PREVIOUS = 'G-C3COCEYX8Q'
BLOCK = re.compile(r'[ \t]*<!-- analytics:start -->.*?<!-- analytics:end -->[ \t]*(?:\r?\n)?', re.S)
TEMPLATE = '''  <!-- analytics:start -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=MEASUREMENT_ID"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'MEASUREMENT_ID');
  </script>
  <!-- analytics:end -->
'''

def approved(mid):
    return TEMPLATE.replace('MEASUREMENT_ID', mid)

def unchanged_except_approved_ga4(before, after):
    old = list(BLOCK.finditer(before))
    new = list(BLOCK.finditer(after))
    if len(new) != 1 or new[0].group().strip() != approved(CURRENT).strip():
        return False
    allowed = {approved(CURRENT).strip(), approved(PREVIOUS).strip()}
    if any(m.group().strip() not in allowed for m in old):
        return False
    for text, matches in ((before, old), (after, new)):
        heads = list(re.finditer(r'<head\b[^>]*>.*?</head\s*>', text, re.S | re.I))
        if len(heads) != 1:
            return False
        if any(not (heads[0].start() <= m.start() and m.end() <= heads[0].end()) for m in matches):
            return False
    return BLOCK.sub('', before) == BLOCK.sub('', after)

def analytics_only_repair(file, base):
    if not base:
        return False
    old = subprocess.run(['git', 'show', f'{base}:{file}'], cwd=ROOT, capture_output=True)
    if old.returncode:
        return False  # New pages always require full AR/EN/FR publication checks.
    try:
        after = (ROOT / file).read_text(encoding='utf-8')
        before = old.stdout.decode('utf-8')
    except (OSError, UnicodeError):
        return False
    return unchanged_except_approved_ga4(before, after)

def self_test():
    raw = '<html><head>\n<title>Original</title>\n</head><body>Original <img src="original.jpg"></body></html>'
    before = raw.replace('</head>', approved(PREVIOUS) + '</head>')
    after = raw.replace('</head>', approved(CURRENT) + '</head>')
    assert unchanged_except_approved_ga4(before, after)
    assert unchanged_except_approved_ga4(raw, after)
    assert unchanged_except_approved_ga4(before.replace('</head>', approved(PREVIOUS) + '</head>'), after)
    for modified in (after.replace('Original', 'Changed', 1),
                     after.replace('original.jpg', 'other.jpg'),
                     after.replace('</body>', '<p>New text</p></body>'),
                     after.replace('analytics:end', 'analytics:fake'),
                     after.replace("gtag('js'", "other('js'"),
                     after.replace('<!-- analytics:end -->', '<p>Hidden story</p><!-- analytics:end -->'),
                     after.replace(CURRENT, 'G-UNAPPROVED'),
                     after.replace('</head>', approved(CURRENT) + '</head>')):
        assert not unchanged_except_approved_ga4(before, modified)
    assert not unchanged_except_approved_ga4('', after)
    outside = raw.replace('</body>', approved(CURRENT) + '</body>')
    assert not unchanged_except_approved_ga4(raw, outside)
    print('PASS: exact GA4-only recognition; title/image/body/script/new-page changes remain rejected')

def install():
    path = ROOT / 'scripts/check_publication_contract.py'
    source = path.read_text(encoding='utf-8')
    import_line = 'from analytics_only_change import analytics_only_repair\n'
    if import_line not in source:
        anchor = 'import seo_foundation as seo\n'
        if source.count(anchor) != 1:
            raise RuntimeError('Unexpected publication checker; refusing patch')
        source = source.replace(anchor, anchor + import_line, 1)
    guard = '        if analytics_only_repair(file,base):\n            continue\n'
    if guard not in source:
        anchor = '        if archive_image_repair(file,base):\n'
        if source.count(anchor) != 1:
            raise RuntimeError('Unexpected story classifier; refusing patch')
        source = source.replace(anchor, guard + anchor, 1)
    ast.parse(source)
    if source != path.read_text(encoding='utf-8'):
        path.write_text(source, encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    self_test()
    if args.install:
        install()
