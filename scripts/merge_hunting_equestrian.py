#!/usr/bin/env python3
"""Synchronize the combined door from its published, retained source listings.

No article bodies, dates, images, translations or legacy URLs are rewritten.
Calling sync_archive() after a publisher updates either old category keeps the
combined archive current. With JavaScript unavailable every story stays visible.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import site_ia as ia

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CARD_RE = re.compile(r'<article\b[^>]*class="(?:post-row|card)(?:\s[^"]*)?"[^>]*>.*?</article>', re.S)
LIST_RE = re.compile(r'<div class="(?:post-list|home-door-grid)">')
FILTER_RE = re.compile(r'\s*<!-- combined-archive:filters -->.*?<!-- /combined-archive:filters -->\s*', re.S)
LABELS = {
    "ar": ("الكل", "صيد", "فروسية", "تصفية الموضوعات", "موضوعًا"),
    "en": ("All", "Hunting", "Equestrian", "Filter stories", "stories"),
    "fr": ("Tous", "Chasse", "Équitation", "Filtrer les articles", "articles"),
}
MONTHS = {}
for names in (
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"],
):
    MONTHS.update({name.casefold(): index for index, name in enumerate(names, 1)})


def slug_of(card: str) -> str:
    hit = re.search(r'<h[23][^>]*>.*?href="[^"]*posts/([^/"?#]+)', card, re.S)
    if not hit:
        raise ValueError("Archive card has no article destination")
    return unquote(hit[1])


def stamp(card: str) -> datetime:
    hit = re.search(r'<div class="meta">(.*?)</div>', card, re.S)
    date = html.unescape(re.sub(r'<[^>]+>', '', hit[1])).strip() if hit else ''
    parsed = re.fullmatch(r'(\d{1,2})\s+(.+?)\s+(\d{4})', date)
    if not parsed or parsed[2].casefold() not in MONTHS:
        raise ValueError(f"Unrecognized publication date for {slug_of(card)}: {date}")
    return datetime(int(parsed[3]), MONTHS[parsed[2].casefold()], int(parsed[1]))


def cards(text: str) -> list[str]:
    main = re.search(r'<main\b[^>]*>.*?</main>', text, re.S)
    return CARD_RE.findall(main[0]) if main else []


def replace_listing(text: str, rows: list[str]) -> str:
    """Keep the exact legacy opening tag so existing publishers can prepend."""
    main = text.index('<main')
    opening = LIST_RE.search(text, main)
    if not opening:
        raise ValueError("Combined archive listing container is missing")
    depth = 1
    for token in re.finditer(r'<div\b[^>]*>|</div>', text[opening.end():]):
        depth += -1 if token[0] == '</div>' else 1
        if depth == 0:
            end = opening.end() + token.start()
            return text[:opening.end()] + '\n' + '\n'.join(rows) + '\n' + text[end:]
    raise ValueError("Combined archive listing container is unclosed")


def equestrian_primary_slugs(lang: str) -> set[str]:
    """Legacy editorial category remains a topic even though its door is merged."""
    slugs = set()
    for ar_slug, spec in ia.PRIMARY.items():
        if spec['door'] != 'equestrian':
            continue
        slug = ar_slug if lang == 'ar' else spec.get('en')
        if slug:
            if lang == 'fr':
                from seo_foundation import FR_SLUG_BY_EN
                slug = FR_SLUG_BY_EN.get(slug, slug)
            slugs.add(slug)
    return slugs


def retitle(text: str, lang: str, count: int) -> str:
    title = ia.door_label('hunting', lang)
    escaped = html.escape(title)
    # Category title/description only; published story titles remain untouched.
    suffix = "مجلة صيد" if lang == 'ar' else "Sayd Magazine"
    text = re.sub(r'<title>.*?</title>', f'<title>{escaped} — {suffix}</title>', text, count=1)
    text = re.sub(r'(<meta\b[^>]*(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)"[^>]*content=")[^"]*(")',
                  lambda m: m[1] + html.escape(title, quote=True) + m[2], text)
    text = re.sub(r'(<div class="breadcrumb">.*? / )[^<]+(</div>)',
                  lambda m: m[1] + escaped + m[2], text, count=1)
    text = re.sub(r'(<div class="section-head(?: [^"]+)?"><h[12]>)[^<]+',
                  lambda m: m[1] + escaped + ' ', text, count=1)
    text = re.sub(r'(<h2>[^<]*<span class="badge">)\d+(</span>)',
                  lambda m: m[1] + str(count) + m[2], text, count=1)
    return text


def filter_html(lang: str, equestrian: set[str], count: int) -> str:
    labels = LABELS[lang]
    controls = '\n'.join(
        f'<button type="button" data-archive-filter="{topic}" aria-pressed="{"true" if topic == "all" else "false"}">{html.escape(label)}</button>'
        for topic, label in zip(('all', 'hunting', 'equestrian'), labels[:3])
    )
    data = json.dumps({'equestrian': sorted(equestrian), 'countLabel': labels[4]}, ensure_ascii=False).replace('<', '\\u003c')
    return (
        '<!-- combined-archive:filters -->\n'
        f'<div class="archive-filters" role="group" aria-label="{labels[3]}" hidden>\n{controls}\n</div>\n'
        f'<p class="archive-result-count" role="status" aria-live="polite" hidden>{count} {labels[4]}</p>\n'
        f'<script type="application/json" id="combined-archive-data">{data}</script>\n'
        '<!-- /combined-archive:filters -->\n'
    )


def sync_archive(languages=('ar', 'en', 'fr')) -> dict[str, dict[str, int]]:
    """Idempotent union of published Hunting and retained Equestrian listings."""
    result = {}
    for lang in languages:
        root = DOCS / (lang if lang != 'ar' else '')
        target = root / 'category/صيد/index.html'
        legacy = root / 'category/فروسية/index.html'
        if not target.is_file() or not legacy.is_file():
            raise ValueError(f"Both source archives are required: {lang}")
        original = target.read_text(encoding='utf-8')
        old_rows = cards(original)
        equestrian_rows = cards(legacy.read_text(encoding='utf-8'))
        # Topic data survives a later publisher rewriting an old listing.
        saved = re.search(r'<script type="application/json" id="combined-archive-data">(.*?)</script>', original, re.S)
        equestrian = set(json.loads(saved[1])['equestrian']) if saved else set()
        equestrian.update(slug_of(row) for row in equestrian_rows)
        equestrian.update(equestrian_primary_slugs(lang))
        unique = {}
        for row in old_rows + equestrian_rows:
            unique.setdefault(slug_of(row), row)
        rows = sorted(unique.values(), key=stamp, reverse=True)
        equestrian.intersection_update(unique)
        text = FILTER_RE.sub('\n', original)
        text = replace_listing(text, rows)
        text = retitle(text, lang, len(rows))
        text = re.sub(r'\s*(<div class="(?:post-list|home-door-grid)">)',
                      lambda m: '\n' + filter_html(lang, equestrian, len(rows)) + m[1], text, count=1)
        style = '<link rel="stylesheet" href="/assets/css/combined-archive.css?v=20261017">'
        script = '<script src="/assets/js/combined-archive.js?v=20261017" defer></script>'
        if '/assets/css/combined-archive.css?' not in text:
            text = text.replace('</head>', '  ' + style + '\n</head>', 1)
        if '/assets/js/combined-archive.js?' not in text:
            text = text.replace('</body>', '  ' + script + '\n</body>', 1)
        if text != original:
            target.write_text(text, encoding='utf-8')
        result[lang] = {'all': len(rows), 'hunting': len(rows) - len(equestrian), 'equestrian': len(equestrian)}
    return result


if __name__ == '__main__':
    print(json.dumps(sync_archive(), ensure_ascii=False, indent=2))
