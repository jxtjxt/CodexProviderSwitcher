# Codex Provider Switcher

[简体中文](#简体中文) | [English](#english)

## 简体中文

### 中文界面与安全更新

- 主窗口、字段、按钮、提示框和运行日志已改为简体中文；模型 ID、API 协议名称和推理级别值保持原样。
- “应用到 Codex”和“恢复原始配置”会先提示强制关闭与重启的影响，默认取消；取消不会修改配置或重启程序。
- API 探测从第一个请求起禁止自动重定向，每一跳校验协议、主机和端口，最多跟随 5 次同源重定向。Responses POST 仅接受保持方法与请求体的 307/308。
- 应用或恢复前先保存恢复记录。普通写入失败会回滚配置、模型目录和状态文件；若程序意外退出或回滚失败，请解决文件写入问题后点击“恢复原始配置”。
- “Responses 基础测试通过”仅表示最小请求通过，不代表流式输出、工具调用等所有能力均已验证。
- 单元测试使用临时目录和本机 HTTP 服务，不发送真实 Provider 请求。未构建 EXE 时跳过打包认证测试；构建后再次运行测试以验证 EXE 的命令认证。

Codex Provider Switcher 是一个 Windows 图形界面工具，用于在以下模式之间切换 Codex Desktop：

- 原始/Native Codex 配置；
- 通过 DeepSeek 原生 Responses API 使用 deepseek-flash；
- 任意实现 Codex 兼容 Responses API 的第三方 Provider。

### 安全设计

- API key 使用 Windows DPAPI 按当前 Windows 用户加密。
- Codex 通过 command-backed authentication 获取 key；key 不会以明文写入 `config.toml`。
- 工具只管理 provider/model/auth/catalog 字段和自己创建的 `model_providers.cps_*` 配置段。
- 原有 MCP、Computer Use、插件、项目 trust、sandbox、hooks 和 features 设置均保留。
- 恢复 Native 时，删除本工具创建的 Provider 段，并恢复第一次切换前记录的 Provider 字段。
- 远程 Provider 必须使用 HTTPS；只有本机回环地址允许 HTTP。
- 拒绝跨域重定向，防止 API key 被转发到其他主机。

### 当前功能范围

已支持：

- deepseek-flash；
- 自定义 Responses-compatible API；
- `/models` 模型发现；
- 最小 Responses 兼容性测试；
- DPAPI 加密 API key；
- 原子配置写入和字段级恢复；
- 请求重启 Codex Desktop。

当前 MVP 不支持：

- Chat Completions 到 Responses 的协议转换；
- 账号池或额度轮换；
- 导入 Claude、Cursor、Grok 或 ChatGPT 凭据；
- 跨 Provider 迁移对话；
- 常驻本地代理。

### 构建

要求：Windows 和 Python 3.11 或更高版本。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install pyinstaller==6.16.0
.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name CodexProviderSwitcher CodexProviderSwitcher.pyw
```

输出文件：

```text
dist\CodexProviderSwitcher.exe
```

### 测试

```powershell
python -m unittest discover -s tests -v
python verify_isolated.py
```

`verify_isolated.py` 使用一次性的 `CODEX_HOME`，不会修改真实的 `~/.codex` 目录。

### 详细操作说明

#### 开始前

- 仅打开切换器、编辑 Profile、保存 API key、列出模型或测试 API 时，不需要关闭 Codex Desktop。
- 点击 **应用到 Codex** 或 **恢复原始配置** 前，应先等待当前 Codex 任务结束并保存未完成的工作。切换器可能强制关闭并重启 Codex Desktop，正在生成的回答、命令或文件编辑会被中断。
- 第一次使用时，最稳妥的做法是先通过 Provider 测试，再手动关闭 Codex Desktop，然后应用配置。
- Provider 切换不会迁移当前对话。每次应用或恢复 Provider 后，都应新建 Codex 对话。

#### 第一次配置 deepseek-flash

1. 运行 `CodexProviderSwitcher.exe`。

2. 在 **Profile** 下拉框中选择 `deepseek`。表单应显示类似内容：

   ```text
   配置 ID: deepseek
   服务商名称: DeepSeek 官方
   Base URL: https://api.deepseek.com
   模型 ID: deepseek-flash
   模型显示名称: deepseek-flash
   上下文窗口: 1048576
   推理级别: low, high, max
   ```

3. 在 **API key** 输入框中粘贴 DeepSeek API key。输入内容会被遮蔽。保存后，key 使用 Windows DPAPI 为当前 Windows 用户加密，不会以明文写入 Codex `config.toml`。

4. 点击 **保存配置**。保存成功后，运行日志 区域应显示类似信息：

   ```text
   Saved profile deepseek; key is DPAPI-encrypted for the current Windows user
   ```

5. 点击 **测试 Responses**。程序会提示该操作将发送一个很小、但可能产生费用的 API 请求。确认可以接受后再继续。

   测试调用：

   ```text
   https://api.deepseek.com/responses
   ```

   成功结果类似：

   ```text
   Responses compatible: HTTP 200; response status=completed
   ```

   如果测试失败，不要应用该 Profile。先检查 API key、模型 ID、端点、账户余额及 运行日志 中的完整错误信息。

6. 等待 Codex 中正在运行的任务结束，最好手动完全退出 Codex Desktop。

7. 点击 **应用到 Codex**。切换器将：

   - 保留 MCP、Computer Use、插件、项目 trust、sandbox、hooks 和 features 等非托管设置；
   - 创建该 Profile 独立的模型目录；
   - 设置必要的 Provider、模型、认证和 catalog 字段；
   - 请求重启 Codex Desktop。

   应用成功时，运行日志 信息类似：

   ```text
   Applied DeepSeek 官方/deepseek-flash.
   Codex Desktop restart requested.
   Start a new Codex conversation.
   ```

8. Codex Desktop 重启后，新建一个对话。不要继续切换前正在使用的对话。Desktop 对自定义 Provider 的模型标签可能只显示通用名称；API 请求成功和 Provider 后台的用量记录，比模型自报身份更可靠。

#### 添加自定义 Responses API Provider

1. 点击 **新建自定义**。

2. 填写表单。通用示例：

   ```text
   配置 ID: example-provider
   服务商名称: Example Provider
   Base URL: https://api.example.com/v1
   API key: 你的 Provider API key
   模型 ID: provider-model-id
   模型显示名称: Provider Model
   上下文窗口: Provider 文档中的实际值
   推理级别: high
   ```

   字段规则：

   - **配置 ID** 只能包含英文字母、数字、下划线和连字符。
   - **Base URL** 通常填写到 `/v1` 等 API 根路径，不要追加 `/responses`。
   - 远程 Provider 必须使用 HTTPS。只有 `localhost` 或 `127.0.0.1` 允许 HTTP。
   - **模型 ID** 必须是 Provider API 实际使用的模型标识，不能只填营销展示名称。
   - 上下文窗口 应采用 Provider 文档给出的数值，不要假定所有模型都支持一百万 tokens。
   - 如果尚未验证 reasoning level，先只填 `high`。

3. 点击 **保存配置**。

4. 点击 **获取模型列表**，程序将调用 `GET <Base URL>/models`。确认需要的 模型 ID 出现在结果中。部分兼容 Provider 不提供 `/models`；这种情况下，应通过 Provider 官方文档核对 模型 ID。

5. 点击 **测试 Responses**。只有 Responses 测试成功后才应用 Profile。

   如果接口返回 `404`、拒绝 Responses 请求结构，或只支持 Chat Completions，则不要应用。当前 MVP 不提供 Chat Completions 到 Responses 的转换。

6. 结束当前 Codex 任务，应用 Profile，等待 Codex Desktop 重启，然后新建对话。

#### 恢复 Native Codex

1. 等待第三方 Provider 正在执行的任务结束。
2. 打开应用该 Provider 时使用的同一个 `CodexProviderSwitcher.exe`。
3. 点击 **恢复原始配置** 并确认。
4. 等待 Codex Desktop 重启；如果没有自动重启，则手动重新打开。
5. 新建对话或重新打开 Native Codex 对话。

恢复操作会删除本工具创建的 `model_providers.cps_*` 配置段，并恢复第一次切换前记录的 provider/model/auth/catalog 字段。它不会修改 Native Codex 登录文件、对话数据库、MCP servers、插件、Computer Use 或其他无关设置。

#### 重要安全注意事项

- 第三方 Profile 生效期间，不要移动、重命名或删除 EXE。Codex 会调用该 EXE 的原始路径来获取 DPAPI 保护的 API key。如果文件不可用，第三方认证会失败，但 Native 账户和对话不会被删除。
- 将 EXE 保存在可信的本地目录。当前发布文件没有 Authenticode 签名，因此 Windows SmartScreen 首次运行时可能警告。
- 不要在不同 Provider 之间继续同一个对话。Native 账号认证和 API-key Provider 可能显示不同的对话列表，这不一定表示 Native 对话被删除。
- Codex Desktop 或 CLI 重大升级后，应先重新运行 Provider 测试再应用，因为自定义 Provider 或模型目录格式可能变化。
- Provider 测试可能产生少量 API 费用。**获取模型列表** 通常是只读请求，但实际计费规则由 Provider 决定。

#### 常见问题

| 现象 | 处理方法 |
|---|---|
| Responses 测试返回 `401` 或 `403` | 检查 API key、账户权限以及所选模型的访问权限。 |
| Responses 测试返回 `404` | 检查 Base URL，并确认 Provider 实现了 `/responses`；当前 MVP 不支持仅 Chat Completions 的 Provider。 |
| 应用成功但 Codex 没有重启 | 完全退出 Codex Desktop 后手动重新打开，并新建对话。 |
| 移动 EXE 后第三方模式无法认证 | 把 EXE 放回原路径，然后恢复 Native，或从新路径重新应用 Profile。 |
| 第三方模式中看不到 Native 对话 | 恢复 Native 并重启 Codex；不要直接判断对话已被删除。 |
| Provider 测试失败 | 不要点击 Apply。保留 运行日志 错误用于排查，但绝不要包含 API key。 |

### 本地验证兼容性

- Windows 10 x64
- Codex Desktop `26.730.8199.0`
- Codex CLI `0.144.3`
- Python `3.11.15`

模型目录、DeepSeek Profile 和恢复路径均已由真实 Codex CLI 在隔离 `CODEX_HOME` 中成功解析。

### 许可证

MIT，参见 `LICENSE`。

---

## English
### Chinese UI and safety update

The GUI now uses Simplified Chinese. Main actions: 保存配置 (Save profile), 获取模型列表 (List models), 测试 Responses (Test Responses), 应用到 Codex (Apply), 恢复原始配置 (Restore).

Apply and Restore now require an explicit confirmation, defaulting to cancellation, before any configuration mutation or forced restart. Every probe redirect is checked before sending credentials; only same-origin redirects are allowed, with at most five hops. POST requests only follow 307/308 while retaining their method and body.

Recovery metadata is persisted before configuration changes. Ordinary write errors roll back modified files; after an interrupted operation or failed rollback, fix file access and use Restore with the retained recovery record. A successful basic Responses probe does not establish streaming or tool-calling compatibility.

Tests use temporary directories and local HTTP servers. Frozen authentication tests are skipped until the EXE is built; rerun the suite after building.

Windows GUI utility for switching Codex Desktop between:

- the original/native Codex configuration;
- deepseek-flash through DeepSeek's native Responses API;
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

- deepseek-flash;
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

### First-time deepseek-flash setup

1. Run `CodexProviderSwitcher.exe`.

2. In the **Profile** drop-down, select `deepseek`. The form should contain values similar to:

   ```text
   Profile ID: deepseek
   Display name: DeepSeek Official
   Base URL: https://api.deepseek.com
   Model ID: deepseek-flash
   Model display name: deepseek-flash
   Context window: 1048576
   Reasoning levels: low, high, max
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
   Applied DeepSeek Official/deepseek-flash.
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
