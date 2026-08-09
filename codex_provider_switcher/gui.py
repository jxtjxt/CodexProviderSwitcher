from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .core import ConfigTransaction, ProviderProfile, responses_url
from .probe import ProviderProbe
from .profiles import ProfileRepository
from .secrets import SecretStore
from .windows import app_executable, codex_home, restart_codex_desktop


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Codex Provider Switcher")
        self.root.geometry("820x620")
        self.root.minsize(760, 560)
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
        self.status_var = tk.StringVar(value=f"Codex home: {self.home}")

        self._build()
        self.refresh_profiles()

    def _build(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Codex Provider Switcher", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Switch Codex Desktop between the original configuration, DeepSeek V4 Flash, and any Responses-compatible API.",
            wraplength=760,
        ).pack(anchor="w", pady=(2, 14))

        selector = ttk.Frame(frame)
        selector.pack(fill="x")
        ttk.Label(selector, text="Profile").pack(side="left")
        self.combo = ttk.Combobox(selector, textvariable=self.profile_var, state="readonly", width=42)
        self.combo.pack(side="left", padx=8)
        self.combo.bind("<<ComboboxSelected>>", lambda _: self.load_selected())
        ttk.Button(selector, text="New custom", command=self.new_custom).pack(side="left")

        form = ttk.LabelFrame(frame, text="Provider profile", padding=12)
        form.pack(fill="x", pady=12)
        fields = [
            ("Profile ID", self.id_var, False),
            ("Display name", self.name_var, False),
            ("Base URL", self.base_var, False),
            ("API key", self.key_var, True),
            ("Model ID", self.model_var, False),
            ("Model display name", self.display_var, False),
            ("Context window", self.context_var, False),
            ("Reasoning levels", self.reasoning_var, False),
        ]
        for row, (label, variable, secret) in enumerate(fields):
            ttk.Label(form, text=label, width=20).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(form, textvariable=variable, show="•" if secret else "")
            entry.grid(row=row, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)
        ttk.Label(
            form,
            text="Reasoning levels: comma-separated (for example high,low,max). Remote URLs require HTTPS; HTTP is allowed only for loopback.",
            wraplength=700,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=4)
        ttk.Button(buttons, text="Save profile", command=self.save_profile).pack(side="left")
        ttk.Button(buttons, text="List models", command=self.list_models).pack(side="left", padx=6)
        ttk.Button(buttons, text="Test Responses", command=self.test_responses).pack(side="left")
        ttk.Button(buttons, text="Apply to Codex", command=self.apply).pack(side="left", padx=6)
        ttk.Button(buttons, text="Restore original / Native", command=self.restore).pack(side="left")
        ttk.Button(buttons, text="Delete custom", command=self.delete_profile).pack(side="right")

        result_frame = ttk.LabelFrame(frame, text="Diagnostics", padding=8)
        result_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.output = tk.Text(result_frame, height=12, wrap="word", state="disabled", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True)
        ttk.Label(frame, textvariable=self.status_var).pack(fill="x", pady=(8, 0))

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
        self.reasoning_var.set(",".join(profile.reasoning_levels))
        self.log(f"Selected {profile.name}; Responses URL: {responses_url(profile.base_url)}")

    def new_custom(self):
        self.profile_var.set("")
        self.id_var.set("custom")
        self.name_var.set("Custom Provider")
        self.base_var.set("https://example.com/v1")
        self.key_var.set("")
        self.model_var.set("")
        self.display_var.set("")
        self.context_var.set("200000")
        self.reasoning_var.set("high")

    def form_profile(self) -> ProviderProfile:
        levels = [item.strip() for item in self.reasoning_var.get().split(",") if item.strip()]
        return ProviderProfile(
            profile_id=self.id_var.get().strip(),
            name=self.name_var.get().strip(),
            base_url=self.base_var.get().strip(),
            model=self.model_var.get().strip(),
            display_name=self.display_var.get().strip() or self.model_var.get().strip(),
            context_window=int(self.context_var.get().strip()),
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
                raise ValueError("Enter an API key before saving")
            self.refresh_profiles(profile.profile_id)
            self.log(f"Saved profile {profile.profile_id}; key is DPAPI-encrypted for the current Windows user")
        except Exception as exc:
            messagebox.showerror("Could not save", str(exc))

    def key_for(self, profile_id: str) -> str:
        key = self.key_var.get().strip()
        if key:
            return key
        stored = self.secrets.get(profile_id)
        if not stored:
            raise ValueError("No API key is stored for this profile")
        return stored

    def background(self, action):
        def runner():
            try:
                message = action()
                self.root.after(0, lambda: self.log(message))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Operation failed", str(exc)))
        threading.Thread(target=runner, daemon=True).start()

    def list_models(self):
        try:
            profile = self.form_profile()
            key = self.key_for(profile.profile_id)
        except Exception as exc:
            messagebox.showerror("Cannot test", str(exc))
            return
        self.log("Querying /models (one network request)...")
        def action():
            result = ProviderProbe(profile.base_url, key).list_models()
            if not result.ok:
                return f"Models probe failed: {result.message}"
            return f"Models ({len(result.models)}): " + ", ".join(result.models[:100])
        self.background(action)

    def test_responses(self):
        try:
            profile = self.form_profile()
            key = self.key_for(profile.profile_id)
        except Exception as exc:
            messagebox.showerror("Cannot test", str(exc))
            return
        if not messagebox.askyesno("Billable API test", "This sends one short Responses API request and may consume paid tokens. Continue?"):
            return
        self.log(f"Testing {responses_url(profile.base_url)} with model {profile.model}...")
        def action():
            result = ProviderProbe(profile.base_url, key).test_responses(profile.model)
            return ("Responses compatible: " if result.ok else "Responses test failed: ") + result.message
        self.background(action)

    def apply(self):
        try:
            profile = self.form_profile()
            key = self.key_for(profile.profile_id)
            self.secrets.set(profile.profile_id, key)
            if profile.profile_id != "deepseek":
                self.repo.save(profile)
            self.transaction.apply(profile, str(app_executable()))
            restarted, note = restart_codex_desktop()
            self.log(f"Applied {profile.name}/{profile.model}. {note}. Start a new Codex conversation.")
        except Exception as exc:
            messagebox.showerror("Could not apply", str(exc))

    def restore(self):
        if not messagebox.askyesno("Restore original configuration", "Restore provider/auth/model fields captured before the first switch? Other Codex settings will be preserved."):
            return
        try:
            self.transaction.restore()
            _, note = restart_codex_desktop()
            self.log(f"Original/Native provider fields restored. {note}.")
        except Exception as exc:
            messagebox.showerror("Restore failed", str(exc))

    def delete_profile(self):
        profile_id = self.id_var.get().strip()
        if not profile_id or profile_id == "deepseek":
            messagebox.showinfo("Built-in profile", "The built-in DeepSeek profile cannot be deleted.")
            return
        if messagebox.askyesno("Delete profile", f"Delete profile '{profile_id}' and its encrypted API key?"):
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
