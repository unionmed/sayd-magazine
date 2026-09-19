#!/usr/bin/env python3
"""Sanity checks for media URL rewrite (no network)."""

from pathlib import Path
from tempfile import TemporaryDirectory

from media_rewrite import (
    LOGO_ORIGINAL,
    in_mirror_scope,
    public_src,
    rewrite_html,
    uploads_rel,
)


def test_uploads_rel() -> None:
    assert (
        uploads_rel(LOGO_ORIGINAL)
        == "uploads/2020/04/Sayd-Magazine-Logo.png"
    )
    jet = "https://i0.wp.com/sayd-magazine.com/wp-content/uploads/2024/09/Design.png?fit=800,600"
    assert uploads_rel(jet) == "uploads/2024/09/Design.png"
    old = "http://i0.wp.com/sayd.alfalivehost.com/wp-content/uploads/2015/02/foo.jpg?resize=600%2C424"
    assert uploads_rel(old) == "uploads/2015/02/foo.jpg"


def test_scope() -> None:
    assert in_mirror_scope(LOGO_ORIGINAL)  # chrome allowlist
    assert in_mirror_scope(
        "https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png"
    )
    assert in_mirror_scope(
        "https://sayd-magazine.com/wp-content/uploads/2026/09/hero.jpg"
    )
    assert not in_mirror_scope(
        "https://sayd-magazine.com/wp-content/uploads/2015/06/سلهب-3.jpg"
    )


def test_public_src_local_only() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dest = root / "uploads/2024/09/Design.png"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"x" * 80)
        url = "https://sayd-magazine.com/wp-content/uploads/2024/09/Design.png"
        assert public_src(url, 0, root) == "media/uploads/2024/09/Design.png"
        assert public_src(url, 2, root) == "../../media/uploads/2024/09/Design.png"
        missing = "https://sayd-magazine.com/wp-content/uploads/2026/09/nope.jpg"
        assert public_src(missing, 0, root) == ""
        wb = "https://web.archive.org/web/0im_/https://sayd-magazine.com/wp-content/uploads/2024/09/Design.png"
        assert public_src(wb, 0, root) == "media/uploads/2024/09/Design.png"


def test_rewrite_html() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dest = root / "uploads/2024/09/Design.png"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"x" * 80)
        html = '<img src="https://sayd-magazine.com/wp-content/uploads/2024/09/Design.png">'
        out = rewrite_html(html, 0, root)
        assert 'src="media/uploads/2024/09/Design.png"' in out
        assert "sayd-magazine.com/wp-content" not in out
        assert "web.archive.org" not in out
        missing = rewrite_html(
            '<img src="https://web.archive.org/web/0im_/https://sayd-magazine.com/wp-content/uploads/2015/06/old.jpg">',
            0,
            root,
        )
        assert "placeholder-thumb" in missing
        assert "web.archive.org" not in missing
        assert "wp-content" not in missing


if __name__ == "__main__":
    test_uploads_rel()
    test_scope()
    test_public_src_local_only()
    test_rewrite_html()
    print("ok")
