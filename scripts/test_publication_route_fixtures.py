"""Isolated growth and negative fixtures for the publication social route gate."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory


def test_route_growth():
    from header_social import apply, LINKS
    from short_links import generate
    from test_header_social import publication_routes, check_route_inventory, check_social_pages

    with TemporaryDirectory(prefix='sayd-route-fixture-') as temporary:
        root=Path(temporary);docs=root/'docs'
        legacy=docs/'legacy/index.html'
        legacy.parent.mkdir(parents=True)
        legacy.write_text('<html><body>Existing headerless route</body></html>')
        preserved={'legacy/index.html'}
        packages=root/'content/features';packages.mkdir(parents=True)
        pairs=root/'content/en/pairs.json';pairs.parent.mkdir(parents=True)
        pairs.write_text(json.dumps({'pairs':{}}))
        package=packages/'future-package.json'
        package.write_text(json.dumps({'articles':[{'publication_ready':True,
            'slugs':{'ar':'خبر-اختبار','en':'fixture-story','fr':'article-test'}}]}))
        declared=publication_routes(root)
        assert len(declared)==3
        for route in declared:
            lang='en' if route.startswith('/en/') else 'fr' if route.startswith('/fr/') else 'ar'
            page=docs/route.strip('/')/'index.html';page.parent.mkdir(parents=True)
            page.write_text(apply(f'<html lang="{lang}"><head><title>Fixture</title>'
                '<script type="application/ld+json">{"datePublished":"2027-01-01"}</script>'
                '</head><body><div class="container mast-top-inner"></div>'
                '<article>Independent future article</article></body></html>',lang))
        links=generate(docs)
        expected=[link[3] for link in LINKS]

        def verify():
            check_route_inventory(docs,preserved,publication_routes(root),json.loads((docs/'s/links.json').read_text()))
            check_social_pages(docs,expected)

        def rejected(label, action):
            try:action()
            except AssertionError:pass
            else:raise AssertionError(f'{label} accepted')

        verify()  # One new trilingual package plus its three generated redirects.
        # Older publication scripts declare mirrors centrally instead of using
        # publication_ready. They must not require another per-release exception.
        package_text=package.read_text();package.unlink()
        pairs.write_text(json.dumps({'pairs':{'خبر-اختبار':'fixture-story'}}))
        from unittest.mock import patch
        with patch.dict('seo_foundation.FR_SLUG_BY_EN',{'fixture-story':'article-test'}):
            verify()
        package.write_text(package_text)
        verify()  # Both sources coexist; explicit distinct French slug wins.
        # A second publication must grow the inventory too, but merely placing
        # an article and a valid alias on disk is not a publication declaration.
        second={'ar':'خبر-ثان','en':'second-story','fr':'second-story'}
        for lang,slug in second.items():
            route='/'+('' if lang=='ar' else lang+'/')+'posts/'+slug+'/'
            page=docs/route.strip('/')/'index.html';page.parent.mkdir(parents=True)
            page.write_text(apply(f'<html lang="{lang}"><title>Second fixture</title>'
                '<script>{"datePublished":"2027-01-02"}</script>'
                '<div class="container mast-top-inner"></div></html>',lang))
        links=generate(docs)
        rejected('Undeclared article with a valid redirect',verify)
        (packages/'second-package.json').write_text(json.dumps({'articles':[
            {'publication_ready':True,'slugs':second}]}))
        verify()
        legacy_text=legacy.read_text();legacy.unlink()
        try:rejected('Missing old route',verify)
        finally:legacy.write_text(legacy_text)
        page=docs/'en/posts/fixture-story/index.html';original=page.read_text()
        mutations=[
            ('Missing article header',original.replace('class="container mast-top-inner"','class="stripped-header"')),
            ('Missing social header',original.replace('class="header-social"','class="stripped-social"')),
            ('Altered social destination',original.replace(expected[0],'https://example.test/other-account')),
        ]
        for label,wrong in mutations:
            assert wrong!=original,label
            try:
                page.write_text(wrong);rejected(label,verify)
            finally:page.write_text(original)
        alias=docs/links['/en/posts/fixture-story/'].strip('/')/'index.html'
        original=alias.read_text()
        target='https://sayd-magazine.com/en/posts/fixture-story/'
        wrong=original.replace(target,'https://sayd-magazine.com/en/posts/wrong/')
        assert wrong!=original
        try:
            alias.write_text(wrong);rejected('Wrong redirect target',verify)
        finally:alias.write_text(original)
        manifest=docs/'s/links.json';original=manifest.read_text()
        wrong=dict(links);wrong['/fr/posts/article-test/']=links['/en/posts/fixture-story/']
        try:
            manifest.write_text(json.dumps(wrong));rejected('Duplicate redirect alias',verify)
        finally:manifest.write_text(original)
        # Removing a new language page must not shrink the expected set silently.
        original=page.read_text();page.unlink()
        try:rejected('Missing new mirror',verify)
        finally:page.write_text(original)
        verify()
    print('PASS: declared trilingual growth; missing routes, headers, changed social links and invalid aliases rejected')


if __name__=='__main__':test_route_growth()
