from pathlib import Path
import shutil
import unittest

from src.note_source import MaterializedNotesSource, NoteSourceError, parse_github_url


class NoteSourceTests(unittest.TestCase):
    def test_parse_root_github_url(self) -> None:
        spec = parse_github_url("https://github.com/PalaiologosLei/DailyTips")
        self.assertEqual(spec.owner, "PalaiologosLei")
        self.assertEqual(spec.repo, "DailyTips")
        self.assertIsNone(spec.branch)
        self.assertEqual(spec.subpath, "")

    def test_parse_tree_github_url(self) -> None:
        spec = parse_github_url("https://github.com/PalaiologosLei/DailyTips/tree/main/math")
        self.assertEqual(spec.branch, "main")
        self.assertEqual(spec.subpath, "math")

    def test_rejects_non_github_url(self) -> None:
        with self.assertRaises(NoteSourceError):
            parse_github_url("https://example.com/repo")

    def test_cleanup_removes_download_dir(self) -> None:
        cleanup_dir = Path("d:/Coding/DailyTipsApp/.tmp_tests/source_cleanup")
        cleanup_dir.mkdir(parents=True, exist_ok=True)
        (cleanup_dir / "sample.txt").write_text("x", encoding="utf-8")

        source = MaterializedNotesSource(notes_dir=cleanup_dir, description="test", cleanup_dir=cleanup_dir)
        source.cleanup()

        self.assertFalse(cleanup_dir.exists())

    def tearDown(self) -> None:
        temp_root = Path("d:/Coding/DailyTipsApp/.tmp_tests")
        if temp_root.exists():
            shutil.rmtree(temp_root)


if __name__ == "__main__":
    unittest.main()
