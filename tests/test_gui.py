import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from codex_provider_switcher.gui import App


class GuiConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        with patch("codex_provider_switcher.gui.codex_home", return_value=Path(self.temp.name)):
            self.app = App(self.root)
        self.app.secrets = Mock()
        self.app.repo = Mock()
        self.app.transaction = Mock()
        self.app.key_var.set("test-only-placeholder")

    def test_cancel_apply_makes_no_changes_and_does_not_restart(self):
        with patch("codex_provider_switcher.gui.messagebox.askyesno", return_value=False) as confirm, \
             patch("codex_provider_switcher.gui.restart_codex_desktop") as restart:
            self.app.apply()
        self.assertIn("强制关闭", confirm.call_args.args[1])
        self.assertEqual(confirm.call_args.kwargs["default"], "no")
        self.app.secrets.set.assert_not_called()
        self.app.repo.save.assert_not_called()
        self.app.transaction.apply.assert_not_called()
        restart.assert_not_called()

    def test_confirm_apply_updates_configuration_then_requests_restart(self):
        order = []
        self.app.transaction.apply.side_effect = lambda *args: order.append("apply")
        def restart():
            order.append("restart")
            return True, "已请求重启 Codex"
        with patch("codex_provider_switcher.gui.messagebox.askyesno", return_value=True), \
             patch("codex_provider_switcher.gui.restart_codex_desktop", side_effect=restart):
            self.app.apply()
        self.assertEqual(order, ["apply", "restart"])

    def test_failed_apply_does_not_restart(self):
        self.app.transaction.apply.side_effect = OSError("test failure")
        with patch("codex_provider_switcher.gui.messagebox.askyesno", return_value=True), \
             patch("codex_provider_switcher.gui.messagebox.showerror") as error, \
             patch("codex_provider_switcher.gui.restart_codex_desktop") as restart:
            self.app.apply()
        error.assert_called_once()
        restart.assert_not_called()

    def test_cancel_restore_does_not_mutate_or_restart(self):
        with patch("codex_provider_switcher.gui.messagebox.askyesno", return_value=False) as confirm, \
             patch("codex_provider_switcher.gui.restart_codex_desktop") as restart:
            self.app.restore()
        self.assertIn("强制关闭", confirm.call_args.args[1])
        self.assertEqual(confirm.call_args.kwargs["default"], "no")
        self.app.transaction.restore.assert_not_called()
        restart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
