from pathlib import Path
import shutil
import unittest

from PIL import Image

from src.background_library import (
    BackgroundLibraryError,
    choose_background_path,
    clear_background_library,
    create_group,
    import_backgrounds,
    list_backgrounds,
    list_groups,
)
from src.models import BackgroundSelection


class BackgroundLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path("d:/Coding/DailyTipsApp/.tmp_tests") / self._testMethodName
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.library_root = self.temp_root / "backgrounds"
        self.library_root.mkdir()
        self.source_image = self.temp_root / "sample.png"
        Image.new("RGB", (50, 50), "red").save(self.source_image)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_create_group_and_import(self) -> None:
        create_group(self.library_root, "nature")
        import_backgrounds(self.library_root, "nature", [self.source_image])
        self.assertEqual(list_groups(self.library_root), ["nature"])
        images = list_backgrounds(self.library_root, "nature")
        self.assertEqual(len(images), 1)

    def test_choose_background_path_is_stable(self) -> None:
        import_backgrounds(self.library_root, "nature", [self.source_image])
        selection = BackgroundSelection(mode="random_group", group_name="nature")
        first = choose_background_path(self.library_root, selection, "item-1")
        second = choose_background_path(self.library_root, selection, "item-1")
        self.assertEqual(first, second)

    def test_clear_background_library_keeps_default_group(self) -> None:
        import_backgrounds(self.library_root, "nature", [self.source_image])
        removed = clear_background_library(self.library_root)
        self.assertEqual(removed, 1)
        self.assertTrue((self.library_root / "default" / ".gitkeep").exists())
        self.assertEqual(list_groups(self.library_root), ["default"])

    def test_rejects_non_image(self) -> None:
        invalid = self.temp_root / "bad.txt"
        invalid.write_text("x", encoding="utf-8")
        with self.assertRaises(BackgroundLibraryError):
            import_backgrounds(self.library_root, "nature", [invalid])


if __name__ == "__main__":
    unittest.main()
