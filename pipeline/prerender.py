"""Render public snapshots using the browser's shared markup functions."""
import json
import os
from pathlib import Path
import subprocess

from . import config


def render(root):
    source = Path(config.FLASH_DIR)
    names = {'flash': source / 'flash.json', 'threads': source / 'daily/threads.json', 'econ': source / 'daily/econ.json'}
    # Brand-new installation: the established loading UI remains available.
    if not all(p.is_file() for p in names.values()):
        return {}
    data = {k: json.loads(p.read_text()) for k, p in names.items()}
    daily = source / 'daily' / (data['threads'].get('daily_latest', '') + '.json')
    data['daily'] = json.loads(daily.read_text()) if daily.is_file() else None
    repo = Path(__file__).resolve().parents[1]
    data.update(now=data['flash']['at'], root=root, en=json.loads((repo / 'web/assets/df/en.json').read_text()))
    env = {k: v for k, v in os.environ.items() if k not in ('NODE_OPTIONS', 'NODE_PATH')}
    env['TZ'] = 'Asia/Seoul'
    result = subprocess.run(['node', '--permission',
                             '--allow-fs-read=' + str(repo / 'web'),
                             '--allow-fs-read=' + str(repo / 'pipeline/prerender.mjs'),
                             str(repo / 'pipeline/prerender.mjs')], input=json.dumps(data), text=True,
                            capture_output=True, env=env, timeout=30, check=True)
    return json.loads(result.stdout)


# 글꼴이 준비된 뒤(최대 4초 — 저속 모바일은 1초로 부족했다, CI 측정) 넣는 방식: 미리 그린 글이 대체 글꼴로 먼저 보였다가 Pretendard 로 바뀌며 줄이 밀리는 것을 막는다.
# (Linux · Windows 처럼 기본 한글 글꼴의 크기가 Pretendard 와 다른 환경에서 CLS 0.13~0.16 — 2026-10-19 CI 측정)
# 그사이 화면 JS 가 실제 데이터를 먼저 그렸으면(#app 이 비어 있지 않으면) 미리 그린 내용은 버린다 — 최악이어도 미리 그리기 전과 같은 동작.
WAIT_FONTS = ("(()=>{const app=document.getElementById('app'),key=(document.documentElement.lang==='ko'?'ko':'en')%s,"
              "t=document.querySelector('template[data-prerender=\"'+key+'\"]');"
              "document.querySelectorAll('template[data-prerender]').forEach(x=>{if(x!==t)x.remove()});if(!t)return;app.dataset.prerender='1';"
              "const go=()=>{if(!app.childElementCount)app.replaceChildren(t.content.cloneNode(true));t.remove()},f=document.fonts;"
              "if(!f||!f.load){go();return}const s=t.content.textContent.replace(/\\s+/g,' ').slice(0,6000);"
              "Promise.race([Promise.all(['400 16px \"Pretendard Variable\"','700 16px \"Pretendard Variable\"','400 16px \"JetBrains Mono\"']"
              ".map(q=>f.load(q,s).catch(()=>0))),new Promise(r=>setTimeout(r,4000))]).then(go)})()")


def insert(html, variants, responsive=False, wait_fonts=False):
    if not variants:
        return html
    templates = ''.join('<template data-prerender="%s">%s</template>' % (key, value) for key, value in variants.items())
    suffix = "+(matchMedia('(min-width:1040px)').matches?'-wide':'-narrow')" if responsive else ''
    if wait_fonts:
        return html.replace('<main id="app"></main>', '<main id="app"></main>' + templates + '<script>' + WAIT_FONTS % suffix + '</script>')
    boot = "<script>(()=>{const app=document.getElementById('app'),key=(document.documentElement.lang==='ko'?'ko':'en')%s,t=document.querySelector('template[data-prerender=\"'+key+'\"]');if(t){app.replaceChildren(t.content.cloneNode(true));app.dataset.prerender='1'}document.querySelectorAll('template[data-prerender]').forEach(t=>t.remove())})()</script>" % suffix
    return html.replace('<main id="app"></main>', '<main id="app"></main>' + templates + boot)
