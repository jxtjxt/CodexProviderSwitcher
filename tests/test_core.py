import json
import tempfile
import unittest
from pathlib import Path

from codex_provider_switcher.core import (
    ConfigTransaction,
    ProviderProfile,
    build_catalog,
    normalize_base_url,
    responses_url,
)


BASE_CONFIG = '''approval_policy = "never"
sandbox_mode = "danger-full-access"
model = "gpt-5.6-sol"
model_reasoning_effort = "medium"

[mcp_servers.node_repl]
command = "node_repl.exe"

[features]
memories = false
'''


class UrlTests(unittest.TestCase):
    def test_normalizes_https_base_without_trailing_slash(self):
        self.assertEqual(normalize_base_url("https://api.example.com/v1/"), "https://api.example.com/v1")
        self.assertEqual(responses_url("https://api.example.com/v1/"), "https://api.example.com/v1/responses")

    def test_rejects_non_loopback_http(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            normalize_base_url("http://api.example.com/v1")

    def test_allows_loopback_http(self):
        self.assertEqual(normalize_base_url("http://127.0.0.1:8080/v1"), "http://127.0.0.1:8080/v1")

    def test_rejects_credentials_in_url(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            normalize_base_url("https://user:pass@example.com/v1")


class CatalogTests(unittest.TestCase):
    def test_catalog_uses_profile_capabilities(self):
        profile = ProviderProfile(
            profile_id="lab",
            name="Lab API",
            base_url="https://api.example.com/v1",
            model="lab-model",
            display_name="Lab Model",
            context_window=200000,
            reasoning_levels=["low", "high"],
        )
        catalog = build_catalog(profile)
        model = catalog["models"][0]
        self.assertEqual(model["slug"], "lab-model")
        self.assertEqual(model["context_window"], 200000)
        self.assertEqual([x["effort"] for x in model["supported_reasoning_levels"]], ["low", "high"])

    def test_catalog_contains_codex_required_instruction_fields(self):
        profile = ProviderProfile(
            profile_id="lab",
            name="Lab API",
            base_url="https://api.example.com/v1",
            model="lab-model",
            display_name="Lab Model",
            context_window=200000,
            reasoning_levels=["high"],
        )
        model = build_catalog(profile)["models"][0]
        self.assertIsInstance(model["base_instructions"], str)
        self.assertTrue(model["base_instructions"])
        self.assertIn("instructions_template", model["model_messages"])
        self.assertIs(model["supports_reasoning_summaries"], False)
        self.assertEqual(model["default_reasoning_summary"], "none")
        self.assertEqual(model["truncation_policy"], {"mode": "tokens", "limit": 10000})
        self.assertEqual(model["experimental_supported_tools"], [])
        self.assertIs(model["supports_search_tool"], True)


class ConfigTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = self.root / "config.toml"
        self.config.write_text(BASE_CONFIG, encoding="utf-8")
        self.manager = ConfigTransaction(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def profile(self):
        return ProviderProfile(
            profile_id="deepseek",
            name="DeepSeek",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            display_name="DeepSeek V4 Flash",
            context_window=1048576,
            reasoning_levels=["low", "high", "max"],
        )

    def test_apply_preserves_unmanaged_sections(self):
        self.manager.apply(self.profile(), auth_executable=r"C:\Tools\CodexProviderSwitcher.exe")
        text = self.config.read_text(encoding="utf-8")
        self.assertIn('[mcp_servers.node_repl]\ncommand = "node_repl.exe"', text)
        self.assertIn('[features]\nmemories = false', text)
        self.assertIn('model = "deepseek-v4-flash"', text)
        self.assertIn('[model_providers.cps_deepseek]', text)
        self.assertIn('[model_providers.cps_deepseek.auth]', text)
        self.assertNotIn('experimental_bearer_token', text)

    def test_restore_reinstates_managed_fields_but_keeps_later_unmanaged_change(self):
        self.manager.apply(self.profile(), auth_executable=r"C:\Tools\CodexProviderSwitcher.exe")
        with self.config.open("a", encoding="utf-8") as handle:
            handle.write('\n[custom_after_switch]\nvalue = true\n')
        self.manager.restore()
        text = self.config.read_text(encoding="utf-8")
        self.assertIn('model = "gpt-5.6-sol"', text)
        self.assertIn('model_reasoning_effort = "medium"', text)
        self.assertNotIn('model_provider = "cps_deepseek"', text)
        self.assertNotIn('[model_providers.cps_deepseek]', text)
        self.assertIn('[custom_after_switch]\nvalue = true', text)

    def test_apply_writes_absolute_catalog_and_valid_json(self):
        self.manager.apply(self.profile(), auth_executable=r"C:\Tools\CodexProviderSwitcher.exe")
        catalog_path = self.root / "provider-switcher" / "catalogs" / "deepseek.json"
        parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(parsed["models"][0]["slug"], "deepseek-v4-flash")
        config_text = self.config.read_text(encoding="utf-8")
        self.assertIn(str(catalog_path).replace("\\", "/"), config_text)

    def test_reapply_switches_owned_provider_without_duplicate_sections(self):
        self.manager.apply(self.profile(), auth_executable=r"C:\Tools\CodexProviderSwitcher.exe")
        second = ProviderProfile(
            profile_id="custom",
            name="Custom",
            base_url="https://gateway.example/v1",
            model="model-x",
            display_name="Model X",
            context_window=128000,
            reasoning_levels=["high"],
        )
        self.manager.apply(second, auth_executable=r"C:\Tools\CodexProviderSwitcher.exe")
        text = self.config.read_text(encoding="utf-8")
        self.assertEqual(text.count("model_provider ="), 1)
        self.assertNotIn("[model_providers.cps_deepseek]", text)
        self.assertEqual(text.count("[model_providers.cps_custom]"), 1)


if __name__ == "__main__":
    unittest.main()
