#!/usr/bin/env python3
"""Make homepage chrome + card images self-contained under docs/media/.

Restored files from git stay in place. Missing originals are fetched from
Wayback when possible; otherwise homepage cards use an already-local stand-in.
Never writes WordPress or Wayback URLs into HTML.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import urllib.error
import urllib.request

from media_rewrite import FORBIDDEN_SRC_RE, uploads_rel  # noqa: E402

UA = "SaydMagazineStatic/1.0 (+https://github.com/unionmed/sayd-magazine; homepage media)"


def _looks_like_image(data: bytes) -> bool:
    if len(data) < 64:
        return False
    head = data[:16].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        return False
    return (
        data[:3] == b"\xff\xd8\xff"
        or data[:8] == b"\x89PNG\r\n\x1a\n"
        or data[:6] in (b"GIF87a", b"GIF89a")
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


def _ascii_url(url: str) -> str:
    parts = urlsplit(url)
    path = quote(parts.path, safe="/")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def try_wayback(url: str, dest: Path) -> str:
    """One-shot Wayback image pull. Skip 2026 originals (never captured)."""
    if "/uploads/2026/" in url:
        return "skip-2026"
    encoded = _ascii_url(url)
    www = encoded.replace("://sayd-magazine.com", "://www.sayd-magazine.com")
    candidates = [
        f"https://web.archive.org/web/0im_/{encoded}",
        www,
    ]
    for candidate in candidates:
        req = urllib.request.Request(candidate, headers={"User-Agent": UA, "Accept": "image/*"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        if _looks_like_image(data):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return f"downloaded {len(data)}"
    return "miss"

HOME = ROOT / "docs" / "index.html"
MEDIA = ROOT / "docs" / "media"

CHROME = {
    "https://sayd-magazine.com/wp-content/uploads/2020/04/Sayd-Magazine-Logo.png": "media/brand/sayd-logo.png",
    "https://sayd-magazine.com/wp-content/uploads/2015/03/Sayd-Footer-Logo.png": "media/brand/sayd-footer-logo.png",
}

# Nayef rule: never map two stories onto the same stand-in file.
# Missing originals stay missing; homepage_thumbs.py assigns unique cards.
STANDINS: dict[str, str] = {}
DEFAULT_STANDIN = ""
FOOTER_NOTE_OLD = "الصور تُحمَّل من sayd-magazine.com (مرفقات غير مُنزَّلة محلياً بعد)."
FOOTER_NOTE_NEW = "صور الرئيسية والشعار تُخدم محلياً من media/ على GitHub Pages."

SRC_RE = re.compile(
    r"""(?P<attr>src|href)=(?P<q>['"])(?P<val>[^'"]+\.(?:png|jpe?g|gif|webp|svg))(?P=q)""",
    re.I,
)


def local_rel_for(url: str) -> str | None:
    if url.startswith("media/") and (ROOT / "docs" / url).is_file():
        return url
    if url in CHROME:
        dest = ROOT / "docs" / CHROME[url]
        return CHROME[url] if dest.is_file() and dest.stat().st_size > 32 else None
    rel = uploads_rel(url)
    if not rel:
        return None
    path = MEDIA / rel
    if path.is_file() and path.stat().st_size > 32:
        return f"media/{rel}"
    standin = STANDINS.get(rel) or DEFAULT_STANDIN
    if not standin:
        return None
    standin_path = MEDIA / standin
    if standin_path.is_file() and standin_path.stat().st_size > 32:
        return f"media/{standin}"
    return None


def main() -> int:
    html = HOME.read_text(encoding="utf-8")
    urls = []
    for m in SRC_RE.finditer(html):
        val = m.group("val")
        if val.startswith("http") or val.startswith("//"):
            urls.append(val)

    skip_fetch = "--skip-fetch" in sys.argv
    # Optional Wayback fill for still-missing pre-2026 thumbs. Failures fall
    # through to already-local stand-ins so the homepage never hotlinks WP.
    for url in sorted(set(urls)):
        if url in CHROME:
            continue
        rel = uploads_rel(url)
        if not rel:
            continue
        dest = MEDIA / rel
        if dest.is_file() and dest.stat().st_size > 32:
            continue
        if skip_fetch:
            print(f"fetch skipped {rel}")
            continue
        try:
            status = try_wayback(url, dest)
        except Exception as exc:  # noqa: BLE001
            status = f"error {exc}"
        print(f"fetch {status} {rel}")

    replacements = {}
    missing = []

    def repl(m: re.Match[str]) -> str:
        val = m.group("val")
        if val.startswith("media/"):
            dest = ROOT / "docs" / val
            if dest.is_file() and dest.stat().st_size > 32:
                return m.group(0)
            missing.append(val)
            return m.group(0)
        new = local_rel_for(val)
        if not new:
            missing.append(val)
            return m.group(0)
        replacements[val] = new
        return f"{m.group('attr')}={m.group('q')}{new}{m.group('q')}"

    new_html = SRC_RE.sub(repl, html)
    if FOOTER_NOTE_OLD in new_html:
        new_html = new_html.replace(FOOTER_NOTE_OLD, FOOTER_NOTE_NEW)

    leftover = FORBIDDEN_SRC_RE.findall(new_html)
    if leftover:
        print("ERROR leftover remote media refs:", leftover[:10])
        return 2
    if missing:
        print("ERROR unresolved srcs:", missing)
        return 3

    HOME.write_text(new_html, encoding="utf-8")
    print("rewrote docs/index.html")
    for old, new in sorted(replacements.items(), key=lambda kv: kv[1]):
        print(f"  {old} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
