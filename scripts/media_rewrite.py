#!/usr/bin/env python3
"""Rewrite WordPress / Jetpack upload URLs to local media or Wayback.

Local files live under docs/media/uploads/YYYY/MM/filename so a WP URL
  https://sayd-magazine.com/wp-content/uploads/2020/04/Sayd-Magazine-Logo.png
maps to
  docs/media/uploads/2020/04/Sayd-Magazine-Logo.png
and a depth-aware site-relative src
  media/uploads/2020/04/Sayd-Magazine-Logo.png          (homepage)
  ../../media/uploads/2020/04/Sayd-Magazine-Logo.png    (posts/)

Depth-relative paths work on both sayd-magazine.com and
unionmed.github.io/sayd-magazine/. Root-absolute /media/... would 404
on the github.io project URL.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

WAYBACK_IM = "https://web.archive.org/web/0im_/{original}"

# Live + historic hosts seen in the WXR / generated HTML.
_HOST = r"(?:(?:www\.)?sayd-magazine\.com|sayd\.alfalivehost\.com)"
_JETPACK = r"(?:i[0-3]\.wp\.com/)"

# Captures the full URL and the uploads-relative path (YYYY/MM/file…),
# stopping before quotes, whitespace, or a query/hash.
UPLOAD_URL_RE = re.compile(
    rf"""(?P<url>
        https?://
        (?:{_JETPACK})?
        {_HOST}
        /wp-content/uploads/
        (?P<rel>[^\s"'\\<>?#]+)
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# Broader finder for srcset / raw text (same pattern, used iteratively).
ANY_UPLOAD_RE = UPLOAD_URL_RE

LOGO_ORIGINAL = (
    "https://sayd-magazine.com/wp-content/uploads/2020/04/Sayd-Magazine-Logo.png"
)
FOOTER_LOGO_ORIGINAL = (
    "https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png"
)

PRIORITY_ORIGINALS = (LOGO_ORIGINAL, FOOTER_LOGO_ORIGINAL)

# Nayef via Mars (2026-09-18): no pre-2022 archive bulk mirror.
MIRROR_YEAR_FROM = 2022
CHROME_ALLOWLIST = {
    "uploads/2020/04/Sayd-Magazine-Logo.png",
    "uploads/2015/03/Sayd-Footer-Logo.png",
}


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
    url = (url or "").replace("&amp;", "&").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed._replace(query="", fragment="").geturl()


def uploads_rel(url: str) -> str | None:
    """Return 'uploads/YYYY/MM/filename' or None if not a WP upload URL."""
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
    """Normalize to https://sayd-magazine.com/wp-content/uploads/... (no query)."""
    rel = uploads_rel(url)
    if not rel:
        return _strip_query(url)
    return "https://sayd-magazine.com/wp-content/" + rel


def wayback_src(url: str) -> str:
    original = canonical_wp_url(url)
    if not original:
        return url
    return WAYBACK_IM.format(original=original)


def local_media_file(media_root: Path, url: str) -> Path | None:
    rel = uploads_rel(url)
    if not rel:
        return None
    path = media_root / rel
    return path if path.is_file() and path.stat().st_size > 32 else None


def public_src(url: str, depth: int, media_root: Path) -> str:
    """Local depth-relative path if the file exists, else Wayback 0im_ URL."""
    if not url:
        return ""
    local = local_media_file(media_root, url)
    prefix = "../" * depth
    if local is not None:
        rel = uploads_rel(url)
        return f"{prefix}media/{rel}"
    if uploads_rel(url):
        return wayback_src(url)
    return url


def rewrite_url(url: str, depth: int, media_root: Path) -> str:
    if not url or not UPLOAD_URL_RE.search(url.replace("&amp;", "&")):
        return url
    return public_src(url.replace("&amp;", "&"), depth, media_root)


def rewrite_srcset(srcset: str, depth: int, media_root: Path) -> str:
    parts = []
    for chunk in srcset.split(","):
        bit = chunk.strip()
        if not bit:
            continue
        tokens = bit.split()
        tokens[0] = rewrite_url(tokens[0], depth, media_root)
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


def rewrite_html(html: str, depth: int, media_root: Path) -> str:
    """Rewrite upload URLs in HTML attributes, srcset, and CSS url()."""
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
        q = m.group("q")
        return f"url({q}{new}{q})"

    html = _SRCSET_RE.sub(srcset_sub, html)
    html = _ATTR_RE.sub(attr_sub, html)
    html = _CSS_URL_RE.sub(css_sub, html)

    # Catch leftover bare URLs in text/JSON (e.g. WordPress galleries).
    def bare_sub(m: re.Match[str]) -> str:
        return rewrite_url(m.group("url"), depth, media_root)

    html = UPLOAD_URL_RE.sub(bare_sub, html)
    return html


def collect_upload_urls(*texts: str) -> list[str]:
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        for m in UPLOAD_URL_RE.finditer(text.replace("&amp;", "&")):
            found.add(canonical_wp_url(m.group("url")))
    return sorted(found)
