import tempfile
import unittest
from pathlib import Path

from codex_provider_switcher.secrets import SecretStore


class SecretStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "secrets.json"
        self.store = SecretStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_round_trip_uses_current_user_encryption(self):
        self.store.set("deepseek", "sk-test-value")
        self.assertEqual(self.store.get("deepseek"), "sk-test-value")

    def test_plaintext_secret_is_not_written_to_disk(self):
        self.store.set("custom", "secret-never-plaintext")
        self.assertNotIn("secret-never-plaintext", self.path.read_text(encoding="utf-8"))

    def test_delete_removes_secret(self):
        self.store.set("custom", "temporary-secret")
        self.store.delete("custom")
        self.assertIsNone(self.store.get("custom"))

    def test_missing_secret_returns_none(self):
        self.assertIsNone(self.store.get("missing"))


if __name__ == "__main__":
    unittest.main()
