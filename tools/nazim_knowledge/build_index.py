#!/usr/bin/env python3
"""Build a read-only Mufid knowledge snapshot from Sayd's PUBLISHED search shards.

Never edits the repository, live site, existing search index, or source content.
Only explicit, published fields are imported. Missing editorial metadata remains unknown.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

LANGS = ("ar", "en", "fr")
ORIGIN = "https://sayd-magazine.com"
EXPECTED_ROW = {"url", "title", "body", "keywords", "date", "category",
                "categories", "image", "excerpt"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
ARCHIVE = {"الأرشيف", "Archives"}


def fail_unless(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def strict_json(raw: bytes):
    def pairs(entries):
        value = {}
        for key, item in entries:
            fail_unless(key not in value, "Duplicate JSON key")
            value[key] = item
        return value
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")))


def public_path(value: str, lang: str) -> bool:
    prefix = "/posts/" if lang == "ar" else f"/{lang}/posts/"
    return (isinstance(value, str) and value.startswith(prefix)
            and value.endswith("/") and len(value) > len(prefix) + 1
            and "/" not in value[len(prefix):-1]
            and "?" not in value and "#" not in value
            and "\\" not in value and "%2f" not in value.lower()
            and value[len(prefix):-1] not in {".", ".."})


def safe_image(value: str) -> str | None:
    if not value:
        return None
    if (not isinstance(value, str) or not value.startswith("/")
            or value.startswith("//") or "?" in value or "#" in value
            or "\\" in value or any(part in {".", ".."} for part in value.split("/"))):
        return None
    return ORIGIN + value


def read_published(root: Path):
    base = root / "docs" / "assets" / "search"
    rows = []
    report = {"schema": 1, "source": "published_search_v3",
              "languages": {}, "source_manifest_sha256": {},
              "limitations": ["Country, article type, source evidence and update date are not verified by the search index.",
                              "Translations are separate records until an explicit published mapping is validated."]}
    for lang in LANGS:
        mraw = (base / f"manifest-{lang}.json").read_bytes()
        manifest = strict_json(mraw)
        fail_unless(isinstance(manifest, dict)
                    and set(manifest) == {"version", "lang", "categories", "article_count", "shards"}
                    and manifest["version"] == 3 and manifest["lang"] == lang,
                    f"Invalid published manifest for {lang}")
        count = manifest["article_count"]
        refs = manifest["shards"]
        fail_unless(type(count) is int and count >= 0
                    and isinstance(refs, list) and 0 < len(refs) <= 2048,
                    f"Invalid shard count for {lang}")
        report["source_manifest_sha256"][lang] = hashlib.sha256(mraw).hexdigest()
        stats = {"articles": 0, "missing_text": 0, "missing_date": 0,
                 "missing_image": 0, "missing_keywords": 0, "archive_only": 0}
        seen_urls, seen_shards = set(), set()
        for ref in refs:
            fail_unless(isinstance(ref, dict)
                        and set(ref) == {"path", "sha256", "bytes", "count"},
                        "Invalid shard metadata")
            name, digest = ref["path"], ref["sha256"]
            fail_unless(isinstance(name, str) and isinstance(digest, str)
                        and SHA.fullmatch(digest) is not None
                        and name == f"shards/{lang}-{digest}.json"
                        and name not in seen_shards, "Invalid/duplicate shard path")
            seen_shards.add(name)
            raw = (base / name).read_bytes()
            fail_unless(type(ref["bytes"]) is int and len(raw) == ref["bytes"]
                        and hashlib.sha256(raw).hexdigest() == digest,
                        f"Shard checksum/length mismatch: {name}")
            piece = strict_json(raw)
            fail_unless(isinstance(piece, dict)
                        and set(piece) == {"version", "lang", "articles"}
                        and piece["version"] == 3 and piece["lang"] == lang
                        and isinstance(piece["articles"], list)
                        and type(ref["count"]) is int
                        and len(piece["articles"]) == ref["count"],
                        f"Invalid shard data: {name}")
            for row in piece["articles"]:
                fail_unless(isinstance(row, dict) and set(row) == EXPECTED_ROW
                            and all(isinstance(row[field], str)
                                    for field in EXPECTED_ROW - {"categories"})
                            and isinstance(row["categories"], list)
                            and all(isinstance(c, str) for c in row["categories"]),
                            "Invalid public search record")
                url = row["url"]
                fail_unless(public_path(url, lang) and url not in seen_urls,
                            f"Invalid/duplicate public URL: {url}")
                seen_urls.add(url)
                if row["date"]:
                    fail_unless(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"]) is not None,
                                "Invalid publication date format")
                    date.fromisoformat(row["date"])
                body = row["body"].strip()
                cats = row["categories"]
                image = safe_image(row["image"])
                stats["missing_text"] += not bool(body)
                stats["missing_date"] += not bool(row["date"])
                stats["missing_image"] += not bool(image)
                stats["missing_keywords"] += not bool(row["keywords"].strip())
                stats["archive_only"] += len(cats) == 1 and cats[0] in ARCHIVE
                rows.append({
                    "id": hashlib.sha256((lang + "\0" + url).encode("utf-8")).hexdigest()[:24],
                    "language": lang,
                    "url": ORIGIN + url,
                    "title": row["title"],
                    "text": body,
                    "summary": row["excerpt"],
                    "published_at": row["date"] or None,
                    "updated_at": None,
                    "categories": cats,
                    "keywords": row["keywords"],
                    "image_url": image,
                    "country": None,
                    "article_type": None,
                    "topics": [],
                    "source_urls": [],
                    "source_review": "not_reviewed",
                    "freshness_review": "not_evaluated",
                    "translation_group_id": None,
                    "searchable_text": bool(body or row["title"] or row["excerpt"]),
                })
        fail_unless(len(seen_urls) == count,
                    f"Published manifest count mismatch for {lang}: {len(seen_urls)} != {count}")
        stats["articles"] = count
        report["languages"][lang] = stats
    rows.sort(key=lambda r: (LANGS.index(r["language"]), r["url"]))
    report["total_language_records"] = len(rows)
    return rows, report


def write_snapshot(out: Path, rows: list, report: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    payloads = {
        "knowledge.jsonl": "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                    for row in rows).encode("utf-8"),
        "quality_report.json": (json.dumps(report, ensure_ascii=False, indent=2,
                                         sort_keys=True) + "\n").encode("utf-8"),
    }
    for name, raw in payloads.items():
        # Atomic replacement: never leave a half-written snapshot file.
        with tempfile.NamedTemporaryFile(dir=out, prefix=f".{name}.", delete=False) as fh:
            staged = Path(fh.name)
            fh.write(raw)
        try:
            os.replace(staged, out / name)
        finally:
            staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path,
                        default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    rows, report = read_published(root)
    if not args.dry_run:
        parser.error("--out-dir is required except when using --dry-run")
    if args.out_dir:
        out = args.out_dir.resolve()
        fail_unless(not out.is_relative_to(root),
                    "Output must be OUTSIDE the repository (no accidental deployment)")
        if not args.dry_run:
            write_snapshot(out, rows, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
