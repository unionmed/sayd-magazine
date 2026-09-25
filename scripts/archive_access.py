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


_ARTICLE_RE = re.compile(
    r'(<article class="article-content">)(.*?)(</article>)',
    re.DOTALL,
)
_IMG_BLOCK_RE = re.compile(
    r"<a\b[^>]*>\s*<img\b[^>]*>\s*</a>|<img\b[^>]*>",
    re.IGNORECASE,
)
_P_IMAGES_ONLY_RE = re.compile(
    r"<p\b[^>]*>\s*(?:(?:<a\b[^>]*>\s*)?<img\b[^>]*>\s*(?:</a>\s*)?)+\s*</p>",
    re.IGNORECASE,
)
_SRC_ATTR_RE = re.compile(r"""src=(['"])(.*?)\1""", re.IGNORECASE | re.DOTALL)
_UPLOAD_YEAR_RE = re.compile(r"media/uploads/(\d{4})/")
REWIRE_MIN_YEAR = 2020


def _src_of(block: str) -> str:
    match = _SRC_ATTR_RE.search(block)
    return match.group(2) if match else ""


def _upload_year(src: str) -> int | None:
    match = _UPLOAD_YEAR_RE.search(src or "")
    return int(match.group(1)) if match else None


def _file_on_page(html: str, name: str) -> bool:
    """True when ``name`` is a path segment, not merely a word in the prose."""
    return bool(name) and f"/{name}" in html


def _visible_chars(html: str) -> str:
    chars: list[str] = []
    index = 0
    while index < len(html):
        if html[index] == "<":
            close = html.find(">", index)
            if close < 0:
                break
            index = close + 1
            continue
        chars.append(html[index])
        index += 1
    return "".join(chars)


def _visible_index(html: str, raw_pos: int) -> int:
    index = visible = 0
    while index < raw_pos and index < len(html):
        if html[index] == "<":
            close = html.find(">", index)
            index = close + 1 if close >= 0 else raw_pos
            continue
        visible += 1
        index += 1
    return visible


def _first_visible_text(visible: str, index: int) -> int:
    while index < len(visible) and visible[index].isspace():
        index += 1
    return index


def _local_image_units(html: str, min_year: int = REWIRE_MIN_YEAR) -> list[tuple[int, int, str]]:
    """Image blocks (or image-only paragraphs) whose src is a local 2020+ upload."""
    spans: list[tuple[int, int, str]] = []
    occupied: list[tuple[int, int]] = []
    for match in _P_IMAGES_ONLY_RE.finditer(html):
        blocks = _IMG_BLOCK_RE.findall(match.group(0))
        years = [_upload_year(_src_of(block)) for block in blocks]
        if years and all(year is not None and year >= min_year for year in years):
            spans.append((match.start(), match.end(), match.group(0)))
            occupied.append((match.start(), match.end()))

    def covered(start: int, end: int) -> bool:
        return any(start >= left and end <= right for left, right in occupied)

    for match in _IMG_BLOCK_RE.finditer(html):
        if covered(match.start(), match.end()):
            continue
        year = _upload_year(_src_of(match.group(0)))
        if year is not None and year >= min_year:
            spans.append((match.start(), match.end(), match.group(0)))
    spans.sort()
    return spans


def _insert_at_visible(html: str, index_map: list[int], vis_index: int, unit: str, block: bool) -> str:
    if vis_index >= len(index_map):
        return html + unit
    idx = index_map[vis_index]
    if block:
        cursor = idx
        while True:
            probe = cursor
            while probe > 0 and html[probe - 1].isspace():
                probe -= 1
            opener = re.search(r"<[^>/][^>]*>$", html[:probe])
            if not opener:
                break
            cursor = opener.start()
        idx = cursor
    return html[:idx] + unit + html[idx:]


def restore_stripped_upload_images(
    published: str,
    fresh: str,
    *,
    min_year: int = REWIRE_MIN_YEAR,
) -> tuple[str, list[str]]:
    """Insert local 2020+ ``<img>`` tags that ``fresh`` has and ``published`` lost.

    ``fresh`` is ``rewrite_html`` of the original article body (local src only
    when the file exists). Existing images — including pre-2020 Wayback
    variants — stay put. Alignment uses visible text, so a mismatch returns
    the published HTML unchanged.
    """
    published_visible = _visible_chars(published)
    fresh_visible = _visible_chars(fresh)
    index_map: list[int] = []
    cursor = 0
    while cursor < len(published):
        if published[cursor] == "<":
            close = published.find(">", cursor)
            if close < 0:
                break
            cursor = close + 1
            continue
        index_map.append(cursor)
        cursor += 1

    events: list[tuple[int, str, bool, list[str]]] = []
    for _start, end, raw in _local_image_units(fresh, min_year):
        names = [Path(_src_of(block)).name for block in _IMG_BLOCK_RE.findall(raw)]
        names = [name for name in names if name]
        if names and all(_file_on_page(published, name) for name in names):
            continue
        block = raw.lstrip().lower().startswith("<p")
        if any(_file_on_page(published, name) for name in names):
            missing = [
                block_html
                for block_html in _IMG_BLOCK_RE.findall(raw)
                if not _file_on_page(published, Path(_src_of(block_html)).name)
            ]
            raw = "".join(missing)
            block = False
            names = [Path(_src_of(block_html)).name for block_html in _IMG_BLOCK_RE.findall(raw)]
        at = _first_visible_text(fresh_visible, _visible_index(fresh, end))
        events.append((at, raw, block, names))

    fresh_i = published_i = 0
    event_i = 0
    inserts: list[tuple[int, str, bool, list[str]]] = []
    while True:
        while event_i < len(events) and events[event_i][0] == fresh_i:
            inserts.append((published_i, events[event_i][1], events[event_i][2], events[event_i][3]))
            event_i += 1
        if fresh_i >= len(fresh_visible) and published_i >= len(published_visible):
            break
        fresh_space = fresh_i < len(fresh_visible) and fresh_visible[fresh_i].isspace()
        published_space = published_i < len(published_visible) and published_visible[published_i].isspace()
        if fresh_space and not published_space:
            fresh_i += 1
            continue
        if published_space and not fresh_space:
            published_i += 1
            continue
        if fresh_space and published_space:
            fresh_i += 1
            published_i += 1
            continue
        if (
            fresh_i >= len(fresh_visible)
            or published_i >= len(published_visible)
            or fresh_visible[fresh_i] != published_visible[published_i]
        ):
            return published, []
        fresh_i += 1
        published_i += 1
    if event_i < len(events):
        return published, []

    grouped: list[tuple[int, str, bool, list[str]]] = []
    for vis_index, raw, block, names in inserts:
        if grouped and grouped[-1][0] == vis_index:
            prev_i, prev_raw, prev_block, prev_names = grouped[-1]
            grouped[-1] = (prev_i, prev_raw + raw, prev_block and block, prev_names + names)
        else:
            grouped.append((vis_index, raw, block, names))

    result = published
    restored: list[str] = []
    for vis_index, raw, block, names in sorted(grouped, key=lambda item: -item[0]):
        result = _insert_at_visible(result, index_map, vis_index, raw, block)
        restored.extend(names)
    return result, restored


def _norm_visible(html: str) -> str:
    return re.sub(r"\s+", " ", _visible_chars(html)).strip()


def _markdown_body(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return path.stem, text
    end = text.find("\n---", 3)
    if end == -1:
        return path.stem, text
    front = text[3:end]
    slug_m = re.search(r"^slug:\s*[\"']?(.+?)[\"']?\s*$", front, re.M)
    slug = slug_m.group(1).strip() if slug_m else path.stem
    return slug, text[end + 4 :].lstrip("\n")


def _rewrite_live_upload_urls(html: str, depth: int, media: Path, min_year: int) -> tuple[str, int]:
    """Point 2020+ upload URLs at local files. Leave a URL alone when the file is missing."""
    from media_rewrite import UPLOAD_URL_RE, public_src, year_of

    rewritten = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal rewritten
        url = match.group("url")
        year = year_of(url)
        if year is None or year < min_year:
            return match.group(0)
        local = public_src(url, depth, media)
        if not local:
            return match.group(0)
        rewritten += 1
        return local

    return UPLOAD_URL_RE.sub(repl, html), rewritten


def rewire_recovered_article_images(
    docs: Path | None = None,
    content_posts: Path | None = None,
    *,
    min_year: int = REWIRE_MIN_YEAR,
) -> dict[str, int]:
    """Restore 2020+ article images from markdown using files already on disk.

    Published HTML is the source of truth. This only rewrites ``<article>``
    bodies under ``docs/posts/``. Nav, homepage, categories, and media
    binaries are left untouched. An image is restored only when
    ``docs/media/uploads/...`` exists.
    """
    from media_rewrite import local_media_file, rewrite_html, uploads_rel, year_of

    docs = docs or DOCS
    content_posts = content_posts or CONTENT_POSTS
    media = docs / "media"
    articles = imgs_restored = imgs_rewritten = skipped_missing = skipped_align = 0
    skipped_names: set[str] = set()

    for md in sorted(content_posts.glob("*.md")):
        slug, body = _markdown_body(md)
        page = docs / "posts" / slug / "index.html"
        if not page.is_file():
            page = docs / "posts" / md.stem / "index.html"
        if not page.is_file():
            continue
        original = page.read_text(encoding="utf-8", errors="replace")
        match = _ARTICLE_RE.search(original)
        if not match:
            continue
        inner = match.group(2)
        inner, rewritten = _rewrite_live_upload_urls(inner, 2, media, min_year)
        fresh = rewrite_html(body, 2, media)
        updated, restored = restore_stripped_upload_images(inner, fresh, min_year=min_year)
        if not restored and any(
            (_upload_year(_src_of(block)) or 0) >= min_year
            and not _file_on_page(inner, Path(_src_of(block)).name)
            for block in _IMG_BLOCK_RE.findall(fresh)
        ):
            skipped_align += 1
        for img in _IMG_BLOCK_RE.findall(body):
            src = _src_of(img)
            rel = uploads_rel(src)
            if not rel:
                continue
            year = year_of(src)
            if year is None or year < min_year:
                continue
            if local_media_file(media, src):
                continue
            key = f"{slug}/{Path(rel).name}"
            if key not in skipped_names:
                skipped_names.add(key)
                skipped_missing += 1
        if updated == match.group(2) and rewritten == 0:
            continue
        if _norm_visible(updated) != _norm_visible(match.group(2)):
            skipped_align += 1
            continue
        for name in restored:
            src_m = re.search(rf"""src=(['"])([^'"]*/{re.escape(name)})\1""", updated)
            if not src_m:
                raise RuntimeError(f"{slug}: restored {name} has no src")
            src = src_m.group(2)
            if "wp-content" in src or src.startswith(("http://", "https://", "//")):
                raise RuntimeError(f"{slug}: restored src still remote {src}")
            path = (page.parent / src.split("?", 1)[0]).resolve()
            try:
                path.relative_to(media.resolve())
            except ValueError as exc:
                raise RuntimeError(f"{slug}: src escapes media {src}") from exc
            if not path.is_file() or path.stat().st_size <= 32:
                raise RuntimeError(f"{slug}: missing local file for {src}")
        page.write_text(
            original[: match.start(2)] + updated + original[match.end(2) :],
            encoding="utf-8",
        )
        articles += 1
        imgs_restored += len(restored)
        imgs_rewritten += rewritten

    stats = {
        "articles_touched": articles,
        "img_src_rewritten": imgs_rewritten,
        "tags_restored": imgs_restored,
        "skipped_no_local_file": skipped_missing,
        "skipped_align": skipped_align,
    }
    print(
        "rewire 2020+: "
        f"articles={articles} restored={imgs_restored} rewritten={imgs_rewritten} "
        f"skipped_missing={skipped_missing} skipped_align={skipped_align}"
    )
    return stats


def main() -> None:
    if "--rewire-2020" in sys.argv:
        rewire_recovered_article_images(DOCS)
        return
    mapping = load_id_slug_map(DOCS)
    posts = [{"id": post_id, "slug": slug} for post_id, slug in sorted(mapping.items(), key=lambda item: int(item[0]))]
    stubs = write_legacy_permalink_stubs(DOCS, posts)
    links = rewrite_post_legacy_links(DOCS, mapping)
    print(f"permalinks: ids={len(mapping)} new_stubs={stubs} articles_relinked={links}")
    restore_archive_images(DOCS)


if __name__ == "__main__":
    main()
