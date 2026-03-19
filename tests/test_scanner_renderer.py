from pathlib import Path
import shutil
import unittest

from PIL import Image

from src.models import KnowledgeItem
from src.renderer import render_item
from src.scanner import find_markdown_files


class ScannerRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path("d:/Coding/DailyTipsApp/.tmp_tests") / self._testMethodName
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_finds_markdown_files_recursively(self) -> None:
        root = self.temp_root
        nested = root / "nested"
        nested.mkdir()
        (root / "a.md").write_text("# a", encoding="utf-8")
        (nested / "b.md").write_text("# b", encoding="utf-8")
        (nested / "c.txt").write_text("x", encoding="utf-8")

        files = find_markdown_files(root)
        self.assertEqual([file.name for file in files], ["a.md", "b.md"])

    def test_renders_png_with_expected_size(self) -> None:
        output_path = self.temp_root / "item.png"
        item = KnowledgeItem(
            title="Test Title",
            body="Body content used to verify that rendering works.",
            notes=["Note one", "Note two"],
            source_path=Path("note.md"),
            source_line=1,
        )
        render_item(item, output_path, width=600, height=1000)

        self.assertTrue(output_path.exists())
        with Image.open(output_path) as image:
            self.assertEqual(image.size, (600, 1000))


if __name__ == "__main__":
    unittest.main()
