"""다크 모드 CSS 자동 생성을 실제 소스(web/)에 돌려 본다. web/ 이 있어야 하므로 tests/unit(변이 검사 기준선)이 아닌 전체 단위 검사에서만 돈다."""
import re
import unittest
from pathlib import Path

from pipeline import darkcss


class DarkCssSources(unittest.TestCase):
    def test_real_sources_generate_balanced_css(self):
        web = Path(__file__).resolve().parents[1] / "web"
        files = [web / "assets/df/lk.css", web / "assets/df/st.css"] + sorted(web.glob("df_*.html"))
        self.assertGreaterEqual(len(files), 8)   # 파일이 없어서 그냥 통과하는 일이 없게
        for f in files:
            text = f.read_text(encoding="utf-8")
            for css in (re.findall(r"<style[^>]*>(.*?)</style>", text, re.S) if f.suffix == ".html" else [text]):
                gen = darkcss.generate(css)
                self.assertEqual(gen.count("{"), gen.count("}"), f.name)
                self.assertNotIn("var(--", "".join(re.findall(r"--[\w-]+: ([^;]+)", gen)), f.name)


if __name__ == "__main__":
    unittest.main()
