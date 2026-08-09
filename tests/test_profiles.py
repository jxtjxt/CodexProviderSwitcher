import json
import tempfile
import unittest
from pathlib import Path

from codex_provider_switcher.profiles import ProfileRepository
from codex_provider_switcher.core import ProviderProfile


class ProfileRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "profiles.json"
        self.repo = ProfileRepository(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_deepseek_profile_is_always_available(self):
        profiles = self.repo.list()
        deepseek = next(profile for profile in profiles if profile.profile_id == "deepseek")
        self.assertEqual(deepseek.model, "deepseek-v4-flash")
        self.assertEqual(deepseek.context_window, 1048576)

    def test_custom_profile_round_trip(self):
        profile = ProviderProfile("lab", "Lab", "https://lab.example/v1", "m", "Model", 128000, ["high"])
        self.repo.save(profile)
        loaded = next(item for item in self.repo.list() if item.profile_id == "lab")
        self.assertEqual(loaded.base_url, "https://lab.example/v1")

    def test_repository_never_contains_api_keys(self):
        profile = ProviderProfile("lab", "Lab", "https://lab.example/v1", "m", "Model", 128000, ["high"])
        self.repo.save(profile)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertNotIn("api_key", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
