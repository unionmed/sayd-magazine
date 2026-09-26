"""Refresh only approved AR/EN homepage doors, leaving lead/latest/memory intact."""
import html
import json
import re
import shutil
from pathlib import Path

import site_ia as ia
import apply_site_ia as build

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def render_card(ar_slug, lang):
    en_slug = ia.PRIMARY[ar_slug]["en"]
    story = build._en_story(en_slug)
    if not story or not story["thumb"]:
        raise ValueError(f"Missing published English story/image: {en_slug}")
    slug = en_slug if lang == "en" else ar_slug
    path = DOCS / ("en/posts" if lang == "en" else "posts") / slug / "index.html"
    text = path.read_text(encoding="utf-8")
    title = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S).group(1)
    title = html.escape(html.unescape(re.sub(r'<[^>]+>', '', title)))
    date = re.search(r'class="article-meta".*?<span class="meta-item">([^<]+)</span>', text, re.S).group(1)
    src = re.search(r'src="([^"]+)"', story["thumb"]).group(1)
    src = src.replace("../../../", "../" if lang == "en" else "", 1)
    href = f"posts/{slug}/index.html"
    card = f'''<article class="card">
  <a class="thumb" href="{href}"><img src="{src}" alt="{title}" loading="lazy"></a>
  <div class="body"><h3><a href="{href}">{title}</a></h3><div class="meta">{date}</div></div>
</article>'''
    return story["stamp"], card


def refresh(path, lang):
    original = path.read_text(encoding="utf-8")
    sections = []
    for door, slugs in ia.DOOR_SECTIONS:
        cards = sorted((render_card(slug, lang) for slug in slugs), key=lambda item: item[0], reverse=True)
        accent = "accent-tv" if door == "tv" else "accent-olive" if door == "photos" else "accent-red"
        block = build.section(lang, door, "\n".join(card for _, card in cards), accent)
        block = block.replace('class="grid-4"', 'class="home-door-grid"').replace('class="grid-photos"', 'class="home-door-grid"')
        sections.append(block)
    pattern = r'(<div class="home-main">).*?(<div class="more-news">)'
    updated, count = re.subn(pattern, lambda m: m[1] + "\n" + "\n".join(sections) + "\n" + m[2], original, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Homepage doors boundary missing: {path}")
    css = ('../' if lang == 'en' else '') + 'assets/css/home-doors.css?v=20260926-two-columns'
    if 'assets/css/home-doors.css' in updated:
        updated = re.sub(r'href="[^"]*assets/css/home-doors\.css[^\"]*"', f'href="{css}"', updated)
    else:
        updated = updated.replace('</head>', f'  <link rel="stylesheet" href="{css}">\n</head>', 1)
    path.write_text(updated, encoding="utf-8")


def main():
    ia.assert_homepage_unique()
    config_path = ROOT / "content/homepage.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config['ia_door_sections'] = [{'door': door, 'slugs': slugs} for door, slugs in ia.DOOR_SECTIONS]
    config['approved_home_repeats'] = sorted(ia.APPROVED_HOME_REPEATS)
    config['demotion'] = 'Lead/latest remain unique; only approved_home_repeats may also appear in door sections, temporarily approved by Nayef on 2026-09-26.'
    for door, slugs in ia.DOOR_SECTIONS:
        spec = ia.door_by_id(door)
        config['desk_slugs'][spec['ar']] = slugs
        config['desk_slugs'][spec['en']] = [ia.PRIMARY[slug]['en'] for slug in slugs]
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'assets/css/home-doors.css', DOCS / 'assets/css/home-doors.css')
    refresh(DOCS / 'index.html', 'ar')
    refresh(DOCS / 'en/index.html', 'en')


if __name__ == '__main__':
    main()
