#!/usr/bin/env python3
"""Homepage latest-feed: long Suheil 80k/158 is featured-only."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
LONG = "80-ألف-زائر-و158-جهة-من-15-دولة-سهيل-2026-يختتم-ع"
QATAR = "قطر-أكثر-من-80-ألف-زائر-في-ختام-سهيل-2026"


def test_long_80k_featured_not_latest() -> None:
    mosaic = HOME.split('class="featured-mosaic"', 1)[1].split('class="latest-col"', 1)[0]
    latest = HOME.split('class="latest-feed"', 1)[1].split("</ul>", 1)[0]
    ticker = HOME.split('class="ticker"', 1)[1].split("</div>", 1)[0]
    assert LONG in mosaic
    assert LONG not in latest
    assert QATAR in latest
    assert QATAR in ticker


if __name__ == "__main__":
    test_long_80k_featured_not_latest()
    print("ok")
