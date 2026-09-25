#!/usr/bin/env python3
"""Publish the Bekaa bird-net seizure (Latest + one ticker line, AR/EN).

Homepage cascade, cover, and CSS stay. The ticker gains one line and drops
the oldest (Saudi season) so it stays at eight. Latest gains the story as
the newest small-thumb card and drops the shelduck card.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
UPLOAD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/bekaa-nets-isf-pickup-2026-09-25_8dc9.jpg"
)

AR_SLUG = "ضبط-اكثر-من-20-الف-م2-شباك-صيد-لبنان"
EN_SLUG = "over-20000-m2-bird-nets-seized-lebanon"
AR_TITLE = "ضبط أكثر من 20 ألف م² شباك صيد في لبنان"
EN_TITLE = "Over 20,000 m² of bird nets seized in Lebanon"
AR_TICKER = "قوى الأمن تضبط 20,640 م² شباك صيد غير قانونية في البقاع"
EN_TICKER = "Internal Security Forces seize 20,640 m² of illegal bird nets in the Bekaa"
IMG_NAME = "bekaa-nets-isf-pickup-2026-09-25.jpg"
IMG = f"media/uploads/2026/09/{IMG_NAME}"
AR_ALT = "بيك أب محمّل بشباك وأعمدة مضبوطة خلال الحملة الميدانية في البقاع."
EN_ALT = "A pickup loaded with seized nets and poles during the field campaign in the Bekaa."
AR_CREDIT = "المديرية العامة لقوى الأمن الداخلي"
EN_CREDIT = "Directorate General of the Internal Security Forces"
AR_DATE = "25 أيلول 2026"
EN_DATE = "25 September 2026"
AR_DESC = (
    "خلال ثلاثة أيام متواصلة، نفّذت مفرزة استقصاء البقاع في وحدة الدرك الإقليمي "
    "حملة ميدانية لضبط شباك صيد الطيور المنصوبة بصورة غير قانونية، في جرود بلدة "
    "عرسال وفي سهول بلدات اللبوة ورأس بعلبك وجديدة الفاكهة وجبولة ومشاريع القاع وماسا والناصرية."
)
EN_DESC = (
    "Over three consecutive days, the Bekaa Investigation Detachment of the Regional "
    "Gendarmerie Unit carried out a field campaign to seize illegally set bird nets "
    "in the highlands of Arsal and in the plains of Labweh, Ras Baalbek, Jadidat "
    "al-Fakiha, Jabouleh, Mashari‘ al-Qaa, Massa and al-Nasiriya."
)

AR_PARAS = [
    AR_DESC,
    (
        "وأسفرت العمليات عن ضبط شباك بلغت مساحتها الإجمالية **20,640 متراً مربعاً**. "
        "جرى تسليم المضبوطات إلى القطعات المعنية، وتمكّنت عناصر المفرزة من تحديد هوية "
        "عدد من المتورطين، والعمل جارٍ على اتخاذ الإجراءات القانونية بحقهم، والتحقيق "
        "مستمر بناءً على إشارة القضاء المختص."
    ),
    (
        "تأتي الحملة في موسم هجرة الخريف، حين تُنصب الشباك في البساتين والسهول كمصائد "
        "تعيق مسارات الطيور المهاجرة. وفي القانون اللبناني للصيد البرّي يُمنع الصيد "
        "بواسطة الشباك والدبق وسواهما من الوسائل الجماعية غير القانونية، ويبقى الردع "
        "الميداني مرتبطاً ببلاغات المواطنين ومتابعة الأجهزة المختصة."
    ),
    (
        "ودعت المديرية العامة لقوى الأمن الداخلي المواطنين إلى الإبلاغ عن مخالفات "
        "الصيد الجائر بحق الطيور المهاجرة عبر خدمة «بلّغ»، مع توثيق المخالفة بالصور "
        "أو مقاطع الفيديو عند الإمكان، أو بالاتصال بغرفة العمليات على الرقم **112**."
    ),
]
EN_PARAS = [
    EN_DESC,
    (
        "The operations yielded nets totaling **20,640 square metres**. The seized "
        "material was handed to the relevant units; officers identified a number of "
        "suspects, legal measures are under way, and the investigation continues "
        "under the competent judiciary’s instructions."
    ),
    (
        "The campaign falls in the autumn migration season, when mist nets in orchards "
        "and open plains can block migratory flyways. Lebanese hunting law prohibits "
        "nets, birdlime and other collective illegal methods; field enforcement still "
        "depends on citizen reports and follow-up by the competent forces."
    ),
    (
        "The Directorate General of the Internal Security Forces renewed its call for "
        "the public to report illegal killing of migratory birds via the «Balligh» "
        "(Report) service—sending photos or video when possible—or by calling the "
        "operations room on **112**."
    ),
]

FIG_STYLE = "margin:24px auto;max-width:680px;"
IMG_STYLE = "display:block;width:100%;max-width:100%;height:auto;border-radius:6px;"
CAP_STYLE = "font-size:13px;line-height:1.7;color:#68705f;margin-top:8px;"


def inline_md(text: str) -> str:
    escaped = html.escape(text.strip(), quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def figure(src: str, alt: str, caption: str, credit_label: str, credit: str) -> str:
    cap = (
        f"{html.escape(caption, quote=False)}<br>"
        f"{html.escape(credit_label, quote=False)}: {html.escape(credit, quote=False)}"
    )
    return (
        f'<figure style="{FIG_STYLE}">\n'
        f'  <img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" '
        f'width="1280" decoding="async" style="{IMG_STYLE}">\n'
        f'  <figcaption style="{CAP_STYLE}">{cap}</figcaption>\n'
        f"</figure>"
    )


def body_html(paras: list[str], fig: str) -> str:
    parts = [fig] + [f"<p>{inline_md(p)}</p>" for p in paras]
    return "\n".join(parts)


def replace_article(html_text: str, body: str) -> str:
    new, n = re.subn(
        r'(<article class="article-content">).*?(</article>)',
        lambda m: m.group(1) + "\n" + body + "\n    " + m.group(2),
        html_text,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit("could not replace article body")
    return new


def replace_description(html_text: str, description: str) -> str:
    new, n = re.subn(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{html.escape(description, quote=True)}">',
        html_text,
        count=1,
    )
    if n != 1:
        raise SystemExit("could not replace description")
    return new


def copy_image() -> None:
    dest = DOCS / IMG
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not UPLOAD.is_file():
        raise SystemExit(f"missing upload: {UPLOAD}")
    data = UPLOAD.read_bytes()
    if not data.startswith(b"\xff\xd8") or len(data) < 20_000:
        raise SystemExit("upload is not a usable JPEG")
    shutil.copyfile(UPLOAD, dest)


def write_markdown() -> None:
    ar = ROOT / "content" / "posts" / f"{AR_SLUG}.md"
    ar.write_text(
        "\n".join(
            [
                "---",
                f'title: "{AR_TITLE}"',
                f"slug: {AR_SLUG}",
                "date: 2026-09-25 09:00:00",
                "author: صيد",
                "categories: [صيد]",
                f"featured: ../../{IMG}",
                "---",
                "",
                body_html(
                    AR_PARAS,
                    figure(f"../../{IMG}", AR_ALT, AR_ALT, "الصورة", AR_CREDIT),
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    en = ROOT / "content" / "en" / f"{EN_SLUG}.md"
    en.write_text(
        "\n".join(
            [
                f"# {EN_TITLE}",
                "",
                f"**Source AR URL:** https://sayd-magazine.com/posts/{AR_SLUG}/",
                f"**Source AR title:** {AR_TITLE}",
                f"**Suggested slug:** {EN_SLUG}",
                "**Category:** Hunting",
                "",
                "## Lead",
                "",
                "## Body",
                "",
                *EN_PARAS,
                "",
                "## Notes",
                "",
                f"- Photo: `{IMG_NAME}`",
                f"- AR caption: {AR_ALT}",
                f"- EN caption: {EN_ALT}",
                f"- Photo credit: {AR_CREDIT} / {EN_CREDIT}",
                f"- Ticker AR: {AR_TICKER}",
                f"- Ticker EN: {EN_TICKER}",
                "- No «المصدر» footer. No opening «أعلنت المديرية» / «صدر عن».",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_articles() -> None:
    ar_src = (
        DOCS / "posts" / "مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات" / "index.html"
    ).read_text(encoding="utf-8")
    ar = ar_src.replace(
        "مصر: قرار جديد لتنظيم الصيد وملاحقة المخالفات في موسم هجرة الخريف",
        AR_TITLE,
    )
    ar = ar.replace(
        "../../en/posts/egypt-new-hunting-rules-burullus-autumn-migration/index.html",
        f"../../en/posts/{EN_SLUG}/index.html",
    )
    ar = ar.replace(
        "../../posts/مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات/index.html",
        f"../../posts/{AR_SLUG}/index.html",
    )
    ar = ar.replace(
        '<div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / '
        '<a href="../../category/أخبار/index.html">أخبار</a> / مقال</div>',
        '<div class="breadcrumb"><a href="../../index.html">الرئيسية</a> / '
        '<a href="../../category/صيد/index.html">صيد وفروسية</a> / مقال</div>',
    )
    ar = ar.replace(
        '<div><a class="badge" href="../../category/أخبار/index.html">أخبار</a></div>',
        '<div><a class="badge" href="../../category/صيد/index.html">صيد وفروسية</a></div>',
    )
    ar = ar.replace(
        f'<div class="article-meta"><span class="meta-item">20 أيلول 2026</span>'
        f'<span class="meta-item">صيد</span></div>',
        f'<div class="article-meta"><span class="meta-item">{AR_DATE}</span>'
        f'<span class="meta-item">صيد</span></div>',
        1,
    )
    ar = replace_description(ar, AR_DESC)
    ar = replace_article(
        ar,
        body_html(AR_PARAS, figure(f"../../{IMG}", AR_ALT, AR_ALT, "الصورة", AR_CREDIT)),
    )
    ar = re.sub(
        r'<ul class="latest-list">.*?</ul>',
        (
            '<ul class="latest-list">'
            f'<li><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a>'
            f'<span class="meta">{AR_DATE}</span></li>'
            '<li><a href="../../posts/مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات/index.html">'
            "مصر: قرار جديد لتنظيم الصيد وملاحقة المخالفات في موسم هجرة الخريف</a>"
            '<span class="meta">20 أيلول 2026</span></li>'
            "</ul>"
        ),
        ar,
        count=1,
        flags=re.S,
    )
    dest = DOCS / "posts" / AR_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(ar, encoding="utf-8")

    en_src = (
        DOCS / "en" / "posts" / "egypt-new-hunting-rules-burullus-autumn-migration" / "index.html"
    ).read_text(encoding="utf-8")
    en = en_src.replace(
        "Egypt: New Hunting Rules and Field Action as Autumn Migration Begins",
        EN_TITLE,
    )
    en = en.replace(
        "../../../posts/مصر-قرار-جديد-لتنظيم-الصيد-وملاحقة-المخالفات/index.html",
        f"../../../posts/{AR_SLUG}/index.html",
    )
    en = en.replace(
        '<div><span class="badge">News</span></div>',
        '<div><span class="badge">Hunting &amp; Equestrian</span></div>',
    )
    en = en.replace(
        '<div class="article-meta"><span class="meta-item">20 September 2026</span>'
        '<span class="meta-item">Sayd</span></div>',
        f'<div class="article-meta"><span class="meta-item">{EN_DATE}</span>'
        '<span class="meta-item">Sayd</span></div>',
        1,
    )
    en = replace_description(en, EN_DESC)
    en = replace_article(
        en,
        body_html(
            EN_PARAS,
            figure(f"../../../{IMG}", EN_ALT, EN_ALT, "Photo", EN_CREDIT),
        ),
    )
    dest = DOCS / "en" / "posts" / EN_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(en, encoding="utf-8")


def patch_listings() -> None:
    row = f"""<article class="post-row">
  <a class="thumb" href="../../posts/{AR_SLUG}/index.html"><img src="../../{IMG}" alt="{html.escape(AR_ALT, quote=True)}" loading="lazy"></a>
  <div class="body">
    <h2><a href="../../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <div class="meta">{AR_DATE}</div>
    <p class="excerpt">{AR_DESC}</p>
  </div>
</article>
"""
    cat = DOCS / "category" / "صيد" / "index.html"
    text = cat.read_text(encoding="utf-8")
    if AR_SLUG not in text.split('class="post-list"', 1)[-1][:2500]:
        text = text.replace('<div class="post-list">\n', '<div class="post-list">\n' + row, 1)
    text = text.replace(
        'صيد وفروسية <span class="badge">9</span>',
        'صيد وفروسية <span class="badge">10</span>',
        1,
    )
    cat.write_text(text, encoding="utf-8")

    archive = DOCS / "articles" / "index.html"
    text = archive.read_text(encoding="utf-8")
    archive_row = f"""<article class="post-row">
  <a class="thumb" href="../posts/{AR_SLUG}/index.html"><img src="../{IMG}" alt="{html.escape(AR_ALT, quote=True)}" loading="lazy"></a>
  <div class="body">
    <h2><a href="../posts/{AR_SLUG}/index.html">{AR_TITLE}</a></h2>
    <div class="meta">{AR_DATE} · صيد وفروسية</div>
    <p class="excerpt">{AR_DESC}</p>
  </div>
</article>
"""
    head = text.split('class="post-list"', 1)[-1][:4000]
    if AR_SLUG not in head:
        text = text.replace('<div class="post-list">\n', '<div class="post-list">\n' + archive_row, 1)
    if "الأرشيف — كل المقالات (710)" not in text:
        raise SystemExit("archive count marker missing")
    text = text.replace("الأرشيف — كل المقالات (710)", "الأرشيف — كل المقالات (711)", 1)
    archive.write_text(text, encoding="utf-8")

    stories = DOCS / "en" / "stories" / "index.html"
    text = stories.read_text(encoding="utf-8")
    if EN_SLUG not in text:
        card = f"""<article class="card overlay">
  <a class="thumb" href="../posts/{EN_SLUG}/index.html"><img src="../../{IMG}" alt="{html.escape(EN_ALT, quote=True)}" loading="lazy"></a>
  <div class="body">
    <h3><a href="../posts/{EN_SLUG}/index.html">{EN_TITLE}</a></h3>
    <div class="meta">{EN_DATE}</div>
  </div>
</article>
"""
        text = text.replace('<div class="grid-4">\n', '<div class="grid-4">\n' + card, 1)
        stories.write_text(text, encoding="utf-8")


def links(items: list[tuple[str, str]], prefix: str) -> str:
    return "".join(
        f'<a href="{prefix}{slug}/index.html">{title}</a>' for slug, title in items
    )


def replace_ticker(html_text: str, inner: str) -> str:
    return re.sub(
        r'(<div class="ticker"[^>]*>)(.*?)(</div>)',
        lambda m: m.group(1) + inner + m.group(3),
        html_text,
        count=2,
        flags=re.S,
    )


def ar_items() -> list[tuple[str, str]]:
    data = json.loads((ROOT / "content" / "ticker.json").read_text(encoding="utf-8"))
    items = [(item["slug"], item["title"]) for item in data["items"]]
    if len(items) != 8 or items[0] != (AR_SLUG, AR_TICKER):
        raise SystemExit(f"ticker.json is not the Bekaa-led eight: {items[0] if items else None}")
    return items


def en_items() -> list[tuple[str, str]]:
    html_text = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<div class="ticker"[^>]*>(.*?)</div>', html_text, re.S)
    if not block:
        raise SystemExit("English homepage ticker missing")
    found = re.findall(
        r'<a href="[^"]*?/([^/]+)/index\.html">([^<]*)</a>',
        block.group(1),
    )
    if found and found[0][0] == EN_SLUG:
        return found[:8]
    if len(found) != 8 or found[-1][0] != "saudi-sixth-hunting-season-2026-2027-rules":
        raise SystemExit(f"English ticker tail is not the Saudi line: {found[-1] if found else None}")
    return [(EN_SLUG, EN_TICKER), *found[:-1]]


def sync_tickers() -> tuple[int, int]:
    ar = ar_items()
    en = en_items()
    ar_n = en_n = 0
    for path in DOCS.rglob("*.html"):
        html_text = path.read_text(encoding="utf-8")
        if '<div class="ticker"' not in html_text:
            continue
        posix = path.as_posix()
        if "/en/" in posix:
            match = re.search(r'<div class="ticker"[^>]*>(.*?)</div>', html_text, re.S)
            href = re.search(r'href="([^"]+)"', match.group(1) if match else "")
            if not href:
                continue
            prefix = re.sub(r"[^/]+/index\.html$", "", href.group(1))
            new = replace_ticker(html_text, links(en, prefix))
            if new != html_text:
                path.write_text(new, encoding="utf-8")
                en_n += 1
            continue
        rel = path.relative_to(DOCS)
        depth = len(rel.parts) - 1
        prefix = "../" * depth + "posts/"
        new = replace_ticker(html_text, links(ar, prefix))
        if new != html_text:
            path.write_text(new, encoding="utf-8")
            ar_n += 1
    return ar_n, en_n


def verify() -> None:
    ar = (DOCS / "index.html").read_text(encoding="utf-8")
    en = (DOCS / "en" / "index.html").read_text(encoding="utf-8")
    ticker = re.findall(r'<div class="ticker"[^>]*>(.*?)</div>', ar, re.S)
    if len(ticker) < 2 or ticker[0] != ticker[1]:
        raise SystemExit("Arabic ticker copies diverged")
    if not ticker[0].startswith(f'<a href="posts/{AR_SLUG}/index.html">{AR_TICKER}</a>'):
        raise SystemExit("ticker does not open with the locked Bekaa line")
    if ticker[0].count("<a ") != 8:
        raise SystemExit("ticker must hold 8 items")
    if "السعودية-تطلق-موسم-الصيد-السادس-بضواب" in ticker[0]:
        raise SystemExit("oldest ticker line should drop to keep 8")
    if "من كل وادي خبر" not in ar:
        raise SystemExit("ticker label changed")
    en_ticker = re.findall(r'<div class="ticker"[^>]*>(.*?)</div>', en, re.S)
    if not en_ticker or not en_ticker[0].startswith(
        f'<a href="posts/{EN_SLUG}/index.html">{EN_TICKER}</a>'
    ):
        raise SystemExit("English ticker does not open with the twin")
    if en_ticker[0].count("<a ") != 8:
        raise SystemExit("English ticker length failed")
    latest = ar.split("latest-feed", 1)[1].split("</ul>", 1)[0]
    if not latest.startswith(f"\n<li>\n  <a href=\"posts/{AR_SLUG}/index.html\">") and AR_SLUG not in latest[:500]:
        raise SystemExit("Bekaa story is not the first Latest item")
    if "feed-thumb" not in latest or IMG_NAME not in latest:
        raise SystemExit("Latest card is missing the small thumb")
    if AR_SLUG in ar.split("featured-mosaic", 1)[1].split("latest-col", 1)[0]:
        raise SystemExit("story must stay off the feature mosaic")
    article = (DOCS / "posts" / AR_SLUG / "index.html").read_text(encoding="utf-8")
    body = article.split('class="article-content"', 1)[1].split("</article>", 1)[0]
    if "20,640" not in body or "جديدة الفاكهة" not in body or "وماسا والناصرية" not in body:
        raise SystemExit("Arabic figures or place list drifted")
    if "المصدر:" in body or body.strip().startswith("<p>أعلنت") or "صدر عن" in body[:400]:
        raise SystemExit("press-release framing leaked into the body")
    if AR_CREDIT not in body:
        raise SystemExit("photo credit missing")
    twin = (DOCS / "en" / "posts" / EN_SLUG / "index.html").read_text(encoding="utf-8")
    if "Jadidat al-Fakiha" not in twin or "20,640" not in twin or EN_TITLE not in twin:
        raise SystemExit("English twin drifted")


def main() -> None:
    copy_image()
    write_markdown()
    write_articles()
    patch_listings()
    import homepage_unique_cards as lock

    lock.apply_ar_home()
    lock.apply_en_home()
    ar_n, en_n = sync_tickers()
    from seo_foundation import apply as apply_seo

    stats = apply_seo(DOCS)
    verify()
    print(f"published Bekaa nets; tickers AR={ar_n} EN={en_n}; seo {stats}")


if __name__ == "__main__":
    main()
