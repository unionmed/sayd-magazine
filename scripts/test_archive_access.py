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


def test_restore_puts_local_2020_image_back() -> None:
    published = "<p>قبل</p>\n<p>بعد النص</p>"
    fresh = (
        "<p>قبل</p>\n"
        '<p><a href="../../media/uploads/2020/06/لوحة.jpg">'
        '<img src="../../media/uploads/2020/06/لوحة.jpg" alt=""></a></p>\n'
        "<p>بعد النص</p>"
    )
    out, names = archive.restore_stripped_upload_images(published, fresh)
    assert names == ["لوحة.jpg"]
    assert 'src="../../media/uploads/2020/06/لوحة.jpg"' in out
    assert out.index("لوحة.jpg") < out.index("بعد النص")
    assert "wp-content" not in out


def test_restore_leaves_missing_and_older_images_alone() -> None:
    published = "<p>نص ثابت</p>"
    fresh = (
        '<img src="../../media/uploads/2015/02/old.jpg">'
        "<p>نص ثابت</p>"
        '<img src="https://sayd-magazine.com/wp-content/uploads/2024/01/gone.jpg">'
    )
    out, names = archive.restore_stripped_upload_images(published, fresh)
    assert names == []
    assert out == published


def test_restore_keeps_trailing_images_in_source_order() -> None:
    published = "<p>المتن</p>"
    fresh = (
        "<p>المتن</p>"
        '<a href="../../media/uploads/2020/06/a.jpg"><img src="../../media/uploads/2020/06/a.jpg"></a>'
        '<a href="../../media/uploads/2020/06/b.jpg"><img src="../../media/uploads/2020/06/b.jpg"></a>'
    )
    out, names = archive.restore_stripped_upload_images(published, fresh)
    assert names == ["a.jpg", "b.jpg"]
    assert out.index("a.jpg") < out.index("b.jpg")
    assert out.index("المتن") < out.index("a.jpg")


def test_restore_skips_file_already_on_the_page() -> None:
    published = '<p><img src="../../media/uploads/2022/10/لين-2.jpg"></p><p>متن</p>'
    fresh = published
    out, names = archive.restore_stripped_upload_images(published, fresh)
    assert names == []
    assert out == published


if __name__ == "__main__":
    test_legacy_permalink_rewrite_skips_upload_paths()
    test_restore_puts_local_2020_image_back()
    test_restore_keeps_trailing_images_in_source_order()
    test_restore_leaves_missing_and_older_images_alone()
    test_restore_skips_file_already_on_the_page()
    test_numeric_stub_is_not_rewritten_or_sitemapped()
    test_recovered_archive_image_is_local()
    print("ok")
