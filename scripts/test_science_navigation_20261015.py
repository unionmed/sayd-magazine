#!/usr/bin/env python3
"""Regression: Science appears once after Wildlife, while Bird Encyclopedia stays distinct."""
import sys
import json
from pathlib import Path
from urllib.parse import unquote
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_science_discoveries_20261015 import new_category, category_for

SCIENCE = "علوم-واكتشافات"
BIRDS = "موسوعة-الطيور"
WILDLIFE = "حياة-برية-وتخييم"
POETRY = "ثقافة-وتراث"

def test_navigation(lang):
    t = html.parse(str(category_for(lang)))
    surfaces = {
        "desktop": t.xpath('//nav[contains(concat(" ",normalize-space(@class)," ")," main-nav ")]'),
        "mobile": t.xpath('//nav[contains(concat(" ",normalize-space(@class)," ")," mobile-nav ")]'),
        "drawer": t.xpath('//nav[contains(concat(" ",normalize-space(@class)," ")," drawer-nav ")]'),
        "footer": t.xpath('//footer[contains(concat(" ",normalize-space(@class)," ")," site-footer ")]'),
    }
    for label, found in surfaces.items():
        assert len(found) == 1, (lang, label, "missing navigation")
        links = [unquote(x) for x in found[0].xpath('.//a/@href') if "/category/" in x]
        def count(folder):
            return sum("/category/" + folder + "/" in x for x in links)
        assert count(SCIENCE) == 1, (lang, label, "Science duplicate/missing", links)
        assert count(WILDLIFE) == 1, (lang, label, "Wildlife missing")
        if label != "drawer":
            assert count(BIRDS) == 1, (lang, label, "Bird Encyclopedia missing")
            assert count(POETRY) == 1, (lang, label, "Poetry missing")
            assert next(i for i,x in enumerate(links) if "/category/"+WILDLIFE+"/" in x) < next(i for i,x in enumerate(links) if "/category/"+SCIENCE+"/" in x) < next(i for i,x in enumerate(links) if "/category/"+POETRY+"/" in x), (lang,label,"Science order")
        else:
            assert next(i for i,x in enumerate(links) if "/category/"+WILDLIFE+"/" in x) < next(i for i,x in enumerate(links) if "/category/"+SCIENCE+"/" in x)
    print("PASS",lang,"four navigation surfaces have exactly one Science link")

def main():
    data=json.loads((ROOT/"content/features/science-discoveries-20261015.json").read_text())
    articles=sorted(data["articles"],key=lambda a:a["published"],reverse=True)
    items=[(a,next(p for p in a["photos"] if p["role"]=="lead")["local_path"]) for a in articles]
    for lang in ("ar","en","fr"):
        test_navigation(lang)
        # Rebuild only the category in this disposable checkout, to prove that
        # a future editorial regeneration cannot recreate the duplicate.
        new_category(items,lang)
        test_navigation(lang)
    print("PASS: category regeneration retains Bird Encyclopedia and ordered unique Science")

if __name__ == "__main__":
    main()
