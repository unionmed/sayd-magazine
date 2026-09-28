#!/usr/bin/env python3
"""Check that a newly published AR/EN pair has matching placement decisions.

Usage: python3 scripts/check_bilingual_publication.py AR_SLUG EN_SLUG CATEGORY
For example, CATEGORY is صيد for the Hunting door. Run before every publish.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def contains(section: str, slug: str) -> bool:
    return f"posts/{slug}/index.html" in section


def block(page: str, start: str, end: str) -> str:
    return page.split(start, 1)[1].split(end, 1)[0]


def placement(home: str, slug: str) -> dict[str, bool]:
    return {
        "lead": contains(block(home, 'class="card overlay feature-lead"', "</article>"), slug),
        "side": contains(block(home, 'class="feature-stack"', '<ul class="latest-feed">'), slug),
        "latest": contains(block(home, 'class="latest-feed"', "</ul>"), slug),
        "ticker": contains(block(home, 'class="ticker"', "</div>"), slug),
    }


def main(ar: str, en: str, category: str) -> None:
    pairs = json.loads((ROOT / "content/en/pairs.json").read_text())["pairs"]
    assert pairs.get(ar) == en, "Missing AR/EN pair mapping"
    homes = [(DOCS / "index.html").read_text(), (DOCS / "en/index.html").read_text()]
    positions = [placement(homes[0], ar), placement(homes[1], en)]
    assert positions[0] == positions[1], f"Homepage placement differs: {positions}"
    assert any(positions[0].values()), "Article has no homepage placement"
    for home in homes:
        latest = block(home, 'class="latest-feed"', "</ul>")
        assert len(re.findall(r"<li\b", latest)) <= 10, "Latest exceeds ten cards"
    for prefix, slug in (("", ar), ("en/", en)):
        article = DOCS / prefix / "posts" / slug / "index.html"
        category_page = DOCS / prefix / "category" / category / "index.html"
        archive = DOCS / prefix / ("articles" if not prefix else "stories") / "index.html"
        assert article.is_file(), f"Missing article: {article}"
        for page in (category_page, archive):
            assert contains(page.read_text(), slug), f"Missing {slug} in {page}"
    print(f"AR/EN placement matched; category {category}, archive, and Latest cap verified: {positions[0]}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: check_bilingual_publication.py AR_SLUG EN_SLUG CATEGORY")
    main(*sys.argv[1:])
