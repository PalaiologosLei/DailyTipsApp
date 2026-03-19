from pathlib import Path
import json
import shutil
import unittest

from src.gui_settings import DEFAULT_GUI_SETTINGS, load_gui_settings, save_gui_settings


class GuiSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path("d:/Coding/DailyTipsApp/.tmp_tests") / self._testMethodName
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.temp_root / ".gui_settings.json"

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_load_defaults_when_missing(self) -> None:
        settings = load_gui_settings(self.settings_path)
        self.assertEqual(settings, DEFAULT_GUI_SETTINGS)

    def test_save_and_load_roundtrip(self) -> None:
        save_gui_settings(
            self.settings_path,
            {
                "language": "en",
                "source_mode": "github",
                "local_path": "D:/notes",
                "github_url": "https://github.com/example/repo",
                "output_dir": "output/images",
                "width": "1000",
                "height": "2000",
                "commit_message": "test",
                "skip_git": True,
            },
        )

        loaded = load_gui_settings(self.settings_path)
        self.assertEqual(loaded["language"], "en")
        self.assertEqual(loaded["source_mode"], "github")
        self.assertEqual(loaded["skip_git"], True)
        raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["width"], "1000")


if __name__ == "__main__":
    unittest.main()
