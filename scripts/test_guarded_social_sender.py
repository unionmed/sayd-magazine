import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import publication_gate as g
from guarded_social_sender import _send, send
from test_publication_gate import fixture


class SenderTests(unittest.TestCase):
    def setUp(self):
        self.source, self.live, self.payload, self.mirrors = fixture()
        self.transport = Mock(return_value={'status': 'PUBLISHED', 'provider_id': 'fake',
                                            'url': 'https://facebook.com/fake'})
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def send(self):
        return _send(self.source, self.mirrors['ar'], self.payload, self.transport,
                    self.directory.name, get=self.live.__getitem__)

    def test_pass_exact_payload_and_receipt(self):
        result = self.send()
        self.transport.assert_called_once_with(self.payload)
        self.assertEqual(result['delivery']['status'], 'PUBLISHED')
        self.assertEqual(set(result['publication']['mirrors']), {'ar', 'en', 'fr'})

    def test_draft_never_calls_sender(self):
        del self.source.data[g.source_path(self.mirrors['ar'])]
        with self.assertRaises(g.Blocked): self.send()
        self.transport.assert_not_called()
        self.assertFalse(list(Path(self.directory.name).glob('*.json')))

    def test_production_rejects_unmerged_before_transport(self):
        with patch('guarded_social_sender.gate.git') as fetch, patch(
                'guarded_social_sender.gate.GitSource', side_effect=g.Blocked('social-before-site')):
            with self.assertRaises(g.Blocked):
                send('c'*40, self.mirrors['ar'], self.payload, self.transport, self.directory.name)
            fetch.assert_called_once_with('fetch', 'origin', 'main')
        self.transport.assert_not_called()

    def test_missing_french_never_calls_sender(self):
        del self.live[self.mirrors['fr']]
        with self.assertRaises(KeyError): self.send()
        self.transport.assert_not_called()

    def test_wrong_short_link_never_calls_sender(self):
        u = g.ORIGIN + '/s/story/'
        self.live[u] = self.live[u].replace(b'/posts/story/', b'/posts/draft/')
        with self.assertRaises(g.Blocked): self.send()
        self.transport.assert_not_called()

    def test_replay_blocked(self):
        self.send()
        self.payload['text'] += ' new caption'
        with self.assertRaisesRegex(g.Blocked, 'Existing delivery'): self.send()
        self.transport.assert_called_once()

    def test_timeout_not_retried(self):
        self.transport.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError): self.send()
        with self.assertRaises(g.Blocked): self.send()
        self.transport.assert_called_once()

    def test_pending_is_not_published(self):
        self.transport.return_value = {'status': 'PENDING', 'provider_id': 'fake'}
        self.assertEqual(self.send()['delivery']['status'], 'PENDING')

    def test_false_published_requires_reconciliation(self):
        self.transport.return_value = {'status': 'PUBLISHED'}
        with self.assertRaises(g.Blocked): self.send()
        with self.assertRaises(g.Blocked): self.send()
        self.transport.assert_called_once()

    def test_instagram_photo_blocked(self):
        self.payload['platform'] = 'instagram'
        with self.assertRaises(g.Blocked): self.send()
        self.transport.assert_not_called()


if __name__ == '__main__': unittest.main()
