"""Homepage framing checks run with the existing editorial revision test job."""
import copy
import json
from pathlib import Path
import sys
import unittest
from lxml import html
import homepage_card_framing as framing
import editorial_revision
import publication_compiler as compiler

ROOT = Path(__file__).resolve().parents[1]


class FramingTests(unittest.TestCase):
    def test_only_selected_image_style_changes_and_is_stable(self):
        for lang, path in framing.HOMES.items():
            page = (ROOT/path).read_text()
            changed = framing.patch(page, lang)
            self.assertEqual(framing.patch(changed, lang), changed)
            old, new = html.fromstring(page), html.fromstring(changed)
            count = 0
            for a, b in zip(old.xpath('//img'), new.xpath('//img')):
                if framing.identity(a.get('src', ''), lang):
                    self.assertEqual(b.get('style'), framing.STYLE)
                    b.attrib.pop('style', None)
                    a.attrib.pop('style', None)
                    count += 1
            self.assertEqual(count, 12 if lang == 'ar' else 11)
            self.assertEqual(html.tostring(old), html.tostring(new))
            # An exact inverse proves all non-IMG bytes also remain intact.
            oldtags = __import__('re').findall(r'<img\b[^>]*>', page)
            newtags = __import__('re').findall(r'<img\b[^>]*>', changed)
            inverse = changed
            for a, b in zip(oldtags, newtags):
                if a != b:
                    self.assertEqual(inverse.count(b), 1)
                    inverse = inverse.replace(b, a, 1)
            self.assertEqual(inverse, page)

    def test_installation_does_not_activate(self):
        if not (ROOT/framing.MARKER).exists():
            for lang, path in framing.HOMES.items():
                page = (ROOT/path).read_text()
                self.assertEqual(framing.render(ROOT, page, lang), page)

    def test_closed_schema_and_target_digest(self):
        marker = ROOT/framing.MARKER
        base = (json.loads(marker.read_text())['expected_base'] if marker.exists() else
                compiler.git(ROOT, 'rev-parse', 'HEAD').decode().strip())
        source = compiler.sha256(compiler.canonical(framing.IMAGES))
        result, record, article = framing.expected_changes(ROOT, base, source)
        self.assertEqual(set(result), set(framing.HOMES.values()))
        self.assertIsNone(record)
        value = dict(schema=editorial_revision.SCHEMA, id=framing.ID, operation=framing.ID,
                     expected_base=base, approval_reference='private:nayef-card-correction-20261127',
                     expected_source_sha256=source, expected_targets_sha256=compiler.sha256(compiler.canonical({
                         p: compiler.sha256(compiler.read_blob(ROOT, compiler.tree(ROOT, base)[p])) for p in sorted(result)})), payload={})
        self.assertEqual(editorial_revision.expected_changes(ROOT, base, value, framing.MARKER)[0], result)
        for mutate in ('payload', 'id', 'expected_source_sha256', 'expected_targets_sha256', 'expected_base'):
            bad = copy.deepcopy(value)
            bad[mutate] = {'path': 'docs/index.html'} if mutate == 'payload' else '0'*64
            with self.assertRaises((ValueError, AssertionError)):
                editorial_revision.expected_changes(ROOT, base, bad, framing.MARKER)

    def test_duplicates_comments_and_remote_sources(self):
        src = next(iter(framing.IMAGES))
        tag = '<img src="' + src + '">'
        with self.assertRaises(ValueError):
            framing.patch('<main>'+tag+tag+'</main>', 'ar')
        with self.assertRaises(ValueError):
            framing.patch('<main>'+tag+'</main><!--'+tag+'-->', 'ar')
        for suffix in ('?x=1', '#x'):
            self.assertIsNone(framing.identity(src+suffix, 'ar'))
        self.assertIsNone(framing.identity('https://example.com/'+src, 'ar'))
        self.assertEqual(framing.patch('<main><img src="other.jpg"></main>', 'ar'),
                         '<main><img src="other.jpg"></main>')


if __name__ == '__main__':
    unittest.main()
