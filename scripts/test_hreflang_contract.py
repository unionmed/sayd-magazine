#!/usr/bin/env python3
"""Check reciprocal language alternates and exclude redirect/noindex targets."""
from pathlib import Path
from urllib.parse import unquote, urlparse
import sys
from lxml import html

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seo_foundation as seo


def main():
    docs = seo.DOCS
    twins = seo.load_twins(docs)
    edges = 0
    for path in sorted(docs.rglob('*.html')):
        tree = html.fromstring(path.read_text(encoding='utf-8'))
        links = tree.xpath('//head/link[@rel="alternate"][@hreflang]')
        if not links:
            continue
        rel = path.relative_to(docs).as_posix()
        # Gallery/noindex article policy is unchanged by this listing repair.
        if "posts" in Path(rel).parts:
            continue
        assert seo.is_alternate_page(rel, docs), rel
        canonicals = tree.xpath('//head/link[@rel="canonical"]/@href')
        assert len(canonicals) == 1, rel
        declared = {(n.get('hreflang'), n.get('href')) for n in links}
        generated = {(n.get('hreflang'), n.get('href')) for n in
                     html.fromstring('<html><head>' + '\n'.join(seo.hreflang_tags(rel, twins, docs)) +
                                     '</head></html>').xpath('//head/link[@hreflang]')}
        assert declared == generated, (rel, 'generated tags differ')
        for link in links:
            href = link.get('href')
            assert href.startswith(seo.ORIGIN + '/'), (rel, href)
            target_rel = unquote(urlparse(href).path).lstrip('/')
            if not target_rel:
                target_rel = 'index.html'
            elif target_rel.endswith('/'):
                target_rel += 'index.html'
            assert seo.is_alternate_page(target_rel, docs), (rel, target_rel)
            target = html.fromstring((docs / target_rel).read_text())
            if link.get('hreflang') != 'x-default':
                assert target.xpath('//html/@lang')[0].split('-')[0] == link.get('hreflang'), (rel, href)
                returned = target.xpath('//head/link[@hreflang]/@href')
                assert canonicals[0] in returned, (rel, 'no return link', href)
                edges += 1
    for slug in ('الصقارة', 'صيد-بري', 'صيد-بحري', 'صيد-الطيور'):
        assert not seo.hreflang_tags(f'fr/category/{slug}/index.html', twins, docs)
    for rel in ('en/stories/index.html', 'en/about/index.html', 'en/license/index.html'):
        assert len(seo.hreflang_tags(rel, twins, docs)) == 4, rel
    print(f'PASS: {edges} reciprocal hreflang links; all listing/static targets self-canonical, no redirect/noindex; generated tags match')


if __name__ == '__main__':
    main()
