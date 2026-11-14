#!/usr/bin/env python3
"""Standalone regression tests for the isolated public knowledge builder."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_index import LANGS, read_published, write_snapshot


def sample(lang):
    route = "/posts/" if lang == "ar" else f"/{lang}/posts/"
    return {"url": route + "demo/", "title": "Bird", "body": "Public article content",
            "keywords": "", "date": "2026-11-12", "category": "Archives",
            "categories": ["Archives"], "image": "/media/photo.jpg",
            "excerpt": "A public summary"}


def prepare(root, replacement=None):
    base = root / "docs" / "assets" / "search"
    (base / "shards").mkdir(parents=True)
    for lang in LANGS:
        rows = [replacement] if replacement is not None and lang == "ar" else [sample(lang)]
        raw = (json.dumps({"version": 3, "lang": lang, "articles": rows},
                          ensure_ascii=False) + "\n").encode()
        digest = hashlib.sha256(raw).hexdigest()
        name = f"shards/{lang}-{digest}.json"
        (base / name).write_bytes(raw)
        manifest = {
            "version": 3, "lang": lang, "categories": ["Archives"],
            "article_count": 1, "shards": [{"path": name, "sha256": digest,
                                             "bytes": len(raw), "count": 1}]
        }
        (base / f"manifest-{lang}.json").write_text(json.dumps(manifest))


class KnowledgeBuilderTests(unittest.TestCase):
    def test_public_records_keep_unknown_fields_unknown(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "repo"
            prepare(root)
            rows, report = read_published(root)
            self.assertEqual(len(rows), 3)
            self.assertEqual(report["total_language_records"], 3)
            self.assertEqual(rows[0]["source_urls"], [])
            self.assertIsNone(rows[0]["country"])
            self.assertIsNone(rows[0]["updated_at"])
            self.assertIsNone(rows[0]["translation_group_id"])
            self.assertTrue(rows[0]["url"].startswith("https://sayd-magazine.com/posts/"))

    def test_rejects_corrupt_shard(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "repo"
            prepare(root)
            shard = next((root / "docs/assets/search/shards").glob("ar-*.json"))
            shard.write_bytes(shard.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "checksum"):
                read_published(root)

    def test_rejects_private_or_cross_language_urls(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "repo"
            bad = sample("ar")
            bad["url"] = "/private/secret/"
            prepare(root, replacement=bad)
            with self.assertRaisesRegex(ValueError, "public URL"):
                read_published(root)

    def test_rejects_duplicate_urls(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "repo"
            prepare(root)
            base = root / "docs/assets/search"
            manifest = json.loads((base / "manifest-ar.json").read_text())
            # A duplicate shard reference is rejected before any output.
            manifest["shards"].append(manifest["shards"][0])
            manifest["article_count"] = 2
            (base / "manifest-ar.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "duplicate shard"):
                read_published(root)

    def test_output_is_stable_and_does_not_touch_sources(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "repo"
            out = Path(t) / "output"
            prepare(root)
            original = {str(x): x.read_bytes() for x in root.rglob("*") if x.is_file()}
            rows, report = read_published(root)
            write_snapshot(out, rows, report)
            first = (out / "knowledge.jsonl").read_bytes()
            write_snapshot(out, rows, report)
            self.assertEqual(first, (out / "knowledge.jsonl").read_bytes())
            self.assertEqual({str(x): x.read_bytes() for x in root.rglob("*") if x.is_file()},
                             original)
            self.assertEqual(len(first.splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
