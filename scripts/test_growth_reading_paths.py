#!/usr/bin/env python3
"""Offline regression checks for growth paths and PR237's retained image cards."""
from urllib.parse import unquote, urlsplit
from lxml import html
import refresh_growth_reading_paths as growth


def verify(root=growth.ROOT):
    total = 0
    for lang in growth.LANGS:
        prefix = '' if lang == 'ar' else lang + '/'
        for number, pair in enumerate(growth.STORIES):
            slug = pair[lang != 'ar']
            page = root / ('docs/' + prefix + 'posts/' + slug + '/index.html')
            text = page.read_text()
            tree = html.fromstring(text)
            blocks = tree.xpath('//section[@class="article-more"]')
            assert len(blocks) == 1, page
            cards = blocks[0].xpath('.//a[@class="reading-card"]')
            assert len(cards) == 2, page
            targets = []
            for card in cards:
                target = (page.parent / unquote(urlsplit(card.get('href')).path)).resolve()
                assert target.is_file() and target.parent.name != slug, target
                assert target.is_relative_to(root / ('docs/' + prefix + 'posts')), target
                targets.append(target.parent.name)
                images = card.xpath('./img')
                assert len(images) == 1 and images[0].get('loading') == 'lazy'
                image = (page.parent / unquote(images[0].get('src'))).resolve()
                assert image.is_relative_to(root / 'docs/media') and image.is_file(), image
                target_tree = html.fromstring(target.read_text())
                cover = target_tree.xpath('//meta[@property="og:image"]/@content')[0]
                assert image == (root / 'docs' / unquote(urlsplit(cover).path.lstrip('/'))).resolve()
            assert len(set(targets)) == 2
            assert tree.xpath('//link[contains(@href,"related-reading.css")]'), page
            assert text.count('googletagmanager.com/gtag/js') == 1
            if not number:
                # Keep the newer editorial choice and card design from PR237.
                expected = growth.STORIES[2][lang != 'ar'], ('باشق-داخل-حقيبة-ظهر-عكار-صيد-الجوارح' if lang == 'ar' else 'akkar-sparrowhawk-backpack-raptor-poaching')
                assert set(targets) == set(expected), page
                assert not growth.LATEST.search(text), page
                continue
            rows = growth.candidates(root, lang, slug)
            assert targets == [s for s, _ in rows], page
            latest = growth.LATEST.findall(text)
            assert len(latest) == 1, page
            assert len(tree.xpath('//section[@class="editorial-background"]')) == 1
            assert growth.patch(text, lang, rows, True, page) == text, page
            source = root / 'content' / ('posts' if lang == 'ar' else lang) / (slug + '.md')
            original = source.read_text()
            assert growth.LATEST.findall(original) == latest
            assert growth.patch(original, lang, rows, False, page) == original
            total += 1
    print(f'PASS: {total} updated pages with 12 image links; 3 Adonis card blocks retained; languages, original images, source parity and idempotence.')


if __name__ == '__main__':
    verify()
