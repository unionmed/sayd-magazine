#!/usr/bin/env python3
"""Offline regression tests: links must originate from GitHub repository content."""
import sys
import pathlib
import unittest

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

if __name__ == "__main__":
    unittest.main()
