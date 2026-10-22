"""배포본 JS 주석 줄 빼기(pipeline/jsstrip.py): 줄 전체 // 주석만, 템플릿 · 문자열 · 정규식 · 블록 주석 안은 그대로."""
import unittest

from pipeline.jsstrip import strip_line_comments as strip


class JsStrip(unittest.TestCase):
    def test_removes_full_line_comments_only(self):
        src = "// 머리\nconst a = 1; // 꼬리는 둔다\n  // 들여쓴 주석\nexport { a };\n"
        self.assertEqual(strip(src), "const a = 1; // 꼬리는 둔다\nexport { a };\n")

    def test_keeps_lines_inside_template_literals(self):
        src = "const t = `첫 줄\n// 글자다(주석 아님)\n${x ? `안\n// 이것도 글자\n` : ''}\n끝`;\n// 지움\n"
        self.assertEqual(strip(src), "const t = `첫 줄\n// 글자다(주석 아님)\n${x ? `안\n// 이것도 글자\n` : ''}\n끝`;\n")

    def test_regex_and_strings_with_quote_or_backtick_do_not_confuse(self):
        src = "const r = /[`'\"]/g, s = '`', d = \"//\";\n// 지움\nconst q = a / b / c;\n// 지움2\n"
        self.assertEqual(strip(src), "const r = /[`'\"]/g, s = '`', d = \"//\";\nconst q = a / b / c;\n")

    def test_block_comment_spanning_lines(self):
        src = "/* 여러 줄\n// 블록 안\n` 백틱 */\n// 지움\nlet z = `${'}'}`;\n// 지움\n"
        self.assertEqual(strip(src), "/* 여러 줄\n// 블록 안\n` 백틱 */\nlet z = `${'}'}`;\n")


if __name__ == "__main__":
    unittest.main()
