#!/usr/bin/env python3
"""Human-reviewed interview format collection, independent of primary topics.

No title-keyword inference, historical translation, or article rewriting occurs.
Registry publication dates are original dates, never update timestamps.
"""
from __future__ import annotations
import html
import json
import os
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from lxml import html as dom

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
REGISTRY = ROOT / 'content/interviews.json'
FOLDER = 'مقابلات'
LABELS = {'ar': 'مقابلات', 'en': 'Interviews', 'fr': 'Entretiens'}


def entries(lang='ar'):
    registry = json.loads(REGISTRY.read_text())
    assert registry['collection'] == 'interviews' and registry['version'] == 1
    rows = registry['entries']
    assert len({r['slug'] for r in rows}) == len(rows), 'Duplicate interview registry entry'
    for row in rows:
        assert row['reviewed_as'] == 'interview'
        assert row['languages']['ar'] == row['slug']
        date.fromisoformat(row['published_at'])
        assert set(row['languages']) <= {'ar', 'en', 'fr'}
    return sorted((r for r in rows if lang in r['languages'] and
                   (lang == 'ar' or date.fromisoformat(r['published_at']).year >= 2026)),
                  key=lambda r: (r['published_at'], r['slug']), reverse=True)


def homepage_slugs(lang='ar', c=None):
    """Return Arabic identities for eligible cards; resolve local URLs separately."""
    if c is None:
        c = json.loads((ROOT / 'content/homepage.json').read_text())
    blocked = set(c['featured'] + c['latest'] + c.get('omit_from_home', []) +
                  c.get('omit_from_home_desks', []))
    return [r['slug'] for r in entries(lang) if r['slug'] not in blocked][:4]


def sync_selection():
    path = ROOT / 'content/homepage.json'
    c = json.loads(path.read_text())
    chosen = homepage_slugs('ar', c)
    for section in c['ia_door_sections']:
        if section['door'] == 'interviews':
            section['slugs'] = chosen
    c['desk_slugs']['مقابلات'] = chosen
    c['desk_slugs']['Interviews'] = [r['languages']['en'] for r in entries('en')
                                   if r['slug'] in homepage_slugs('en', c)]
    path.write_text(json.dumps(c, ensure_ascii=False, indent=2) + '\n')
    return chosen


def source_cards(lang):
    """Read real published listings; the generated collection cannot source itself."""
    from merge_hunting_equestrian import cards, slug_of, stamp
    root = DOCS / (lang if lang != 'ar' else '')
    selected = entries(lang)
    wanted = {r['languages'][lang]: r for r in selected}
    found = {}
    sources = sorted((root / 'category').glob('*/index.html'))
    sources += sorted((root / 'articles').glob('*.html'))
    sources += sorted((root / 'stories').glob('*.html'))
    target_parent = root / 'category' / FOLDER
    for path in sources:
        if path.parent.name == FOLDER:
            continue
        for card in cards(path.read_text()):
            slug = slug_of(card)
            if slug not in wanted or slug in found:
                continue
            row = wanted[slug]
            dated = re.sub(r'(<div class="meta">)(.*?)(</div>)', lambda m:m[1]+m[2].split(' · ')[0]+m[3], card, flags=re.S)
            assert stamp(dated).date().isoformat() == row['published_at'], f'Interview publication date mismatch: {slug}'
            article = root / 'posts' / slug / 'index.html'
            assert article.is_file(), f'Missing published interview: {article}'
            article_tree = dom.parse(str(article))
            body = article_tree.xpath('//article[contains(concat(" ",normalize-space(@class)," ")," article-content ")]')
            assert body and len(body[0].text_content().strip()) > 20, f'Empty interview: {article}'
            def relocate(match):
                value = html.unescape(match[2])
                url = urlsplit(value)
                if url.scheme or url.netloc or value.startswith(('/', '#', 'data:')):
                    return match[0]
                resolved = (path.parent / unquote(url.path)).resolve()
                relative = os.path.relpath(resolved, target_parent)
                if url.query: relative += '?' + url.query
                if url.fragment: relative += '#' + url.fragment
                return match[1] + html.escape(relative, quote=True) + match[3]
            relocated = re.sub(r'((?:href|src)=")([^"]+)(")', relocate, card)
            node = dom.fromstring(relocated)
            title_node = node.xpath('.//h2/a | .//h3/a')[0]
            title = title_node.text_content().strip()
            href = title_node.get('href')
            # Rebuild the small archive card, never copy malformed legacy markup.
            # Explicit approved portraits win; then the source thumbnail, then
            # the article's own locally archived featured image.
            candidates = ([row['image']] if row.get('image') else [])
            candidates += node.xpath('.//img/@src')
            candidates += article_tree.xpath('//meta[@property="og:image"]/@content')
            image_file = None
            for value in candidates:
                url = urlsplit(value)
                if url.netloc not in ('', 'sayd-magazine.com', 'www.sayd-magazine.com'):
                    continue
                clean = unquote(url.path)
                candidate = (DOCS / clean.lstrip('/') if clean.startswith('/') else target_parent / clean).resolve()
                media_root = (DOCS / 'media').resolve()
                if candidate.is_relative_to(media_root) and candidate.is_file():
                    image_file = candidate
                    break
            thumb = ''
            if image_file:
                image = os.path.relpath(image_file, target_parent)
                thumb = '<a class="thumb" href="'+html.escape(href,quote=True)+'"><img src="'+html.escape(image,quote=True)+'" alt="'+html.escape(title,quote=True)+'" loading="lazy"></a>'
            meta_nodes = node.xpath('.//div[@class="meta"]')
            excerpt_nodes = node.xpath('.//p[@class="excerpt"]')
            meta = meta_nodes[0].text_content().strip() if meta_nodes else ''
            excerpt = excerpt_nodes[0].text_content().strip() if excerpt_nodes else ''
            relocated = ('<article class="post-row">'+thumb+'<div class="body">'
                         '<h2><a href="'+html.escape(href,quote=True)+'">'+html.escape(title)+'</a></h2>'
                         '<div class="meta">'+html.escape(meta)+'</div>'
                         '<p class="excerpt">'+html.escape(excerpt)+'</p></div></article>')
            found[slug] = relocated
    assert wanted.keys() <= found.keys(), f'Missing published interview cards: {wanted.keys() - found.keys()}'
    return [found[r['languages'][lang]] for r in selected]


def sync_archives(languages=('ar', 'en', 'fr')):
    """Reuse language-local archive chrome and card markup at the same path depth."""
    from merge_hunting_equestrian import replace_listing, FILTER_RE
    from seo_foundation import add_ga4
    counts = {}
    for lang in languages:
        root = DOCS / (lang if lang != 'ar' else '')
        template = root / 'category/صيد/index.html'
        text = template.read_text()
        rows = source_cards(lang)
        text = replace_listing(FILTER_RE.sub('\n', text), rows)
        text = re.sub(r'\s*<(?:link|script)\b[^>]*(?:src|href)="/assets/(?:css|js)/combined-archive\.[^" ]+"[^>]*(?:></script>|>)', '', text)
        title = LABELS[lang]
        escaped = html.escape(title)
        suffix = 'مجلة صيد' if lang == 'ar' else 'Sayd Magazine'
        text = re.sub(r'<title>.*?</title>', f'<title>{escaped} — {suffix}</title>', text, count=1)
        text = re.sub(r'(<meta\b[^>]*(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)"[^>]*content=")[^"]*(")', lambda m: m[1]+escaped+m[2], text)
        text = re.sub(r'(<div class="breadcrumb">.*? / )[^<]+(</div>)', lambda m: m[1]+escaped+m[2], text, count=1)
        text = re.sub(r'(<div class="section-head(?: [^"]+)?"><h[12]>)[^<]+', lambda m: m[1]+escaped+' ', text, count=1)
        text = re.sub(r'(<h2>[^<]*<span class="badge">)\d+(</span>)', lambda m: m[1]+str(len(rows))+m[2], text, count=1)
        # Change self-identifying SEO URLs only; all navigation/topic links stay intact.
        text = re.sub(r'(<(?:link|meta)\b[^>]*(?:href|content)=")(https://sayd-magazine\.com/(?:en/|fr/)?category/)(?:صيد|%D8%B5%D9%8A%D8%AF)(/[^" ]*)(")', lambda m: m[1]+m[2]+quote(FOLDER)+m[3]+m[4], text)
        def breadcrumb_json(match):
            data = json.loads(match[1])
            if data.get('@type') == 'BreadcrumbList':
                for item in data.get('itemListElement', []):
                    if item.get('position') == 2:
                        item['name'] = title
                        item['item'] = 'https://sayd-magazine.com/' + (lang+'/' if lang!='ar' else '') + 'category/' + quote(FOLDER) + '/'
            return '<script type="application/ld+json">'+json.dumps(data, ensure_ascii=False, separators=(',',':'))+'</script>'
        text = re.sub(r'<script type="application/ld\+json">(.*?)</script>', breadcrumb_json, text, flags=re.S)
        if '<script type="application/ld+json">' not in text:
            base = 'https://sayd-magazine.com/' + (lang+'/' if lang!='ar' else '')
            breadcrumb = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[
                {'@type':'ListItem','position':1,'name':{'ar':'الرئيسية','en':'Home','fr':'Accueil'}[lang],'item':base},
                {'@type':'ListItem','position':2,'name':title,'item':base+'category/'+quote(FOLDER)+'/'}]}
            text = text.replace('</head>', '<script type="application/ld+json">'+json.dumps(breadcrumb,ensure_ascii=False,separators=(',',':'))+'</script>\n</head>', 1)

        target = root / 'category' / FOLDER / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        from interview_sharing import add_sharing, friendly_view
        text = add_ga4(add_sharing(text, lang, DOCS, target))
        # Keep the search stylesheet immediately before analytics, matching the
        # shared search rebuild's stable ordering.
        search_style = re.search(r'<link rel="stylesheet" href="[^" ]*search-entry\.css[^" ]*">\n', text)
        if search_style:
            text = text.replace(search_style[0], '', 1)
            text = text.replace('  <!-- analytics:start -->', search_style[0] + '  <!-- analytics:start -->', 1)
        target.write_text(text)
        friendly = root / 'interviews/index.html'
        friendly.parent.mkdir(parents=True, exist_ok=True)
        friendly.write_text(friendly_view(text, target, friendly))
        counts[lang] = len(rows)
    return counts


if __name__ == '__main__':
    print(sync_selection())
    print(sync_archives())
