#!/usr/bin/env python3
"""Repair/verify GA4 only; never rebuild editorial, layout or SEO content.

The measurement ID was verified from GA4 property 364751350 on 2026-10-05.
Run after HTML generation. --check verifies without writing any file.
"""
from __future__ import annotations
import argparse
import ast
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEASUREMENT_ID = "G-C3C0CEYX8Q"
OLD_ID = "G-C3COCEYX8Q"
BLOCK_RE = re.compile(r'[ \t]*<!-- analytics:start -->.*?<!-- analytics:end -->[ \t]*(?:\r?\n)?', re.S)
FUNCTION = '''def add_ga4(text: str) -> str:
    """Keep one GA4 block, preserving every byte outside the managed block."""
    match = re.search(r"</head\\s*>", text, re.I)
    if not match:
        return text
    text = re.sub(
        r'[ \\t]*<!-- analytics:start -->.*?<!-- analytics:end -->[ \\t]*(?:\\r?\\n)?',
        '', text, flags=re.S,
    )
    if 'googletagmanager.com/gtag/js' in text:
        raise ValueError("Unmanaged Google tag: review before adding another")
    match = re.search(r"</head\\s*>", text, re.I)
    assert match is not None
    block = f''' + "'''" + '''  <!-- analytics:start -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA4_MEASUREMENT_ID}');
  </script>
  <!-- analytics:end -->
''' + "'''" + '''
    return text[:match.start()] + block + text[match.start():]
'''


def repaired_source(source: str) -> str:
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'add_ga4']
    if len(nodes) != 1:
        raise RuntimeError('Expected exactly one add_ga4 function; refusing broad edits')
    n = nodes[0]
    lines = source.splitlines(keepends=True)
    source = ''.join(lines[:n.lineno - 1]) + FUNCTION + ''.join(lines[n.end_lineno:])
    source, count = re.subn(r'^GA4_MEASUREMENT_ID = "G-[A-Z0-9]+"$',
                           f'GA4_MEASUREMENT_ID = "{MEASUREMENT_ID}"', source, flags=re.M)
    if count != 1:
        raise RuntimeError('Expected exactly one measurement constant')
    compile(source, 'seo_foundation.py', 'exec')
    return source


def self_test() -> None:
    namespace = {'re': re, 'GA4_MEASUREMENT_ID': MEASUREMENT_ID}
    exec(compile(FUNCTION, '<ga4-unit-test>', 'exec'), namespace)
    add = namespace['add_ga4']
    for lang in ('ar', 'en', 'fr'):
        raw = f'<html lang="{lang}"><head>\n<title>Test</title>\n</head><body>unchanged</body></html>'
        once = add(raw)
        assert add(once) == once
        assert BLOCK_RE.sub('', once) == raw
        assert once.count('analytics:start') == 1
        assert once.count('googletagmanager.com/gtag/js') == 1
        duplicate = once.replace('</head>', BLOCK_RE.search(once).group(0) + '</head>')
        assert add(duplicate) == once
        assert add(once.replace(MEASUREMENT_ID, OLD_ID)) == once
    assert add('<body>no head</body>') == '<body>no head</body>'
    assert MEASUREMENT_ID in add('<HEAD></HEAD><body>unchanged</body>')
    print('GA4 self-tests: AR/EN/FR, idempotence, duplicates, incorrect ID, body preservation: PASS')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test()
    if args.self_test:
        return
    source_path = ROOT / 'scripts/seo_foundation.py'
    source = source_path.read_text(encoding='utf-8')
    fixed = repaired_source(source)
    if fixed != source:
        if args.check:
            raise RuntimeError('GA4 generator needs repair')
        source_path.write_text(fixed, encoding='utf-8')
    spec = importlib.util.spec_from_file_location('sayd_seo_ga4_check', source_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    stats = {'checked': 0, 'changed': 0, 'redirects_skipped': 0, 'no_head': 0, 'languages': {}}
    for page in sorted((ROOT / 'docs').rglob('*.html')):
        raw = page.read_text(encoding='utf-8')
        rel = page.relative_to(ROOT / 'docs')
        if (rel.as_posix() in module.ALIAS_REDIRECTS | module.CANCELLED_SHELLS
            or 'http-equiv="refresh"' in raw
            or (module.is_numeric_permalink_stub(rel) and 'location.replace' in raw)):
            stats['redirects_skipped'] += 1
            continue
        if not re.search(r'</head\s*>', raw, re.I):
            stats['no_head'] += 1
            continue
        updated = module.add_ga4(raw)
        assert BLOCK_RE.sub('', raw) == BLOCK_RE.sub('', updated), f'Non-analytics change: {rel}'
        assert module.add_ga4(updated) == updated, f'Not idempotent: {rel}'
        assert updated.count('analytics:start') == 1, str(rel)
        assert updated.count('googletagmanager.com/gtag/js') == 1, str(rel)
        assert OLD_ID not in updated, str(rel)
        assert f"gtag('config', '{MEASUREMENT_ID}');" in updated, str(rel)
        stats['checked'] += 1
        lang = 'en' if rel.parts[0] == 'en' else 'fr' if rel.parts[0] == 'fr' else 'ar'
        stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
        if updated != raw:
            stats['changed'] += 1
            if not args.check:
                page.write_text(updated, encoding='utf-8')
    print(json.dumps(stats, ensure_ascii=False))
    if args.check and stats['changed']:
        raise RuntimeError('Published HTML has missing, wrong or duplicated GA4 tags')


if __name__ == '__main__':
    main()
