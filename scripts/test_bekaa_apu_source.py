#!/usr/bin/env python3
"""Keep the APU publisher source, renderer and stored mirrors on one tally."""
import ast
import html as esc
import json
from pathlib import Path
import unittest

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
AR = 'البقاع-الشمالي-إزالة-38280-متر-شباك-apu-cabs'
EN = 'northern-bekaa-38280-square-metres-bird-nets-apu-cabs'


def paragraphs(markup):
    tree = html.fromstring(markup)
    return [n.text_content() for n in tree.xpath('//div[@class="statement-text"]/p')]


def renderer(data):
    """Execute the actual pure body renderer, never the publisher's side effects.

    Importing this historical one-off publisher would rewrite article files and
    change homepage placement. Extract its two rendering functions instead.
    """
    path = ROOT / 'scripts/publish_bekaa_apu_cabs.py'
    source = ast.parse(path.read_text(), filename=str(path))
    constants = {}
    functions = []
    for node in source.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'IMAGES', 'OFFICIAL'}:
                    constants[target.id] = ast.literal_eval(node.value)
        if isinstance(node, ast.FunctionDef) and node.name in {'figure', 'body'}:
            functions.append(node)
    assert len(functions) == 2
    scope = {'T': data, 'esc': esc, **constants}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), scope)
    return scope['body']


class BekaaSourceTest(unittest.TestCase):
    def test_tally_survives_article_body_regeneration(self):
        data = json.loads((ROOT / 'content/features/bekaa-apu-cabs-20261009.json').read_text())
        render = renderer(data)
        checks = {
            'ar': ('17,640 مترًا مربعًا إضافيًا', 'الحصيلة الإجمالية للحملة إلى 38,280', 'خلال ثلاثة أيام'),
            'en': ('an additional 17,640 square metres', 'campaign’s overall total to 38,280', 'over three days'),
            'fr': ('17 640 mètres carrés supplémentaires', 'bilan total de la campagne à 38 280', 'en trois jours'),
        }
        for lang, (additional, total, period) in checks.items():
            with self.subTest(language=lang):
                expected = data[lang]['paragraphs']
                for para in (expected[0], expected[-1]):
                    self.assertIn(additional, para)
                    self.assertIn(total, para)
                self.assertIn(period, expected[-1])
                self.assertEqual(paragraphs(render(lang)), expected)
                slug = AR if lang == 'ar' else EN
                markdown = ROOT / 'content' / ('posts' if lang == 'ar' else lang) / (slug + '.md')
                published = ROOT / 'docs' / ('' if lang == 'ar' else lang) / 'posts' / slug / 'index.html'
                self.assertEqual(paragraphs(markdown.read_text()), expected, str(markdown))
                self.assertEqual(paragraphs(published.read_text()), expected, str(published))


if __name__ == '__main__':
    unittest.main()
