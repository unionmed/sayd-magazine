#!/usr/bin/env python3
"""Offline regression tests: links must originate from GitHub repository content."""
import sys
import pathlib
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import link_historical_articles as linker

class LinkTests(unittest.TestCase):
    def test_relative_path(self):
        self.assertEqual(linker.extract_media_path(
            "../../media/uploads/2026/09/hero-closing-80k.jpg"),
            "docs/media/uploads/2026/09/hero-closing-80k.jpg")

    def test_repository_path(self):
        self.assertEqual(linker.extract_media_path(
            "docs/media/uploads/2026/09/hero-closing-80k.jpg"),
            "docs/media/uploads/2026/09/hero-closing-80k.jpg")

    def test_github_blob(self):
        self.assertEqual(linker.extract_media_path(
            "https://github.com/unionmed/sayd-magazine/blob/main/docs/media/uploads/2016/10/%D8%B3%D8%AF.jpg"),
            "docs/media/uploads/2016/10/سد.jpg")

    def test_github_raw(self):
        self.assertEqual(linker.extract_media_path(
            "https://raw.githubusercontent.com/unionmed/sayd-magazine/main/docs/media/uploads/2026/09/hero.jpg"),
            "docs/media/uploads/2026/09/hero.jpg")

    def test_external_hosts_ignored(self):
        for url in (
            "http://sayd.alfalivehost.com/wp-content/uploads/2015/02/asparagus-ok.jpg",
            "https://sayd-magazine.com/wp-content/uploads/2016/10/photo.jpg",
            "https://other.example.org/media/uploads/2026/09/hero.jpg",
            "https://github.com/another/repo/blob/main/docs/media/uploads/2026/09/hero.jpg",
        ):
            self.assertIsNone(linker.extract_media_path(url))
            self.assertFalse(linker.image_references(url))

    def test_unique_reference_per_article(self):
        body = '''featured: ../../media/uploads/2026/09/hero-closing-80k.jpg
<img src="../../media/uploads/2026/09/hero-closing-80k.jpg" />
<img src="https://sayd-magazine.com/wp-content/uploads/2015/02/old.jpg" />
<img src="../../media/uploads/2026/09/gallery-shil-day2.jpg">'''
        self.assertEqual(len(linker.image_references(body)), 2)

    def test_ignore_nonimages(self):
        self.assertIsNone(linker.extract_media_path(
            "docs/media/uploads/2026/09/press.pdf"))
        self.assertFalse(linker.image_references("https://example.org/2026/09/news/"))

    def test_title(self):
        self.assertEqual(linker.title_from_post('title: "مرحبا"\n', 'fallback'), 'مرحبا')

    def test_prospective_publication_exact_namespace(self):
        path = "docs/media/publications/example-20261023/bird-01.jpg"
        for reference in (path, path.removeprefix("docs/"), "../../" + path.removeprefix("docs/"),
                          "https://github.com/unionmed/sayd-magazine/blob/main/" + path,
                          "https://raw.githubusercontent.com/unionmed/sayd-magazine/main/" + path):
            with self.subTest(reference=reference):
                self.assertEqual(linker.extract_media_path(reference), path)
                self.assertEqual(set(linker.image_references('<img src="' + reference + '">')), {path})

    def test_publication_namespace_does_not_accept_other_hosts_or_paths(self):
        for reference in (
            "https://external.invalid/media/publications/example/bird.jpg",
            "https://sayd-magazine.com/media/publications/example/bird.jpg",
            "https://github.com/another/repo/blob/main/docs/media/publications/example/bird.jpg",
            "media/publications/../bird.jpg",
            "media/publications/example/../bird.jpg",
            "media/publications/example/%2e%2e%2fbird.jpg",
            "media/publications/example/nested/bird.jpg",
            "media/publications/example/rights.pdf",
            "media/publications/example/animation.gif",
            "media/publications/UPPER/bird.jpg",
        ):
            with self.subTest(reference=reference):
                self.assertIsNone(linker.extract_media_path(reference))
                self.assertFalse(linker.image_references(reference))

    def test_new_article_title_search_keeps_rights_unverified_and_writes_nothing(self):
        import search_editorial
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            posts = root / "content/posts"; posts.mkdir(parents=True)
            image = "docs/media/publications/example-20261023/bird-01.jpg"
            post = posts / "test.md"
            post.write_text('title: "Unmistakable new article title"\nfeatured: media/publications/example-20261023/bird-01.jpg\n<img src="../../media/publications/example-20261023/bird-01.jpg">')
            snapshot = root / "audit/image-catalog/article-image-links.json"
            snapshot.parent.mkdir(parents=True); snapshot.write_bytes(b"immutable historical snapshot")
            rows = [{"path": image, "sha": "a" * 40, "sections": []}]
            with patch.object(linker, "ROOT", root), patch.object(linker, "POSTS", posts), \
                 patch.object(linker, "records", return_value=rows), \
                 patch.object(search_editorial, "ROOT", root), \
                 patch.object(search_editorial, "records", return_value=rows), \
                 patch.object(search_editorial, "load_overrides", return_value=[]):
                links = linker.build_links()
                self.assertEqual(links["exact_links"], 1)
                self.assertEqual(links["exact"][0]["expected_local_path"], image)
                self.assertEqual(links["exact"][0]["visual_status"], "UNVERIFIED")
                result = search_editorial.search("Unmistakable")
            self.assertEqual(result["returned"], 1)
            item = result["results"][0]
            self.assertEqual(item["visual_status"], "UNVERIFIED")
            self.assertEqual(item["rights_status"], "NOT_VERIFIED")
            self.assertEqual(item["articles"][0]["inherited_editorial_evidence"], [])
            self.assertEqual(snapshot.read_bytes(), b"immutable historical snapshot")
            self.assertFalse((root / ".catalog-build").exists())

if __name__ == "__main__":
    unittest.main()
