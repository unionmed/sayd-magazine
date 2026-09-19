#!/usr/bin/env python3
"""Batch 1: mirror 2022+ binaries + uniquify homepage/recent card thumbs.

Never writes WP / Jetpack / Wayback URLs into HTML.
Never overwrites Mars-owned Kaps / Adonis / Suhail / brand files.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util  # noqa: E402

from homepage_thumbs import (  # noqa: E402
    BRAND_KEEP,
    HOMEPAGE_FETCH_RELS,
    HOMEPAGE_UNIQUE_THUMBS,
    MARS_OWNED,
    SUHAIL_KEEP,
    assigned_file_set,
    resolve_home_thumb,
)
from media_rewrite import FORBIDDEN_SRC_RE  # noqa: E402

_spec = importlib.util.spec_from_file_location("mirror_media", Path(__file__).resolve().parent / "mirror-media.py")
_mm = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mm)
looks_like_image = _mm.looks_like_image
mm_fetch = _mm.fetch
cdx_best = _mm.cdx_best


def wp_url_for(rel: str) -> str:
    path = rel[len("uploads/") :] if rel.startswith("uploads/") else rel
    return "https://sayd-magazine.com/wp-content/uploads/" + path


def fetch_image(original: str, try_cdx: bool = False) -> tuple[bool, bytes, str | None]:
    """Wayback 0im_ first (fast); optional CDX for stubborn originals."""
    encoded = original
    parts = urlsplit(original)
    encoded = urlunsplit(
        (parts.scheme, parts.netloc, quote(parts.path, safe="/"), parts.query, parts.fragment)
    )
    www = encoded.replace("://sayd-magazine.com", "://www.sayd-magazine.com")
    urls = [
        f"https://web.archive.org/web/0im_/{encoded}",
        f"https://web.archive.org/web/0im_/{www}",
        f"https://web.archive.org/web/im_/{encoded}",
    ]
    if try_cdx:
        cdx = cdx_best(original)
        if cdx:
            urls.insert(0, cdx)
    for url in urls:
        status, data, ctype = mm_fetch(url, timeout=25)
        if status in (200, 203) and looks_like_image(data, ctype):
            return True, data, url
        time.sleep(0.15)
    return False, b"", None

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
HOME = DOCS / "index.html"
WXR = ROOT / "exports" / "saydmagazine-.WordPress.2026-09-15.xml"
CONTENT = ROOT / "content"
YT_BABTAIN = (
    "https://img.youtube.com/vi/P4m8fY--RRg/maxresdefault.jpg",
    "https://img.youtube.com/vi/P4m8fY--RRg/hqdefault.jpg",
)
YT_DEST = MEDIA / "uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg"

UPLOAD_RE = re.compile(
    r"""(?:https?:)?(?://)?(?:web\.archive\.org/web/[^/\s\"']+/)?(?:https?:)?(?://)?
        (?:i[0-3]\.wp\.com/)?
        (?:(?:www\.)?sayd-magazine\.com|sayd\.alfalivehost\.com)
        /wp-content/uploads/(?P<rel>20\d{2}/\d{2}/[^\"'\s?#<>]+)
    """,
    re.I | re.X,
)
LOCAL_MEDIA_RE = re.compile(
    r"""(?:\.\./)*media/uploads/(?P<rel>20\d{2}/\d{2}/[^\"'\s?#<>]+)""",
    re.I,
)
THUMB_BLOCK_RE = re.compile(
    r"""<a\s+class="thumb"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<inner>.*?)</a>""",
    re.I | re.S,
)
FEATURED_RE = re.compile(
    r"""<div class="article-featured">(?P<inner>.*?)</div>""",
    re.I | re.S,
)
IMG_SRC_RE = re.compile(r"""src=(['"])(.*?)\1""", re.I | re.S)

PROTECTED = set(MARS_OWNED) | set(SUHAIL_KEEP) | {
    f"uploads/{k.split('/', 1)[1]}" if k.startswith("brand/") else k for k in BRAND_KEEP
}
_PRIORITY_SET: set[str] = set()


def _ascii_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/"), parts.query, parts.fragment))


def collect_upload_rels(*texts: str) -> set[str]:
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        blob = text.replace("&amp;", "&")
        for m in UPLOAD_RE.finditer(blob):
            rel = unquote(m.group("rel")).split(";")[0]
            found.add(f"uploads/{rel}")
        for m in LOCAL_MEDIA_RE.finditer(blob):
            rel = unquote(m.group("rel")).split(";")[0]
            found.add(f"uploads/{rel}")
    return found


def collect_priority_and_all() -> tuple[list[str], list[str]]:
    """Return (priority rels, all 2022+ rels)."""
    texts: list[str] = []
    if HOME.exists():
        texts.append(HOME.read_text(encoding="utf-8", errors="ignore"))
    home_slugs = set(re.findall(r'href="posts/([^/"]+)/index.html"', texts[0] if texts else ""))
    for slug in home_slugs:
        page = DOCS / "posts" / slug / "index.html"
        if page.is_file():
            texts.append(page.read_text(encoding="utf-8", errors="ignore"))
        md = CONTENT / "posts" / f"{slug}.md"
        if md.is_file():
            texts.append(md.read_text(encoding="utf-8", errors="ignore"))
    priority = collect_upload_rels(*texts)
    priority.update(f"uploads/{r.split('uploads/', 1)[-1]}" if r.startswith("uploads/") else r for r in HOMEPAGE_FETCH_RELS)
    priority.update(HOMEPAGE_UNIQUE_THUMBS.values())

    all_rels = set(priority)
    if WXR.exists():
        all_rels |= collect_upload_rels(WXR.read_text(encoding="utf-8", errors="ignore"))
    for md in CONTENT.rglob("*.md"):
        all_rels |= collect_upload_rels(md.read_text(encoding="utf-8", errors="ignore"))
    for html in DOCS.rglob("*.html"):
        all_rels |= collect_upload_rels(html.read_text(encoding="utf-8", errors="ignore"))

    def year_of(rel: str) -> int:
        m = re.search(r"uploads/(\d{4})/", rel)
        return int(m.group(1)) if m else 0

    scoped_all = sorted(r for r in all_rels if year_of(r) >= 2022)
    scoped_pri = sorted(
        r
        for r in priority
        if year_of(r) >= 2022 or r in {f if f.startswith("uploads/") else f"uploads/{f}" for f in HOMEPAGE_FETCH_RELS} or r in HOMEPAGE_FETCH_RELS
    )
    # Keep targeted pre-2022 homepage originals in priority only.
    extra_pre = [r if r.startswith("uploads/") else f"uploads/{r}" for r in HOMEPAGE_FETCH_RELS]
    for r in extra_pre:
        if r not in scoped_pri:
            scoped_pri.append(r)
    return scoped_pri, scoped_all


def should_overwrite(rel: str) -> bool:
    if rel in PROTECTED or rel in MARS_OWNED or rel in SUHAIL_KEEP:
        return False
    dest = MEDIA / rel
    if not dest.is_file():
        return True
    # Replace known stand-in copies (same bytes as a different source file).
    size = dest.stat().st_size
    standin_sizes = set()
    for src in (
        "uploads/2022/12/بارودة.png",
        "uploads/2024/06/Bird-02.jpeg",
        "uploads/2024/09/Design.png",
        "uploads/2025/09/AP4I0956-1024x683.jpg",
        "uploads/2025/09/AP4I0032-1024x683.jpg",
        "uploads/2020/05/سينتيا.jpg",
        "uploads/2015/06/سلهب-3.jpg",
    ):
        p = MEDIA / src
        if p.is_file():
            standin_sizes.add(p.stat().st_size)
    if dest.resolve() != (MEDIA / rel).resolve() and size in standin_sizes:
        # Don't replace the stand-in source itself.
        return rel not in (
            "uploads/2022/12/بارودة.png",
            "uploads/2024/06/Bird-02.jpeg",
            "uploads/2024/09/Design.png",
            "uploads/2025/09/AP4I0956-1024x683.jpg",
            "uploads/2025/09/AP4I0032-1024x683.jpg",
            "uploads/2020/05/سينتيا.jpg",
            "uploads/2015/06/سلهب-3.jpg",
        )
    if size in standin_sizes and rel not in (
        "uploads/2022/12/بارودة.png",
        "uploads/2024/06/Bird-02.jpeg",
        "uploads/2024/09/Design.png",
        "uploads/2025/09/AP4I0956-1024x683.jpg",
        "uploads/2025/09/AP4I0032-1024x683.jpg",
        "uploads/2020/05/سينتيا.jpg",
        "uploads/2015/06/سلهب-3.jpg",
    ):
        return True
    return False


def fetch_one(rel: str) -> dict:
    record = {"rel": rel, "status": "skipped", "bytes": 0, "source": None}
    dest = MEDIA / rel
    if rel in PROTECTED and dest.is_file() and dest.stat().st_size > 32:
        record["status"] = "protected"
        record["bytes"] = dest.stat().st_size
        return record
    if dest.is_file() and dest.stat().st_size > 32 and not should_overwrite(rel):
        record["status"] = "exists"
        record["bytes"] = dest.stat().st_size
        record["source"] = "local"
        return record
    url = wp_url_for(rel)
    try_cdx = rel in _PRIORITY_SET
    ok, data, source = fetch_image(url, try_cdx=try_cdx)
    if ok:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        record["status"] = "downloaded"
        record["bytes"] = len(data)
        record["source"] = source
        return record
    record["status"] = "failed"
    return record


def fetch_youtube_babtain() -> dict:
    record = {"rel": "uploads/2026/09/babtain-maqnas-afghanistan-yt.jpg", "status": "failed", "bytes": 0}
    if YT_DEST.is_file() and YT_DEST.stat().st_size > 32:
        record["status"] = "exists"
        record["bytes"] = YT_DEST.stat().st_size
        return record
    import urllib.request

    ua = "SaydMagazineStatic/1.0 (+https://github.com/unionmed/sayd-magazine; media recovery)"
    for url in YT_BABTAIN:
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "image/*"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
        except Exception:
            continue
        if looks_like_image(data, "image/jpeg"):
            YT_DEST.parent.mkdir(parents=True, exist_ok=True)
            YT_DEST.write_bytes(data)
            record["status"] = "downloaded"
            record["bytes"] = len(data)
            record["source"] = url
            return record
    return record


def slug_from_href(href: str) -> str | None:
    m = re.search(r"(?:\.\./)*posts/([^/]+)/index\.html", href)
    return m.group(1) if m else None


def public_src(rel: str, depth: int) -> str:
    return f"{'../' * depth}media/{rel}"


def html_depth(path: Path) -> int:
    rel = path.relative_to(DOCS)
    return 0 if rel == Path("index.html") else len(rel.parts) - 1


def rewrite_thumbs(path: Path, mapping: dict[str, str]) -> int:
    html = path.read_text(encoding="utf-8")
    original = html
    depth = html_depth(path)
    changed = 0

    def thumb_sub(m: re.Match[str]) -> str:
        nonlocal changed
        slug = slug_from_href(m.group("href"))
        if not slug or slug not in mapping:
            return m.group(0)
        rel = mapping[slug]
        src = public_src(rel, depth)
        inner = m.group("inner")
        img_m = IMG_SRC_RE.search(inner)
        if img_m:
            if img_m.group(2) == src:
                return m.group(0)
            new_inner = inner[: img_m.start()] + f"src={img_m.group(1)}{src}{img_m.group(1)}" + inner[img_m.end() :]
        else:
            # placeholder-thumb or empty
            alt = slug
            new_inner = f'<img src="{src}" alt="{alt}" loading="lazy">'
        changed += 1
        return m.group(0).replace(inner, new_inner, 1)

    html = THUMB_BLOCK_RE.sub(thumb_sub, html)

    # Article featured block for mapped slugs
    slug = path.parent.name if path.parent.parent.name == "posts" else None
    if slug and slug in mapping and FEATURED_RE.search(html):
        rel = mapping[slug]
        src = public_src(rel, depth)

        def feat_sub(m: re.Match[str]) -> str:
            nonlocal changed
            inner = m.group("inner")
            img_m = IMG_SRC_RE.search(inner)
            if img_m and img_m.group(2) == src:
                return m.group(0)
            changed += 1
            return f'<div class="article-featured"><img src="{src}" alt="" loading="lazy"></div>'

        html = FEATURED_RE.sub(feat_sub, html, count=1)

    leftover = FORBIDDEN_SRC_RE.findall(html)
    if leftover:
        raise RuntimeError(f"forbidden src in {path}: {leftover[:5]}")
    if html != original:
        path.write_text(html, encoding="utf-8")
    return changed


def rewrite_all(mapping: dict[str, str]) -> int:
    total = 0
    for path in DOCS.rglob("*.html"):
        total += rewrite_thumbs(path, mapping)
    return total


def main() -> int:
    global _PRIORITY_SET
    pri, all_rels = collect_priority_and_all()
    _PRIORITY_SET = set(pri)
    print(f"priority={len(pri)} all_2022plus={len(all_rels)}")

    yt = fetch_youtube_babtain()
    print(f"youtube babtain {yt['status']} {yt['bytes']}")

    # Fetch priority first, then remaining 2022+
    seen = set()
    queue = []
    for rel in pri + all_rels:
        if rel in seen:
            continue
        seen.add(rel)
        queue.append(rel)

    records = [yt]
    workers = 6
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fetch_one, rel): rel for rel in queue}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            records.append(rec)
            if rec["status"] in ("downloaded", "failed"):
                print(f"[{i}/{len(queue)}] {rec['status']:12} {rec['rel']}")

    mapping = assigned_file_set(MEDIA)
    # Fill from resolve for any homepage slug still missing
    for slug in HOMEPAGE_UNIQUE_THUMBS:
        if slug not in mapping:
            pick = resolve_home_thumb(slug, MEDIA)
            if pick:
                mapping[slug] = pick

    changed = rewrite_all(mapping)
    print(f"rewrote thumb attrs on {changed} blocks; unique homepage slugs={len(mapping)}")

    (MEDIA / "batch1-fetch.json").write_text(
        json.dumps(
            {
                "records": records,
                "mapping": mapping,
                "priority": len(pri),
                "all": len(all_rels),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    cname = (DOCS / "CNAME").read_text(encoding="utf-8").strip()
    if cname != "sayd-magazine.com":
        print("ERROR CNAME", cname)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
