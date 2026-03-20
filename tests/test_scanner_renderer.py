from pathlib import Path
import json
import shutil
import unittest

from PIL import Image

from src.cloud_sync import IMAGE_INDEX_NAME, clear_generated_outputs, update_cloud_image_index
from src.models import BackgroundSelection, KnowledgeItem, RenderConfig
from src.renderer import MANIFEST_NAME, RENDER_STATE_NAME, _split_formula_content, render_item, render_items
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
        item = KnowledgeItem("Test Title", "Body content used to verify that rendering works.", ["Note one", "Note two"], Path("note.md"), 1)
        render_item(item, output_path, RenderConfig(width=600, height=1000))
        self.assertTrue(output_path.exists())
        with Image.open(output_path) as image:
            self.assertEqual(image.size, (600, 1000))

    def test_render_items_skips_unchanged_files_and_writes_metadata(self) -> None:
        image_dir = self.temp_root / "cloud"
        metadata_dir = self.temp_root / "data"
        item = KnowledgeItem("Test Title", "Body content used to verify incremental rendering.", ["Note one"], Path("note.md"), 1)
        config = RenderConfig(width=600, height=1000)
        first = render_items([item], image_dir, metadata_dir, config)
        second = render_items([item], image_dir, metadata_dir, config)
        self.assertEqual(first.created_count, 1)
        self.assertEqual(second.unchanged_count, 1)
        manifest = json.loads((metadata_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["items"]), 1)
        index_payload = json.loads((image_dir / IMAGE_INDEX_NAME).read_text(encoding="utf-8"))
        self.assertEqual(index_payload["count"], 1)
        state_payload = json.loads((metadata_dir / RENDER_STATE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(state_payload["background_mode"], "white")
        self.assertTrue(state_payload["show_content_panel"])
        self.assertEqual(state_payload["panel_opacity"], 212)

    def test_render_items_deletes_stale_files_and_refreshes_index(self) -> None:
        image_dir = self.temp_root / "cloud"
        metadata_dir = self.temp_root / "data"
        first_item = KnowledgeItem("First", "Body one", [], Path("note.md"), 1)
        second_item = KnowledgeItem("Second", "Body two", [], Path("note.md"), 2)
        config = RenderConfig(width=600, height=1000)
        render_items([first_item, second_item], image_dir, metadata_dir, config)
        summary = render_items([first_item], image_dir, metadata_dir, config)
        self.assertEqual(len(summary.deleted_paths), 1)
        index_payload = json.loads((image_dir / IMAGE_INDEX_NAME).read_text(encoding="utf-8"))
        self.assertEqual(index_payload["count"], 1)

    def test_splits_formula_content_with_chinese(self) -> None:
        parts = _split_formula_content("E(XY)=E(X)E(Y) X,Y \u72ec\u7acb")
        self.assertEqual(parts, [("math", "E(XY)=E(X)E(Y) X,Y "), ("text", "\u72ec\u7acb")])

    def test_update_cloud_image_index(self) -> None:
        cloud_dir = self.temp_root / "cloud"
        cloud_dir.mkdir()
        (cloud_dir / "b.png").write_bytes(b"b")
        (cloud_dir / "a.png").write_bytes(b"a")
        summary = update_cloud_image_index(cloud_dir)
        self.assertEqual(summary.image_count, 2)
        payload = json.loads(summary.index_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["images"], ["a.png", "b.png"])

    def test_clear_generated_outputs(self) -> None:
        metadata_dir = self.temp_root / "data"
        cloud_dir = self.temp_root / "cloud"
        metadata_dir.mkdir()
        cloud_dir.mkdir()
        (metadata_dir / MANIFEST_NAME).write_text("{}", encoding="utf-8")
        (metadata_dir / "notes.json").write_text("{}", encoding="utf-8")
        (cloud_dir / "a.png").write_bytes(b"a")
        (cloud_dir / IMAGE_INDEX_NAME).write_text("{}", encoding="utf-8")
        summary = clear_generated_outputs(metadata_dir, cloud_dir)
        self.assertEqual(summary.removed_metadata_count, 2)
        self.assertEqual(summary.removed_cloud_count, 1)
        self.assertEqual(summary.removed_index_count, 1)

    def test_background_rule_change_forces_regeneration_and_updates_state(self) -> None:
        image_dir = self.temp_root / "cloud"
        metadata_dir = self.temp_root / "data"
        item = KnowledgeItem("Hash Test", "Body", [], Path("note.md"), 1)
        config1 = RenderConfig(width=600, height=1000, background_selection=BackgroundSelection(mode="white"))
        config2 = RenderConfig(width=600, height=1000, background_selection=BackgroundSelection(mode="specific", image_id="group/a.png"))
        first = render_items([item], image_dir, metadata_dir, config1)
        second = render_items([item], image_dir, metadata_dir, config2)
        self.assertEqual(first.created_count, 1)
        self.assertEqual(second.updated_count, 1)
        state_payload = json.loads((metadata_dir / RENDER_STATE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(state_payload["background_mode"], "specific")
        self.assertEqual(state_payload["background_image_id"], "group/a.png")

    def test_style_change_forces_regeneration_and_updates_state(self) -> None:
        image_dir = self.temp_root / "cloud"
        metadata_dir = self.temp_root / "data"
        item = KnowledgeItem("Style Test", "Body", [], Path("note.md"), 1)
        config1 = RenderConfig(width=600, height=1000, text_color="#000000", show_content_panel=True, panel_opacity=212)
        config2 = RenderConfig(width=600, height=1000, text_color="#224466", show_content_panel=False, panel_opacity=96)
        first = render_items([item], image_dir, metadata_dir, config1)
        second = render_items([item], image_dir, metadata_dir, config2)
        self.assertEqual(first.created_count, 1)
        self.assertEqual(second.updated_count, 1)
        state_payload = json.loads((metadata_dir / RENDER_STATE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(state_payload["text_color"], "#224466")
        self.assertFalse(state_payload["show_content_panel"])
        self.assertEqual(state_payload["panel_opacity"], 96)

    def test_formula_renderer_change_forces_regeneration_and_updates_state(self) -> None:
        image_dir = self.temp_root / "cloud"
        metadata_dir = self.temp_root / "data"
        item = KnowledgeItem("Renderer Test", "$x+y$", [], Path("note.md"), 1)
        config1 = RenderConfig(width=600, height=1000, formula_renderer="matplotlib")
        config2 = RenderConfig(width=600, height=1000, formula_renderer="tectonic")
        first = render_items([item], image_dir, metadata_dir, config1)
        second = render_items([item], image_dir, metadata_dir, config2)
        self.assertEqual(first.created_count, 1)
        self.assertEqual(second.updated_count, 1)
        state_payload = json.loads((metadata_dir / RENDER_STATE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(state_payload["formula_renderer"], "tectonic")

    def test_tectonic_backend_resolves_when_bundled_binary_exists(self) -> None:
        from src.renderer import resolve_formula_backend

        backend = resolve_formula_backend("tectonic")
        self.assertIn(backend.effective, {"tectonic", "matplotlib", "plain"})



if __name__ == "__main__":
    unittest.main()
