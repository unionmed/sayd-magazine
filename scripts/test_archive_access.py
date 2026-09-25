#!/usr/bin/env python3
"""Archive permalink redirects and recovered article images."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import archive_access as archive  # noqa: E402
import seo_foundation as seo  # noqa: E402

DOCS = ROOT / "docs"


def test_legacy_permalink_rewrite_skips_upload_paths() -> None:
    html = (
        '<a href="https://sayd-magazine.com/4267/">https://sayd-magazine.com/4267/</a>'
        '<a href="/?p=169">أخبار</a>'
        '<a href="https://sayd-magazine.com/?p=2945">https://sayd-magazine.com/?p=2945</a>'
        '<img src="https://sayd-magazine.com/wp-content/uploads/2015/07/photo.jpg">'
    )
    hrefs = {
        "4267": "https://sayd-magazine.com/posts/rescued-bird/",
        "169": "https://sayd-magazine.com/posts/tracking/",
        "2945": "https://sayd-magazine.com/posts/training/",
    }
    out = archive.rewrite_legacy_permalinks(html, hrefs)
    assert 'href="https://sayd-magazine.com/posts/rescued-bird/"' in out
    assert "4267" not in out
    assert 'href="https://sayd-magazine.com/posts/tracking/"' in out
    assert 'href="https://sayd-magazine.com/posts/training/"' in out
    assert "wp-content/uploads/2015/07/photo.jpg" in out


def test_numeric_stub_is_not_rewritten_or_sitemapped() -> None:
    """/{post_id}/ must open the article and stay out of the sitemap."""
    samples = {
        "57": "منى-الخطيب-عاشقة-المغامرات-على-الدراج-2",
        "92": "طائر-الحسون-يقتله-القواصون-الجهلة",
        "1302": "قوانين-تصاريح-الاسلحه-في-السعوديه",
        "4267": "بالصور-والفيديو-صياد-مسؤول-ينقذ-طائر-ا",
    }
    sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    for post_id, slug in samples.items():
        rel = Path(f"{post_id}/index.html")
        url = seo.public_url(Path(f"posts/{slug}/index.html"))
        text = (DOCS / rel).read_text(encoding="utf-8")
        assert not seo.in_sitemap(rel)
        assert f"<loc>https://sayd-magazine.com/{post_id}/</loc>" not in sitemap
        assert f'<link rel="canonical" href="{url}">' in text
        assert f'<meta http-equiv="refresh" content="0; url={url}">' in text
        assert f'location.replace("{url}");' in text
        assert (DOCS / "posts" / slug / "index.html").is_file()
        assert seo.apply_html(text, DOCS / rel, DOCS, rel, {}) == text


def test_recovered_archive_image_is_local() -> None:
    """The Saudi flag photo on the permits article used to hotlink a dead host."""
    page = DOCS / "posts" / "قوانين-تصاريح-الاسلحه-في-السعوديه" / "index.html"
    text = page.read_text(encoding="utf-8")
    assert "alfalivehost" not in text
    assert "wp-content" not in text
    assert "العلم-السعودي-علم-السعودية-السعوديه.jpg" in text
    src = None
    for match in archive._IMG_SRC_RE.finditer(text):
        if "العلم-السعودي" in match.group(2):
            src = match.group(2)
            break
    assert src and "media/uploads/" in src
    path = (page.parent / src.split("?", 1)[0]).resolve()
    assert path.is_file() and path.stat().st_size > 32
    assert path.read_bytes().startswith(b"\xff\xd8\xff")


if __name__ == "__main__":
    test_legacy_permalink_rewrite_skips_upload_paths()
    test_numeric_stub_is_not_rewritten_or_sitemapped()
    test_recovered_archive_image_is_local()
    print("ok")
