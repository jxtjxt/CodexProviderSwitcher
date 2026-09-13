import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
        with patch("codex_provider_switcher.probe.build_opener") as build:
            build.return_value.open.return_value = FakeResponse(200, payload)
            result = ProviderProbe("https://api.example/v1", "token").test_responses("model-x")
        self.assertTrue(result.ok)
        self.assertEqual(result.protocol, "responses")

    def test_cross_host_redirect_is_rejected(self):
        probe = ProviderProbe("https://api.example/v1", "token")
        result = probe.validate_redirect("https://evil.example/v1/responses")
        self.assertFalse(result.ok)
        self.assertIn("重定向", result.message)

    def test_models_probe_extracts_ids(self):
        payload = json.dumps({"data": [{"id": "a"}, {"id": "b"}]})
        with patch("codex_provider_switcher.probe.build_opener") as build:
            build.return_value.open.return_value = FakeResponse(200, payload)
            result = ProviderProbe("https://api.example/v1", "token").list_models()
        self.assertTrue(result.ok)
        self.assertEqual(result.models, ["a", "b"])

    def test_error_message_does_not_include_key(self):
        secret = "top-secret-key"
        with patch("codex_provider_switcher.probe.build_opener") as build:
            build.return_value.open.side_effect = OSError(f"failure {secret}")
            result = ProviderProbe("https://api.example/v1", secret).test_responses("model")
        self.assertNotIn(secret, result.message)


@contextmanager
def server(routes):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            received.append((self.path, self.command, self.headers.get("Authorization"), body))
            status, location = routes.get(self.path, (200, None))
            self.send_response(status)
            if location:
                self.send_header("Location", location)
            self.end_headers()
            self.wfile.write(b'{"status":"completed","data":[{"id":"test"}]}')

        do_POST = do_GET

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", received
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


class RedirectIntegrationTests(unittest.TestCase):
    def test_cross_origin_never_receives_request_or_key(self):
        with server({}) as (target, leaked):
            for status in (301, 302, 303, 307, 308):
                with self.subTest(status=status), server({"/models": (status, target + "/models")}) as (base, requests):
                    result = ProviderProbe(base, "test-only-placeholder").list_models()
                    self.assertFalse(result.ok)
                    self.assertIn("跨源", result.message)
                    self.assertEqual(len(requests), 1)
            self.assertEqual(leaked, [])

    def test_later_cross_origin_hop_is_also_blocked(self):
        with server({}) as (target, leaked), server({"/models": (302, "/next"), "/next": (302, target)}) as (base, requests):
            self.assertFalse(ProviderProbe(base, "test-only-placeholder").list_models().ok)
            self.assertEqual(len(requests), 2)
            self.assertEqual(leaked, [])

    def test_same_origin_get_chain_succeeds(self):
        with server({"/models": (302, "/next"), "/next": (308, "/final")}) as (base, requests):
            self.assertTrue(ProviderProbe(base, "test-only-placeholder").list_models().ok)
            self.assertEqual(len(requests), 3)

    def test_post_307_and_308_preserve_method_and_body(self):
        for status in (307, 308):
            with self.subTest(status=status), server({"/responses": (status, "/final")}) as (base, requests):
                self.assertTrue(ProviderProbe(base, "test-only-placeholder").test_responses("test").ok)
                self.assertEqual(requests[0][1:], requests[1][1:])
                self.assertEqual(requests[1][1], "POST")

    def test_post_302_does_not_silently_become_get(self):
        with server({"/responses": (302, "/final")}) as (base, requests):
            self.assertFalse(ProviderProbe(base, "test-only-placeholder").test_responses("test").ok)
            self.assertEqual(len(requests), 1)

    def test_redirect_loop_is_bounded(self):
        with server({"/models": (302, "/models")}) as (base, requests):
            result = ProviderProbe(base, "test-only-placeholder").list_models()
            self.assertFalse(result.ok)
            self.assertEqual(len(requests), 6)

    def test_origin_validation_checks_scheme_port_and_credentials(self):
        probe = ProviderProbe("https://api.example", "test-only-placeholder")
        self.assertTrue(probe.validate_redirect("https://api.example:443/models").ok)
        for target in ("http://api.example/models", "https://api.example:444/models",
                       "https://user@api.example/models", "https://api.example:bad/models"):
            self.assertFalse(probe.validate_redirect(target).ok)


if __name__ == "__main__":
    unittest.main()
