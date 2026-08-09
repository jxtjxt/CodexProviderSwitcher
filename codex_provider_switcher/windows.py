from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    return Path(value) if value else Path.home() / ".codex"


def app_executable() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return Path(__file__).resolve().parents[1] / "CodexProviderSwitcher.pyw"


def restart_codex_desktop() -> tuple[bool, str]:
    if os.name != "nt":
        return False, "Desktop restart is supported only on Windows"
    creation_flags = 0x08000000
    subprocess.run(
        ["taskkill.exe", "/IM", "Codex.exe", "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        check=False,
    )
    result = subprocess.run(
        ["explorer.exe", "shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        check=False,
    )
    return result.returncode == 0, "Codex Desktop restart requested" if result.returncode == 0 else "Could not launch Codex Desktop"
