#!/usr/bin/env python3
"""Rewrite WordPress / Jetpack / Wayback upload URLs to local media only.

Local files live under docs/media/uploads/YYYY/MM/filename.
Site-relative srcs are depth-aware:
  media/uploads/2020/04/Sayd-Magazine-Logo.png          (homepage)
  ../../media/uploads/2020/04/Sayd-Magazine-Logo.png    (posts/)

Missing files become empty srcs; rewrite_html swaps those <img> tags
for a CSS placeholder. NEVER emit sayd-magazine.com/wp-content,
Jetpack, or web.archive.org image URLs.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

_HOST = r"(?:(?:www\.)?sayd-magazine\.com|sayd\.alfalivehost\.com)"
_JETPACK = r"(?:i[0-3]\.wp\.com/)"
_WAYBACK = r"(?:https?://web\.archive\.org/web/[^/\s\"']+/)"

UPLOAD_URL_RE = re.compile(
    rf"""(?P<url>
        (?:{_WAYBACK})?
        https?://
        (?:{_JETPACK})?
        {_HOST}
        /wp-content/uploads/
        (?P<rel>[^\s"'\\<>?#]+)
    )""",
    re.IGNORECASE | re.VERBOSE,
)

WAYBACK_PREFIX_RE = re.compile(r"https?://web\.archive\.org/web/[^/]+/", re.I)
FORBIDDEN_SRC_RE = re.compile(
    r"web\.archive\.org|(?:www\.)?sayd-magazine\.com/wp-content|"
    r"i[0-3]\.wp\.com|sayd\.alfalivehost\.com/wp-content",
    re.I,
)

PLACEHOLDER_HTML = '<div class="placeholder-thumb" aria-hidden="true">صيد</div>'

LOGO_ORIGINAL = (
    "https://sayd-magazine.com/wp-content/uploads/2020/04/Sayd-Magazine-Logo.png"
)
FOOTER_LOGO_ORIGINAL = (
    "https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png"
)

PRIORITY_ORIGINALS = (LOGO_ORIGINAL, FOOTER_LOGO_ORIGINAL)

MIRROR_YEAR_FROM = 2022
CHROME_ALLOWLIST = {
    "uploads/2020/04/Sayd-Magazine-Logo.png",
    "uploads/2015/03/Sayd-Footer-Logo.png",
}


def unwrap(url: str) -> str:
    url = (url or "").replace("&amp;", "&").strip()
    return WAYBACK_PREFIX_RE.sub("", url)


def year_of(url: str) -> int | None:
    m = re.search(r"/uploads/(\d{4})/", url or "")
    return int(m.group(1)) if m else None


def in_mirror_scope(url: str) -> bool:
    """2022+ uploads, plus homepage chrome logos (older years allowed)."""
    rel = uploads_rel(url) or ""
    if rel in CHROME_ALLOWLIST:
        return True
    year = year_of(url)
    return year is not None and year >= MIRROR_YEAR_FROM


def _strip_query(url: str) -> str:
    url = unwrap(url)
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed._replace(query="", fragment="").geturl()


def uploads_rel(url: str) -> str | None:
    """Return 'uploads/YYYY/MM/filename' or None if not a WP/Wayback upload URL."""
    if not url:
        return None
    cleaned = _strip_query(url)
    m = UPLOAD_URL_RE.search(cleaned)
    if not m:
        return None
    rel = unquote(m.group("rel")).lstrip("/")
    if not rel:
        return None
    return f"uploads/{rel}"


def canonical_wp_url(url: str) -> str:
    """Normalize to a lookup key (never used as a live img src)."""
    rel = uploads_rel(url)
    if not rel:
        return _strip_query(url)
    return "https://sayd-magazine.com/wp-content/" + rel


def local_media_file(media_root: Path, url: str) -> Path | None:
    rel = uploads_rel(url)
    if not rel:
        return None
    path = media_root / rel
    return path if path.is_file() and path.stat().st_size > 32 else None


def public_src(url: str, depth: int, media_root: Path) -> str:
    """Local depth-relative path if the file exists, else empty (placeholder)."""
    if not url:
        return ""
    local = local_media_file(media_root, url)
    if local is None:
        return ""
    rel = uploads_rel(url)
    return f"{'../' * depth}media/{rel}"


def rewrite_url(url: str, depth: int, media_root: Path) -> str:
    raw = unwrap(url)
    if not raw:
        return ""
    if UPLOAD_URL_RE.search(raw) or FORBIDDEN_SRC_RE.search(url):
        return public_src(raw, depth, media_root)
    return url


def rewrite_srcset(srcset: str, depth: int, media_root: Path) -> str:
    parts = []
    for chunk in srcset.split(","):
        bit = chunk.strip()
        if not bit:
            continue
        tokens = bit.split()
        tokens[0] = rewrite_url(tokens[0], depth, media_root)
        if not tokens[0] or FORBIDDEN_SRC_RE.search(tokens[0]):
            continue
        parts.append(" ".join(tokens))
    return ", ".join(parts)


_ATTR_RE = re.compile(
    r"""(?P<attr>src|href|poster)=(?P<q>['"])(?P<val>.*?)(?P=q)""",
    re.IGNORECASE | re.DOTALL,
)
_SRCSET_RE = re.compile(
    r"""(?P<attr>srcset)=(?P<q>['"])(?P<val>.*?)(?P=q)""",
    re.IGNORECASE | re.DOTALL,
)
_CSS_URL_RE = re.compile(
    r"""url\((?P<q>['"]?)(?P<val>https?://[^)'"]+)(?P=q)\)""",
    re.IGNORECASE,
)
_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def rewrite_html(html: str, depth: int, media_root: Path) -> str:
    """Rewrite upload URLs to local paths; replace missing images with placeholders."""
    if not html:
        return html

    def attr_sub(m: re.Match[str]) -> str:
        val = m.group("val")
        new = rewrite_url(val, depth, media_root)
        return f'{m.group("attr")}={m.group("q")}{new}{m.group("q")}'

    def srcset_sub(m: re.Match[str]) -> str:
        new = rewrite_srcset(m.group("val"), depth, media_root)
        return f'{m.group("attr")}={m.group("q")}{new}{m.group("q")}'

    def css_sub(m: re.Match[str]) -> str:
        new = rewrite_url(m.group("val"), depth, media_root)
        if not new:
            return "none"
        q = m.group("q")
        return f"url({q}{new}{q})"

    html = _SRCSET_RE.sub(srcset_sub, html)
    html = _ATTR_RE.sub(attr_sub, html)
    html = _CSS_URL_RE.sub(css_sub, html)

    def bare_sub(m: re.Match[str]) -> str:
        return rewrite_url(m.group("url"), depth, media_root)

    html = UPLOAD_URL_RE.sub(bare_sub, html)
    html = WAYBACK_PREFIX_RE.sub("", html)

    def img_sub(m: re.Match[str]) -> str:
        tag = m.group(0)
        src_m = re.search(r"""src=(['"])(.*?)\1""", tag, re.I | re.DOTALL)
        src = (src_m.group(2) if src_m else "").strip()
        if (
            not src
            or src.startswith(("http://", "https://", "//"))
            or FORBIDDEN_SRC_RE.search(src)
        ):
            return PLACEHOLDER_HTML
        return tag

    return _IMG_RE.sub(img_sub, html)


def collect_upload_urls(*texts: str) -> list[str]:
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        for m in UPLOAD_URL_RE.finditer(text.replace("&amp;", "&")):
            found.add(canonical_wp_url(m.group("url")))
    return sorted(found)
