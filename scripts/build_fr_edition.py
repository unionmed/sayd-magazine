#!/usr/bin/env python3
"""Build reviewed French 2026 article pages from the corresponding English HTML.

Fails closed: missing articles or missing translated blocks never reach docs/fr.
The second-pass audit runs separately in audit_fr_edition.py.
"""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, unquote
from lxml import html
from html import escape, unescape

import seo_foundation as seo

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
MANIFEST = json.loads((ROOT / 'content/fr/edition-2026.json').read_text())
FR = ROOT / 'content/fr/segments'
ITEMS = {x['slug']: x for x in MANIFEST['articles']}
BASE = 'https://sayd-magazine.com'
CATS = {
    'صيد': 'Chasse', 'عتاد-وسلاح-الصيد': 'Tir et équipement',
    'فروسية': 'Équitation', 'حياة-برية-وتخييم': 'Faune et camping',
    'ثقافة-وتراث': 'Poésie et arts', 'قوانين': 'Réglementation de la chasse',
    'موسوعة-الطيور': 'Encyclopédie des oiseaux', 'استديو-صيد': 'Sayd TV',
    'صور': 'Photos', 'الصقارة': 'Fauconnerie', 'صيد-الطيور': 'Chasse aux oiseaux',
    'صيد-بري': 'Chasse terrestre', 'صيد-بحري': 'Pêche en mer',
}
UI = {
    'Home':'Accueil', 'Stories':'Articles', 'Article':'Article', 'Team':'Équipe', 'Contact':'Contact',
    'Hunting':'Chasse', 'Shooting & Gear':'Tir et équipement',
    'Equestrian':'Équitation', 'Wildlife & Camping':'Faune et camping',
    'Wildlife':'Faune', 'Poetry & Art':'Poésie et arts',
    'Hunting Laws':'Réglementation de la chasse',
    'Bird Encyclopedia':'Encyclopédie des oiseaux', 'Sayd TV':'Sayd TV',
    'Photos':'Photos', 'More':'Plus', 'Menu':'Menu', 'Updates':'Actualités',
    'From Sayd’s Memory':'Dans les archives de Sayd', 'See all':'Voir tout',
    'All stories':'Tous les articles', 'Sections':'Rubriques', 'Pages':'Pages',
    'Archive':'Archives', 'Subscribe by email':'S’abonner par courriel',
    'Skip to content':'Aller au contenu', 'Top links':'Liens utiles',
    'Main menu':'Menu principal', 'Mobile menu':'Menu mobile',
    'From every valley, a story':'De chaque vallée, une histoire',
    'Follow Sayd':'Suivre Sayd', 'Share this story':'Partager cet article',
    'Share':'Partager', 'Link copied':'Lien copié', 'Doors':'Rubriques',
    'Language':'Langues', 'Featured stories and latest news':'À la une et dernières nouvelles',
    'September 2026 stories':'Articles de septembre 2026', 'Related':'À lire aussi',
    'Magazine':'Magazine', 'Read the interview':'Lire l’entretien',
    'The magazine of nature’s masters on land, sea, and sky':
        'Le magazine des passionnés de nature, sur terre, en mer et dans le ciel',
    'Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 September 2016':
        'Autorisé par le Conseil national des médias au Liban, avis officiel nº 157 du 5 septembre 2016',
}
STATIC_COPY = {
 'team': {
  'Team':'Équipe', 'Page':'Page', 'Publisher and editor-in-chief':'Éditeur et rédacteur en chef',
  'General manager':'Directeur général', 'Managing editor':'Rédactrice en chef adjointe',
  'Website manager':'Responsable du site', 'Legal counsel':'Conseil juridique',
  'Lawyer Ziad Al-Khazen':'Me Ziad Al-Khazen', 'Public relations':'Relations publiques',
  'Office director: Rona Abi Assi':'Directrice du bureau : Rona Abi Assi',
  'External relations and translation':'Relations extérieures et traduction',
  'Desks':'Rubriques', 'Hunting and field photography: Fouad Itani':'Chasse et photographie de terrain : Fouad Itani',
  'Equestrian: Donna Kazzi':'Équitation : Donna Kazzi', 'Shooting: Joelle Akiki':'Tir : Joelle Akiki',
  'Gear and arms: Hani Al-Ahmad':'Équipement et armes : Hani Al-Ahmad',
  'Eco-tourism: Aoun Abi Aoun':'Écotourisme : Aoun Abi Aoun',
  'Sports: Tony Bajani':'Sports : Tony Bajani', 'Your health in nature: Rita Haddad':'Votre santé dans la nature : Rita Haddad',
  'Miscellany: Abdel Hadi Saab':'Divers : Abdel Hadi Saab',
  'Poetry & Art: visual artist Saad Shaiban':'Poésie et arts : Saad Shaiban, artiste plasticien',
  'Photography: Hussein Idriss':'Photographie : Hussein Idriss',
  'This is an English stub of the masthead. The Arabic team page remains the full reference.':
    'Cette présentation résume l’équipe. La page arabe reste la référence complète.',
  'Team:':'Équipe :'
 },
 'contact': {
  'Contact':'Contact', 'Page':'Page',
  'Sharing experience and information raises the level of knowledge. Write to us — with a story, a question, or a field note.':
    'Partager expériences et informations enrichit les connaissances. Écrivez-nous pour proposer une histoire, poser une question ou transmettre une observation de terrain.',
  'Email:':'Courriel :', 'publisher and editor-in-chief':'éditeur et rédacteur en chef',
  'general manager':'directeur général', 'See the English team stub':'Voir l’équipe',
  '(publisher and editor-in-chief)':'(éditeur et rédacteur en chef)',
  '(general manager)':'(directeur général)'
 },
 'about': {'About us':'À propos', 'Page':'Page',
  'Sayd is the magazine of nature’s masters on land, sea, and sky — hunting, wildlife, birds, equestrian sport, and heritage from Lebanon and the Arab world. Founded in 2012.':
  'Sayd est le magazine des passionnés de nature, sur terre, en mer et dans le ciel : chasse, faune sauvage, oiseaux, équitation et patrimoine au Liban et dans le monde arabe. Fondé en 2012.'},
 'license': {'License':'Licence', 'Page':'Page',
  'Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 September 2016.':
  'Autorisé par le Conseil national des médias au Liban, avis officiel nº 157 du 5 septembre 2016.',
  'Licensed by the National Media Council in Lebanon under official notice No. 157 dated 5 septembre 2016.':
  'Autorisé par le Conseil national des médias au Liban, avis officiel nº 157 du 5 septembre 2016.'},
}
MONTHS = {'January':'janvier','February':'février','March':'mars',
          'April':'avril','May':'mai','June':'juin','July':'juillet',
          'August':'août','September':'septembre','October':'octobre',
          'November':'novembre','December':'décembre'}
MONTH_INDEX = {name: index for index, name in enumerate(MONTHS)}
MONTH_INDEX.update({french: index for index, french in enumerate(MONTHS.values())})


def source_blocks(body):
    return [e for e in body if e.tag in ('p', 'h2', 'h3', 'h4', 'blockquote', 'aside', 'ul', 'ol')]


def validate() -> dict:
    translations = {}
    problems = []
    for item in MANIFEST['articles']:
        slug = item['slug']
        path = FR / f'{slug}.json'
        if not path.exists():
            problems.append(f'{slug}: missing translation')
            continue
        data = json.loads(path.read_text())
        source = html.parse(str(DOCS / 'en/posts' / slug / 'index.html'))
        bodies = source.xpath('//article[contains(@class,"article-content")]')
        if len(bodies) != 1:
            problems.append(f'{slug}: source body missing')
            continue
        blocks = source_blocks(bodies[0])
        figures = bodies[0].xpath('./figure')
        if len(data.get('blocks', [])) != len(blocks):
            problems.append(f'{slug}: {len(data.get("blocks", []))}/{len(blocks)} translated blocks')
        if len(data.get('figures', [])) != len(figures):
            problems.append(f'{slug}: {len(data.get("figures", []))}/{len(figures)} translated figures')
        if not data.get('title'):
            problems.append(f'{slug}: missing title')
        translations[slug] = data
    if problems:
        raise SystemExit('French edition incomplete:\n' + '\n'.join(problems))
    return translations


def content(el, value: str):
    for child in list(el): el.remove(child)
    el.text = None
    fragments = html.fragments_fromstring(value)
    last = None
    for part in fragments:
        if isinstance(part, str):
            if last is None: el.text = (el.text or '') + part
            else: last.tail = (last.tail or '') + part
        else:
            el.append(part)
            last = part


def date_fr(s: str) -> str:
    for en, fr in MONTHS.items():
        s = s.replace(en, fr)
    return s


def translate_text_nodes(tree, translations):
    titles = {ITEMS[s]['english_title']: d['title'] for s,d in translations.items()}
    for e in tree.iter():
        for field in ('text', 'tail'):
            val = getattr(e, field)
            if not val or not val.strip(): continue
            stripped = val.strip()
            new = titles.get(stripped, UI.get(stripped, stripped))
            new = date_fr(new)
            if new != stripped:
                setattr(e, field, val.replace(stripped, new))
        for attr in ('alt','aria-label','title','data-copied'):
            val = e.get(attr)
            if val:
                e.set(attr, date_fr(titles.get(val, UI.get(val,val))))


def head(tree, slug: str | None, title: str, ar_href: str | None):
    h = tree.find('.//head')
    for e in h.xpath('.//link[@rel="canonical" or @rel="alternate"] | .//meta[starts-with(@property,"og:") or starts-with(@name,"twitter:")]'):
        e.getparent().remove(e)
    tree.xpath('//title')[0].text = title + ' | Sayd Magazine'
    d = tree.xpath('//meta[@name="description"]')
    if d: d[0].set('content', title)


def chrome(tree, slug: str | None, translations):
    tree.getroot().set('lang','fr')
    tree.getroot().set('dir','ltr')
    translate_text_nodes(tree, translations)
    for nav in tree.xpath('//nav[contains(@class,"lang-switch")]'):
        content(nav, '<a href="' + ('../../../' if slug else '../') + 'index.html" lang="ar" hreflang="ar">العربية</a> '
                + '<a href="' + ('../../../en/posts/'+slug+'/index.html' if slug else '../en/index.html') + '" lang="en" hreflang="en">English</a> '
                + '<a href="' + ('index.html' if slug else 'index.html') + '" lang="fr" hreflang="fr" class="is-current" aria-current="page">Français</a>')
    for a in tree.xpath('//a[@href]'):
        href=a.get('href')
        if any('lang-switch' in (p.get('class') or '') or 'lang-twin' in (p.get('class') or '') for p in a.iterancestors()):
            continue
        if '%2Fen%2Fposts%2F' in href:
            a.set('href',href.replace('%2Fen%2Fposts%2F','%2Ffr%2Fposts%2F'))
            continue
        if slug and href.startswith('../../../posts/'):
            continue
        if href.startswith('https://') or href.startswith('mailto:') or href.startswith('#'): continue
        # The /fr/ tree mirrors /en/; references to ../en/ must point at this edition.
        a.set('href', href.replace('../en/', '../fr/').replace('../../en/', '../../fr/'))


def prune_and_translate_cards(tree, translations):
    for a in list(tree.xpath('//a[@href]')):
        if any('lang-switch' in (p.get('class') or '') or 'lang-twin' in (p.get('class') or '') or 'article-content' in (p.get('class') or '') for p in a.iterancestors()):
            continue
        href=a.get('href') or ''
        match=re.search(r'(?:^|/)posts/([^/]+)/index\.html',href)
        if not match and href.startswith('../') and '/index.html' in href:
            match=re.search(r'^\.\./([^/]+)/index\.html',href)
        if not match: continue
        slug=match.group(1)
        if slug in translations:
            label=a.text_content().strip()
            if label and not a.xpath('.//img') and a.getparent().tag not in ('figcaption',):
                a.text=translations[slug]['title']
                for child in list(a): a.remove(child)
            for img in a.xpath('.//img[@alt]'): img.set('alt',translations[slug]['title'])
        else:
            ancestor=next((p for p in a.iterancestors() if p.tag=='article'),None)
            if ancestor is not None and ancestor.getparent() is not None:
                ancestor.getparent().remove(ancestor)
            elif any('ticker' in (p.get('class') or '') for p in a.iterancestors()) and a.getparent() is not None:
                a.getparent().remove(a)


def category_slug(item):
    source=html.parse(str(DOCS/'en/posts'/item['slug']/'index.html'))
    badge=source.xpath('//header[contains(@class,"article-header")]//a[contains(@class,"badge")]/@href')
    if not badge: return None
    m=re.search(r'category/([^/]+)/',badge[0]); return m.group(1) if m else None


LANG_NAV_RE = re.compile(r'(<nav class="lang-switch"[^>]*>)(.*?)(</nav>)', re.S)
TICKER_RE = re.compile(r'<div class="ticker"(?: aria-hidden="true")?>.*?</div>', re.S)
CSS_TOKEN = '20260929-door-date'


def category_public(prefix: str, slug: str) -> str:
    return f'{prefix}category/{quote(slug, safe="")}/'


def fr_public_slug(slug: str) -> str:
    """French public post slug. Twins such as automne-chasse-arabe-2026 win over the English slug."""
    return seo.FR_SLUG_BY_EN.get(slug, slug)


def _url_parts(url: str) -> tuple[str, str, str]:
    path, _, frag = url.partition('#')
    path, _, query = path.partition('?')
    return path, query, frag


def _join_url(path: str, query: str, frag: str) -> str:
    url = path
    if query:
        url += '?' + query
    if frag:
        url += '#' + frag
    return url


def absolutize_fr_href(url: str) -> str:
    """Root-absolute French edition path. External, mail, and hash links stay put."""
    if not url or url.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'data:', 'javascript:')):
        return url
    path, query, frag = _url_parts(url)
    if path in ('/fr/', '/fr/index.html') or re.fullmatch(r'(?:\.\./)*fr/index\.html', path):
        return '/fr/'
    post = re.search(r'(?:^|/)posts/([^/?#]+?)(?:/index\.html|/)?$', path)
    if post:
        slug = fr_public_slug(unquote(post.group(1)))
        return _join_url(f'/fr/posts/{slug}/', '', frag)
    category = re.search(r'(?:^|/)category/([^/?#]+?)(?:/index\.html|/)?$', path)
    if category:
        slug = quote(unquote(category.group(1)), safe='')
        return _join_url(f'/fr/category/{slug}/', '', frag)
    page = re.search(r'(?:^|/)(team|contact|about|license|stories)(?:/index\.html)?/?$', path)
    if page:
        return f'/fr/{page.group(1)}/'
    asset = re.search(r'(?:^|/)((?:assets|media)/.+)$', path)
    if asset:
        return _join_url('/' + asset.group(1), query, frag)
    return url


def absolutize_fr_tree(tree) -> None:
    for element in tree.xpath('//*[@href or @src]'):
        if any('lang-switch' in (parent.get('class') or '') for parent in element.iterancestors()):
            continue
        for attr in ('href', 'src'):
            value = element.get(attr)
            if value:
                element.set(attr, absolutize_fr_href(value))


FR_TAGLINE = (
    'Le magazine des passionnés de nature, sur terre, en mer et dans le ciel'
)
EN_CHROME_MARKERS = (
    '>Hunting<', '>Shooting &amp; Gear<', '>Shooting & Gear<', '>Equestrian<',
    '>Wildlife &amp; Camping<', '>Wildlife & Camping<', '>Poetry &amp; Art<',
    '>Poetry & Art<', '>Hunting Laws<', '>Bird Encyclopedia<',
    'aria-label="Main menu"', 'aria-label="Mobile menu"', 'aria-label="Language"',
    'aria-label="Top links"', '>Skip to content<', '>Home<', '>Stories<', '>Team<',
)


def listing_card(entry: dict) -> str:
    href = f"/fr/posts/{fr_public_slug(entry['slug'])}/"
    title = escape(entry['title'])
    alt = escape(entry.get('alt') or entry['title'])
    image = entry.get('image') or ''
    if image.startswith(('http://', 'https://')):
        src = escape(image, quote=True)
    else:
        src = escape(absolutize_fr_href(image), quote=True)
    date = escape(date_fr(entry.get('date') or ''))
    return (
        '<article class="card">'
        f'<a class="thumb" href="{href}"><img src="{src}" alt="{alt}" loading="lazy"></a>'
        f'<div class="body"><h2><a href="{href}">{title}</a></h2>'
        f'<div class="meta">{date}</div></div></article>'
    )


def _month_index(date: str) -> int:
    names = sorted(MONTH_INDEX.items(), key=lambda item: -len(item[0]))
    for name, index in names:
        if name in date:
            return index
    return 0


def listing_sort_key(record: dict) -> tuple[int, int, int]:
    date = record.get('date') or ''
    year_match = re.search(r'\d{4}', date)
    day_match = re.search(r'\d+', date)
    year = int(year_match.group()) if year_match else 0
    day = int(day_match.group()) if day_match else 0
    return (year, _month_index(date), day)


def post_category_slug(slug: str) -> str | None:
    page = DOCS / 'fr' / 'posts' / slug / 'index.html'
    if not page.is_file():
        return None
    badge = html.parse(str(page)).xpath('//a[contains(@class,"badge")]/@href')
    if not badge:
        return None
    match = re.search(r'category/([^/]+)/', badge[0])
    return unquote(match.group(1)) if match else None


def harvest_extra_listing_cards(known: set[str]) -> list[dict]:
    """Cards published onto French listings outside the 2026 manifest.

    Autumn hunting and the equestrian essay use their own French slugs.
    Rebuilding the grid from the manifest alone would drop them.
    """
    extras: dict[str, dict] = {}
    pages: list[tuple[Path, str | None]] = [
        (path, path.parent.name) for path in sorted((DOCS / 'fr' / 'category').glob('*/index.html'))
    ]
    stories = DOCS / 'fr' / 'stories' / 'index.html'
    if stories.is_file():
        pages.append((stories, None))
    for path, category in pages:
        if not path.is_file():
            continue
        tree = html.parse(str(path))
        for card in tree.xpath('//main//article[contains(@class,"card")]'):
            links = card.xpath('.//a[@href]')
            if not links:
                continue
            href = links[0].get('href') or ''
            match = re.search(r'(?:^|/)posts/([^/"#]+)/', unquote(href))
            if not match:
                continue
            slug = fr_public_slug(match.group(1))
            if slug in known or slug in extras:
                continue
            images = card.xpath('.//img')
            titles = card.xpath('.//h2//a|.//h3//a')
            meta = card.xpath('.//*[contains(@class,"meta")]')
            title = unescape(titles[0].text_content()).strip() if titles else slug
            extras[slug] = {
                'slug': slug,
                'title': title,
                'alt': unescape(images[0].get('alt') or title) if images else title,
                'date': unescape(meta[0].text_content()).strip() if meta else '',
                'image': images[0].get('src') or '' if images else '',
                'category_slug': category or post_category_slug(slug),
            }
    return list(extras.values())


def collect_listing_records(translations: dict) -> list[dict]:
    records = []
    for item in MANIFEST['articles']:
        src = html.parse(str(DOCS / 'en' / 'posts' / item['slug'] / 'index.html'))
        img = src.xpath('//meta[@property="og:image"]/@content') or src.xpath('//article[contains(@class,"article-content")]//img/@src')
        image = ''
        if img:
            image = img[0]
            if image.startswith(BASE):
                image = image[len(BASE):]
            image = image.replace('../../../', '').replace('../../', '')
        records.append({
            **item,
            'slug': fr_public_slug(item['slug']),
            'title': translations[item['slug']]['title'],
            'image': image or 'media/brand/sayd-logo.png',
            'category_slug': category_slug(item),
        })
    known = {record['slug'] for record in records}
    records.extend(harvest_extra_listing_cards(known))
    records.sort(key=listing_sort_key, reverse=True)
    return records


def listing_switch(rel: str) -> tuple[str, str, str] | None:
    """Root-absolute AR / EN / FR twins for a French listing page."""
    if rel == 'fr/stories/index.html':
        # Arabic /stories/ is not a page; the archive lives at /articles/.
        return ('/articles/', '/en/stories/', '/fr/stories/')
    match = re.fullmatch(r'fr/category/([^/]+)/index\.html', rel)
    if not match:
        return None
    return (
        category_public('/', match.group(1)),
        category_public('/en/', match.group(1)),
        category_public('/fr/', match.group(1)),
    )


def french_ticker_blocks() -> list[str] | None:
    """Homepage ticker, with post links rooted at /fr/ so category pages cannot escape."""
    home = DOCS / 'fr' / 'index.html'
    if not home.is_file():
        return None
    blocks = TICKER_RE.findall(home.read_text(encoding='utf-8'))
    if len(blocks) < 2:
        return None

    def absolutize(block: str) -> str:
        def repl(match: re.Match[str]) -> str:
            href = match.group(1)
            path, _, frag = href.partition('#')
            post = re.search(r'(?:^|/)posts/(.+)$', path)
            if not post:
                return match.group(0)
            slug = re.sub(r'(?:/index\.html|/)+$', '', post.group(1)).strip('/')
            slug = fr_public_slug(unquote(slug))
            suffix = '#' + frag if frag else ''
            return f'href="/fr/posts/{slug}/{suffix}"'
        return re.sub(r'href="([^"]*)"', repl, block)

    visible, hidden = absolutize(blocks[0]), absolutize(blocks[1])
    if 'aria-hidden' not in hidden:
        hidden = hidden.replace('<div class="ticker">', '<div class="ticker" aria-hidden="true">', 1)
    return [visible, hidden]


def patch_listing_html(text: str, switch: tuple[str, str, str]) -> str:
    ar, en, fr = switch
    nav = (
        f'<a href="{ar}" lang="ar" hreflang="ar">العربية</a> '
        f'<a href="{en}" lang="en" hreflang="en">English</a> '
        f'<a href="{fr}" lang="fr" hreflang="fr" class="is-current" aria-current="page">Français</a>'
    )
    text, count = LANG_NAV_RE.subn(lambda match: match.group(1) + nav + match.group(3), text, count=1)
    if not count:
        return text
    blocks = french_ticker_blocks()
    if blocks:
        index = {'n': 0}

        def repl(match: re.Match[str]) -> str:
            block = blocks[min(index['n'], len(blocks) - 1)]
            index['n'] += 1
            return block

        text = TICKER_RE.sub(repl, text)
    return text


def order_like_existing(entries: list[dict], path: Path) -> list[dict]:
    """Keep the published card order when a listing is regenerated.

    Same-day stories were prepended by later publishes. A fresh date sort
    would bury those leads under other cards from the same day.
    """
    page = DOCS / path
    by_slug: dict[str, dict] = {}
    for entry in entries:
        by_slug.setdefault(fr_public_slug(entry['slug']), entry)
    if not page.is_file():
        return entries
    ordered: list[dict] = []
    seen: set[str] = set()
    tree = html.parse(str(page))
    for card in tree.xpath('//main//article[contains(@class,"card")]'):
        links = card.xpath('.//a[@href]')
        if not links:
            continue
        match = re.search(r'(?:^|/)posts/([^/"#]+)/', unquote(links[0].get('href') or ''))
        if not match:
            continue
        slug = fr_public_slug(match.group(1))
        if slug in seen or slug not in by_slug:
            continue
        ordered.append(by_slug[slug])
        seen.add(slug)
    for entry in entries:
        slug = fr_public_slug(entry['slug'])
        if slug not in seen:
            ordered.append(entry)
            seen.add(slug)
    return ordered


def listing_page(title, entries, translations, path, depth=0):
    """French listing chrome is the French homepage, never the English one.

    Card, door, and brand links are root-absolute so `/fr/category/<slug>/`
    (no index.html) cannot resolve `../../posts` out of the French edition.
    `depth` is unused; listings no longer depend on relative path depth.
    """
    del translations, depth
    entries = order_like_existing(entries, Path(path))
    tree = html.parse(str(DOCS / 'fr' / 'index.html'))
    main = tree.xpath('//main')[0]
    empty_note = '<p>Aucun article de 2026 dans cette rubrique pour le moment.</p>' if not entries else ''
    content(
        main,
        '<div class="container"><div class="section-head accent-olive"><h1>' + escape(title) + '</h1></div>'
        '<div class="home-door-grid">' + ''.join(listing_card(entry) for entry in entries) + '</div>'
        + empty_note + '</div>',
    )
    tree.xpath('//title')[0].text = title + ' | Sayd Magazine'
    description = tree.xpath('//meta[@name="description"]')
    if description:
        description[0].set('content', FR_TAGLINE)
    absolutize_fr_tree(tree)
    dest = DOCS / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = html.tostring(tree, encoding='unicode', method='html', doctype='<!DOCTYPE html>')
    switch = listing_switch(Path(path).as_posix())
    if switch:
        raw = patch_listing_html(raw, switch)
    raw = re.sub(r'(assets/css/site\.css\?v=)[^"\']+', r'\g<1>' + CSS_TOKEN, raw)
    rel = Path(path)
    raw = seo.apply_html(raw, dest, DOCS, rel, seo.load_twins(DOCS))
    for marker in EN_CHROME_MARKERS:
        if marker in raw:
            raise SystemExit(f'English chrome leaked into {path}: {marker}')
    relative = [
        url for url in re.findall(r'\b(?:href|src)="([^"]*)"', raw)
        if url and not url.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', '/', 'data:'))
    ]
    if relative:
        raise SystemExit(f'Relative links left on {path}: {relative[:8]}')
    dest.write_text(raw, encoding='utf-8')


def rebuild_french_listings(translations: dict) -> int:
    records = collect_listing_records(translations)
    listing_page('Articles de 2026', records, translations, Path('fr/stories/index.html'))
    for cat, label in CATS.items():
        entries = [record for record in records if record['category_slug'] == cat]
        listing_page(label, entries, translations, Path('fr/category') / cat / 'index.html')
    return len(records)


def refresh_published_listings() -> int:
    """Rewrite listing switchers and tickers without rebuilding story grids.

    A full listing_page() rebuild would drop cards published outside the
    French manifest (equestrian essay, autumn hunting). Chrome-only refresh
    keeps that placement.
    """
    changed = 0
    for path in [DOCS/'fr'/'stories'/'index.html', *sorted((DOCS/'fr'/'category').glob('*/index.html'))]:
        rel = path.relative_to(DOCS).as_posix()
        switch = listing_switch(rel)
        if not switch:
            continue
        text = path.read_text(encoding='utf-8')
        updated = patch_listing_html(text, switch)
        updated = re.sub(r'(assets/css/site\.css\?v=)[^"\']+', r'\g<1>'+CSS_TOKEN, updated)
        if updated != text:
            path.write_text(updated, encoding='utf-8')
            changed += 1
    return changed


def render_home(translations):
    tree=html.parse(str(DOCS/'en/index.html'))
    # The English memory strip points to old Arabic interviews. Its 2026 retrospective is the French entry.
    for section in tree.xpath('//section[contains(@class,"memory-strip")]'):
        title=translations['memory-of-sayd-awareness-responsibility-2016-2024']['title']
        content(section, '<div class="section-head accent-olive"><h2>Dans les archives de Sayd</h2></div><div class="home-door-grid"><article class="card"><div class="body"><h3><a href="posts/memory-of-sayd-awareness-responsibility-2016-2024/index.html">'+escape(title)+'</a></h3><div class="meta">19 septembre 2026</div></div></article></div>')
    prune_and_translate_cards(tree,translations)
    chrome(tree,None,translations)
    tree.xpath('//title')[0].text='Sayd Magazine · Français'
    head(tree,None,'Sayd Magazine · Français',BASE+'/')
    dest=DOCS/'fr/index.html';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(html.tostring(tree,encoding='utf-8',method='html',doctype='<!DOCTYPE html>'))


def render_static(name,translations):
    tree=html.parse(str(DOCS/'en'/name/'index.html'))
    chrome(tree,None,translations)
    mapping=STATIC_COPY[name]
    mapping={**mapping,'اقرأ بالعربية':'Lire en arabe'}
    for e in tree.iter():
        for field in ('text','tail'):
            value=getattr(e,field)
            if value:
                for source,target in sorted(mapping.items(),key=lambda pair:-len(pair[0])):
                    value=value.replace(source,target)
                setattr(e,field,value)
    for nav in tree.xpath('//nav[contains(@class,"lang-switch")]'):
        content(nav,'<a href="../../index.html" lang="ar" hreflang="ar">العربية</a> '
                + '<a href="../../en/'+name+'/index.html" lang="en" hreflang="en">English</a> '
                + '<a href="index.html" lang="fr" hreflang="fr" class="is-current" aria-current="page">Français</a>')
    title={'team':'Équipe','contact':'Contact','about':'À propos','license':'Licence'}[name]
    tree.xpath('//title')[0].text=title+' | Sayd Magazine'
    dest=DOCS/'fr'/name/'index.html';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(html.tostring(tree,encoding='utf-8',method='html',doctype='<!DOCTYPE html>'))


def wire_original_switches():
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    inverted={en:ar for ar,en in pairs.items()}
    targets=[(DOCS/'index.html',DOCS/'fr/index.html'),
             (DOCS/'en/index.html',DOCS/'fr/index.html')]
    for slug in ITEMS:
        french=DOCS/'fr/posts'/slug/'index.html'
        targets.append((DOCS/'en/posts'/slug/'index.html',french))
        ar=inverted.get(slug)
        if ar: targets.append((DOCS/'posts'/ar/'index.html',french))
    for name in STATIC_COPY:
        targets.append((DOCS/'en'/name/'index.html',DOCS/'fr'/name/'index.html'))
    for source,french in targets:
        if not source.is_file(): continue
        relative=os.path.relpath(french,source.parent)
        page=source.read_text()
        match=re.search(r'(<nav class="lang-switch"[^>]*>)(.*?)(</nav>)',page,re.S)
        if not match: continue
        inside=re.sub(r'\s*<a\b[^>]*hreflang="fr"[^>]*>.*?</a>', '',match.group(2),flags=re.S)
        inside+='\n          <a href="'+escape(relative,quote=True)+'" lang="fr" hreflang="fr">Français</a>\n        '
        updated=page[:match.start()]+match.group(1)+inside+match.group(3)+page[match.end():]
        updated=re.sub(r'(assets/css/site\.css\?v=)[^"\']+',r'\g<1>20260929-fr-nav',updated)
        if updated!=page:source.write_text(updated)
    for source in (DOCS/'fr').rglob('index.html'):
        page=source.read_text()
        updated=re.sub(r'(assets/css/site\.css\?v=)[^"\']+',r'\g<1>20260929-fr-nav',page)
        if updated!=page:source.write_text(updated)
    wire_listing_switches()


def _lang_link(href: str, lang: str, label: str, current: bool) -> str:
    attrs = ' class="is-current" aria-current="page"' if current else ''
    return f'<a href="{escape(href, quote=True)}" lang="{lang}" hreflang="{lang}"{attrs}>{label}</a>'


def listing_lang_inner(ar: str, en: str | None, fr: str | None, current: str) -> str:
    parts = [_lang_link(ar, 'ar', 'العربية', current == 'ar')]
    if en:
        parts.append(_lang_link(en, 'en', 'English', current == 'en'))
    if fr:
        if '/en/' in fr:
            raise SystemExit(f'Français door must stay on /fr/, got {fr}')
        parts.append(_lang_link(fr, 'fr', 'Français', current == 'fr'))
    return '\n          ' + '\n          '.join(parts) + '\n        '


def replace_lang_nav(page: str, inner: str) -> str:
    match = LANG_NAV_RE.search(page)
    if not match or 'http-equiv="refresh"' in page:
        return page
    updated = page[:match.start()] + match.group(1) + inner + match.group(3) + page[match.end():]
    return re.sub(r'(assets/css/site\.css\?v=)[^"\']+', r'\g<1>' + CSS_TOKEN, updated)


def _listing_self(prefix: str, folder: str, filename: str) -> str:
    if filename == 'index.html':
        return f'{prefix}{folder}/' if folder else prefix
    return f'{prefix}{folder}/{filename}'


def wire_listing_switches() -> int:
    """Root-absolute العربية / English / Français on AR, EN, and archive listings.

    English on an Arabic door is the twin `/en/category/<arabic-slug>/` when that
    door exists. It is not the English homepage. Français is `/fr/category/<slug>/`.
    """
    changed = 0
    seen: set[Path] = set()
    targets: list[tuple[Path, str]] = []

    def queue(page: Path, inner: str) -> None:
        targets.append((page, inner))

    for page in (DOCS / 'category').glob('*/*.html'):
        slug = page.parent.name
        en_door = (DOCS / 'en' / 'category' / slug / 'index.html').is_file()
        fr_door = (DOCS / 'fr' / 'category' / slug / 'index.html').is_file()
        ar = _listing_self('/', f'category/{quote(slug, safe="")}', page.name)
        en = category_public('/en/', slug) if en_door else '/en/'
        fr = category_public('/fr/', slug) if fr_door else None
        queue(page, listing_lang_inner(ar, en, fr, 'ar'))
    for page in (DOCS / 'en' / 'category').glob('*/*.html'):
        slug = page.parent.name
        fr_door = (DOCS / 'fr' / 'category' / slug / 'index.html').is_file()
        ar = category_public('/', slug)
        en = _listing_self('/en/', f'category/{quote(slug, safe="")}', page.name)
        fr = category_public('/fr/', slug) if fr_door else None
        queue(page, listing_lang_inner(ar, en, fr, 'en'))
    if (DOCS / 'fr' / 'stories' / 'index.html').is_file():
        stories = DOCS / 'en' / 'stories' / 'index.html'
        if stories.is_file():
            queue(stories, listing_lang_inner('/articles/', '/en/stories/', '/fr/stories/', 'en'))
        for page in (DOCS / 'articles').glob('*.html'):
            ar = '/articles/' if page.name == 'index.html' else f'/articles/{page.name}'
            queue(page, listing_lang_inner(ar, '/en/stories/', '/fr/stories/', 'ar'))
    for page, inner in targets:
        if page in seen or not page.is_file():
            continue
        seen.add(page)
        text = page.read_text(encoding='utf-8')
        updated = replace_lang_nav(text, inner)
        if updated != text:
            page.write_text(updated, encoding='utf-8')
            changed += 1
    # Legacy AR doors with no language twin still need the door-date stylesheet.
    for page in (DOCS / 'category').glob('*/*.html'):
        if page in seen or not page.is_file():
            continue
        text = page.read_text(encoding='utf-8')
        if 'class="post-row"' not in text:
            continue
        updated = re.sub(r'(assets/css/site\.css\?v=)[^"\']+', r'\g<1>' + CSS_TOKEN, text)
        if updated != text:
            page.write_text(updated, encoding='utf-8')
            changed += 1
    return changed


def render_article(slug, data, translations):
    source = DOCS / 'en/posts' / slug / 'index.html'
    tree = html.parse(str(source))
    body = tree.xpath('//article[contains(@class,"article-content")]')[0]
    for el, fr in zip(source_blocks(body), data['blocks']): content(el, fr)
    for figure, fr in zip(body.xpath('./figure'), data['figures']):
        cap = figure.find('figcaption')
        if cap is None: continue
        original_links = [(a.get('href'),a.text_content()) for a in cap.xpath('.//a[@href]')]
        content(cap, fr)
        present = {a.get('href') for a in cap.xpath('.//a[@href]')}
        for href, label in original_links:
            if href not in present:
                small = html.Element('small', **{'class':'photo-credit'})
                small.text = ' Source : '
                a = html.Element('a', href=href)
                a.text = label
                small.append(a)
                cap.append(small)
        caption_html=''.join(html.tostring(child,encoding='unicode',method='html') for child in cap)
        caption_html=(cap.text or '')+caption_html
        if 'class="photo-credit"' not in caption_html:
            marker=re.search(r'(?:Photo|Source|Crédit)\s*:',caption_html)
            if marker:
                prefix,credit=caption_html[:marker.start()],caption_html[marker.start():]
                content(cap,prefix+'<small class="photo-credit" style="display:block;font-size:.72em;line-height:1.4;color:#68705f">'+credit+'</small>')
        for span in cap.xpath('.//span'):
            if 'Source :' in span.text_content():
                span.set('class','photo-credit')
                span.set('style','display:block;font-size:.72em;line-height:1.4;color:#68705f')
        image = figure.find('.//img')
        if image is not None: image.set('alt', re.sub(r'<[^>]+>','',fr).split('Source :')[0][:180])
    tree.xpath('//h1')[0].text = data['title']
    chrome(tree,slug,translations)
    prune_and_translate_cards(tree,translations)
    pairs=json.loads((ROOT/'content/en/pairs.json').read_text())['pairs']
    ar_slug=next((key for key,value in pairs.items() if value==slug),None)
    ar=['../../../posts/'+ar_slug+'/index.html'] if ar_slug else []
    if ar:
        switch_ar=tree.xpath('//nav[contains(@class,"lang-switch")]//a[@hreflang="ar"]')
        if switch_ar: switch_ar[0].set('href',ar[0])
    ar_url=BASE + ar[0].replace('../../../','/') .replace('index.html','') if ar else None
    head(tree,slug,data['title'],ar_url)
    dest=DOCS/'fr/posts'/slug/'index.html'; dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(html.tostring(tree,encoding='utf-8',method='html',doctype='<!DOCTYPE html>'))


def main():
    translations=validate()
    for slug,data in translations.items(): render_article(slug,data,translations)
    render_home(translations)
    for name in STATIC_COPY: render_static(name,translations)
    count = rebuild_french_listings(translations)
    wire_original_switches()
    print(f'Rendered {len(translations)} articles, homepage, archive and {len(CATS)} categories ({count} French listing cards)')


if __name__ == '__main__':
    main()
