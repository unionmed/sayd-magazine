#!/usr/bin/env python3
"""Strip Nayef chrome links and rename ثقافة وتراث → شعر وفن in published HTML.

Does not rebuild from WXR. Archive articles for Partners and Miscellany stay.
شريط and the hunter-game page (and other empty shells still linked in chrome)
are replaced with an archive redirect.
"""

from __future__ import annotations

import re
from pathlib import Path

from site_cache import CSS_CACHE

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARCHIVE = "https://sayd-magazine.com/articles/"

# Removed from nav / drawer only. Badges and breadcrumbs stay (deep URLs).
NAV_ONLY = ("category/جعبة-المنوعات/index.html",)

# Removed from sidebar and footer lists. Category index stays.
CHROME_LISTS = (
    "category/جعبة-المنوعات/index.html",
    "category/شريط/index.html",
    "pages/شركاؤنا/index.html",
    "pages/751-2/index.html",
    "pages/تصفح-صيد/index.html",
    "pages/الأحوال-الجوية/index.html",
    "pages/الدخول/index.html",
    "pages/أرشيف-الموقع/index.html",
)

# Destination is cancelled: strip every remaining href, including badges.
CANCELLED_HREFS = (
    "category/شريط/index.html",
    "pages/751-2/index.html",
    "pages/تصفح-صيد/index.html",
    "pages/الأحوال-الجوية/index.html",
    "pages/الدخول/index.html",
    "pages/أرشيف-الموقع/index.html",
)

CANCELLED_PAGES = (
    "category/شريط/index.html",
    "pages/751-2/index.html",
    "pages/تصفح-صيد/index.html",
    "pages/الأحوال-الجوية/index.html",
    "pages/الدخول/index.html",
    "pages/أرشيف-الموقع/index.html",
)

NAV_RE = re.compile(
    r'(<nav class="(?:main-nav|drawer-nav)"[^>]*>)(.*?)(</nav>)',
    re.S,
)
REGION_RE = re.compile(
    r'(<(?:aside class="sidebar[^"]*"|footer class="site-footer")[^>]*>)(.*?)(</(?:aside|footer)>)',
    re.S,
)
HOME_SECTION_RE = (
    r'<section class="home-section[^"]*">\s*'
    r'<div class="section-head[^"]*">\s*'
    r"<h2>{heading}</h2>.*?</section>\s*"
)


def _strip_hrefs(html: str, suffixes: tuple[str, ...], *, crumbs: bool) -> str:
    for suf in suffixes:
        esc = re.escape(suf)
        if crumbs:
            html = re.sub(
                rf'\s*/\s*<a\b[^>]*href="[^"]*{esc}"[^>]*>.*?</a>',
                "",
                html,
                flags=re.S,
            )
        html = re.sub(
            rf'\s*<a\b[^>]*href="[^"]*{esc}"[^>]*>.*?</a>',
            "",
            html,
            flags=re.S,
        )
    return html


def _strip_lists(html: str, suffixes: tuple[str, ...]) -> str:
    def repl(match: re.Match[str]) -> str:
        block = match.group(2)
        for suf in suffixes:
            block = re.sub(
                rf'\s*<li>\s*<a\b[^>]*href="[^"]*{re.escape(suf)}"[^>]*>.*?</a>\s*</li>',
                "",
                block,
                flags=re.S,
            )
        return match.group(1) + block + match.group(3)

    return REGION_RE.sub(repl, html)


def _strip_nav(html: str, suffixes: tuple[str, ...]) -> str:
    def repl(match: re.Match[str]) -> str:
        inner = _strip_hrefs(match.group(2), suffixes, crumbs=False)
        return match.group(1) + inner + match.group(3)

    return NAV_RE.sub(repl, html)


def _drop_home_desk(html: str, heading: str) -> str:
    return re.sub(HOME_SECTION_RE.format(heading=re.escape(heading)), "", html, count=1, flags=re.S)


def rename_culture(html: str) -> str:
    """Visible category label. Leave prose such as «ثقافة وتراث الخيل»."""
    html = html.replace(">ثقافة وتراث<", ">شعر وفن<")
    html = html.replace(">ثقافة وتراث ", ">شعر وفن ")
    html = html.replace("تصنيفات / ثقافة وتراث", "تصنيفات / شعر وفن")
    html = html.replace(" · ثقافة وتراث", " · شعر وفن")
    html = html.replace("ثقافة وتراث —", "شعر وفن —")
    html = html.replace("قسم ثقافة وتراث", "قسم شعر وفن")
    html = html.replace('title="ثقافة وتراث"', 'title="شعر وفن"')
    html = html.replace("Culture and heritage", "Poetry &amp; Art")
    return html


def _strip_en_miscellany_label(html: str) -> str:
    """EN sidebar item labeled Miscellany that points at the stories index."""
    return re.sub(
        r'\s*<li>\s*<a\b[^>]*>\s*<span>Miscellany</span>\s*</a>\s*</li>',
        "",
        html,
        flags=re.S,
    )


def rewrite_html(html: str) -> str:
    html = _strip_lists(html, CHROME_LISTS)
    html = _strip_nav(html, NAV_ONLY + ("category/شريط/index.html",))
    html = _strip_hrefs(html, CANCELLED_HREFS, crumbs=True)
    html = _drop_home_desk(html, "جعبة المنوعات")
    html = _drop_home_desk(html, "Miscellany")
    html = _strip_en_miscellany_label(html)
    html = rename_culture(html)
    html = html.replace("?v=20260922-empty-cats-b", f"?v={CSS_CACHE}")
    return html


def archive_redirect_html() -> str:
    url = ARCHIVE
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>الأرشيف — مجلة صيد</title>
  <link rel="canonical" href="{url}">
  <meta http-equiv="refresh" content="0; url={url}">
  <meta property="og:title" content="الأرشيف — مجلة صيد">
  <meta property="og:url" content="{url}">
  <script>location.replace("{url}");</script>
</head>
<body>
  <p><a href="{url}">الأرشيف</a></p>
</body>
</html>
"""


def apply(docs: Path = DOCS) -> int:
    changed = 0
    for path in docs.rglob("*.html"):
        rel = path.relative_to(docs).as_posix()
        if rel in CANCELLED_PAGES:
            continue
        original = path.read_text(encoding="utf-8")
        updated = rewrite_html(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    redirect = archive_redirect_html()
    for rel in CANCELLED_PAGES:
        dest = docs / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        for extra in dest.parent.glob("page-*.html"):
            extra.unlink()
        dest.write_text(redirect, encoding="utf-8")
    sitemap = docs / "sitemap.xml"
    if sitemap.is_file():
        text = sitemap.read_text(encoding="utf-8")
        text2 = re.sub(
            r"\s*<url>\s*<loc>https://sayd-magazine.com/category/%D8%B4%D8%B1%D9%8A%D8%B7/</loc>\s*</url>",
            "",
            text,
        )
        if text2 != text:
            sitemap.write_text(text2, encoding="utf-8")
    return changed


if __name__ == "__main__":
    n = apply()
    print(f"rewrote {n} html files; cancelled shells now redirect to the archive")
