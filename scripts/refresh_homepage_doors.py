#!/usr/bin/env python3
"""Fill homepage desks from paired 2026 listings.

A door uses stories that are not already the feature-lead, feature-stack,
or Latest. If that still falls short of the door target, it may repeat
stack or Latest stories. It never repeats the feature-lead and never
uses a pre-2026 story. Equestrian stops at two cards; every other door
stops at four.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAIRS = json.loads((ROOT / "content/en/pairs.json").read_text())["pairs"]
UNDATED = json.loads((ROOT / "content/homepage.json").read_text()).get("undated_stories", {})
SILENCE = {
    "ar": "الصمت-الذي-يتكلمه-الخيل",
    "en": "the-silence-horses-speak",
    "fr": "le-silence-que-parlent-les-chevaux",
}
# صيد door: these four 2026 stories only. They are not on the lead or the stack.
# They must also leave Latest.
HUNTING_PIN = [
    "ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان",
    "منظمات-دولية-ابادة-بيئية-جنوب-لبنان",
    "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات",
    "حماية-طيور-هجرة-الخريف-لبنان-شراكة-منذ-2017",
]
# Latest is eight other 2026 stories: not lead, not stack, not the hunting door.
LATEST_PIN = [
    "بين-قمم-الأرز-دليل-الهايكينغ-والتخييم-في-لبنان",
    "من-القصيدة-إلى-المقناص-رحلة-هجرة-في-ذاكرة-العرب",
    "في-الميزان-الميداني-beretta-a400-أم-benelli-sbe-3",
    "شجيرة-العوسج-حين-تقرأ-الأرض",
    "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
    "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع",
    "السعودية-تطلق-موسم-الصيد-السادس-بضواب",
    "صيد-تعود-وهذا-ما-نريد-أن-نقدّمه-لكم",
]
DOORS = [
    ("صيد", "Hunting", "Chasse", "صيد", 4),
    ("رماية وعتاد", "Shooting &amp; Gear", "Tir et équipement", "عتاد-وسلاح-الصيد", 4),
    ("فروسية", "Equestrian", "Équitation", "فروسية", 2),
    ("برية وتخييم", "Wildlife &amp; Camping", "Faune et camping", "حياة-برية-وتخييم", 4),
    ("شعر وفن", "Poetry &amp; Art", "Poésie et arts", "ثقافة-وتراث", 4),
    ("صيد TV", "Sayd TV", "Sayd TV", "استديو-صيد", 4),
    ("صور", "Photos", "Photos", "صور", 4),
]
IMAGE_OVERRIDES = {
    "مع-بدء-هجرة-الخريف-تحرك-ميداني-لحماية": "media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
    "autumn-migration-field-action-protect-flyways-lebanon": "media/uploads/2026/09/mecshap-apu-cabs-baalbek-release.jpg",
    "مع-هجرة-الخريف-كيف-يحمي-العالم-الطيو": "media/uploads/2026/09/narta-egret.jpg",
    "بالفيديو-مقناص-سعود-عبد-العزيز-الباب": "media/uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg",
    "video-saud-al-babtain-maqnas-afghanistan": "media/uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg",
    "سهيل-2026-بالصور-الصقور-والزوار-ووجوه-ا": "media/uploads/2026/09/gallery-alsharq.jpg",
    "suhail-2026-in-photos-falcons-visitors": "media/uploads/2026/09/gallery-alsharq.jpg",
}


def zone_slugs(page, start, end):
    chunk = page.split(start, 1)[1].split(end, 1)[0]
    return set(re.findall(r'href="posts/([^/]+)/index\.html"', chunk))


def strip_latest(page, slug):
    """Silence stays in the feature stack. It is not a Latest item."""
    pre, rest = page.split('<ul class="latest-feed">', 1)
    feed, post = rest.split("</ul>", 1)
    updated = re.sub(
        rf'\n?<li>\s*<a href="posts/{re.escape(slug)}/index\.html">.*?</li>\s*',
        "\n",
        feed,
        count=1,
        flags=re.S,
    )
    return pre + '<ul class="latest-feed">' + updated + "</ul>" + post


def rows(folder, lang):
    prefix = {"en": "en/", "fr": "fr/"}.get(lang, "")
    page_path = DOCS / prefix / "category" / folder / "index.html"
    page = page_path.read_text()
    blocks = re.findall(r'<article class="post-row".*?</article>', page, re.S)
    if not blocks:
        blocks = re.findall(r'<article class="card".*?</article>', page, re.S)
    result = {}
    for row in blocks:
        slug = re.search(r'posts/([^/"#]+)', row)
        title = re.search(r'<h[23][^>]*>\s*<a[^>]*>(.*?)</a>', row, re.S)
        date = re.search(r'class="meta"[^>]*>([^<]+)', row) or re.search(r'data-published="([^"]+)"', row)
        thumb = re.search(r'<a class="thumb"[^>]*>.*?</a>', row, re.S)
        img_scope = thumb.group(0) if thumb else row
        img = re.search(r'<img[^>]+src="([^"]+)"[^>]*>|<img[^>]+>', img_scope)
        src = re.search(r'src="([^"]+)"', img.group(0)) if img else None
        alt = re.search(r'alt="([^"]*)"', img.group(0)) if img else None
        if not (slug and title and date and "2026" in date.group(1)):
            continue
        override = IMAGE_OVERRIDES.get(slug.group(1))
        if not (src or override):
            continue
        source = override or src.group(1)
        if source.startswith("/media/"):
            source = source[1:]
        caption = html.unescape(alt.group(1)).strip() if alt and alt.group(1).strip() else ""
        if source.startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/", "https://s1.wklcdn.com/")):
            image = source
        else:
            path = (DOCS / source if (override or source.startswith("media/")) else page_path.parent / source).resolve()
            if not path.is_file():
                continue
            home = DOCS / prefix / "index.html"
            image = Path(os_relpath(path, home.parent)).as_posix()
        shown = UNDATED.get(slug.group(1), date.group(1))
        label = html.unescape(re.sub(r'<[^>]+>', '', title.group(1)))
        result[slug.group(1)] = (label, shown, image, caption or label)
    return result


def os_relpath(path, start):
    import os
    return os.path.relpath(path, start)


def card(slug, details):
    title, date, image, alt = details
    date = UNDATED.get(slug, date)
    href = f"posts/{slug}/index.html"
    return (f'<article class="card"><a class="thumb" href="{href}">'
            f'<img src="{image}" alt="{html.escape(alt or title, quote=True)}" loading="lazy"></a>'
            f'<div class="body"><h3><a href="{href}">{html.escape(title)}</a></h3>'
            f'<div class="meta">{date}</div></div></article>')


def existing_cards(page, heading):
    pattern = (r'<h2>' + re.escape(heading) + r'</h2>.*?<div class="home-door-grid">'
               r'(.*?)</div>\s*</section>')
    match = re.search(pattern, page, re.S)
    found = {}
    if not match:
        return found
    for article in re.findall(r'<article class="card">.*?</article>', match.group(1), re.S):
        slug = re.search(r'href="posts/([^/]+)/index\.html"', article)
        if slug:
            found[slug.group(1)] = article
    return found


def card_to_li(article: str) -> str:
    href = re.search(r'href="(posts/[^"]+)"', article).group(1)
    img = re.search(r"<img\b[^>]*>", article).group(0)
    src = re.search(r'src="([^"]+)"', img).group(1)
    alt_match = re.search(r'alt="([^"]*)"', img)
    alt = alt_match.group(1) if alt_match else ""
    title = re.search(r"<h3><a [^>]*>(.*?)</a>", article, re.S).group(1).strip()
    date = re.search(r'class="meta">([^<]+)', article).group(1).strip()
    return (
        "<li>\n"
        f'  <a href="{href}">\n'
        f'    <span class="feed-thumb"><img src="{src}" alt="{alt}" loading="lazy"></span>\n'
        "    <span class=\"feed-text\">\n"
        f"      <span class=\"feed-title\">{title}</span>\n"
        f"      <span class=\"feed-date\">{date}</span>\n"
        "    </span>\n"
        "  </a>\n"
        "</li>"
    )


def rebuild_latest(page: str, slugs: list[str]) -> str:
    pre, rest = page.split('<ul class="latest-feed">', 1)
    feed, post = rest.split("</ul>", 1)
    lis = {}
    for item in re.findall(r"<li>.*?</li>", feed, re.S):
        slug = re.search(r"posts/([^/]+)/", item)
        if slug:
            lis[slug.group(1)] = item.strip()
    cards = {}
    for article in re.findall(r'<article class="card">.*?</article>', page, re.S):
        slug = re.search(r"posts/([^/]+)/", article)
        if slug:
            cards[slug.group(1)] = article
    items = []
    for slug in slugs:
        if slug in lis:
            items.append(lis[slug])
        elif slug in cards:
            items.append(card_to_li(cards[slug]))
        else:
            raise ValueError(f"Latest story has no card on this homepage: {slug}")
    return pre + '<ul class="latest-feed">\n' + "\n".join(items) + "\n</ul>" + post


def replace_door(page, heading, cards):
    pattern = (r'(<section class="home-section(?: sayd-tv)?">\s*<div class="section-head[^>]*">'
               r'\s*<h2>' + re.escape(heading) + r'</h2>.*?<div class="home-door-grid">)'
               r'.*?(</div>\s*</section>)')
    updated, count = re.subn(pattern, lambda m: m[1] + "\n" + "\n".join(cards) + "\n" + m[2],
                             page, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Missing homepage door: {heading}")
    return updated


def placement(page):
    lead = zone_slugs(page, "feature-lead", "feature-side")
    above = zone_slugs(page, 'class="feature-stack"', "latest-col")
    latest = zone_slugs(page, 'class="latest-feed"', "</ul>")
    return lead, above | latest


def main():
    pages = {
        "ar": (DOCS / "index.html").read_text(),
        "en": (DOCS / "en" / "index.html").read_text(),
        "fr": (DOCS / "fr" / "index.html").read_text(),
    }
    for lang in pages:
        pages[lang] = strip_latest(pages[lang], SILENCE[lang])
    lead, blocked = {}, {}
    for lang in ("ar", "en"):
        lead[lang], blocked[lang] = placement(pages[lang])
    catalogs = {}
    for _ar_name, _en_name, _fr_name, folder, _target in DOORS:
        catalogs[folder] = {lang: rows(folder, lang) for lang in ("ar", "en", "fr")}
    used = set()
    selection = {}
    repeated = []
    fr_override = {SILENCE["en"]: SILENCE["fr"]}
    for ar_name, en_name, fr_name, folder, target in DOORS:
        ar_rows, en_rows = catalogs[folder]["ar"], catalogs[folder]["en"]
        order = {slug: index for index, slug in enumerate(ar_rows)}
        if ar_name == "صيد":
            choices = [(slug, PAIRS[slug]) for slug in HUNTING_PIN]
            for ar_slug, _en_slug in choices:
                used.add(ar_slug)
            selection[ar_name] = [ar for ar, _ in choices]
            prior = {lang: existing_cards(pages[lang], heading)
                     for lang, heading in (("ar", ar_name), ("en", en_name), ("fr", fr_name))}
            pages["ar"] = replace_door(pages["ar"], ar_name, [
                prior["ar"].get(ar) or card(ar, ar_rows[ar]) for ar, _ in choices])
            pages["en"] = replace_door(pages["en"], en_name, [
                prior["en"].get(en) or card(en, en_rows[en]) for _, en in choices])
            fr_rows = catalogs[folder]["fr"]
            fr_cards = []
            for _ar_slug, en_slug in choices:
                if en_slug in prior["fr"]:
                    fr_cards.append(prior["fr"][en_slug])
                elif en_slug in fr_rows:
                    fr_cards.append(card(en_slug, fr_rows[en_slug]))
            if fr_cards:
                pages["fr"] = replace_door(pages["fr"], fr_name, fr_cards)
            continue
        fresh, repeats = [], []
        for ar_slug in ar_rows:  # Category listing is newest first.
            en_slug = PAIRS.get(ar_slug)
            if not en_slug or en_slug not in en_rows or ar_slug in used:
                continue
            if ar_slug in lead["ar"] or en_slug in lead["en"]:
                continue
            pair = (ar_slug, en_slug)
            if ar_slug in blocked["ar"] or en_slug in blocked["en"]:
                repeats.append(pair)
            else:
                fresh.append(pair)
        choices = fresh[:target]
        for pair in repeats:
            if len(choices) >= target:
                break
            choices.append(pair)
            repeated.append(pair[0])
        choices.sort(key=lambda pair: order[pair[0]])
        for ar_slug, _en_slug in choices:
            used.add(ar_slug)
        selection[ar_name] = [ar for ar, _ in choices]
        prior = {lang: existing_cards(pages[lang], heading)
                 for lang, heading in (("ar", ar_name), ("en", en_name), ("fr", fr_name))}
        pages["ar"] = replace_door(pages["ar"], ar_name, [
            prior["ar"].get(ar) or card(ar, ar_rows[ar]) for ar, _ in choices])
        pages["en"] = replace_door(pages["en"], en_name, [
            prior["en"].get(en) or card(en, en_rows[en]) for _, en in choices])
        fr_rows = catalogs[folder]["fr"]
        fr_cards = []
        for _ar_slug, en_slug in choices:
            fr_slug = fr_override.get(en_slug, en_slug)
            if fr_slug in prior["fr"]:
                fr_cards.append(prior["fr"][fr_slug])
            elif fr_slug in fr_rows:
                fr_cards.append(card(fr_slug, fr_rows[fr_slug]))
        if fr_cards:
            pages["fr"] = replace_door(pages["fr"], fr_name, fr_cards)
    pages["ar"] = rebuild_latest(pages["ar"], LATEST_PIN)
    en_latest = [PAIRS[slug] for slug in LATEST_PIN]
    pages["en"] = rebuild_latest(pages["en"], en_latest)
    pages["fr"] = rebuild_latest(pages["fr"], en_latest)
    for lang, prefix in (("ar", ""), ("en", "en/"), ("fr", "fr/")):
        (DOCS / prefix / "index.html").write_text(pages[lang])
    config_path = ROOT / "content/homepage.json"
    config = json.loads(config_path.read_text())
    ids = ["hunting", "gear", "equestrian", "wildlife", "poetry", "tv", "photos"]
    config["ia_door_sections"] = [
        {"door": door_id, "slugs": selection[ar_name]}
        for door_id, (ar_name, *_) in zip(ids, DOORS)
    ]
    desks = config.setdefault("desk_slugs", {})
    for door_id, (ar_name, en_name, _fr_name, _folder, _target) in zip(ids, DOORS):
        ar_key = "الحياة البرية والتخييم" if door_id == "wildlife" else ar_name
        desks[ar_key] = selection[ar_name]
        desks[html.unescape(en_name)] = [PAIRS[slug] for slug in selection[ar_name]]
    desks["الفروسية"] = selection["فروسية"]
    config["latest"] = list(LATEST_PIN)
    config["ia_slots"]["latest"] = list(LATEST_PIN)
    omit = config.setdefault("omit_from_latest", [])
    for slug in [SILENCE["ar"], SILENCE["en"], *HUNTING_PIN, *[PAIRS[slug] for slug in HUNTING_PIN]]:
        if slug not in omit:
            omit.append(slug)
    config["demotion"] = (
        "Hunting door is four 2026 stories outside the feature lead and stack, and those four stay off Latest. "
        "Latest is eight other 2026 stories, also outside the lead and stack. "
        "Equestrian may repeat the stack because silence and Taif are the only 2026 pair. Gear stays the single 2026 Beretta story."
    )
    config["approved_home_repeats"] = [
        SILENCE["ar"],
        "العد-التنازلي-لختام-موسم-الطائف-كأس-الملك-فيصل-واليوم-الوطني",
        "كيف-يحمي-المزارع-الطيور-المهاجرة-هذا-الخريف",
    ]
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(selection, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
