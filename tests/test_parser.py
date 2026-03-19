from pathlib import Path
import unittest

from src.parser import parse_markdown_text


class ParserTests(unittest.TestCase):
    def test_extracts_title_body_and_notes(self) -> None:
        text = """
- 【牛顿-莱布尼茨公式】
  - F(b) - F(a) = ∫[a,b] f(x) dx
  - 用原函数差值表示定积分
  - 常用于积分计算
"""
        items = parse_markdown_text(text, Path("sample.md"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "牛顿-莱布尼茨公式")
        self.assertEqual(items[0].body, "F(b) - F(a) = ∫[a,b] f(x) dx")
        self.assertEqual(items[0].notes, ["用原函数差值表示定积分", "常用于积分计算"])

    def test_skips_title_without_child_content(self) -> None:
        text = """
- 【空标题】
正文
"""
        items = parse_markdown_text(text, Path("sample.md"))
        self.assertEqual(items, [])

    def test_supports_nested_indent(self) -> None:
        text = """
  - 【CAPM核心结论】
    - 预期收益 = 无风险利率 + Beta * 市场风险溢价
    - 风险越高，要求收益通常越高
"""
        items = parse_markdown_text(text, Path("sample.md"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "CAPM核心结论")


if __name__ == "__main__":
    unittest.main()
