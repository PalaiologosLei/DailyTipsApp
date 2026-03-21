from pathlib import Path
import shutil
import unittest

from PIL import Image

from src.models import KnowledgeItem, RenderConfig
from src.render_backend import build_prepared_requests
from src.renderer import _is_complex_tectonic_formula, _split_formula_content, render_item


class RendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path("d:/Coding/DailyTipsApp/.tmp_tests") / self._testMethodName
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_renders_png_with_expected_size(self) -> None:
        output_path = self.temp_root / "item.png"
        item = KnowledgeItem("Test Title", "Body content used to verify rendering works.", ["Note one", "Note two"], Path("note.md"), 1)
        render_item(item, output_path, RenderConfig(width=600, height=1000))
        self.assertTrue(output_path.exists())
        with Image.open(output_path) as image:
            self.assertEqual(image.size, (600, 1000))

    def test_splits_formula_content_with_chinese(self) -> None:
        parts = _split_formula_content("E(XY)=E(X)E(Y) X,Y 独立")
        self.assertEqual(parts, [("math", "E(XY)=E(X)E(Y) X,Y "), ("text", "独立")])

    def test_accepts_camel_case_prepared_render_payload(self) -> None:
        requests = build_prepared_requests(
            [
                {
                    "title": "贝叶斯公式",
                    "body": "$P(A|B)=\\frac{P(B|A)P(A)}{P(B)}$",
                    "notes": ["说明"],
                    "sourcePath": "test.md",
                    "sourceLine": 3,
                    "outputFile": "bayes.png",
                }
            ],
            self.temp_root,
        )
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].output_path, self.temp_root / "bayes.png")
        self.assertEqual(requests[0].item.source_path, Path("test.md"))
        self.assertEqual(requests[0].item.source_line, 3)

    def test_marks_fraction_formula_as_complex(self) -> None:
        self.assertTrue(_is_complex_tectonic_formula(r"P(A|B)=\frac{P(B|A)P(A)}{P(B)}"))
        self.assertTrue(_is_complex_tectonic_formula(r"\sum_{i=1}^n \frac{x_i^2}{1+y_i}"))
        self.assertFalse(_is_complex_tectonic_formula(r"E(X)=E(E(X|Y))"))


if __name__ == "__main__":
    unittest.main()
