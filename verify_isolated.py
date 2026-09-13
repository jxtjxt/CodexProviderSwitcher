from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from codex_provider_switcher.core import ConfigTransaction
from codex_provider_switcher.profiles import DEEPSEEK_PROFILE
from codex_provider_switcher.windows import app_executable, codex_home


def run_codex(codex_home: Path, label: str) -> dict:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(codex_home)
    result = subprocess.run(
        ["codex", "features", "list"],
        capture_output=True,
        text=True,
        timeout=45,
        env=env,
    )
    return {
        "label": label,
        "returncode": result.returncode,
        "stdout_first_lines": result.stdout.splitlines()[:5],
        "stderr_first_lines": result.stderr.splitlines()[:8],
    }


def main() -> int:
    live_config = codex_home() / "config.toml"
    def live_digest():
        return hashlib.sha256(live_config.read_bytes()).hexdigest() if live_config.exists() else None
    before = live_digest()
    with tempfile.TemporaryDirectory(prefix="hermes-verify-cps-") as directory:
        home = Path(directory)
        config_path = home / "config.toml"
        config_path.write_text(
            'model = "gpt-5.6-sol"\n'
            'model_reasoning_effort = "medium"\n\n'
            '[mcp_servers.keep]\n'
            'command = "keep.exe"\n\n'
            '[features]\n'
            'memories = false\n',
            encoding="utf-8",
        )
        manager = ConfigTransaction(home)
        reports = [run_codex(home, "native")]

        manager.apply(
            DEEPSEEK_PROFILE,
            str(app_executable()),
        )
        applied = config_path.read_text(encoding="utf-8")
        reports.append(run_codex(home, "deepseek"))

        manager.restore()
        restored = config_path.read_text(encoding="utf-8")
        reports.append(run_codex(home, "restored"))

        assertions = {
            "native_parse_ok": reports[0]["returncode"] == 0,
            "deepseek_parse_ok": reports[1]["returncode"] == 0,
            "restored_parse_ok": reports[2]["returncode"] == 0,
            "deepseek_provider_written": 'model_provider = "cps_deepseek"' in applied,
            "deepseek_auth_command_written": "[model_providers.cps_deepseek.auth]" in applied,
            "unmanaged_mcp_preserved_during_apply": '[mcp_servers.keep]\ncommand = "keep.exe"' in applied,
            "original_model_restored": 'model = "gpt-5.6-sol"' in restored,
            "unmanaged_mcp_preserved_after_restore": '[mcp_servers.keep]\ncommand = "keep.exe"' in restored,
            "managed_provider_removed": "cps_deepseek" not in restored,
            "temporary_home_isolated": home.resolve() != codex_home().resolve(),
            "live_config_untouched": before == live_digest(),
        }
        print(json.dumps({"reports": reports, "assertions": assertions}, ensure_ascii=False, indent=2))
        return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
