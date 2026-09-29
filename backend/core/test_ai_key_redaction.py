from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, override_settings

from core import ai_utils

FAKE_KEY = 'AIzaFAKE-test-key-0000000000000000000'


@override_settings(GEMINI_API_KEY=FAKE_KEY, GEMINI_MODEL='gemini-test')
class GeminiKeyNotInUrlTests(SimpleTestCase):
    """Regression: the Gemini key was sent as ?key= and leaked into logs on any HTTP error."""

    def test_key_sent_in_header_not_url(self):
        resp = MagicMock()
        resp.json.return_value = {'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]}
        with patch.object(ai_utils._http, 'post', return_value=resp) as post:
            ai_utils._call_gemini([{'role': 'user', 'content': 'hi'}])
        url = post.call_args.args[0]
        self.assertNotIn(FAKE_KEY, url)
        self.assertNotIn('key=', url)
        self.assertEqual(post.call_args.kwargs['headers']['x-goog-api-key'], FAKE_KEY)

    def test_http_error_log_does_not_contain_key(self):
        def fail(url, **kwargs):
            raise requests.HTTPError(f'404 Client Error: Not Found for url: {url}')

        with patch.object(ai_utils._http, 'post', side_effect=fail):
            with self.assertLogs('core.ai_utils', level='WARNING') as logs:
                self.assertIsNone(ai_utils._call_gemini([{'role': 'user', 'content': 'hi'}]))
        self.assertNotIn(FAKE_KEY, '\n'.join(logs.output))
