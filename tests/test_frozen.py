import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from codex_provider_switcher.core import ConfigTransaction
from codex_provider_switcher.profiles import DEEPSEEK_PROFILE
from codex_provider_switcher.secrets import SecretStore


EXE = Path(__file__).resolve().parents[1] / "dist" / "CodexProviderSwitcher.exe"


class FrozenExecutableTests(unittest.TestCase):
    @unittest.skipUnless(EXE.exists(), "Build the executable to run frozen authentication integration")
    def test_auth_subcommand_reads_secret_from_isolated_codex_home(self):
        self.assertTrue(EXE.exists(), EXE)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            SecretStore(home / "provider-switcher" / "secrets.json").set("deepseek", "frozen-secret")
            env = dict(os.environ, CODEX_HOME=str(home))
            result = subprocess.run(
                [str(EXE), "auth", "--profile", "deepseek"],
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "frozen-secret")

    def test_isolated_apply_restore_preserves_unmanaged_config(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            original = 'model = "native-model"\n\n[mcp_servers.demo]\ncommand = "demo.exe"\n'
            (home / "config.toml").write_text(original, encoding="utf-8")
            manager = ConfigTransaction(home)
            manager.apply(DEEPSEEK_PROFILE, str(EXE))
            applied = (home / "config.toml").read_text(encoding="utf-8")
            self.assertIn('model_provider = "cps_deepseek"', applied)
            self.assertIn('[mcp_servers.demo]\ncommand = "demo.exe"', applied)
            manager.restore()
            restored = (home / "config.toml").read_text(encoding="utf-8")
            self.assertIn('model = "native-model"', restored)
            self.assertIn('[mcp_servers.demo]\ncommand = "demo.exe"', restored)
            self.assertNotIn("cps_deepseek", restored)


if __name__ == "__main__":
    unittest.main()
