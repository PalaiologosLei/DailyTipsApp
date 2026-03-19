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
                "cloud_dir": "C:/Users/test/iCloudDrive/DailyTips",
                "device_model": "iphone_14",
                "width": "1170",
                "height": "2532",
                "background_mode": "random_group",
                "background_group": "nature",
                "background_image_id": "nature/a.png",
            },
        )

        loaded = load_gui_settings(self.settings_path)
        self.assertEqual(loaded["device_model"], "iphone_14")
        self.assertEqual(loaded["background_mode"], "random_group")
        self.assertEqual(loaded["cloud_dir"], "C:/Users/test/iCloudDrive/DailyTips")
        raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["width"], "1170")


if __name__ == "__main__":
    unittest.main()
