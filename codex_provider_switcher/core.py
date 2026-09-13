from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse


MANAGED_KEYS = (
    "model",
    "model_provider",
    "preferred_auth_method",
    "forced_login_method",
    "model_reasoning_effort",
    "model_catalog_json",
)


@dataclass
class ProviderProfile:
    profile_id: str
    name: str
    base_url: str
    model: str
    display_name: str
    context_window: int
    reasoning_levels: list[str] = field(default_factory=lambda: ["high"])

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", self.profile_id):
            raise ValueError("配置 ID 须为 1–48 位英文字母、数字、下划线或连字符")
        if not self.model.strip():
            raise ValueError("请填写模型 ID")
        if self.context_window <= 0:
            raise ValueError("上下文窗口必须为正整数")
        self.base_url = normalize_base_url(self.base_url)


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        raise ValueError("API 地址不得包含用户名或密码")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("API 地址必须为完整的 HTTP(S) URL")
    loopback = parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not loopback:
        raise ValueError("远程 API 地址必须使用 HTTPS")
    return value


def responses_url(base_url: str) -> str:
    base = normalize_base_url(base_url)
    return base if base.endswith("/responses") else f"{base}/responses"


def build_catalog(profile: ProviderProfile) -> dict:
    instructions = (
        "You are Codex, a coding agent. Work in the user's repository, follow "
        "the active configuration and project instructions, use tools carefully, "
        "and continue until the user's requested outcome is verified."
    )
    return {
        "models": [
            {
                "slug": profile.model,
                "display_name": profile.display_name or profile.model,
                "description": f"{profile.name} model via Responses API.",
                "prefer_websockets": False,
                "support_verbosity": False,
                "input_modalities": ["text"],
                "supports_image_detail_original": False,
                "truncation_policy": {"mode": "tokens", "limit": 10000},
                "supports_parallel_tool_calls": True,
                "apply_patch_tool_type": "freeform",
                "web_search_tool_type": "text",
                "supports_search_tool": True,
                "experimental_supported_tools": [],
                "multi_agent_version": "v2",
                "use_responses_lite": False,
                "tool_mode": None,
                "context_window": profile.context_window,
                "max_context_window": profile.context_window,
                "effective_context_window_percent": 95,
                "auto_compact_token_limit": None,
                "supports_reasoning_summaries": False,
                "default_reasoning_summary": "none",
                "include_skills_usage_instructions": False,
                "comp_hash": "3000",
                "default_reasoning_level": profile.reasoning_levels[0] if profile.reasoning_levels else "high",
                "supported_reasoning_levels": [
                    {"effort": level, "description": f"{level.capitalize()} reasoning effort"}
                    for level in profile.reasoning_levels
                ],
                "shell_type": "shell_command",
                "visibility": "list",
                "minimal_client_version": "0.144.0",
                "supported_in_api": True,
                "priority": 1,
                "availability_nux": None,
                "upgrade": None,
                "base_instructions": instructions,
                "model_messages": {
                    "instructions_template": instructions,
                    "instructions_variables": {
                        "personality_default": "",
                        "personality_friendly": "",
                        "personality_pragmatic": "",
                    },
                },
            }
        ]
    }


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _section_spans(lines: list[str]) -> list[tuple[int, int, str]]:
    headers: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$", line)
        if match:
            headers.append((index, match.group(1).strip().strip('"').strip("'")))
    spans: list[tuple[int, int, str]] = []
    for offset, (start, name) in enumerate(headers):
        end = headers[offset + 1][0] if offset + 1 < len(headers) else len(lines)
        spans.append((start, end, name))
    return spans


def _remove_sections(text: str, prefixes: tuple[str, ...]) -> str:
    lines = text.splitlines()
    remove: set[int] = set()
    for start, end, name in _section_spans(lines):
        if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
            remove.update(range(start, end))
    return "\n".join(line for i, line in enumerate(lines) if i not in remove).rstrip() + "\n"


def _replace_top_level(text: str, values: dict[str, str | None]) -> str:
    lines = text.splitlines()
    first_section = next((i for i, line in enumerate(lines) if re.match(r"^\s*\[", line)), len(lines))
    leading, rest = lines[:first_section], lines[first_section:]
    output: list[str] = []
    seen: set[str] = set()
    for line in leading:
        match = re.match(r"^(\s*)([A-Za-z0-9_-]+)\s*=", line)
        key = match.group(2) if match else ""
        if key in values:
            if key in seen:
                continue
            seen.add(key)
            if values[key] is not None:
                output.append(f"{key} = {values[key]}")
        else:
            output.append(line)
    missing = [key for key in MANAGED_KEYS if key in values and key not in seen and values[key] is not None]
    while output and output[-1] == "":
        output.pop()
    if missing:
        if output:
            output.append("")
        output.extend(f"{key} = {values[key]}" for key in missing)
    if rest:
        if output and output[-1] != "":
            output.append("")
        output.extend(rest)
    return "\n".join(output).rstrip() + "\n"


class ConfigTransaction:
    def __init__(self, codex_home: Path):
        self.codex_home = Path(codex_home)
        self.config_path = self.codex_home / "config.toml"
        self.data_dir = self.codex_home / "provider-switcher"
        self.catalog_dir = self.data_dir / "catalogs"
        self.state_path = self.data_dir / "state.json"

    def _read(self) -> str:
        return self.config_path.read_text(encoding="utf-8-sig") if self.config_path.exists() else ""

    def _write_atomic(self, path: Path, content: str | bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content.encode("utf-8") if isinstance(content, str) else content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _commit(self, changes: dict[Path, str], state: dict) -> None:
        previous_state = self._load_state()
        state_text = self.state_path.read_bytes() if self.state_path.exists() else None
        originals = {path: path.read_bytes() if path.exists() else None for path in changes}
        # Persist the native baseline and both provider IDs BEFORE any mutation.
        # After process termination, Restore can clean up either side of the switch.
        pending = dict(state)
        pending["owned_provider_ids"] = sorted(set(
            (previous_state or {}).get("owned_provider_ids", []) + state.get("owned_provider_ids", [])
        ))
        pending["active_profile"] = (previous_state or {}).get("active_profile")
        pending["pending"] = True
        self._write_atomic(self.state_path, json.dumps(pending, ensure_ascii=False, indent=2) + "\n")
        written = []
        try:
            for path, content in changes.items():
                self._write_atomic(path, content)
                written.append(path)
            self._write_atomic(self.state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        except Exception as exc:
            try:
                for path in reversed(written):
                    if originals[path] is None:
                        path.unlink(missing_ok=True)
                    else:
                        self._write_atomic(path, originals[path])
                if state_text is None:
                    self.state_path.unlink(missing_ok=True)
                else:
                    self._write_atomic(self.state_path, state_text)
            except Exception as rollback_error:
                raise OSError("写入失败且自动回滚未完成；恢复记录已保留。请解决文件写入问题后点击“恢复原始配置”。") from rollback_error
            raise OSError("写入失败，已回滚到操作前的配置。") from exc

    def _load_state(self) -> dict | None:
        if not self.state_path.exists():
            return None
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _managed_values(self, text: str) -> dict[str, str | None]:
        lines = text.splitlines()
        first_section = next((i for i, line in enumerate(lines) if re.match(r"^\s*\[", line)), len(lines))
        found: dict[str, str | None] = {key: None for key in MANAGED_KEYS}
        for line in lines[:first_section]:
            match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.+?)\s*$", line)
            if match and match.group(1) in found:
                found[match.group(1)] = match.group(2)
        return found

    def apply(self, profile: ProviderProfile, auth_executable: str) -> None:
        current = self._read()
        state = self._load_state()
        if state is None:
            state = {"version": 1, "baseline": self._managed_values(current), "owned_provider_ids": []}

        owned = tuple(f"model_providers.{provider_id}" for provider_id in state.get("owned_provider_ids", []))
        cleaned = _remove_sections(current, owned) if owned else current
        catalog_path = self.catalog_dir / f"{profile.profile_id}.json"
        catalog = json.dumps(build_catalog(profile), ensure_ascii=False, indent=2) + "\n"

        provider_id = f"cps_{profile.profile_id}"
        values = {
            "model": _toml_string(profile.model),
            "model_provider": _toml_string(provider_id),
            "preferred_auth_method": _toml_string("apikey"),
            "forced_login_method": _toml_string("api"),
            "model_reasoning_effort": _toml_string(profile.reasoning_levels[0] if profile.reasoning_levels else "high"),
            "model_catalog_json": _toml_string(str(catalog_path.resolve()).replace("\\", "/")),
        }
        next_text = _replace_top_level(cleaned, values).rstrip() + "\n\n"
        next_text += (
            f"[model_providers.{provider_id}]\n"
            f"name = {_toml_string(profile.name)}\n"
            f"base_url = {_toml_string(profile.base_url)}\n"
            'wire_api = "responses"\n'
            'request_max_retries = 3\n'
            'stream_max_retries = 3\n'
            'stream_idle_timeout_ms = 300000\n\n'
            f"[model_providers.{provider_id}.auth]\n"
            f"command = {_toml_string(str(Path(auth_executable).resolve()))}\n"
            f"args = [\"auth\", \"--profile\", {_toml_string(profile.profile_id)}]\n"
            'timeout_ms = 5000\n'
            'refresh_interval_ms = 0\n'
        )
        state["owned_provider_ids"] = [provider_id]
        state["active_profile"] = asdict(profile)
        state.pop("pending", None)
        self._commit({catalog_path: catalog, self.config_path: next_text}, state)

    def restore(self) -> None:
        state = self._load_state()
        if not state:
            return
        current = self._read()
        prefixes = tuple(f"model_providers.{provider_id}" for provider_id in state.get("owned_provider_ids", []))
        cleaned = _remove_sections(current, prefixes)
        restored = _replace_top_level(cleaned, state.get("baseline", {}))
        state["active_profile"] = None
        state["owned_provider_ids"] = []
        state.pop("pending", None)
        self._commit({self.config_path: restored}, state)
