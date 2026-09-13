from __future__ import annotations

import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from .core import ConfigTransaction, ProviderProfile, responses_url
from .probe import ProviderProbe
from .profiles import ProfileRepository
from .secrets import SecretStore
from .windows import app_executable, codex_home, restart_codex_desktop


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Codex 服务商切换器")
        self.root.geometry("880x820")
        self.root.minsize(820, 800)
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.nametofont(name).configure(family="Microsoft YaHei UI", size=10)
        self.home = codex_home()
        self.data_dir = self.home / "provider-switcher"
        self.repo = ProfileRepository(self.data_dir / "profiles.json")
        self.secrets = SecretStore(self.data_dir / "secrets.json")
        self.transaction = ConfigTransaction(self.home)
        self.profiles: dict[str, ProviderProfile] = {}

        self.profile_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.id_var = tk.StringVar()
        self.base_var = tk.StringVar()
        self.key_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.display_var = tk.StringVar()
        self.context_var = tk.StringVar(value="200000")
        self.reasoning_var = tk.StringVar(value="high")
        self.status_var = tk.StringVar(value=f"Codex 配置目录：{self.home}")

        self._build()
        self.refresh_profiles()

    def _build(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Codex 服务商切换器", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="在原始配置、deepseek-flash 和兼容 Responses API 的服务商之间切换 Codex。",
            wraplength=760,
        ).pack(anchor="w", pady=(2, 14))

        selector = ttk.Frame(frame)
        selector.pack(fill="x")
        ttk.Label(selector, text="配置方案").pack(side="left")
        self.combo = ttk.Combobox(selector, textvariable=self.profile_var, state="readonly", width=42)
        self.combo.pack(side="left", padx=8)
        self.combo.bind("<<ComboboxSelected>>", lambda _: self.load_selected())
        ttk.Button(selector, text="新建自定义", command=self.new_custom).pack(side="left")

        form = ttk.LabelFrame(frame, text="服务商配置", padding=12)
        form.pack(fill="x", pady=12)
        fields = [
            ("配置 ID", self.id_var, False),
            ("服务商名称", self.name_var, False),
            ("API 地址", self.base_var, False),
            ("API 密钥", self.key_var, True),
            ("模型 ID", self.model_var, False),
            ("模型显示名称", self.display_var, False),
            ("上下文窗口", self.context_var, False),
            ("推理级别", self.reasoning_var, False),
        ]
        for row, (label, variable, secret) in enumerate(fields):
            ttk.Label(form, text=label, width=20).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(form, textvariable=variable, show="•" if secret else "")
            entry.grid(row=row, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)
        ttk.Label(
            form,
            text="推理级别使用英文逗号分隔，例如 low, high, max。远程地址须使用 HTTPS；仅本机回环地址允许 HTTP。",
            wraplength=700,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=4)
        ttk.Button(buttons, text="保存配置", command=self.save_profile).pack(side="left")
        ttk.Button(buttons, text="获取模型列表", command=self.list_models).pack(side="left", padx=6)
        ttk.Button(buttons, text="测试 Responses", command=self.test_responses).pack(side="left")
        ttk.Button(buttons, text="应用到 Codex", command=self.apply).pack(side="left", padx=6)
        ttk.Button(buttons, text="恢复原始配置", command=self.restore).pack(side="left")
        ttk.Button(buttons, text="删除自定义", command=self.delete_profile).pack(side="right")

        ttk.Label(frame, textvariable=self.status_var, wraplength=780).pack(side="bottom", fill="x", pady=(8, 0))
        result_frame = ttk.LabelFrame(frame, text="运行日志", padding=8)
        result_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.output = tk.Text(result_frame, height=6, wrap="word", state="disabled", font=("Microsoft YaHei UI", 10))
        self.output.pack(fill="both", expand=True)

    def log(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text.rstrip() + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")
        self.status_var.set(text)

    def refresh_profiles(self, select: str | None = None):
        profiles = self.repo.list()
        self.profiles = {profile.profile_id: profile for profile in profiles}
        self.combo["values"] = list(self.profiles)
        target = select if select in self.profiles else "deepseek"
        self.profile_var.set(target)
        self.load_selected()

    def load_selected(self):
        profile = self.profiles.get(self.profile_var.get())
        if not profile:
            return
        self.id_var.set(profile.profile_id)
        self.name_var.set(profile.name)
        self.base_var.set(profile.base_url)
        self.key_var.set("")
        self.model_var.set(profile.model)
        self.display_var.set(profile.display_name)
        self.context_var.set(str(profile.context_window))
        self.reasoning_var.set(", ".join(profile.reasoning_levels))
        self.log(f"已选择 {profile.name}；Responses 地址：{responses_url(profile.base_url)}")

    def new_custom(self):
        self.profile_var.set("")
        self.id_var.set("custom")
        self.name_var.set("自定义服务商")
        self.base_var.set("https://example.com/v1")
        self.key_var.set("")
        self.model_var.set("")
        self.display_var.set("")
        self.context_var.set("200000")
        self.reasoning_var.set("high")

    def form_profile(self) -> ProviderProfile:
        levels = [item.strip() for item in self.reasoning_var.get().split(",") if item.strip()]
        try:
            context_window = int(self.context_var.get().strip())
        except ValueError:
            raise ValueError("上下文窗口必须填写正整数") from None
        return ProviderProfile(
            profile_id=self.id_var.get().strip(),
            name=self.name_var.get().strip(),
            base_url=self.base_var.get().strip(),
            model=self.model_var.get().strip(),
            display_name=self.display_var.get().strip() or self.model_var.get().strip(),
            context_window=context_window,
            reasoning_levels=levels or ["high"],
        )

    def save_profile(self):
        try:
            profile = self.form_profile()
            if profile.profile_id != "deepseek":
                self.repo.save(profile)
            key = self.key_var.get().strip()
            if key:
                self.secrets.set(profile.profile_id, key)
            elif not self.secrets.get(profile.profile_id):
                raise ValueError("请先输入 API 密钥，再保存配置")
            self.refresh_profiles(profile.profile_id)
            self.log(f"已保存配置 {profile.profile_id}；密钥已使用当前 Windows 用户的 DPAPI 加密")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def key_for(self, profile_id: str) -> str:
        key = self.key_var.get().strip()
        if key:
            return key
        stored = self.secrets.get(profile_id)
        if not stored:
            raise ValueError("此配置尚未保存 API 密钥")
        return stored

    def background(self, action):
        def runner():
            try:
                message = action()
                self.root.after(0, lambda: self.log(message))
            except Exception as exc:
                message = str(exc)
                self.root.after(0, lambda message=message: messagebox.showerror("操作失败", message))
        threading.Thread(target=runner, daemon=True).start()

    def list_models(self):
        try:
            profile = self.form_profile()
            key = self.key_for(profile.profile_id)
        except Exception as exc:
            messagebox.showerror("无法测试", str(exc))
            return
        self.log("正在请求 /models 获取模型列表……")
        def action():
            result = ProviderProbe(profile.base_url, key).list_models()
            if not result.ok:
                return f"获取模型列表失败：{result.message}"
            return f"模型（共 {len(result.models)} 个）：" + ", ".join(result.models[:100])
        self.background(action)

    def test_responses(self):
        try:
            profile = self.form_profile()
            key = self.key_for(profile.profile_id)
        except Exception as exc:
            messagebox.showerror("无法测试", str(exc))
            return
        if not messagebox.askyesno("确认 API 测试费用", "此操作将发送一次简短的 Responses API 请求，可能产生少量费用。是否继续？"):
            return
        self.log(f"正在测试 {responses_url(profile.base_url)}，模型：{profile.model}……")
        def action():
            result = ProviderProbe(profile.base_url, key).test_responses(profile.model)
            return ("Responses 基础测试通过：" if result.ok else "Responses 测试失败：") + result.message
        self.background(action)

    def apply(self):
        try:
            profile = self.form_profile()
            key = self.key_for(profile.profile_id)
            if not messagebox.askyesno(
                "确认应用并重启 Codex",
                f"即将应用 {profile.name} / {profile.model}。\n\n"
                "此操作会强制关闭并重启 Codex，正在运行的回答、命令和文件编辑会被中断。\n"
                "请先完成当前任务并保存工作。重启后请新建对话。\n\n是否继续？",
                default=messagebox.NO,
                parent=self.root,
            ):
                return
            self.secrets.set(profile.profile_id, key)
            if profile.profile_id != "deepseek":
                self.repo.save(profile)
            self.transaction.apply(profile, str(app_executable()))
            restarted, note = restart_codex_desktop()
            self.log(f"已应用 {profile.name} / {profile.model}。{note}。请新建 Codex 对话。")
        except Exception as exc:
            messagebox.showerror("应用失败", str(exc))

    def restore(self):
        if not messagebox.askyesno(
            "确认恢复并重启 Codex",
            "将恢复首次切换前的服务商、认证和模型设置，保留其他 Codex 设置。\n\n"
            "此操作会强制关闭并重启 Codex，正在运行的回答、命令和文件编辑会被中断。\n"
            "请先完成当前任务并保存工作。\n\n是否继续？",
            default=messagebox.NO,
            parent=self.root,
        ):
            return
        try:
            self.transaction.restore()
            _, note = restart_codex_desktop()
            self.log(f"已恢复原始服务商配置。{note}。")
        except Exception as exc:
            messagebox.showerror("恢复失败", str(exc))

    def delete_profile(self):
        profile_id = self.id_var.get().strip()
        if not profile_id or profile_id == "deepseek":
            messagebox.showinfo("内置配置", "不能删除内置的 DeepSeek 配置。")
            return
        if messagebox.askyesno("删除配置", f"是否删除配置“{profile_id}”及其加密保存的 API 密钥？"):
            self.repo.delete(profile_id)
            self.secrets.delete(profile_id)
            self.refresh_profiles()


def run():
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
