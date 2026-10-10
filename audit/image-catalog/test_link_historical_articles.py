#!/usr/bin/env python3
"""Offline regression tests for historical image-to-article linking."""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import link_historical_articles as linker

class LinkTests(unittest.TestCase):
    def test_legacy_wordpress(self):
        self.assertEqual(linker.extract_media_path(
            "http://sayd.alfalivehost.com/wp-content/uploads/2015/02/asparagus-ok.jpg"),
            "docs/media/uploads/2015/02/asparagus-ok.jpg")

    def test_modern_relative(self):
        self.assertEqual(linker.extract_media_path(
            "../../media/uploads/2026/09/hero-closing-80k.jpg"),
            "docs/media/uploads/2026/09/hero-closing-80k.jpg")

    def test_percent_encoding(self):
        self.assertEqual(linker.extract_media_path(
            "https://sayd-magazine.com/wp-content/uploads/2016/10/%D8%B3%D8%AF.jpg"),
            "docs/media/uploads/2016/10/سد.jpg")

    def test_unique_reference_per_article(self):
        body = '''featured: ../../media/uploads/2026/09/hero-closing-80k.jpg
<img src="../../media/uploads/2026/09/hero-closing-80k.jpg" />
<a href="https://sayd-magazine.com/wp-content/uploads/2026/09/hero-closing-80k.jpg">original</a>
<img src="../../media/uploads/2026/09/gallery-shil-day2.jpg">'''
        r = linker.image_references(body)
        self.assertEqual(len(r), 2)

    def test_do_not_claim_nonimage(self):
        self.assertFalse(linker.image_references("https://sayd-magazine.com/2026/09/news/"))
        self.assertIsNone(linker.extract_media_path(
            "https://sayd-magazine.com/wp-content/uploads/2026/09/press.pdf"))

    def test_title(self):
        self.assertEqual(linker.title_from_post('title: "مرحبا"\n', 'fallback'), 'مرحبا')

if __name__ == "__main__":
    unittest.main()
