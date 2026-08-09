import json
import unittest
from unittest.mock import patch

from codex_provider_switcher.probe import ProbeResult, ProviderProbe


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body.encode("utf-8")
        self.headers = headers or {"Content-Type": "application/json"}

    def read(self, amount=-1):
        return self._body if amount == -1 else self._body[:amount]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ProviderProbeTests(unittest.TestCase):
    def test_basic_responses_probe_accepts_completed_output(self):
        payload = json.dumps({
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "OK"}]}],
        })
        with patch("codex_provider_switcher.probe.urlopen", return_value=FakeResponse(200, payload)):
            result = ProviderProbe("https://api.example/v1", "token").test_responses("model-x")
        self.assertTrue(result.ok)
        self.assertEqual(result.protocol, "responses")

    def test_cross_host_redirect_is_rejected(self):
        probe = ProviderProbe("https://api.example/v1", "token")
        with patch("codex_provider_switcher.probe.urlopen", side_effect=AssertionError("must not call default redirect opener")):
            result = probe.validate_redirect("https://evil.example/v1/responses")
        self.assertFalse(result.ok)
        self.assertIn("redirect", result.message.lower())

    def test_models_probe_extracts_ids(self):
        payload = json.dumps({"data": [{"id": "a"}, {"id": "b"}]})
        with patch("codex_provider_switcher.probe.urlopen", return_value=FakeResponse(200, payload)):
            result = ProviderProbe("https://api.example/v1", "token").list_models()
        self.assertTrue(result.ok)
        self.assertEqual(result.models, ["a", "b"])

    def test_error_message_does_not_include_key(self):
        secret = "top-secret-key"
        with patch("codex_provider_switcher.probe.urlopen", side_effect=OSError(f"failure {secret}")):
            result = ProviderProbe("https://api.example/v1", secret).test_responses("model")
        self.assertNotIn(secret, result.message)


if __name__ == "__main__":
    unittest.main()
