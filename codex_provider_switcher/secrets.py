from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise OSError("DPAPI is available only on Windows")
    source, source_buffer = _blob(data)
    destination = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(
        ctypes.byref(source), "CodexProviderSwitcher", None, None, None, 0, ctypes.byref(destination)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel32.LocalFree(destination.pbData)
        del source_buffer


def _unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise OSError("DPAPI is available only on Windows")
    source, source_buffer = _blob(data)
    destination = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(destination)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel32.LocalFree(destination.pbData)
        del source_buffer


class SecretStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _save(self, values: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    def set(self, profile_id: str, secret: str) -> None:
        if not secret:
            raise ValueError("API key is required")
        values = self._load()
        values[profile_id] = base64.b64encode(_protect(secret.encode("utf-8"))).decode("ascii")
        self._save(values)

    def get(self, profile_id: str) -> str | None:
        encoded = self._load().get(profile_id)
        if not encoded:
            return None
        return _unprotect(base64.b64decode(encoded)).decode("utf-8")

    def delete(self, profile_id: str) -> None:
        values = self._load()
        values.pop(profile_id, None)
        self._save(values)
