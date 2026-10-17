#!/usr/bin/env python3
"""Friendly collection views preserve content, destination URLs and SEO identity."""
import json
import unittest
from pathlib import Path
from urllib.parse import urljoin, unquote, urlsplit
from lxml import html
from interview_collection import DOCS, FOLDER, entries
from interview_sharing import friendly_view, ORIGIN
from seo_foundation import canonical_rel, in_sitemap


class InterviewSharingTests(unittest.TestCase):
    def test_views_match_canonical_collections(self):
        for lang in ('ar', 'en', 'fr'):
            prefix = '' if lang == 'ar' else lang
            old = DOCS / prefix / 'category' / FOLDER / 'index.html'
            new = DOCS / prefix / 'interviews/index.html'
            self.assertEqual(new.read_text(), friendly_view(old.read_text(), old, new))
            a, b = html.fromstring(old.read_text()), html.fromstring(new.read_text())
            self.assertFalse(b.xpath('//link[@rel="alternate"]'))
            for alternate in a.xpath('//link[@rel="alternate"]'):
                alternate.getparent().remove(alternate)
            self.assertEqual(a.xpath('//article//text()'), b.xpath('//article//text()'))
            self.assertEqual(len(b.xpath('//article')), len(entries(lang)))
            canonical = a.xpath('//link[@rel="canonical"]/@href')
            self.assertEqual(b.xpath('//link[@rel="canonical"]/@href'), canonical)
            self.assertIn('/category/', canonical[0])
            rel = new.relative_to(DOCS)
            self.assertEqual(canonical_rel(rel), old.relative_to(DOCS))
            self.assertFalse(in_sitemap(rel))
            self.assertNotIn('http-equiv="refresh"', new.read_text())
            self.assertEqual(b.xpath('//*[@data-copy-interviews]/@data-copy-interviews'),
                             [ORIGIN + '/' + (prefix+'/' if prefix else '') + 'interviews/'])
            self.assertEqual(len(b.xpath('//*[@role="status"]')), 1)
            # Relative images, styles, scripts and archive/article links keep destinations.
            for old_url, new_url in zip(a.xpath('//@href | //@src'), b.xpath('//@href | //@src')):
                if old_url.startswith(('#', '/')) or urlsplit(old_url).scheme:
                    self.assertEqual(old_url, new_url)
                    continue
                old_abs = urljoin(old.as_uri(), old_url)
                new_abs = urljoin(new.as_uri(), new_url)
                self.assertEqual(old_abs, new_abs)
                parsed = urlsplit(new_abs)
                if parsed.scheme == 'file':
                    path = Path(unquote(parsed.path))
                    if path.is_dir(): path /= 'index.html'
                    self.assertTrue(path.is_file(), str(path))

    def test_homepages_link_friendly_collection(self):
        for lang in ('ar','en','fr'):
            prefix = '' if lang=='ar' else lang
            tree=html.parse(str(DOCS/prefix/'index.html'))
            expected='/' + (prefix+'/' if prefix else '') + 'interviews/'
            self.assertIn(expected,tree.xpath('//a/@href'))

if __name__ == '__main__': unittest.main()
