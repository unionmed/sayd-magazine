#!/usr/bin/env python3
"""Build the English edition and wire visible العربية / English chrome.

Reads reviewed drafts from content/en/, writes docs/en/, and patches
existing docs HTML so the mast-top language switch is never hidden
behind a "Sayd Magazine" brand link.
"""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONTENT_EN = ROOT / "content" / "en"
PAIRS_PATH = CONTENT_EN / "pairs.json"

FONTS = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800"
    "&family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;0,700&display=swap"
)
CSS_CACHE = "20260919-kaps-stack-en"
ABOUT_EN = (
    "The magazine of nature’s masters on land, sea, and sky — hunting, "
    "wildlife, birds, equestrianism, and heritage from Lebanon and the Arab world."
)
TAGLINE_EN = "The magazine of nature’s masters on land, sea, and sky"
TAGLINE_AR = "مجلة أسياد الطبيعة في البر والبحر والجو"

# Live homepage / ticker 2026 set (Nayef editorial list).
HOME_FEATURED = [
    "cabs-mecshap-autumn-birds-lebanon-khatib",
    "suhail-2026-closes-decade-katara-80000-visitors",
    "saudi-sixth-hunting-season-2026-2027-rules",
    "sayd-returns-what-we-want-to-offer",
]
# Mosaic side stack (includes Memory; do not drop featured stories).
HOME_MOSAIC_SIDE = [
    "suhail-2026-closes-decade-katara-80000-visitors",
    "saudi-sixth-hunting-season-2026-2027-rules",
    "memory-of-sayd-awareness-responsibility-2016-2024",
    "sayd-returns-what-we-want-to-offer",
]
HOME_LATEST = [
    "cabs-mecshap-autumn-birds-lebanon-khatib",
    "qatar-suhail-2026-80000-visitors-teaser",
    "saudi-sixth-hunting-season-2026-2027-rules",
    "video-saud-al-babtain-maqnas-afghanistan",
    "autumn-migration-how-world-protects-birds-regulates-hunting",
    "sayd-returns-what-we-want-to-offer",
    "autumn-migration-field-action-protect-flyways-lebanon",
]
HOME_TICKER = list(HOME_LATEST)

META: dict[str, dict] = {
    "memory-of-sayd-awareness-responsibility-2016-2024": {
        "date": "19 September 2026",
        "date_sort": "2026-09-19",
        "category": "From Sayd’s Memory",
        "author": "Editorial Board",
        "image": "media/uploads/2024/02/ريتا-الشعار6.jpg",
        "image_alt": "Hunter Rita Habib Al-Shaar — from Sayd magazine’s archive",
    },
    "cabs-mecshap-autumn-birds-lebanon-khatib": {
        "date": "13 September 2026",
        "date_sort": "2026-09-13",
        "category": "News",
        "author": "Sayd",
        # Nayef-locked: fries is the only Kaps/CABS image (hero + cards).
        "image": "media/uploads/2026/09/kaps-makshab-apu-fries-hero.jpg",
        "image_alt": "A member of the APU team prepares food outdoors during a break",
    },
    "suhail-2026-closes-decade-katara-80000-visitors": {
        "date": "13 September 2026",
        "date_sort": "2026-09-13",
        "category": "News",
        "author": "Sayd",
        "image": "media/uploads/2026/09/hero-closing-80k.jpg",
        "image_alt": "Falcons at Suhail 2026 in Katara, Doha",
    },
    "qatar-suhail-2026-80000-visitors-teaser": {
        "date": "13 September 2026",
        "date_sort": "2026-09-13",
        "category": "News",
        "author": "Sayd",
        "image": "media/uploads/2026/09/gallery-katara-crowd.jpg",
        "image_alt": "Visitors at the close of Suhail 2026",
    },
    "suhail-2026-in-photos-falcons-visitors": {
        "date": "13 September 2026",
        "date_sort": "2026-09-13",
        "category": "Photos",
        "author": "Sayd",
        "image": "media/uploads/2026/09/gallery-alsharq.jpg",
        "image_alt": "Suhail 2026 in photos: falcons, visitors, and faces of the fair",
    },
    "saudi-hunting-fines-5000-riyal-prohibited-areas": {
        "date": "13 September 2026",
        "date_sort": "2026-09-13",
        "category": "News",
        "author": "Sayd",
        "image": "media/uploads/2026/09/saudi-hunting-season-2026-card.jpg",
        "image_alt": "Saudi Arabia tightens hunting rules",
    },
    "saudi-5000-riyal-hunting-fine-teaser": {
        "date": "13 September 2026",
        "date_sort": "2026-09-13",
        "category": "News",
        "author": "Sayd",
        "image": "media/uploads/2026/09/ncw-wildlife-card.jpg",
        "image_alt": "National Center for Wildlife — Saudi Arabia",
    },
    "saudi-sixth-hunting-season-2026-2027-rules": {
        "date": "9 September 2026",
        "date_sort": "2026-09-09",
        "category": "News",
        "author": "Sayd",
        "image": "media/uploads/2026/09/ncw-wildlife-card.jpg",
        "image_alt": "National Center for Wildlife — Saudi Arabia",
    },
    "sayd-returns-what-we-want-to-offer": {
        "date": "8 September 2026",
        "date_sort": "2026-09-08",
        "category": "Editorial",
        "author": "Adonis Al-Khatib, Editor-in-Chief",
        "image": "media/uploads/2026/09/sayd-returns-adonis-editor.jpg",
        "image_alt": "Adonis Al-Khatib — Sayd returns",
    },
    "autumn-migration-how-world-protects-birds-regulates-hunting": {
        "date": "8 September 2026",
        "date_sort": "2026-09-08",
        "category": "News",
        "author": "Sayd",
        "image": "media/uploads/2026/09/narta-egret.jpg",
        "image_alt": "Little Egret over Narta Lagoon, Albania",
    },
    "video-saud-al-babtain-maqnas-afghanistan": {
        "date": "8 September 2026",
        "date_sort": "2026-09-08",
        "category": "Sayd TV",
        "author": "Sayd",
        "image": "media/uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg",
        "image_alt": "Saud Abdulaziz Al-Babtain’s maqnas in Afghanistan",
    },
    "autumn-migration-field-action-protect-flyways-lebanon": {
        "date": "7 September 2026",
        "date_sort": "2026-09-07",
        "category": "News",
        "author": "Sayd",
        "image": "media/uploads/2026/09/kaps-makshab-apu-fries-hero.jpg",
        "image_alt": "Field work to protect migratory birds over Lebanon",
    },
    "sayd-returns-new-look-wider-vision": {
        "date": "6 September 2026",
        "date_sort": "2026-09-06",
        "category": "Editorial",
        "author": "Editorial Board",
        "image": "media/uploads/2026/09/sayd-returns-adonis-editor.jpg",
        "image_alt": "Sayd returns in a new look and a wider vision",
    },
}


def load_pairs() -> dict[str, str]:
    data = json.loads(PAIRS_PATH.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data["pairs"].items()}


def invert(pairs: dict[str, str]) -> dict[str, str]:
    return {v: k for k, v in pairs.items()}


def rel(depth: int, path: str) -> str:
    return "../" * depth + path


def lang_switch_html(ar_href: str, en_href: str, current: str) -> str:
    ar_cur = ' class="is-current" aria-current="page"' if current == "ar" else ""
    en_cur = ' class="is-current" aria-current="page"' if current == "en" else ""
    return (
        '<nav class="lang-switch" aria-label="Language">\n'
        f'          <a href="{escape(ar_href, quote=True)}" lang="ar" hreflang="ar"{ar_cur}>العربية</a>\n'
        f'          <a href="{escape(en_href, quote=True)}" lang="en" hreflang="en"{en_cur}>English</a>\n'
        "        </nav>"
    )


def md_inline(text: str) -> str:
    parts: list[str] = []
    i = 0
    pattern = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")
    for m in pattern.finditer(text):
        parts.append(escape(text[i : m.start()]))
        token = m.group(0)
        if token.startswith("**"):
            parts.append(f"<strong>{escape(token[2:-2])}</strong>")
        elif token.startswith("*"):
            parts.append(f"<em>{escape(token[1:-1])}</em>")
        elif token.startswith("`"):
            parts.append(f"<code>{escape(token[1:-1])}</code>")
        else:
            label, href = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()
            parts.append(f'<a href="{escape(href, quote=True)}">{escape(label)}</a>')
        i = m.end()
    parts.append(escape(text[i:]))
    return "".join(parts)


def md_blocks(text: str) -> str:
    chunks = re.split(r"\n\s*\n", text.strip())
    out: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("### "):
            out.append(f"<h2>{md_inline(chunk[4:].strip())}</h2>")
            continue
        if chunk.startswith("## "):
            out.append(f"<h2>{md_inline(chunk[3:].strip())}</h2>")
            continue
        lines = chunk.splitlines()
        if all(line.startswith("> ") or line == ">" for line in lines):
            quote = " ".join(line[2:] if line.startswith("> ") else "" for line in lines)
            out.append(f"<blockquote><p>{md_inline(quote.strip())}</p></blockquote>")
            continue
        if chunk.startswith("“") or (chunk.startswith('"') and chunk.endswith('"')):
            out.append(f"<blockquote><p>{md_inline(chunk.strip('\"“”'))}</p></blockquote>")
            continue
        out.append(f"<p>{md_inline(chunk)}</p>")
    return "\n".join(out)


def parse_draft(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    raw = re.split(r"\n## Notes\b", raw, maxsplit=1)[0]
    lines = raw.splitlines()
    title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else path.stem
    meta: dict[str, str] = {}
    body_start = 0
    for i, line in enumerate(lines[1:], start=1):
        m = re.match(r"\*\*([^*]+):\*\*\s*(.*)", line)
        if m:
            meta[m.group(1).strip()] = m.group(2).strip()
            continue
        if line.startswith("## "):
            body_start = i
            break
    rest = "\n".join(lines[body_start:])
    lead = ""
    body = rest
    m = re.search(r"## Lead\s*(.*?)\s*## Body\s*(.*)", rest, re.S)
    if m:
        lead, body = m.group(1).strip(), m.group(2).strip()
    return {"title": title, "meta": meta, "lead": lead, "body": body}


def figure(src: str, alt: str, caption: str, media_prefix: str) -> str:
    return (
        f'<figure><img src="{media_prefix}{src}" alt="{escape(alt, quote=True)}" loading="lazy">'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def article_body_html(slug: str, draft: dict, media_prefix: str) -> str:
    lead_html = md_blocks(draft["lead"]) if draft["lead"] else ""
    body_html = md_blocks(draft["body"]) if draft["body"] else ""
    extra = ""
    if slug == "cabs-mecshap-autumn-birds-lebanon-khatib":
        extra = figure(
            "media/uploads/2026/09/kaps-makshab-apu-fries-hero.jpg",
            "A member of the APU team prepares food outdoors during a break",
            "From the daily field life of the Anti-Poaching Unit (APU) team: a break to prepare food outdoors.",
            media_prefix,
        )
        lead_html = "<p><strong>Beirut — Sayd</strong></p>"
    elif slug == "suhail-2026-closes-decade-katara-80000-visitors":
        extra = (
            '<p class="en-callout"><a href="../suhail-2026-in-photos-falcons-visitors/index.html">'
            "<strong>See the Suhail 2026 photo album: falcons, visitors, and faces of the fair →</strong></a></p>"
        )
        lead_html = "<p><strong>Doha — Sayd</strong></p>"
        body_html = re.sub(
            r"<p>Falcons topped the interest of visitors to Suhail 2026.*?</p>",
            figure(
                "media/uploads/2026/09/hero-closing-80k.jpg",
                "Falcons at Suhail 2026",
                "Falcons topped the interest of visitors to Suhail 2026 and its specialized auction.<br>"
                "<span>Source: QNA</span>",
                media_prefix,
            ),
            body_html,
            count=1,
            flags=re.S,
        )
        body_html = re.sub(
            r"<p>A scene from falcon activities at Suhail 2026.*?</p>",
            figure(
                "media/uploads/2026/09/gallery-shil-day2.jpg",
                "A falconer at Suhail 2026",
                "A scene from falcon activities at Suhail 2026.<br><span>Source: QNA</span>",
                media_prefix,
            ),
            body_html,
            count=1,
            flags=re.S,
        )
    elif slug == "suhail-2026-in-photos-falcons-visitors":
        photos = [
            (
                "gallery-qna-extra-1.jpg",
                "From the opening tour",
                "A falcon spreads its wings on a falconer’s hand during a delegation’s walk among the exhibition stands.",
            ),
            (
                "gallery-qna-extra-1.jpg",
                "The falcon and its owner",
                "A falconer carries a falcon on his hand in one of the frames from Suhail’s activities.",
            ),
            (
                "gallery-shil-day2.jpg",
                "In the falcon halls",
                "Falcons wearing hoods (baraqi‘) stand on perches before fair visitors.",
            ),
            (
                "gallery-qna-extra-3.jpg",
                "Interest across all ages",
                "Visitors contemplate the fair and take part in its educational stands.",
            ),
            (
                "gallery-katara-crowd.jpg",
                "At the gates of Suhail",
                "Visitors in front of the Suhail exhibition entrance at Katara.",
            ),
            (
                "hero-closing-80k.jpg",
                "A gathering of falconers and visitors",
                "A wide view of corridors, stands, and visitor movement inside the fair.",
            ),
        ]
        gallery = ['<p><strong>Doha — Sayd | Photo album</strong></p>', lead_html]
        gallery.append(
            "<p>Click any image to view it full size. Photos: Qatar News Agency (QNA) and Al-Sharq newspaper.</p>"
        )
        for file, title, caption in photos:
            src = f"media/uploads/2026/09/{file}"
            gallery.append(
                '<figure class="sayd-suhail-photo">'
                f'<a href="{media_prefix}{src}">'
                f'<img src="{media_prefix}{src}" alt="{escape(caption, quote=True)}" loading="lazy"></a>'
                f"<figcaption><strong>{escape(title)}</strong><br>{escape(caption)}"
                "<br><span>Source: QNA</span></figcaption></figure>"
            )
        gallery.append("<h2>Faces in organizing Suhail</h2>")
        gallery.append(
            "<p><strong>Dr. Khalid bin Ibrahim Al-Sulaiti</strong><br>"
            "Director General of the Cultural Village Foundation “Katara,” and chair of the "
            "organizing supreme committee of the Suhail exhibition.</p>"
        )
        gallery.append(
            "<p><strong>Abdulaziz Al-Bu Hashem Al-Sayed</strong><br>"
            "Director of the Suhail exhibition and member of the organizing supreme committee.</p>"
        )
        gallery.append(
            "<p><strong>Malaka Mohammed Al-Shreem</strong><br>"
            "Member and secretary of the organizing supreme committee of the Suhail exhibition, "
            "and director of the Marketing Department at Katara.</p>"
        )
        gallery.append(
            '<p class="en-callout"><a href="../suhail-2026-closes-decade-katara-80000-visitors/index.html">'
            "<strong>Read the full Suhail 2026 wrap-up →</strong></a></p>"
        )
        return "\n".join(gallery)
    elif slug == "video-saud-al-babtain-maqnas-afghanistan":
        extra = (
            '<div class="en-video">'
            '<iframe title="Saud Abdulaziz Al-Babtain’s maqnas in Afghanistan — Al-Bawadi"'
            ' src="https://www.youtube.com/embed/P4m8fY--RRg"'
            ' allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"'
            " allowfullscreen></iframe></div>"
            '<p>Video: <a href="https://www.youtube.com/watch?v=P4m8fY--RRg" target="_blank" rel="noopener">'
            "Al-Bawadi channel on YouTube</a>.</p>"
        )
    elif slug == "autumn-migration-how-world-protects-birds-regulates-hunting":
        body_html = body_html.replace(
            "<p>Little Egret over Narta Lagoon, Albania — archival photo, 2015. Photo: Pasztilla (Attila Terbócs) / Wikimedia Commons — CC BY-SA 4.0. The image is for site identification and does not document current development works.</p>",
            figure(
                "media/uploads/2026/09/narta-egret.jpg",
                "Little Egret over Narta Lagoon, Albania",
                "Little Egret over Narta Lagoon, Albania — archival photo, 2015. Photo: Pasztilla (Attila Terbócs) / Wikimedia Commons — CC BY-SA 4.0. The image is for site identification and does not document current development works.",
                media_prefix,
            ),
        )
        body_html = body_html.replace(
            "<p>Ferruginous Duck in Aswan, Egypt — archival photo, 2010. terolinjama / iNaturalist, via Wikimedia Commons — CC0.</p>",
            figure(
                "media/uploads/2026/09/duck-aswan-960.jpg",
                "Ferruginous Duck in Aswan, Egypt",
                "Ferruginous Duck in Aswan, Egypt — archival photo, 2010. terolinjama / iNaturalist, via Wikimedia Commons — CC0.",
                media_prefix,
            ),
        )
    elif slug == "saudi-hunting-fines-5000-riyal-prohibited-areas":
        extra = (
            '<p class="en-callout">This item has been merged with the season-launch story. '
            '<a href="../saudi-sixth-hunting-season-2026-2027-rules/index.html">'
            "Read the unified version: Saudi Arabia launches the sixth hunting season and tightens the rules →"
            "</a></p>"
        )
        lead_html = "<p><strong>Riyadh — Sayd</strong></p>"
    elif slug == "saudi-5000-riyal-hunting-fine-teaser":
        extra = (
            '<p class="en-callout">This item has been merged with the season-launch story. '
            '<a href="../saudi-sixth-hunting-season-2026-2027-rules/index.html">'
            "Read the unified version →</a></p>"
        )
    elif slug == "memory-of-sayd-awareness-responsibility-2016-2024":
        extra = figure(
            "media/uploads/2024/02/ريتا-الشعار6.jpg",
            "Hunter Rita Habib Al-Shaar",
            "Hunter Rita Habib Al-Shaar — from Sayd magazine’s archive.",
            media_prefix,
        )
    elif slug == "sayd-returns-what-we-want-to-offer":
        extra = figure(
            "media/uploads/2026/09/sayd-returns-adonis-editor.jpg",
            "Adonis Al-Khatib",
            "Adonis Al-Khatib, editor-in-chief of Sayd.",
            media_prefix,
        )

    parts = [p for p in (lead_html, extra, body_html) if p]
    return "\n".join(parts)


def en_post_href(depth: int, slug: str) -> str:
    """Relative href to an EN article from a page at `depth` below docs/."""
    if depth == 1:
        return f"posts/{slug}/index.html"
    if depth == 2:
        return f"../posts/{slug}/index.html"
    if depth == 3:
        return f"../{slug}/index.html"
    return rel(depth, f"en/posts/{slug}/index.html")


def ticker_html(depth: int, articles: dict[str, dict], lang: str) -> str:
    if lang != "en":
        raise ValueError("AR ticker is already in docs/")
    label = "From every valley, a story"
    links = []
    for slug in HOME_TICKER:
        title = articles[slug]["title"]
        href = en_post_href(depth, slug)
        links.append(f'<a href="{href}">{escape(title)}</a>')
    inner = "".join(links)
    return f"""
    <div class="news-strip">
      <div class="container news-strip-inner">
        <div class="labels">
          <span class="label-feed">{escape(label)}</span>
        </div>
        <div class="ticker-viewport" aria-label="{escape(label)}">
          <div class="ticker-track">
            <div class="ticker">{inner}</div>
            <div class="ticker" aria-hidden="true">{inner}</div>
          </div>
        </div>
      </div>
    </div>"""


def en_chrome(
    *,
    depth: int,
    title: str,
    description: str,
    body: str,
    ar_href: str,
    en_href: str,
    articles: dict[str, dict],
    extra_head: str = "",
) -> str:
    css = rel(depth, "assets/css/site.css") + f"?v={CSS_CACHE}"
    logo = rel(depth, "media/brand/sayd-logo.png")
    home_en = rel(depth, "en/index.html")
    home_ar = rel(depth, "index.html")
    stories = rel(depth, "en/stories/index.html")
    team = rel(depth, "en/team/index.html")
    contact = rel(depth, "en/contact/index.html")
    nav_items = [
        ("nav-home", "en/index.html", "Home"),
        ("", "category/صيد/index.html", "Hunting &amp; Equestrian"),
        ("", "category/رماية/index.html", "Shooting"),
        ("", "category/عتاد-وسلاح-الصيد/index.html", "Gear &amp; Arms"),
        ("", "category/رياضات-وسياحة-بيئية/index.html", "Eco-Tourism"),
        ("", "category/مقابلات-تحقيقات/index.html", "Interviews &amp; Investigations"),
        ("", "category/صور/index.html", "Photos"),
        ("", "category/قوانين-وخرائط/index.html", "Laws &amp; Maps"),
        ("", "category/جعبة-المنوعات/index.html", "Miscellany"),
        ("nav-all", "articles/index.html", "Archive"),
    ]
    nav_links = []
    for cls, path, label in nav_items:
        attr = f' class="{cls}"' if cls else ""
        nav_links.append(f'        <a{attr} href="{rel(depth, path)}">{label}</a>')
    nav = "\n".join(nav_links)
    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  <meta name="theme-color" content="#3e421d">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="{FONTS}">
  <link rel="stylesheet" href="{css}">
  <link rel="icon" href="{logo}">
  <link rel="alternate" hreflang="ar" href="{ar_href}">
  <link rel="alternate" hreflang="en" href="{en_href}">
{extra_head}</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <div class="site-sticky">
    <div class="mast-top">
      <div class="container mast-top-inner">
        <nav class="top-secondary" aria-label="Top links">
          <a href="{team}">Team</a>
          <a href="{contact}">Contact</a>
        </nav>
        {lang_switch_html(ar_href if ar_href else home_ar, en_href, "en")}
      </div>
    </div>
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" href="{home_en}">
          <span class="brand-wordmark" lang="en">Sayd</span>
          <span class="tagline">{escape(TAGLINE_EN)}</span>
        </a>
        <nav class="main-nav" aria-label="Main menu">
{nav}
        </nav>
        <details class="nav-toggle">
          <summary>Menu</summary>
          <nav class="drawer-nav" aria-label="Mobile menu">
{nav}
          </nav>
        </details>
      </div>
    </header>
    {ticker_html(depth, articles, "en")}
  </div>
{body}
  <footer class="site-footer">
    <div class="footer-main">
      <div class="container footer-grid">
        <div class="footer-col">
          <p class="footer-wordmark" lang="en">Sayd</p>
          <p>{escape(ABOUT_EN)}</p>
        </div>
        <div class="footer-col">
          <h3>In this edition</h3>
          <ul>
            <li><a href="{home_en}">English homepage</a></li>
            <li><a href="{stories}">September 2026 stories</a></li>
            <li><a href="{home_ar}">Arabic homepage</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h3>Links</h3>
          <ul>
            <li><a href="{home_en}">Home</a></li>
            <li><a href="{stories}">Stories</a></li>
            <li><a href="{contact}">Contact</a></li>
            <li><a href="{team}">Team</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="container footer-bottom-inner">
        <div>© Sayd Magazine</div>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def related_for(slug: str, articles: dict[str, dict]) -> list[str]:
    others = [s for s in HOME_FEATURED + HOME_LATEST if s != slug]
    seen: list[str] = []
    for s in others:
        if s not in seen:
            seen.append(s)
    return seen[:3]


def related_card_html(other: str, articles: dict[str, dict], media_prefix: str) -> str:
    o = articles[other]
    thumb = o.get("card_image") or o.get("image") or "media/brand/sayd-logo.png"
    alt = o.get("card_image_alt") or o.get("image_alt") or o["title"]
    return f"""<article class="card overlay">
  <a class="thumb" href="../{other}/index.html"><img src="{media_prefix}{thumb}" alt="{escape(alt, quote=True)}" loading="lazy"></a>
  <div class="body">
    <div class="meta">{escape(o["date"])}<span class="cat-pill">{escape(o["category"])}</span></div>
    <h3><a href="../{other}/index.html">{escape(o["title"])}</a></h3>
  </div>
</article>"""


def related_block_html(slug: str, articles: dict[str, dict]) -> str:
    cards = "".join(
        related_card_html(other, articles, "../../../")
        for other in related_for(slug, articles)
    )
    return f"""    <section class="related-block">
      <div class="section-head"><h2>Related</h2></div>
      <div class="related-grid">
{cards}
      </div>
    </section>
"""


def ensure_en_related_blocks(articles: dict[str, dict]) -> int:
    """Insert or refresh Related on published EN articles without rewriting chrome."""
    n = 0
    for slug in articles:
        path = DOCS / "en" / "posts" / slug / "index.html"
        if not path.is_file():
            continue
        html = path.read_text(encoding="utf-8")
        block = related_block_html(slug, articles)
        if '<section class="related-block">' in html:
            new_html = re.sub(
                r'[ \t]*<section class="related-block">.*?</section>\s*',
                block,
                html,
                count=1,
                flags=re.S,
            )
        else:
            new_html, count = re.subn(
                r'(<article class="article-content">.*?</article>)(\s*)',
                r"\1\n" + block + r"\2",
                html,
                count=1,
                flags=re.S,
            )
            if count != 1:
                continue
        if new_html != html:
            path.write_text(new_html, encoding="utf-8")
            n += 1
    return n


def write_article(slug: str, articles: dict[str, dict], pairs_inv: dict[str, str]) -> None:
    item = articles[slug]
    ar_slug = pairs_inv[slug]
    dest = DOCS / "en" / "posts" / slug
    dest.mkdir(parents=True, exist_ok=True)
    media_prefix = "../../../"
    body_inner = article_body_html(slug, item["draft"], media_prefix)
    featured = ""
    image = item.get("image")
    if image and slug not in {
        "cabs-mecshap-autumn-birds-lebanon-khatib",
        "suhail-2026-in-photos-falcons-visitors",
        "video-saud-al-babtain-maqnas-afghanistan",
    }:
        featured = (
            f'<div class="article-featured"><img src="{media_prefix}{image}" '
            f'alt="{escape(item.get("image_alt") or item["title"], quote=True)}" loading="lazy"></div>'
        )
    related = []
    for other in related_for(slug, articles):
        related.append(related_card_html(other, articles, media_prefix))
    ar_href = f"../../../posts/{ar_slug}/index.html"
    en_href = "index.html"
    main = f"""
<main class="page-main" id="content">
  <div class="container">
    <div class="article-layout">
    <div class="article-shell">
    <div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../../stories/index.html">Stories</a> / Article</div>
    <header class="article-header">
      <div><span class="badge">{escape(item["category"])}</span></div>
      <h1>{escape(item["title"])}</h1>
      <div class="article-meta"><span class="meta-item">{escape(item["date"])}</span><span class="meta-item">{escape(item["author"])}</span></div>
      <p class="lang-twin"><a href="{ar_href}" hreflang="ar" lang="ar">اقرأ بالعربية</a></p>
    </header>
    {featured}
    <article class="article-content">
      {body_inner}
    </article>
    <section class="related-block">
      <div class="section-head"><h2>Related</h2></div>
      <div class="related-grid">
{"".join(related)}
      </div>
    </section>
    </div>
    </div>
  </div>
</main>
"""
    html = en_chrome(
        depth=3,
        title=f"{item['title']} — Sayd Magazine",
        description=re.sub("<[^>]+>", "", body_inner)[:160],
        body=main,
        ar_href=ar_href,
        en_href=en_href,
        articles=articles,
    )
    (dest / "index.html").write_text(html, encoding="utf-8")


def card(slug: str, articles: dict[str, dict], href: str, heading: str = "h3") -> str:
    item = articles[slug]
    img = item.get("image") or "media/brand/sayd-logo.png"
    byline = ""
    if slug == "sayd-returns-what-we-want-to-offer":
        byline = (
            '<p class="byline" style="font-size:0.72rem;color:var(--muted);'
            'margin:0.15rem 0 0;line-height:1.35;">Editor-in-Chief Adonis Al-Khatib</p>'
        )
    return f"""<article class="card overlay">
  <a class="thumb" href="{href}"><img src="{img}" alt="{escape(item.get("image_alt") or item["title"], quote=True)}" loading="lazy"></a>
  <div class="body">
    <div class="meta">{escape(item["date"])}<span class="cat-pill">{escape(item["category"])}</span></div>
    <{heading}><a href="{href}">{escape(item["title"])}</a></{heading}>
    {byline}
  </div>
</article>"""


def write_home(articles: dict[str, dict]) -> None:
    lead = HOME_FEATURED[0]
    side = HOME_MOSAIC_SIDE
    side_html = []
    for slug in side:
        cls = "card card-stack"
        if slug == "memory-of-sayd-awareness-responsibility-2016-2024":
            cls += " feature-memory"
        if slug == "sayd-returns-what-we-want-to-offer":
            cls += " feature-adonis"
        item = articles[slug]
        img = item["image"]
        byline = ""
        if slug == "sayd-returns-what-we-want-to-offer":
            byline = (
                '<p class="byline" style="font-size:0.72rem;color:var(--muted);'
                'margin:0.15rem 0 0;line-height:1.35;">Editor-in-Chief Adonis Al-Khatib</p>'
            )
        side_html.append(
            f"""<article class="{cls}">
  <a class="thumb" href="posts/{slug}/index.html"><img src="../{img}" alt="{escape(item.get("image_alt") or item["title"], quote=True)}" loading="lazy"></a>
  <div class="body">
    <div class="meta">{escape(item["date"])}<span class="cat-pill">{escape(item["category"])}</span></div>
    <h3><a href="posts/{slug}/index.html">{escape(item["title"])}</a></h3>
    {byline}
  </div>
</article>"""
        )
    latest_items = []
    for slug in HOME_LATEST:
        item = articles[slug]
        latest_items.append(
            f"""<li>
  <a href="posts/{slug}/index.html">
    <span class="feed-text">
      <span class="feed-cat">{escape(item["category"])}</span>
      <span class="feed-title">{escape(item["title"])}</span>
      <span class="feed-date">{escape(item["date"])}</span>
    </span>
  </a>
</li>"""
        )
    more = [
        s
        for s in articles
        if s not in HOME_FEATURED
    ]
    more.sort(key=lambda s: articles[s]["date_sort"], reverse=True)
    more_cards = []
    for slug in more:
        item = articles[slug]
        more_cards.append(
            f"""<article class="card overlay">
  <a class="thumb" href="posts/{slug}/index.html"><img src="../{item["image"]}" alt="{escape(item.get("image_alt") or item["title"], quote=True)}" loading="lazy"></a>
  <div class="body">
    <div class="meta">{escape(item["date"])}<span class="cat-pill">{escape(item["category"])}</span></div>
    <h3><a href="posts/{slug}/index.html">{escape(item["title"])}</a></h3>
  </div>
</article>"""
        )
    lead_item = articles[lead]
    main = f"""
<main class="page-main" id="content">
  <div class="container">
    <section class="masthead" aria-label="Featured stories and latest news">
      <div class="featured-col">
        <div class="section-head">
          <h2>Featured stories</h2>
        </div>
        <div class="featured-mosaic">
<article class="card feature-lead kaps-lead">
  <div class="body">
    <div class="meta">{escape(lead_item["date"])}<span class="cat-pill">{escape(lead_item["category"])}</span></div>
    <h2><a href="posts/{lead}/index.html">{escape(lead_item["title"])}</a></h2>
  </div>
  <a class="thumb" href="posts/{lead}/index.html"><img src="../{lead_item["image"]}" alt="{escape(lead_item.get("image_alt") or lead_item["title"], quote=True)}" loading="lazy"></a>
</article>
          <div class="feature-side">
          <div class="feature-stack">
{"".join(side_html)}
          </div>
          </div>
        </div>
      </div>
      <div class="latest-col">
        <div class="section-head">
          <h2>Latest</h2>
          <a href="stories/index.html">All stories</a>
        </div>
        <ul class="latest-feed">
{"".join(latest_items)}
        </ul>
      </div>
    </section>
    <section class="home-section">
      <div class="section-head accent-olive">
        <h2>September 2026</h2>
        <a href="stories/index.html">All English stories</a>
      </div>
      <div class="grid-4">
{"".join(more_cards)}
      </div>
    </section>
  </div>
</main>
"""
    html = en_chrome(
        depth=1,
        title="Sayd Magazine · English",
        description=TAGLINE_EN,
        body=main,
        ar_href="../index.html",
        en_href="index.html",
        articles=articles,
    )
    dest = DOCS / "en"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(html, encoding="utf-8")


def write_stories(articles: dict[str, dict]) -> None:
    slugs = sorted(articles, key=lambda s: articles[s]["date_sort"], reverse=True)
    rows = []
    for slug in slugs:
        item = articles[slug]
        img = item.get("card_image") or item["image"]
        alt = item.get("card_image_alt") or item.get("image_alt") or item["title"]
        rows.append(
            f"""<article class="card overlay">
  <a class="thumb" href="../posts/{slug}/index.html"><img src="../../{img}" alt="{escape(alt, quote=True)}" loading="lazy"></a>
  <div class="body">
    <div class="meta">{escape(item["date"])}<span class="cat-pill">{escape(item["category"])}</span></div>
    <h3><a href="../posts/{slug}/index.html">{escape(item["title"])}</a></h3>
  </div>
</article>"""
        )
    main = f"""
<main class="page-main" id="content">
  <div class="container">
    <div class="section-head">
      <h2>September 2026 English stories</h2>
    </div>
    <div class="grid-4">
{"".join(rows)}
    </div>
  </div>
</main>
"""
    html = en_chrome(
        depth=2,
        title="September 2026 stories — Sayd Magazine",
        description="English twins of Sayd Magazine’s September 2026 edition.",
        body=main,
        ar_href="../../index.html",
        en_href="../index.html",
        articles=articles,
    )
    dest = DOCS / "en" / "stories"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(html, encoding="utf-8")


TOP_EN_RE = re.compile(
    r'[ \t]*<a class="top-en" href="([^"]+)">Sayd Magazine</a>\s*'
)
LANG_SWITCH_RE = re.compile(
    r'<nav class="lang-switch" aria-label="Language">.*?</nav>',
    re.S,
)


def patch_existing_html(pairs: dict[str, str]) -> int:
    changed = 0
    for path in DOCS.rglob("*.html"):
        if "/en/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        rel_to_docs = path.relative_to(DOCS)
        depth = len(rel_to_docs.parts) - 1
        ar_home = rel(depth, "index.html")
        en_home = rel(depth, "en/index.html")
        en_href = en_home
        ar_href = ar_home
        if rel_to_docs.parts[:1] == ("posts",) and len(rel_to_docs.parts) >= 2:
            ar_slug = rel_to_docs.parts[1]
            ar_href = "index.html"
            if ar_slug in pairs:
                en_href = rel(depth, f"en/posts/{pairs[ar_slug]}/index.html")
        if "class=\"lang-switch\"" in text or "class='lang-switch'" in text:
            new = LANG_SWITCH_RE.sub(lang_switch_html(ar_href, en_href, "ar"), text, count=1)
        elif TOP_EN_RE.search(text):
            new = TOP_EN_RE.sub(lang_switch_html(ar_href, en_href, "ar"), text, count=1)
        else:
            continue
        if path.name == "index.html" and path.parent == DOCS:
            new = new.replace(
                "assets/css/site.css?v=20260919-mosaic3",
                "assets/css/site.css?v=20260919-lang",
            )
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def patch_css() -> None:
    block = """
.lang-switch {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 800;
  letter-spacing: 0;
  white-space: nowrap;
}
.lang-switch a {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 0.55rem;
  border: 1px solid rgba(239, 232, 212, 0.35);
  border-radius: 3px;
  line-height: 1;
  opacity: 1;
  color: #efe8d4;
}
.lang-switch a:hover {
  color: var(--ink);
  background: var(--gold-soft);
  border-color: var(--gold-soft);
}
.lang-switch a.is-current {
  background: var(--gold);
  color: var(--ink);
  border-color: var(--gold);
}
html[lang="en"] {
  direction: ltr;
}
html[lang="en"] .article-content {
  font-family: var(--font-en-serif);
}
html[lang="en"] .article-header h1,
html[lang="en"] .section-head h2,
html[lang="en"] .card h2,
html[lang="en"] .card h3 {
  font-family: var(--font-en);
}
.lang-twin {
  margin: 0.45rem 0 0;
  font-size: 0.85rem;
  font-weight: 700;
}
.en-callout {
  padding: 12px 16px;
  background: #f7f3e9;
  border-inline-start: 4px solid #a78643;
}
.en-video {
  position: relative;
  padding-bottom: 56.25%;
  height: 0;
  overflow: hidden;
  margin: 1rem 0;
}
.en-video iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}

"""
    for css_path in (ROOT / "assets" / "css" / "site.css", DOCS / "assets" / "css" / "site.css"):
        css = css_path.read_text(encoding="utf-8")
        if ".lang-switch" not in css:
            css = css.replace(".top-en {", block + ".top-en {", 1)
        css = css.replace(
            """@media (max-width: 560px) {
  .mast-top { display: none; }
}""",
            """@media (max-width: 560px) {
  .mast-top {
    display: block;
  }
  .mast-top-inner {
    min-height: 32px;
    padding: 0.2rem 0;
  }
  .top-secondary {
    display: none;
  }
}""",
        )
        css_path.write_text(css, encoding="utf-8")


def load_articles(pairs: dict[str, str]) -> dict[str, dict]:
    articles: dict[str, dict] = {}
    for ar_slug, en_slug in pairs.items():
        path = CONTENT_EN / f"{en_slug}.md"
        if not path.exists():
            raise SystemExit(f"missing draft: {path}")
        draft = parse_draft(path)
        meta = dict(META[en_slug])
        meta.update(
            {
                "slug": en_slug,
                "ar_slug": ar_slug,
                "title": draft["title"],
                "draft": draft,
            }
        )
        articles[en_slug] = meta
    return articles


def main() -> None:
    pairs = load_pairs()
    articles = load_articles(pairs)
    pairs_inv = invert(pairs)
    patch_css()
    n = patch_existing_html(pairs)
    write_home(articles)
    write_stories(articles)
    for slug in articles:
        write_article(slug, articles, pairs_inv)
    related_n = ensure_en_related_blocks(articles)
    print(f"patched {n} Arabic HTML files")
    print(f"wrote {len(articles)} English articles + /en/index.html")
    print(f"ensured Related on {related_n} English articles")


if __name__ == "__main__":
    main()
