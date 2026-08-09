import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_provider_switcher.cli import auth_command
from codex_provider_switcher.secrets import SecretStore


class AuthCommandTests(unittest.TestCase):
    def test_auth_prints_dpapi_secret_only(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            SecretStore(home / "provider-switcher" / "secrets.json").set("lab", "secret-token")
            stdout = io.StringIO()
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}), contextlib.redirect_stdout(stdout):
                code = auth_command("lab")
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue(), "secret-token")

    def test_missing_secret_fails_without_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(os.environ, {"CODEX_HOME": directory}), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = auth_command("missing")
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("No API key", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
