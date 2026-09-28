#!/usr/bin/env python3
"""Fill AR/EN homepage desks from paired 2026 category listings without repeats."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAIRS = json.loads((ROOT / "content/en/pairs.json").read_text())["pairs"]
UNDATED = json.loads((ROOT / "content/homepage.json").read_text()).get("undated_stories", {})
DOORS = [
    ("صيد", "Hunting", "صيد"),
    ("رماية وعتاد", "Shooting &amp; Gear", "عتاد-وسلاح-الصيد"),
    ("فروسية", "Equestrian", "فروسية"),
    ("برية وتخييم", "Wildlife &amp; Camping", "حياة-برية-وتخييم"),
    ("شعر وفن", "Poetry &amp; Art", "ثقافة-وتراث"),
    ("صيد TV", "Sayd TV", "استديو-صيد"),
    ("صور", "Photos", "صور"),
]
IMAGE_OVERRIDES = {
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية": "media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
    "autumn-migration-field-action-protect-flyways-lebanon": "media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": "media/uploads/2026/09/narta-egret.jpg",
}


def occupied(page):
    top = page.split('<section class="masthead"', 1)[1].split('</section>', 1)[0]
    return set(re.findall(r'href="posts/([^/]+)/index\.html"', top))


def rows(folder, lang):
    prefix = "en/" if lang == "en" else ""
    page = (DOCS / prefix / "category" / folder / "index.html").read_text()
    result = {}
    for row in re.findall(r'<article class="post-row".*?</article>', page, re.S):
        slug = re.search(r'href="[^"]*posts/([^/]+)/index\.html"', row)
        title = re.search(r'<h2[^>]*>\s*<a[^>]*>(.*?)</a>', row, re.S)
        date = re.search(r'class="meta"[^>]*>([^<]+)', row) or re.search(r'data-published="([^"]+)"', row)
        img = re.search(r'<img[^>]+src="([^"]+)"', row)
        if not (slug and title and date and "2026" in date.group(1)):
            continue
        override = IMAGE_OVERRIDES.get(slug.group(1))
        if not (img or override):
            continue
        source = override or img.group(1)
        if source.startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/", "https://s1.wklcdn.com/")):
            image = source
        else:
            path = (DOCS / override if override else
                    DOCS / prefix / "category" / folder / source).resolve()
            if not path.is_file():
                continue
            image = ("../" if lang == "en" else "") + path.relative_to(DOCS).as_posix()
        result[slug.group(1)] = (html.unescape(re.sub(r'<[^>]+>', '', title.group(1))), date.group(1), image)
    return result


def card(slug, details):
    title, date, image = details
    date = UNDATED.get(slug, date)
    href = f"posts/{slug}/index.html"
    return (f'<article class="card"><a class="thumb" href="{href}">'
            f'<img src="{image}" alt="{html.escape(title, quote=True)}" loading="lazy"></a>'
            f'<div class="body"><h3><a href="{href}">{html.escape(title)}</a></h3>'
            f'<div class="meta">{date}</div></div></article>')


def replace_door(page, heading, cards):
    pattern = (r'(<section class="home-section(?: sayd-tv)?">\s*<div class="section-head[^>]*">'
               r'\s*<h2>' + re.escape(heading) + r'</h2>.*?<div class="home-door-grid">)'
               r'.*?(</div>\s*</section>)')
    updated, count = re.subn(pattern, lambda m: m[1] + "\n" + "\n".join(cards) + "\n" + m[2],
                             page, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Missing homepage door: {heading}")
    return updated


def main():
    pages = {lang: (DOCS / ("en/" if lang == "en" else "") / "index.html").read_text()
             for lang in ("ar", "en")}
    upper = {lang: occupied(page) for lang, page in pages.items()}
    used = set()
    selection = {}
    for ar_name, en_name, folder in DOORS:
        ar_rows, en_rows = rows(folder, "ar"), rows(folder, "en")
        choices = []
        for ar_slug in ar_rows:  # Published category is newest first.
            en_slug = PAIRS.get(ar_slug)
            if not en_slug or en_slug not in en_rows or ar_slug in used:
                continue
            if ar_slug in upper["ar"] or en_slug in upper["en"]:
                continue
            choices.append((ar_slug, en_slug))
            used.add(ar_slug)
            if len(choices) == 4:
                break
        selection[ar_name] = [ar for ar, _ in choices]
        pages["ar"] = replace_door(pages["ar"], ar_name,
                                   [card(ar, ar_rows[ar]) for ar, _ in choices])
        pages["en"] = replace_door(pages["en"], en_name,
                                   [card(en, en_rows[en]) for _, en in choices])
    for lang, page in pages.items():
        (DOCS / ("en/" if lang == "en" else "") / "index.html").write_text(page)
    config_path = ROOT / "content/homepage.json"
    config = json.loads(config_path.read_text())
    ids = ["hunting", "gear", "equestrian", "wildlife", "poetry", "tv", "photos"]
    config["ia_door_sections"] = [{"door": door_id, "slugs": selection[ar_name]}
                                  for door_id, (ar_name, _, _) in zip(ids, DOORS)]
    for door_id, (ar_name, en_name, _) in zip(ids, DOORS):
        ar_key = "الحياة البرية والتخييم" if door_id == "wildlife" else ar_name
        config.setdefault("desk_slugs", {})[ar_key] = selection[ar_name]
        config["desk_slugs"][html.unescape(en_name)] = [PAIRS[slug] for slug in selection[ar_name]]
    config["demotion"] = "Desks show up to four paired 2026 stories outside feature and Latest, without repeats."
    config["approved_home_repeats"] = []
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    print(selection)


if __name__ == "__main__":
    main()
