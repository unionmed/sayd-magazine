"""Offline regression tests. The browser's only network route is a local trap proxy."""
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock
from playwright.sync_api import sync_playwright
import verify_ga4_live as verifier


class ParserTests(unittest.TestCase):
    def test_get_and_batched_post(self):
        request = SimpleNamespace(url='https://region1.google-analytics.com/g/collect?tid=' + verifier.ID,
                                  post_data='en=page_view\nen=user_engagement')
        events = verifier.event_info(request)
        self.assertEqual([x['event'] for x in events], ['page_view', 'user_engagement'])
        self.assertTrue(verifier.correct_single_page_view(events))
        self.assertFalse(verifier.correct_single_page_view(events + events))
        self.assertFalse(verifier.correct_single_page_view([]))
        self.assertFalse(verifier.correct_single_page_view([{'event': 'page_view', 'measurement_id': verifier.OLD_ID}]))

    def test_only_real_ga4_endpoint_validates(self):
        for url in ['https://evilgoogle-analytics.com/g/collect',
                    'https://fixture.invalid/g/collect',
                    'http://www.google-analytics.com/g/collect',
                    'https://www.google-analytics.com/collect']:
            self.assertEqual(verifier.event_info(SimpleNamespace(url=url + '?en=page_view', post_data=None)), [])

    def test_html_redirects_refused_before_following(self):
        from urllib.error import HTTPError
        from urllib.request import Request
        with self.assertRaises(HTTPError):
            verifier.NoRedirects().redirect_request(Request('https://sayd-magazine.com/'), None, 302,
                'Found', {}, 'https://www.google-analytics.com/g/collect?en=page_view')

    def test_all_telemetry_and_unrecognized_requests_abort(self):
        for url, method, resource in [
            ('https://www.google-analytics.com/g/collect?en=page_view&tid=' + verifier.ID, 'GET', 'image'),
            ('https://region1.google-analytics.com/g/collect?en=page_view&tid=' + verifier.ID, 'POST', 'fetch'),
            ('https://fixture.invalid/g/collect?en=page_view&tid=' + verifier.ID, 'POST', 'ping'),
            ('https://unknown.invalid/telemetry', 'GET', 'fetch'),
            (verifier.GTAG_URL + '&unexpected=1', 'GET', 'script'),
            (verifier.GTAG_URL, 'POST', 'script'),
            ('https://www.googletagmanager.com/gtm.js', 'GET', 'script'),
        ]:
            with self.subTest(url=url, method=method):
                ctx = Mock()
                events, blocked = [], []
                verifier.isolate_runtime(ctx, 'https://fixture.invalid/', '', events, blocked)
                route = Mock()
                route.request = SimpleNamespace(url=url, method=method, resource_type=resource, post_data=None)
                ctx.route.call_args.args[1](route)
                route.abort.assert_called_once()
                route.fetch.assert_not_called()
                route.fulfill.assert_not_called()
                route.continue_.assert_not_called()
                self.assertEqual(blocked, [url])
                socket = Mock()
                ctx.route_web_socket.call_args.args[1](socket)
                socket.close.assert_called_once()

    def test_only_cached_document_and_exact_loader_allowed(self):
        for url, resource in [('https://fixture.invalid/', 'document'), (verifier.GTAG_URL, 'script')]:
            ctx = Mock()
            verifier.isolate_runtime(ctx, 'https://fixture.invalid/', '<html></html>', [], [], loader_body='fixture')
            route = Mock()
            route.request = SimpleNamespace(url=url, method='GET', resource_type=resource, post_data=None)
            ctx.route.call_args.args[1](route)
            route.fulfill.assert_called_once()
            route.fetch.assert_not_called()
            route.continue_.assert_not_called()

    def test_fixed_loader_cannot_redirect(self):
        ctx = Mock()
        verifier.isolate_runtime(ctx, 'https://fixture.invalid/', '', [], [])
        route = Mock()
        route.request = SimpleNamespace(url=verifier.GTAG_URL, method='GET', resource_type='script', post_data=None)
        route.fetch.return_value.status = 302
        with self.assertRaisesRegex(RuntimeError, 'no redirects'):
            ctx.route.call_args.args[1](route)
        route.fetch.assert_called_once_with(max_redirects=0)
        route.abort.assert_called_once()
        route.fulfill.assert_not_called()
        route.continue_.assert_not_called()


class OfflineBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = []
        network = cls.network
        class Trap(BaseHTTPRequestHandler):
            def do_GET(self):
                network.append((self.command, self.path))
                self.send_response(200)
                self.end_headers()
            do_POST = do_GET
            do_CONNECT = do_GET
            def log_message(self, *args):
                pass
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Trap)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.pw = sync_playwright().start()
        options = {'proxy': {'server': f'http://127.0.0.1:{cls.server.server_port}', 'bypass': '<-loopback>'}}
        if os.environ.get('GA4_TEST_CHROMIUM'):
            options['executable_path'] = os.environ['GA4_TEST_CHROMIUM']
        cls.browser = cls.pw.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def check_fixture(self, measurement_id, count, mobile=False):
        self.network.clear()
        options = dict(self.pw.devices['Pixel 7']) if mobile else {}
        ctx = self.browser.new_context(**options, service_workers='block')
        events, blocked = [], []
        html = '<script async src="' + verifier.GTAG_URL + '"></script>'
        # Exercise actual browser GET, fetch POST, beacon, image, unknown endpoint,
        # WebSocket and unload traffic, without contacting a production endpoint.
        loader = '''
          const base = 'https://region1.google-analytics.com';
          for (let i=0; i<COUNT; i++) {
            fetch(base + '/g/collect?tid=MEASUREMENT&en=page_view').catch(()=>{});
          }
          fetch(base + '/g/collect?tid=MEASUREMENT', {method:'POST',body:'en=user_engagement\\nen=batch_event'}).catch(()=>{});
          navigator.sendBeacon(base + '/g/collect?tid=MEASUREMENT', 'en=scroll');
          new Image().src = base + '/g/collect?tid=MEASUREMENT&en=image_event';
          fetch(base + '/unknown-telemetry').catch(()=>{});
          window.socketClosed = false;
          const socket = new WebSocket('wss://analytics.fixture.invalid/socket');
          socket.onclose = () => { window.socketClosed = true; };
          window.workerAttempted = true;
          window.workerFinished = false;
          window.workerRegistered = false;
          navigator.serviceWorker.register('/worker.js').then(registration => {
            window.workerRegistered = !!registration; window.workerFinished = true;
          }).catch(() => { window.workerFinished = true; });
          addEventListener('pagehide',()=>navigator.sendBeacon(base + '/g/collect?tid=MEASUREMENT&en=unload',''));
        '''.replace('COUNT', str(count)).replace('MEASUREMENT', measurement_id)
        verifier.isolate_runtime(ctx, 'https://fixture.invalid/', html, events, blocked, loader_body=loader)
        page = ctx.new_page()
        try:
            page.goto('https://fixture.invalid/', wait_until='load')
            page.wait_for_function('window.socketClosed && window.workerFinished', timeout=5000)
            deadline = time.monotonic() + 5
            while not {'scroll', 'user_engagement', 'batch_event', 'image_event'}.issubset({e['event'] for e in events}) and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            actual = verifier.correct_single_page_view(events)
            self.assertEqual(len([e for e in events if e['event']=='page_view']), count)
            self.assertIn('scroll', [e['event'] for e in events])
            self.assertIn('user_engagement', [e['event'] for e in events])
            self.assertIn('batch_event', [e['event'] for e in events])
            self.assertTrue(page.evaluate('window.socketClosed'))
            self.assertTrue(page.evaluate('window.workerAttempted'))
            self.assertFalse(page.evaluate('window.workerRegistered'))
            self.assertEqual(ctx.service_workers, [])
            self.assertFalse(any('/worker.js' in url for url in blocked))
            self.assertIn('image_event', [e['event'] for e in events])
            self.assertTrue(any('/unknown-telemetry' in url for url in blocked))
            page.goto('about:blank')
            deadline = time.monotonic() + 5
            while not any(e['event'] == 'unload' for e in events) and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            self.assertIn('unload', [e['event'] for e in events])
        finally:
            ctx.close()
        self.assertEqual(self.network, [], 'A browser request escaped interception into the trap proxy')
        return actual

    def test_trap_proxy_positive_control(self):
        self.network.clear()
        ctx = self.browser.new_context(service_workers='block')
        try:
            page = ctx.new_page()
            page.goto('http://proxy-control.invalid/', wait_until='domcontentloaded')
            self.assertIn(('GET', 'http://proxy-control.invalid/'), self.network)
        finally:
            ctx.close()

    def test_single_correct_desktop_and_mobile(self):
        for mobile in [False, True]:
            with self.subTest(mobile=mobile):
                self.assertTrue(self.check_fixture(verifier.ID, 1, mobile))

    def test_duplicate_rejected(self):
        self.assertFalse(self.check_fixture(verifier.ID, 2))

    def test_missing_rejected(self):
        self.assertFalse(self.check_fixture(verifier.ID, 0))

    def test_wrong_id_rejected(self):
        self.assertFalse(self.check_fixture(verifier.OLD_ID, 1))


if __name__ == '__main__':
    unittest.main()
