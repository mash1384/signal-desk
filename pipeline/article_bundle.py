"""Atomic article asset bundle: stable HTML ABI, matching CSS and JS in one GET."""
import base64
import json
from pathlib import Path
import re

from . import darkcss


def bundle(web, out):
    root = Path(web)
    fonts = root / 'assets/fonts'
    css = (fonts / 'subsets.css').read_text()
    css = re.sub(r'url\("(?!data:)([^\"]+)"\)', lambda m: 'url("data:font/woff2;base64,' + base64.b64encode((fonts / m[1]).read_bytes()).decode() + '")', css)   # 이미 CSS 안에 든 글꼴(data:)은 그대로
    inter = fonts / 'inter.css'
    # Keep Inter reversible; its pinned external font URLs are immutable.
    if inter.is_file() and '"Inter"' in (root / 'assets/df/lk.css').read_text():
        css += inter.read_text()
    css += '\n' + darkcss.inject((root / 'assets/df/lk.css').read_text()) + '\n' + darkcss.inject((root / 'assets/df/st.css').read_text())   # 다크 규칙 자동 생성
    js = "// Article ABI v1: this single response contains the matching CSS + JS.\n(()=>{\n"
    js += "const style=document.createElement('style');style.textContent=" + json.dumps(css, ensure_ascii=False) + ";document.head.appendChild(style);\n"
    js += (root / 'assets/df/data.js').read_text() + '\n'
    js += "DFI.init({ n1:'라이브',n2:'테마',n3:'정리',n4:'일정',n5:'내 자산' });\n"
    js += (root / 'assets/df/st.js').read_text() + '\n'
    # 회원(2026-10-29): 머리글 로그인 — 다른 화면은 HTML 인라인(버전 붙음)이지만 기사 HTML 에는 버전을 넣지 않으므로 여기서. acct.js 는 버전 없이(호스팅이 매번 다시 확인한다)
    js += ("{const S=document.currentScript.src;let m;const L=()=>m=m||import(new URL('df/acct.js',S).href);"
           "addEventListener('click',(e)=>{const b=e.target.closest('[data-acct]');if(b)L().then((x)=>x.open(b.dataset.acct,b))});"
           "if(/acct-on/.test(document.documentElement.className)||/auth=/.test(location.hash))L().then((x)=>x.head());}\n")
    js += '})();\n'
    dest = Path(out) / 'assets/article-v1.js'
    dest.write_text(js)


def article_html(html):
    # Only article pages use this stable ABI. Other pages keep their normal
    # versioned module graph. No generation identifier leaks into article HTML.
    # 대체 글꼴 맞추기(pf.js)는 기사 HTML 에 넣지 않는다 — 넣으면 그 스크립트를 고칠 때마다 기사 6,000쪽이 다시 바뀐다
    html = re.sub(r'<script>// 대체 글꼴 맞추기[\s\S]*?</script>\n', '', html, count=1)
    html = re.sub(r'<link[^>]+href="[^\"]*assets/(?:df/(?:lk|st)\.css|fonts/(?:subsets|inter)\.css)\?v=[^\"]+"[^>]*>','',html)
    html = re.sub(r'<script src="([^\"]*)assets/df/data\.js\?v=[^\"]+"></script>\s*<script>DFI.init\([\s\S]*?</script>\s*<script src="[^\"]*assets/df/st\.js\?v=[^\"]+"></script>',
                  r'<script src="\1assets/article-v1.js"></script>',html)
    html = re.sub(r"<script>\(\(\)=>\{let m;const L=\(\)=>m=m\|\|import\('[^']*assets/df/acct\.js\?v=[^']*'\)[\s\S]*?</script>", '', html, count=1)   # 회원 불러오기는 article-v1.js 안에
    return html
