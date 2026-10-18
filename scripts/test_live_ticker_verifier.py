#!/usr/bin/env python3
"""CDN email protection is allowed; ticker and editorial drift never are."""
import unittest
from verify_live_ticker import matches_release, origin_html


def encode_email(value, key=81):
    return bytes([key] + [byte ^ key for byte in value.encode()]).hex()


class LiveTickerVerifierTests(unittest.TestCase):
    def setUp(self):
        self.links = '<a href="posts/new/index.html">New story</a><a href="posts/old/index.html">Old story</a>'
        self.ticker = '<div class="ticker">' + self.links + '</div><div class="ticker" aria-hidden="true">' + self.links + '</div>'
        self.email = 'editor@sayd-magazine.com?subject=News&body=Hello'
        self.source = '<html lang="en"><body>' + self.ticker + '<article>Keep this text<img src="photo.jpg"></article><a href="mailto:editor@sayd-magazine.com?subject=News&amp;body=Hello">Email</a>\n</body></html>'
        self.cdn = self.source.replace('mailto:editor@sayd-magazine.com?subject=News&amp;body=Hello', '/cdn-cgi/l/email-protection#' + encode_email(self.email)).replace('</body>', '<script data-cfasync="false" src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script><script type="module" src="https://static.cloudflareinsights.com/beacon.min.js/v123" integrity="sha512-ABC123+/=" data-cf-beacon=\'{"r":1}\' crossorigin="anonymous"></script>\n</body>')

    def accepts(self, actual, source=None, count=2):
        return matches_release(actual.encode(), (source or self.source).encode(), count)

    def test_exact_release_and_known_cdn_transform(self):
        self.assertTrue(self.accepts(self.source))
        self.assertTrue(self.accepts(self.cdn))
        self.assertEqual(origin_html(self.cdn), self.source)
        email = 'editor@sayd-magazine.com'
        span = '<span class="__cf_email__" data-cfemail="' + encode_email(email) + '">[email&#160;protected]</span>'
        self.assertEqual(origin_html(span), email)

    def test_ticker_drift_rejected_before_any_normalization(self):
        for changed in [self.cdn.replace('New story','Wrong title'), self.cdn.replace('posts/new/','posts/wrong/'), self.cdn.replace(self.links, ''.join(reversed(['<a href="posts/new/index.html">New story</a>', '<a href="posts/old/index.html">Old story</a>']))), self.cdn.replace(self.ticker, ''), self.cdn.replace('aria-hidden="true"','aria-hidden="false"')]:
            self.assertFalse(self.accepts(changed))
        self.assertFalse(self.accepts(self.cdn, count=1))
        self.assertFalse(self.accepts(self.cdn, count=11))
        self.assertFalse(self.accepts(self.cdn, count=0))

    def test_unrelated_content_and_unrecognized_scripts_rejected(self):
        for changed in [self.cdn.replace('Keep this text','Edited text'), self.cdn.replace('photo.jpg','other.jpg'), self.cdn.replace('lang="en"','lang="fr"'), self.cdn.replace('</body>','<script src="https://other.example/script.js"></script></body>'), self.cdn.replace('static.cloudflareinsights.com','lookalike.example'), self.cdn.replace('<body>','<body>\n')]:
            self.assertFalse(self.accepts(changed))

    def test_lookalike_attributes_events_and_nested_scripts_rejected(self):
        probes = [
            '<script src="https://other.example/script.js" data-src="https://static.cloudflareinsights.com/beacon.min.js"></script>',
            '<script data-cfasync="false" src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js" onload="alert(1)"></script>',
            '<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js/v123" integrity="sha512-ABC123+/=" data-cf-beacon=\'{"r":1}\' crossorigin="anonymous" onload="alert(1)"></script>',
        ]
        for script in probes:
            self.assertFalse(self.accepts(self.cdn.replace('</body>', script + '</body>')))
        email = 'editor@sayd-magazine.com'
        wrapped = '<span class="__cf_email__" data-cfemail="' + encode_email(email) + '"><script src="https://other.example/script.js"></script></span>'
        self.assertEqual(origin_html(wrapped), wrapped)

    def test_malformed_cdn_email_rejected(self):
        self.assertFalse(self.accepts(self.cdn.replace(encode_email(self.email), 'abc')))
        self.assertFalse(matches_release(b'\xff', self.source.encode(), 2))


if __name__ == '__main__':
    unittest.main()
