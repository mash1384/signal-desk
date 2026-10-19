"""Atomic article asset bundle: stable HTML ABI, matching CSS and JS in one GET."""
import base64
import json
from pathlib import Path
import re


def bundle(web, out):
    root = Path(web)
    fonts = root / 'assets/fonts'
    css = (fonts / 'subsets.css').read_text()
    css = re.sub(r'url\("([^\"]+)"\)', lambda m: 'url("data:font/woff2;base64,' + base64.b64encode((fonts / m[1]).read_bytes()).decode() + '")', css)
    inter = fonts / 'inter.css'
    # Keep Inter reversible; its pinned external font URLs are immutable.
    if inter.is_file() and '"Inter"' in (root / 'assets/df/lk.css').read_text():
        css += inter.read_text()
    css += '\n' + (root / 'assets/df/lk.css').read_text() + '\n' + (root / 'assets/df/st.css').read_text()
    js = "// Article ABI v1: this single response contains the matching CSS + JS.\n(()=>{\n"
    js += "const style=document.createElement('style');style.textContent=" + json.dumps(css, ensure_ascii=False) + ";document.head.appendChild(style);\n"
    js += (root / 'assets/df/data.js').read_text() + '\n'
    js += "DFI.init({ n1:'라이브',n2:'테마',n3:'정리',n4:'일정',n5:'내 자산' });\n"
    js += (root / 'assets/df/st.js').read_text() + '\n})();\n'
    dest = Path(out) / 'assets/article-v1.js'
    dest.write_text(js)


def article_html(html):
    # Only article pages use this stable ABI. Other pages keep their normal
    # versioned module graph. No generation identifier leaks into article HTML.
    html = re.sub(r'<link[^>]+href="[^\"]*assets/(?:df/(?:lk|st)\.css|fonts/(?:subsets|inter)\.css)\?v=[^\"]+"[^>]*>','',html)
    html = re.sub(r'<script src="([^\"]*)assets/df/data\.js\?v=[^\"]+"></script>\s*<script>DFI.init\([\s\S]*?</script>\s*<script src="[^\"]*assets/df/st\.js\?v=[^\"]+"></script>',
                  r'<script src="\1assets/article-v1.js"></script>',html)
    return html
