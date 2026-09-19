#!/usr/bin/env python3
"""Mirror leftover WP/Jetpack hotlinks on homepage-linked / recent pages.

2022+ upload-year hotlinks are already gone. This pass touches only:
- posts linked from AR/EN homepages
- homepage.json featured + latest
- footer chrome page «شركاؤنا»

Pre-2022 archive bulk stays deferred. Never writes CSS/layout. Never
drops the featured mosaic. Mars-owned binaries are not overwritten.
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from homepage_thumbs import MARS_OWNED  # noqa: E402
from media_rewrite import (  # noqa: E402
    FORBIDDEN_SRC_RE,
    canonical_wp_url,
    rewrite_html,
    uploads_rel,
)
from importlib.util import module_from_spec, spec_from_file_location

_spec = spec_from_file_location("mirror_media", Path(__file__).resolve().parent / "mirror-media.py")
_mm = module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mm)

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
HOTLINK_RE = re.compile(
    r"""(?:https?:)?//[^\s"'<>\\]+?(?:wp-content/uploads/|i[0-3]\.wp\.com/)[^\s"'<>\\]+""",
    re.I,
)
MARS_KEEP = {Path(rel).name for rel in MARS_OWNED}


def html_depth(path: Path) -> int:
    rel = path.relative_to(DOCS)
    return 0 if rel == Path("index.html") else len(rel.parts) - 1


def homepage_linked_pages() -> list[Path]:
    slugs: set[str] = set()
    for index in (DOCS / "index.html", DOCS / "en" / "index.html"):
        if index.is_file():
            slugs.update(re.findall(r"posts/([^/\"']+)/", index.read_text(encoding="utf-8")))
    lists = json.loads((ROOT / "content" / "homepage.json").read_text(encoding="utf-8"))
    slugs.update(str(s) for s in lists.get("featured") or [])
    slugs.update(str(s) for s in lists.get("latest") or [])
    pages: list[Path] = []
    for slug in sorted(slugs):
        for base in (DOCS / "posts" / slug, DOCS / "en" / "posts" / slug):
            page = base / "index.html"
            if page.is_file():
                pages.append(page)
    partners = DOCS / "pages" / "شركاؤنا" / "index.html"
    if partners.is_file():
        pages.append(partners)
    return pages


def collect_hotlinks(text: str) -> list[str]:
    found: list[str] = []
    for raw in HOTLINK_RE.findall(text.replace("&amp;", "&")):
        url = raw if raw.startswith("http") else f"https:{raw}"
        found.append(canonical_wp_url(url) if uploads_rel(url) else url)
    return list(dict.fromkeys(found))


def local_ok(rel: str) -> bool:
    path = MEDIA / rel
    return path.is_file() and path.stat().st_size > 32


def fetch_one(url: str) -> dict:
    rel = uploads_rel(url)
    if not rel:
        return {"url": url, "status": "skip-not-upload"}
    dest = MEDIA / rel
    if dest.name in MARS_KEEP and dest.is_file():
        return {"url": url, "rel": rel, "status": "mars-keep"}
    if local_ok(rel):
        return {"url": url, "rel": rel, "status": "exists"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Live WP first, then Wayback CDX / 0im_.
    for candidate in [url, *_mm.candidates(url)]:
        status, data, ctype = _mm.fetch(candidate)
        if status == 200 and _mm.looks_like_image(data, ctype):
            dest.write_bytes(data)
            return {
                "url": url,
                "rel": rel,
                "status": "mirrored",
                "bytes": len(data),
                "source": candidate,
            }
    return {"url": url, "rel": rel, "status": "missing"}


def rewrite_page(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    if not HOTLINK_RE.search(original) and not FORBIDDEN_SRC_RE.search(original):
        return False
    new = rewrite_html(original, html_depth(path), MEDIA)
    # Belt: drop any leftover forbidden src (never leave a live WP/Jetpack URL).
    if FORBIDDEN_SRC_RE.search(new) or HOTLINK_RE.search(new):
        new = HOTLINK_RE.sub("", new)
        new = re.sub(
            r"""<img\b[^>]*(?:wp-content|i[0-3]\.wp\.com|jetpack)[^>]*>""",
            "",
            new,
            flags=re.I,
        )
    if new != original:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def main() -> int:
    pages = homepage_linked_pages()
    urls: list[str] = []
    dirty_pages: list[Path] = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        found = collect_hotlinks(text)
        if found:
            dirty_pages.append(page)
            urls.extend(found)
    urls = list(dict.fromkeys(urls))
    print(f"target pages={len(pages)} dirty={len(dirty_pages)} unique_urls={len(urls)}")

    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(fetch_one, u): u for u in urls}
        for fut in as_completed(futs):
            rec = fut.result()
            records.append(rec)
            print(f"  {rec.get('status'):10} {rec.get('rel') or rec.get('url')}", flush=True)

    rewritten = 0
    for page in dirty_pages:
        if rewrite_page(page):
            rewritten += 1

    leftover = 0
    leftover_pages: list[str] = []
    for page in dirty_pages:
        text = page.read_text(encoding="utf-8")
        if FORBIDDEN_SRC_RE.search(text) or HOTLINK_RE.search(text):
            leftover += 1
            leftover_pages.append(str(page.relative_to(DOCS)))

    mirrored = sum(1 for r in records if r["status"] == "mirrored")
    missing = [r for r in records if r["status"] == "missing"]
    print(
        f"mirrored={mirrored} exists={sum(1 for r in records if r['status']=='exists')} "
        f"missing={len(missing)} pages_rewritten={rewritten} leftover_hotlink_pages={leftover}"
    )
    if leftover_pages:
        print("leftover:", leftover_pages)
    if missing:
        print("unrecoverable:")
        for r in missing:
            print(" ", r.get("rel"))
    return 0 if leftover == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
