"""Regression checks for English door thumbnails; no network or writes to docs."""
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote

import apply_site_ia as build


def test_published_doors():
    total = pictured = 0
    missing = []
    for page in sorted((build.DOCS / "en/category").glob("*/index.html")):
        text = page.read_text(encoding="utf-8")
        for row in build.POST_ROW_RE.findall(text):
            total += 1
            href = re.search(r'<h2><a href="([^"]+)"', row).group(1)
            target = (page.parent / unquote(href)).resolve()
            assert target.is_file(), href
            expected = build._en_story_thumb(target.parent.name, "Title", target.read_text(encoding="utf-8"))
            image = re.search(r'<a class="thumb" href="([^"]+)"><img src="([^"]+)" alt="([^"]+)"', row)
            assert bool(image) == bool(expected), target.parent.name
            if not image:
                missing.append(target.parent.name)
                continue
            assert image.group(1) == href
            assert (page.parent / unquote(image.group(2))).resolve().is_file()
            assert "/media/brand/" not in image.group(2)
            assert image.group(2) == re.search(r'src="([^"]+)"', expected).group(1)
            pictured += 1
    assert total > 0 and pictured > 0
    print(f"English doors: {pictured}/{total} cards have verified local images; missing: {missing}")


def test_image_selection():
    original = build.DOCS
    with tempfile.TemporaryDirectory() as folder:
        build.DOCS = Path(folder)
        try:
            (build.DOCS / "en").mkdir()
            (build.DOCS / "media").mkdir()
            for name in ("chosen.jpg", "lead.jpg", "related.jpg"):
                (build.DOCS / "media" / name).write_bytes(b"fixture")
            home = build.DOCS / "en/index.html"
            home.write_text('<article><a href="posts/story/index.html"><img src="../media/chosen.jpg"></a></article>')
            body = '<article class="article-content"><img src="../../../media/missing.jpg"><img src="../../../media/lead.jpg"></article><article><img src="../../../media/related.jpg"></article>'
            chosen = build._en_story_thumb("story", 'Title & "quote"', body)
            assert "chosen.jpg" in chosen and "&amp; &quot;quote&quot;" in chosen
            home.write_text("")
            assert "lead.jpg" in build._en_story_thumb("story", "Title", body)
            assert build._en_story_thumb("story", "Title", '<article class="article-content"></article><img src="../../../media/related.jpg">') == ""
        finally:
            build.DOCS = original


if __name__ == "__main__":
    test_image_selection()
    test_published_doors()
