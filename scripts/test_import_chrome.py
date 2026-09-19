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


if __name__ == "__main__":
    test_source_has_no_regression_strings()
    test_ticker_source_is_mars_list()
    test_shared_ticker_all_depths()
    test_layout_footer_and_default_ticker()
    test_docs_already_share_clean_chrome()
    print("ok")
