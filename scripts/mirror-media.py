#!/usr/bin/env python3
"""Download Sayd Magazine WP uploads from the Wayback Machine into docs/media/.

Priority: homepage + logos. Remaining URLs are left for HTML rewrite to
https://web.archive.org/web/0im_/ORIGINAL (import-wxr.py).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from media_rewrite import (
    FOOTER_LOGO_ORIGINAL,
    LOGO_ORIGINAL,
    PRIORITY_ORIGINALS,
    canonical_wp_url,
    collect_upload_urls,
    in_mirror_scope,
    uploads_rel,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "media"
DEFAULT_HOME = ROOT / "docs" / "index.html"
UA = "SaydMagazineStatic/1.0 (+https://github.com/unionmed/sayd-magazine; media recovery)"
CDX = "https://web.archive.org/cdx/search/cdx"

IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/avif",
    "image/svg+xml",
    "application/octet-stream",
}


def _opener() -> urllib.request.OpenerDirector:
    handlers = [
        urllib.request.HTTPRedirectHandler(),
        urllib.request.HTTPSHandler(),
    ]
    opener = urllib.request.build_opener(*handlers)
    opener.addheaders = [("User-Agent", UA), ("Accept", "image/*,*/*;q=0.8")]
    return opener


OPENER = _opener()


def fetch(url: str, timeout: int = 45) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"})
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            data = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            return resp.status, data, ctype
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b"", (e.headers.get("Content-Type") or "")
    except Exception:
        return 0, b"", ""


def cdx_best(original: str) -> str | None:
    """Closest 200 image capture, or None."""
    qs = urllib.parse.urlencode(
        {
            "url": original,
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype",
            "filter": "statuscode:200",
            "limit": "20",
            "fastLatest": "true",
        }
    )
    # Also try without scheme host variants
    status, data, _ = fetch(f"{CDX}?{qs}", timeout=30)
    if status != 200 or not data:
        # host-less wildcard
        parsed = urllib.parse.urlparse(original)
        qs2 = urllib.parse.urlencode(
            {
                "url": parsed.path.lstrip("/"),
                "output": "json",
                "fl": "timestamp,original,statuscode,mimetype",
                "filter": "statuscode:200",
                "limit": "10",
            }
        )
        status, data, _ = fetch(f"{CDX}?{qs2}", timeout=30)
        if status != 200 or not data:
            return None
    try:
        rows = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list) or len(rows) < 2:
        return None
    header, *entries = rows
    try:
        ts_i, orig_i, st_i, mt_i = (
            header.index("timestamp"),
            header.index("original"),
            header.index("statuscode"),
            header.index("mimetype"),
        )
    except ValueError:
        return None
    # Prefer image mimetypes, latest timestamp
    images = [
        r
        for r in entries
        if str(r[st_i]) == "200" and str(r[mt_i]).startswith("image/")
    ]
    pool = images or [r for r in entries if str(r[st_i]) == "200"]
    if not pool:
        return None
    pool.sort(key=lambda r: str(r[ts_i]), reverse=True)
    ts, orig = pool[0][ts_i], pool[0][orig_i]
    return f"https://web.archive.org/web/{ts}im_/{orig}"


def looks_like_image(data: bytes, ctype: str) -> bool:
    if len(data) < 64:
        return False
    if data[:15].lstrip().lower().startswith(b"<!doctype") or data[:6].lstrip().lower().startswith(
        b"<html"
    ):
        return False
    if ctype.startswith("text/html"):
        return False
    if ctype in IMAGE_TYPES or ctype.startswith("image/"):
        return True
    # Magic numbers
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def candidates(original: str) -> list[str]:
    urls = []
    cdx = cdx_best(original)
    if cdx:
        urls.append(cdx)
    urls.append(f"https://web.archive.org/web/0im_/{original}")
    urls.append(f"https://web.archive.org/web/im_/{original}")
    # Historic www host (logo CDX redirected there)
    www = original.replace("://sayd-magazine.com", "://www.sayd-magazine.com")
    if www != original:
        urls.append(f"https://web.archive.org/web/0im_/{www}")
    return list(dict.fromkeys(urls))


def dest_for(original: str, out: Path) -> Path | None:
    rel = uploads_rel(original)
    if not rel:
        return None
    return out / rel


def save_image(original: str, out: Path) -> dict:
    dest = dest_for(original, out)
    record = {
        "original": original,
        "rel": uploads_rel(original),
        "status": "failed",
        "source": None,
        "bytes": 0,
        "year": None,
    }
    if dest is None:
        record["status"] = "skipped-not-upload"
        return record
    m = re.search(r"/uploads/(\d{4})/", original)
    record["year"] = m.group(1) if m else None
    if dest.is_file() and dest.stat().st_size > 32:
        record["status"] = "exists"
        record["bytes"] = dest.stat().st_size
        record["source"] = "local"
        return record

    last_err = ""
    for url in candidates(original):
        status, data, ctype = fetch(url)
        if status in (200, 203) and looks_like_image(data, ctype):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            record["status"] = "downloaded"
            record["source"] = url
            record["bytes"] = len(data)
            return record
        last_err = f"http {status} ctype={ctype} n={len(data)}"
        time.sleep(0.35)
    record["error"] = last_err
    return record


def homepage_urls(home_html: Path) -> list[str]:
    urls = list(PRIORITY_ORIGINALS)
    if home_html.exists():
        urls.extend(collect_upload_urls(home_html.read_text(encoding="utf-8", errors="ignore")))
    # unique, logos first; skip pre-2022 archive except chrome allowlist
    seen = set()
    ordered = []
    for u in urls:
        c = canonical_wp_url(u)
        if not c or c in seen or not in_mirror_scope(c):
            continue
        seen.add(c)
        ordered.append(c)
    return ordered


def all_docs_urls(docs: Path) -> list[str]:
    texts = []
    for p in docs.rglob("*.html"):
        texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return collect_upload_urls(*texts)


def write_report(records: list[dict], path: Path) -> None:
    downloaded = [r for r in records if r["status"] in ("downloaded", "exists")]
    failed = [r for r in records if r["status"] == "failed"]
    y2026 = [r for r in failed if r.get("year") == "2026"]
    lines = [
        "# Media recovery — Sayd Magazine static site",
        "",
        f"- Attempted: **{len(records)}** unique upload URLs (homepage + logos)",
        f"- Mirrored locally: **{len(downloaded)}**",
        f"- Failed (no Wayback image): **{len(failed)}**",
        f"- Unrecoverable 2026 (no Wayback capture found): **{len(y2026)}**",
        "",
        "## Mirrored",
        "",
    ]
    for r in downloaded:
        lines.append(f"- `{r['rel']}` ← {r.get('source') or 'local'} ({r['bytes']} bytes)")
    lines += ["", "## Failed (Wayback interim / CSS placeholder)", ""]
    for r in failed:
        note = " — 2026, likely never archived" if r.get("year") == "2026" else ""
        lines.append(f"- `{r['rel']}`{note}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Mirror WP uploads from Wayback → docs/media/")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--home", type=Path, default=DEFAULT_HOME)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument(
        "--all-docs",
        action="store_true",
        help="Also attempt every unique 2022+ URL found in docs/ (still skips pre-2022 archive)",
    )
    args = ap.parse_args()

    urls = homepage_urls(args.home)
    if args.all_docs:
        extra = [u for u in all_docs_urls(ROOT / "docs") if in_mirror_scope(u)]
        extra_new = [u for u in extra if u not in set(urls)]
        print(f"Adding {len(extra_new)} extra 2022+ URLs from docs/ (total {len(urls)+len(extra_new)})")
        urls.extend(extra_new)

    print(f"Mirroring {len(urls)} URLs → {args.out}")
    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(save_image, u, args.out): u for u in urls}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            records.append(rec)
            mark = rec["status"]
            print(f"[{i}/{len(urls)}] {mark:12} {rec.get('rel')}")

    records.sort(key=lambda r: r.get("rel") or "")
    manifest = args.out / "manifest.json"
    args.out.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(records, ROOT / "audit" / "MEDIA-RECOVERY.md")
    ok = sum(1 for r in records if r["status"] in ("downloaded", "exists"))
    fail = sum(1 for r in records if r["status"] == "failed")
    print(f"Done. mirrored={ok} failed={fail} report=audit/MEDIA-RECOVERY.md")


if __name__ == "__main__":
    sys.exit(main())
