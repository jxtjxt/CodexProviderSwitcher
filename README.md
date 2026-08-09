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

## Detailed usage

### Before you start

- You do not need to close Codex Desktop merely to open the switcher, edit a profile, save an API key, list models, or run an API test.
- Before clicking **Apply to Codex** or **Restore original / Native**, finish the current Codex task and save any open work. The switcher may force-close and restart Codex Desktop, which interrupts an active response, command, or file edit.
- For the safest first use, close Codex Desktop manually after the provider test passes and before applying the profile.
- Switching providers does not migrate an active conversation. Always start a new Codex conversation after applying or restoring a provider.

### First-time DeepSeek V4 Flash setup

1. Run `CodexProviderSwitcher.exe`.

2. In the **Profile** drop-down, select `deepseek`. The form should contain values similar to:

   ```text
   Profile ID: deepseek
   Display name: DeepSeek Official
   Base URL: https://api.deepseek.com
   Model ID: deepseek-v4-flash
   Model display name: DeepSeek V4 Flash
   Context window: 1048576
   Reasoning levels: high,low,max
   ```

3. Paste the DeepSeek API key into **API key**. The field is masked. When saved, the key is encrypted with Windows DPAPI for the current Windows user; it is not written in plaintext to Codex `config.toml`.

4. Click **Save profile**. A successful save produces a Diagnostics message similar to:

   ```text
   Saved profile deepseek; key is DPAPI-encrypted for the current Windows user
   ```

5. Click **Test Responses**. The switcher warns that this sends a small request that may consume paid tokens. Confirm only if that is acceptable.

   The probe calls:

   ```text
   https://api.deepseek.com/responses
   ```

   A successful result looks similar to:

   ```text
   Responses compatible: HTTP 200; response status=completed
   ```

   If the test fails, do not apply the profile. Check the key, model ID, endpoint, account balance, and the exact Diagnostics error first.

6. Finish any active Codex task. Preferably exit Codex Desktop manually.

7. Click **Apply to Codex**. The switcher will:

   - preserve non-managed Codex settings such as MCP, Computer Use, plugins, project trust, sandbox, hooks, and features;
   - create a profile-specific model catalog;
   - set the required provider, model, authentication, and catalog fields;
   - request a Codex Desktop restart.

   A successful apply message looks similar to:

   ```text
   Applied DeepSeek Official/deepseek-v4-flash.
   Codex Desktop restart requested.
   Start a new Codex conversation.
   ```

8. After Codex Desktop restarts, create a new conversation. Do not continue the conversation that was active under the previous provider. The Desktop model label may be generic for custom providers; a successful API response and provider-side usage record are stronger evidence than the model's self-reported identity.

### Add a custom Responses API provider

1. Click **New custom**.

2. Complete the form. Example values for a generic provider:

   ```text
   Profile ID: example-provider
   Display name: Example Provider
   Base URL: https://api.example.com/v1
   API key: your provider API key
   Model ID: provider-model-id
   Model display name: Provider Model
   Context window: the provider's documented value
   Reasoning levels: high
   ```

   Field rules:

   - **Profile ID** must contain only letters, numbers, underscores, and hyphens.
   - **Base URL** should normally end at the API root such as `/v1`; do not append `/responses`.
   - Remote providers must use HTTPS. HTTP is accepted only for `localhost` or `127.0.0.1`.
   - **Model ID** must match the provider's actual API model identifier, not merely a marketing display name.
   - Use the provider's documented context window. Do not assume that every model supports one million tokens.
   - If reasoning-level behavior has not been verified, begin with `high` only.

3. Click **Save profile**.

4. Click **List models** to call `GET <Base URL>/models`. Confirm that the desired model ID appears. Some compatible providers do not expose `/models`; in that case, verify the model ID in the provider's documentation.

5. Click **Test Responses**. Apply the profile only after a successful Responses result.

   If the endpoint returns `404`, rejects the Responses request schema, or only supports Chat Completions, do not apply it. This MVP does not translate Chat Completions to Responses.

6. Finish the current Codex task, apply the profile, allow Codex Desktop to restart, and then start a new conversation.

### Restore native Codex

1. Finish any task running through the third-party provider.
2. Open the same `CodexProviderSwitcher.exe` used to apply the provider.
3. Click **Restore original / Native** and confirm.
4. Wait for Codex Desktop to restart, or restart it manually if the automatic restart does not occur.
5. Start a new conversation or reopen a native Codex conversation.

Restore removes switcher-owned `model_providers.cps_*` sections and restores the managed provider/model/auth/catalog fields captured before the first switch. It does not alter the native Codex login file, conversation database, MCP servers, plugins, Computer Use, or unrelated Codex settings.

### Important safety notes

- Do not move, rename, or delete the EXE while a third-party profile is active. Codex invokes that exact EXE path to retrieve the DPAPI-protected API key. If the file is unavailable, third-party authentication fails; the native account and conversations are not deleted.
- Keep the EXE in a trusted local folder. The distributed binary is not Authenticode-signed, so Windows SmartScreen may warn on first launch.
- Do not continue the same conversation across providers. Conversation visibility may differ between native account authentication and API-key providers; this does not necessarily mean the native conversations were deleted.
- After a major Codex Desktop or CLI upgrade, rerun the provider test before applying because custom-provider and model-catalog formats may change.
- A provider test can incur a small API charge. **List models** is normally read-only, but provider billing policies vary.

### Troubleshooting

| Symptom | Action |
|---|---|
| Responses test returns `401` or `403` | Verify the API key, account permissions, and provider access to the selected model. |
| Responses test returns `404` | Check the Base URL and confirm that the provider implements `/responses`; Chat-only providers are unsupported in this MVP. |
| Apply succeeds but Codex does not restart | Exit Codex Desktop completely and open it manually, then start a new conversation. |
| Third-party mode stops authenticating after the EXE was moved | Put the EXE back at its original path, then restore native mode or reapply the profile from the new location. |
| Native conversations are not visible in third-party mode | Restore native mode and restart Codex; do not assume the conversations were deleted. |
| Provider test fails | Do not click Apply. Copy the Diagnostics error for investigation, but never include the API key. |

## Compatibility validated locally

- Windows 10 x64
- Codex Desktop `26.730.8199.0`
- Codex CLI `0.144.3`
- Python `3.11.15`

The model catalog, DeepSeek profile, and restore path were parsed successfully by the real Codex CLI in an isolated `CODEX_HOME`.

## License

MIT. See `LICENSE`.
