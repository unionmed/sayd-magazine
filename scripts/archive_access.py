#!/usr/bin/env python3
"""Restore archive articles and the images inside them.

WordPress served every story at ``/{post_id}/``. The static site stores the
same story at ``/posts/{slug}/``. After the domain moved to GitHub Pages,
the old id URLs return "Page not found". This writes the same thin HTML
redirect the site already uses for a handful of 2026 ids.

Archive photos were left pointing at ``/wp-content/uploads/`` on
sayd-magazine.com and the retired sayd.alfalivehost.com host. Those URLs
404 (or no longer resolve) because the files were not in ``docs/media``.
Captures that still exist on the Wayback Machine are saved under
``docs/media/uploads/`` and article HTML is rewritten to those local paths.
Images with no capture are omitted instead of left as a broken hotlink.
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from media_rewrite import UPLOAD_URL_RE, rewrite_html, uploads_rel  # noqa: E402
from seo_foundation import _title_of, public_url, redirect_stub_html  # noqa: E402

DOCS = ROOT / "docs"
MEDIA = DOCS / "media"
CONTENT_POSTS = ROOT / "content" / "posts"
WXR = ROOT / "exports" / "saydmagazine-.WordPress.2026-09-15.xml"

_LEGACY_ID_RE = re.compile(
    r"https?://(?:www\.)?sayd-magazine\.com/(\d+)/?(?=[\"'\s<#?]|$)",
    re.IGNORECASE,
)
_LEGACY_P_ABS_RE = re.compile(
    r"https?://(?:www\.)?sayd-magazine\.com/\?p=(\d+)",
    re.IGNORECASE,
)
_LEGACY_P_REL_RE = re.compile(r"(?<=[\"'])/\?p=(\d+)")
_SIZE_RE = re.compile(
    r"^(?P<stem>.+)-(?P<w>\d+)x(?P<h>\d+)(?P<ext>\.[A-Za-z0-9]+)$"
)
_ANCHOR_RE = re.compile(r"<a\b[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
_IMG_SRC_RE = re.compile(
    r"""<img\b[^>]*\bsrc=(['"])([^'"]+)\1""",
    re.IGNORECASE,
)
_HREF_RE = re.compile(r"""\bhref=(['"])[^'"]*\1""", re.IGNORECASE)
_EMPTY_ANCHOR_RE = re.compile(
    r"""<a\b[^>]*\bhref=(['"])\1[^>]*>\s*</a>"""
    r"""|<a\b[^>]*\bhref=(['"])http://sayd\.alfalivehost\.com/\?attachment_id=\d+\2[^>]*>\s*</a>""",
    re.IGNORECASE,
)

CDX_URLS = (
    "https://web.archive.org/cdx/search/cdx?url=www.sayd-magazine.com/wp-content/uploads/"
    "&matchType=prefix&output=json&fl=original,timestamp,statuscode,mimetype"
    "&filter=statuscode:200&collapse=urlkey&limit=20000",
    "https://web.archive.org/cdx/search/cdx?url=sayd-magazine.com/wp-content/uploads/"
    "&matchType=prefix&output=json&fl=original,timestamp,statuscode,mimetype"
    "&filter=statuscode:200&collapse=urlkey&limit=20000",
    "https://web.archive.org/cdx/search/cdx?url=sayd.alfalivehost.com/wp-content/uploads/"
    "&matchType=prefix&output=json&fl=original,timestamp,statuscode,mimetype"
    "&filter=statuscode:200&collapse=urlkey&limit=20000",
)
UA = {"User-Agent": "SaydArchiveRestore/1.0"}


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def rel_key(url: str) -> str | None:
    rel = uploads_rel(url)
    if not rel:
        return None
    return nfc(rel)


def rewrite_legacy_permalinks(html: str, id_to_href: dict[str, str]) -> str:
    """Point ``/{id}/`` and ``?p=id`` links at the static article."""
    if not html or not id_to_href:
        return html

    def repl(match: re.Match[str]) -> str:
        return id_to_href.get(match.group(1), match.group(0))

    html = _LEGACY_ID_RE.sub(repl, html)
    html = _LEGACY_P_ABS_RE.sub(repl, html)
    html = _LEGACY_P_REL_RE.sub(repl, html)
    return html


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def _is_article(path: Path) -> bool:
    if not path.is_file():
        return False
    head = path.read_text(encoding="utf-8", errors="replace")[:1200]
    return "<h1" in head


def canonical_slug(docs: Path, slug: str, seen: set[str] | None = None) -> str:
    """Follow one thin redirect so duplicates land on the kept story."""
    seen = seen or set()
    if slug in seen:
        return slug
    seen.add(slug)
    page = docs / "posts" / slug / "index.html"
    if _is_article(page) or not page.is_file():
        return slug
    head = page.read_text(encoding="utf-8", errors="replace")[:1500]
    match = re.search(r'location\.replace\("([^"]+)"\)', head)
    if not match:
        return slug
    dest = re.search(r"/posts/([^/]+)/", unquote(match.group(1)))
    if not dest:
        return slug
    return canonical_slug(docs, dest.group(1), seen)


def load_id_slug_map(docs: Path | None = None) -> dict[str, str]:
    """WordPress post id → live ``docs/posts`` slug."""
    docs = docs or DOCS
    found: dict[str, str] = {}

    def remember(post_id: str, slug: str) -> None:
        if not post_id.isdigit() or not slug:
            return
        page = docs / "posts" / slug / "index.html"
        if not page.is_file():
            return
        slug = canonical_slug(docs, slug)
        if not (docs / "posts" / slug / "index.html").is_file():
            return
        current = found.get(post_id)
        if current and _is_article(docs / "posts" / current / "index.html"):
            return
        found[post_id] = slug

    if CONTENT_POSTS.is_dir():
        for md in sorted(CONTENT_POSTS.glob("*.md")):
            fm = _frontmatter(md)
            id_m = re.search(r"^wp_id:\s*(\d+)\s*$", fm, re.M)
            slug_m = re.search(r"^slug:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
            if not id_m:
                continue
            slug = slug_m.group(1).strip() if slug_m else md.stem
            if not (docs / "posts" / slug / "index.html").is_file():
                slug = md.stem
            remember(id_m.group(1), slug)

    if WXR.is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "import_wxr", ROOT / "scripts" / "import-wxr.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load import-wxr.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.parse_wxr(WXR)
        for post in data.get("posts") or []:
            remember(str(post.get("id") or ""), str(post.get("slug") or ""))
    return found


def id_hrefs(mapping: dict[str, str]) -> dict[str, str]:
    return {
        post_id: public_url(Path(f"posts/{slug}/index.html"))
        for post_id, slug in mapping.items()
    }


def write_legacy_permalink_stubs(out: Path, posts: list[dict]) -> int:
    """Write ``/{post_id}/index.html`` redirects. Existing stubs are kept."""
    written = 0
    for post in posts:
        post_id = str(post.get("id") or "").strip()
        slug = str(post.get("slug") or "").strip()
        if not post_id.isdigit() or not slug:
            continue
        dest = out / "posts" / slug / "index.html"
        stub = out / post_id / "index.html"
        if stub.is_file() or not dest.is_file():
            continue
        url = public_url(Path(f"posts/{slug}/index.html"))
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(
            redirect_stub_html(_title_of(dest), url, "ar"),
            encoding="utf-8",
        )
        written += 1
    return written


def _sniff_image(data: bytes) -> bool:
    if len(data) < 32:
        return False
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data.startswith((b"GIF87a", b"GIF89a")):
        return True
    return data.startswith(b"RIFF") and data[8:12] == b"WEBP"


def _cdx_rows(url: str) -> list[list[str]]:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload or not isinstance(payload[0], list):
        return []
    return payload[1:]


def fetch_capture_index() -> dict[str, tuple[str, str]]:
    """NFC ``uploads/...`` path → (timestamp, original URL), newest capture."""
    index: dict[str, tuple[str, str]] = {}
    for url in CDX_URLS:
        try:
            rows = _cdx_rows(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"CDX failed: {exc}")
            continue
        for row in rows:
            if len(row) < 4 or not str(row[3]).startswith("image/"):
                continue
            key = rel_key(row[0])
            if not key:
                continue
            previous = index.get(key)
            if previous is None or row[1] > previous[0]:
                index[key] = (row[1], row[0])
    return index


def _variant_index(captures: dict[str, tuple[str, str]]) -> dict[tuple[str, str, str], list[tuple[int, str]]]:
    variants: dict[tuple[str, str, str], list[tuple[int, str]]] = {}
    for rel in captures:
        path = Path(rel)
        match = _SIZE_RE.match(path.name)
        if not match:
            continue
        parent = path.parent.as_posix()
        if parent == ".":
            parent = ""
        key = (parent, nfc(match.group("stem")), match.group("ext").lower())
        area = int(match.group("w")) * int(match.group("h"))
        variants.setdefault(key, []).append((area, rel))
    return variants


def choose_capture(
    requested: str,
    captures: dict[str, tuple[str, str]],
    variants: dict[tuple[str, str, str], list[tuple[int, str]]],
) -> str | None:
    """Return the ``uploads/...`` path to store for this request."""
    if requested in captures:
        return requested
    path = Path(requested)
    match = _SIZE_RE.match(path.name)
    stem = nfc(match.group("stem") if match else path.stem)
    ext = (match.group("ext") if match else path.suffix).lower()
    parent = path.parent.as_posix()
    if parent == ".":
        parent = ""
    options = variants.get((parent, stem, ext)) or []
    if not options:
        return None
    return max(options)[1]


def _download(timestamp: str, original: str, dest: Path) -> str:
    if dest.is_file() and dest.stat().st_size > 32:
        with dest.open("rb") as handle:
            if _sniff_image(handle.read(32)):
                return "exists"
    url = f"https://web.archive.org/web/{timestamp}id_/{original}"
    last_error = "failed"
    for attempt in range(4):
        request = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code not in {429, 503, 502, 504}:
                return last_error
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = type(exc).__name__
        else:
            if not _sniff_image(data):
                return "not-image"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return "saved"
        time.sleep(1.5 * (attempt + 1))
    return last_error


def referenced_upload_keys(docs: Path) -> set[str]:
    keys: set[str] = set()
    for page in (docs / "posts").glob("*/index.html"):
        text = page.read_text(encoding="utf-8", errors="replace").replace("&amp;", "&")
        for match in UPLOAD_URL_RE.finditer(text):
            key = rel_key(match.group("url"))
            if key:
                keys.add(key)
    return keys


def restore_archive_images(docs: Path | None = None) -> dict[str, int]:
    """Download recovered originals and point article <img> tags at them."""
    docs = docs or DOCS
    media = docs / "media"
    captures = fetch_capture_index()
    if not captures:
        print("images: no Wayback captures fetched; article image URLs left unchanged")
        return {
            "captures": 0,
            "referenced": 0,
            "matched": 0,
            "saved": 0,
            "exists": 0,
            "failed": 0,
            "pages": 0,
            "left": -1,
        }
    variants = _variant_index(captures)
    requested = referenced_upload_keys(docs)
    chosen: dict[str, str] = {}
    jobs: list[tuple[str, str, str, Path]] = []
    for key in sorted(requested):
        dest_rel = choose_capture(key, captures, variants)
        if not dest_rel:
            continue
        capture = captures.get(dest_rel)
        if not capture:
            continue
        chosen[key] = dest_rel
        jobs.append((dest_rel, capture[0], capture[1], media / dest_rel))

    saved = exists = failed = 0
    failures: list[str] = []
    unique_jobs: list[tuple[str, str, str, Path]] = []
    seen_dest: set[str] = set()
    for rel, ts, original, dest in jobs:
        if rel in seen_dest:
            continue
        seen_dest.add(rel)
        unique_jobs.append((rel, ts, original, dest))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_download, ts, original, dest): rel
            for rel, ts, original, dest in unique_jobs
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            rel = futures[future]
            try:
                status = future.result()
            except Exception as exc:  # noqa: BLE001 — keep going through the batch
                status = type(exc).__name__
            if status == "saved":
                saved += 1
            elif status == "exists":
                exists += 1
            else:
                failed += 1
                if len(failures) < 12:
                    failures.append(f"{status} {rel}")
            if done % 40 == 0:
                print(f"  images {done}/{len(unique_jobs)} saved={saved} exists={exists} failed={failed}")

    for src, dest_rel in list(chosen.items()):
        path = media / dest_rel
        if not path.is_file() or path.stat().st_size < 32:
            chosen.pop(src, None)

    pages = 0
    for page in sorted((docs / "posts").glob("*/index.html")):
        original = page.read_text(encoding="utf-8", errors="replace")
        if "wp-content" not in original and "alfalivehost" not in original and "attachment_id" not in original:
            continue
        updated = _retarget_uploads(original, chosen)
        updated = rewrite_html(updated, 2, media)
        updated = _sync_image_hrefs(updated)
        updated = _EMPTY_ANCHOR_RE.sub("", updated)
        if updated != original:
            page.write_text(updated, encoding="utf-8")
            pages += 1

    still = 0
    for page in (docs / "posts").glob("*/index.html"):
        text = page.read_text(encoding="utf-8", errors="replace")
        still += len(UPLOAD_URL_RE.findall(text))
    print(
        f"images: captures={len(captures)} referenced={len(requested)} "
        f"matched={len(jobs)} saved={saved} already={exists} failed={failed} "
        f"pages_rewritten={pages} upload_urls_left={still}"
    )
    for line in failures:
        print("  ", line)
    return {
        "captures": len(captures),
        "referenced": len(requested),
        "matched": len(jobs),
        "saved": saved,
        "exists": exists,
        "failed": failed,
        "pages": pages,
        "left": still,
    }


def _retarget_uploads(html: str, chosen: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = rel_key(match.group("url"))
        dest = chosen.get(key or "")
        if not dest:
            return match.group(0)
        return "https://sayd-magazine.com/wp-content/" + dest

    return UPLOAD_URL_RE.sub(repl, html)


def _sync_image_hrefs(html: str) -> str:
    """Image links that still point at WordPress should open the local file."""

    def repl(match: re.Match[str]) -> str:
        tag = match.group(0)
        if not re.search(r"wp-content|attachment_id|alfalivehost|href=[\"'][\"']", tag, re.I):
            return tag
        img = _IMG_SRC_RE.search(tag)
        if not img:
            return tag
        src = img.group(2)
        if "media/" not in src:
            return tag
        return _HREF_RE.sub(f'href="{src}"', tag, count=1)

    return _ANCHOR_RE.sub(repl, html)


def rewrite_post_legacy_links(docs: Path, mapping: dict[str, str]) -> int:
    hrefs = id_hrefs(mapping)
    changed = 0
    for page in (docs / "posts").glob("*/index.html"):
        original = page.read_text(encoding="utf-8", errors="replace")
        updated = rewrite_legacy_permalinks(original, hrefs)
        if updated != original:
            page.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def main() -> None:
    mapping = load_id_slug_map(DOCS)
    posts = [{"id": post_id, "slug": slug} for post_id, slug in sorted(mapping.items(), key=lambda item: int(item[0]))]
    stubs = write_legacy_permalink_stubs(DOCS, posts)
    links = rewrite_post_legacy_links(DOCS, mapping)
    print(f"permalinks: ids={len(mapping)} new_stubs={stubs} articles_relinked={links}")
    restore_archive_images(DOCS)


if __name__ == "__main__":
    main()
