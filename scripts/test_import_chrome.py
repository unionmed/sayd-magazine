#!/usr/bin/env python3
"""Shared chrome: one ticker + professional footer, no urgent/export notes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "import_wxr", ROOT / "scripts" / "import-wxr.py"
)
import_wxr = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(import_wxr)

ABOUT_BLURB = import_wxr.ABOUT_BLURB
DEFAULT_TICKER_ITEMS = import_wxr.DEFAULT_TICKER_ITEMS
TICKER_LABEL = import_wxr.TICKER_LABEL
chrome_ticker = import_wxr.chrome_ticker
layout = import_wxr.layout
load_ticker_items = import_wxr.load_ticker_items
load_homepage_lists = import_wxr.load_homepage_lists

FORBIDDEN = (
    "عاجل",
    "TICKER_URGENT",
    "نسخة ثابتة على GitHub Pages",
    "المحتوى من تصدير ووردبريس",
    "label-urgent",
)


def test_source_has_no_regression_strings() -> None:
    src = (ROOT / "scripts" / "import-wxr.py").read_text(encoding="utf-8")
    for needle in FORBIDDEN:
        assert needle not in src, needle


def test_ticker_source_is_mars_list() -> None:
    items = load_ticker_items()
    assert items == list(DEFAULT_TICKER_ITEMS)
    assert len(items) == 7
    slugs = [slug for slug, _ in items]
    assert slugs[0].startswith("كابس")
    assert "سهيل" in items[1][1]


def test_shared_ticker_all_depths() -> None:
    items = load_ticker_items()
    html0 = chrome_ticker(0, items)
    html1 = chrome_ticker(1, items)
    html2 = chrome_ticker(2, items)
    titles = [title for _, title in items]
    for html, prefix in ((html0, "posts/"), (html1, "../posts/"), (html2, "../../posts/")):
        assert f'aria-label="{TICKER_LABEL}"' in html
        assert f">{TICKER_LABEL}<" in html
        assert "label-urgent" not in html
        assert "عاجل" not in html
        assert html.count('<div class="ticker">') == 1
        for title in titles:
            assert title in html
        assert prefix in html


def test_layout_footer_and_default_ticker() -> None:
    page = layout("فريق العمل", "<main>body</main>", depth=2)
    assert ABOUT_BLURB in page
    assert "نسخة ثابتة على GitHub Pages" not in page
    assert "تصدير ووردبريس" not in page
    assert "GitHub Pages" not in page
    assert "عاجل" not in page
    assert "label-urgent" not in page
    assert TICKER_LABEL in page
    for _, title in DEFAULT_TICKER_ITEMS:
        assert title in page
    assert 'src="../../media/brand/sayd-logo.png"' in page
    assert 'src="../../media/brand/sayd-footer-logo.png"' in page


def test_docs_already_share_clean_chrome() -> None:
    """Mars synced HTML — generator must keep emitting the same ticker titles."""
    samples = [
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "pages" / "من-نحن" / "index.html",
        ROOT / "docs" / "posts" / "كابس-ومكشب-لحماية-طيور-الخريف-في-ل" / "index.html",
    ]
    titles = [title for _, title in DEFAULT_TICKER_ITEMS]
    for path in samples:
        html = path.read_text(encoding="utf-8")
        assert "عاجل" not in html, path
        assert "label-urgent" not in html, path
        assert "GitHub Pages" not in html, path
        assert "تصدير ووردبريس" not in html, path
        assert TICKER_LABEL in html
        for title in titles:
            assert title in html, (path, title)
        m = re.search(r'<div class="ticker">(.*?)</div>', html, re.S)
        assert m, path
        found = re.findall(r">([^<]+)</a>", m.group(1))
        assert found == titles, (path.name, found)


def _section(html: str, start: str, end: str) -> str:
    i = html.find(start)
    j = html.find(end, i + 1) if i >= 0 else -1
    assert i >= 0 and j > i, (start, end)
    return html[i:j]


def test_homepage_latest_matches_nayef() -> None:
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    lists = load_homepage_lists()
    featured = _section(html, "featured-mosaic", "latest-feed")
    latest = _section(html, "latest-feed", "</ul>")
    ticker = re.search(r'<div class="ticker">(.*?)</div>', html, re.S).group(1)

    assert "80-ألف-زائر-و158-جهة" in featured
    assert "80-ألف-زائر-و158-جهة" not in latest
    assert "80-ألف-زائر-و158-جهة" not in ticker
    assert "البجع-الأبيض" not in latest
    assert "البجع-الأبيض" not in ticker
    assert "البجع-الأبيض" not in featured
    assert "عصفور-الشمس" not in latest
    assert "عصفور-الشمس" not in ticker
    assert "عصفور-الشمس" not in featured
    assert "صيد-تعود-بحلة-جديدة" not in html
    assert "السعودية-تشدد-على-ضوابط" not in html
    assert "قطر-أكثر-من-80-ألف-زائر" in latest
    assert "قطر-أكثر-من-80-ألف-زائر" in ticker
    assert "السعودية-تطلق-موسم-الصيد-السادس-بضواب" in featured
    assert "السعودية-تطلق-موسم-الصيد-السادس-بضواب" in latest

    latest_slugs = re.findall(r'href="posts/([^/"]+)/index.html"', latest)
    assert latest_slugs == lists["latest"]
    assert "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع" not in lists["latest"]
    assert "البجع-الأبيض-الكبير-great-white-pelican-بعدسة-نايف-ك" in lists["omit"]


if __name__ == "__main__":
    test_source_has_no_regression_strings()
    test_ticker_source_is_mars_list()
    test_shared_ticker_all_depths()
    test_layout_footer_and_default_ticker()
    test_docs_already_share_clean_chrome()
    test_homepage_latest_matches_nayef()
    print("ok")
