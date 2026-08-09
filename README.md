# Codex Provider Switcher

Windows GUI utility for switching Codex Desktop between:

- the original/native Codex configuration;
- DeepSeek V4 Flash through DeepSeek's native Responses API;
- any third-party provider that implements a Codex-compatible Responses API.

## Security model

- API keys are encrypted with Windows DPAPI for the current user.
- Keys are supplied to Codex through command-backed authentication and are not written to `config.toml`.
- The utility only manages provider/model/auth/catalog fields and its own `model_providers.cps_*` sections.
- Existing MCP, Computer Use, plugins, project trust, sandbox, hooks, and feature settings are preserved.
- Restore removes switcher-owned provider sections and restores the provider fields captured before the first switch.
- Remote providers must use HTTPS. Plain HTTP is accepted only for loopback addresses.
- Cross-origin redirects are rejected so an API key is not forwarded to another host.

## Current scope

Supported:

- DeepSeek V4 Flash;
- custom Responses-compatible APIs;
- `/models` discovery;
- minimal Responses compatibility probe;
- DPAPI-encrypted API keys;
- atomic config writes and field-level restore;
- Codex Desktop restart request.

Not supported in this MVP:

- Chat Completions to Responses translation;
- account pooling or quota rotation;
- importing Claude, Cursor, Grok, or ChatGPT credentials;
- cross-provider conversation migration;
- a persistent local proxy.

## Build

Requirements: Windows and Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install pyinstaller==6.16.0
.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name CodexProviderSwitcher CodexProviderSwitcher.pyw
```

Output:

```text
dist\CodexProviderSwitcher.exe
```

## Test

```powershell
python -m unittest discover -s tests -v
python verify_isolated.py
```

`verify_isolated.py` uses a disposable `CODEX_HOME`; it does not modify the live `~/.codex` directory.

## Usage

1. Run `CodexProviderSwitcher.exe`.
2. Select the built-in DeepSeek profile or create a custom provider profile.
3. Enter the API key and save the profile.
4. Run the Responses probe before applying. The probe sends one small billable request.
5. Apply the profile and start a new Codex conversation after Desktop restarts.
6. Use **Restore original / Native** to return to the provider state captured before the first switch.

Do not move or delete the EXE while a third-party profile is active: Codex invokes the same EXE to retrieve the DPAPI-protected API key.

## Compatibility validated locally

- Windows 10 x64
- Codex Desktop `26.730.8199.0`
- Codex CLI `0.144.3`
- Python `3.11.15`

The model catalog, DeepSeek profile, and restore path were parsed successfully by the real Codex CLI in an isolated `CODEX_HOME`.

## License

MIT. See `LICENSE`.
