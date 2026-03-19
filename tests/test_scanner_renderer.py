from pathlib import Path
import json
import shutil
import unittest

from PIL import Image

from src.cloud_sync import sync_images_to_cloud
from src.models import KnowledgeItem
from src.renderer import MANIFEST_NAME, _split_formula_content, render_item, render_items
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

    def test_render_items_skips_unchanged_files(self) -> None:
        output_dir = self.temp_root / "images"
        item = KnowledgeItem(
            title="Test Title",
            body="Body content used to verify incremental rendering.",
            notes=["Note one"],
            source_path=Path("note.md"),
            source_line=1,
        )

        first = render_items([item], output_dir, width=600, height=1000)
        second = render_items([item], output_dir, width=600, height=1000)

        self.assertEqual(first.created_count, 1)
        self.assertEqual(second.unchanged_count, 1)
        manifest_path = output_dir / MANIFEST_NAME
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["items"]), 1)

    def test_render_items_deletes_stale_files(self) -> None:
        output_dir = self.temp_root / "images"
        first_item = KnowledgeItem(
            title="First",
            body="Body one",
            notes=[],
            source_path=Path("note.md"),
            source_line=1,
        )
        second_item = KnowledgeItem(
            title="Second",
            body="Body two",
            notes=[],
            source_path=Path("note.md"),
            source_line=2,
        )

        render_items([first_item, second_item], output_dir, width=600, height=1000)
        summary = render_items([first_item], output_dir, width=600, height=1000)

        self.assertEqual(len(summary.deleted_paths), 1)

    def test_splits_formula_content_with_chinese(self) -> None:
        parts = _split_formula_content("E(XY)=E(X)E(Y) X,Y 独立")
        self.assertEqual(parts, [("math", "E(XY)=E(X)E(Y) X,Y "), ("text", "独立")])

    def test_sync_images_to_cloud_copies_and_deletes(self) -> None:
        source_dir = self.temp_root / "source"
        cloud_dir = self.temp_root / "cloud"
        source_dir.mkdir()
        cloud_dir.mkdir()
        (source_dir / "a.png").write_bytes(b"a")
        (source_dir / "b.png").write_bytes(b"b")
        (cloud_dir / "old.png").write_bytes(b"old")

        summary = sync_images_to_cloud(source_dir, cloud_dir)

        self.assertEqual(summary.copied_count, 2)
        self.assertEqual(summary.deleted_count, 1)
        self.assertTrue((cloud_dir / "a.png").exists())
        self.assertFalse((cloud_dir / "old.png").exists())


if __name__ == "__main__":
    unittest.main()
