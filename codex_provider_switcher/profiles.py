from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from .core import ProviderProfile


DEEPSEEK_PROFILE = ProviderProfile(
    profile_id="deepseek",
    name="DeepSeek 官方",
    base_url="https://api.deepseek.com",
    model="deepseek-flash",
    display_name="deepseek-flash",
    context_window=1048576,
    reasoning_levels=["low", "high", "max"],
)


class ProfileRepository:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _load_custom(self) -> list[ProviderProfile]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        entries = raw.get("profiles", []) if isinstance(raw, dict) else []
        return [ProviderProfile(**entry) for entry in entries if entry.get("profile_id") != "deepseek"]

    def list(self) -> list[ProviderProfile]:
        return [DEEPSEEK_PROFILE, *self._load_custom()]

    def save(self, profile: ProviderProfile) -> None:
        if profile.profile_id == "deepseek":
            raise ValueError("不能覆盖内置的 DeepSeek 配置")
        profiles = {entry.profile_id: entry for entry in self._load_custom()}
        profiles[profile.profile_id] = profile
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        payload = {"profiles": [asdict(item) for item in sorted(profiles.values(), key=lambda item: item.profile_id)]}
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    def delete(self, profile_id: str) -> None:
        if profile_id == "deepseek":
            raise ValueError("不能删除内置的 DeepSeek 配置")
        remaining = [entry for entry in self._load_custom() if entry.profile_id != profile_id]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"profiles": [asdict(item) for item in remaining]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
