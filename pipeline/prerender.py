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


def insert(html, variants, responsive=False):
    if not variants:
        return html
    templates = ''.join('<template data-prerender="%s">%s</template>' % (key, value) for key, value in variants.items())
    suffix = "+(matchMedia('(min-width:1040px)').matches?'-wide':'-narrow')" if responsive else ''
    boot = "<script>(()=>{const app=document.getElementById('app'),key=(document.documentElement.lang==='ko'?'ko':'en')%s,t=document.querySelector('template[data-prerender=\"'+key+'\"]');if(t){app.replaceChildren(t.content.cloneNode(true));app.dataset.prerender='1'}document.querySelectorAll('template[data-prerender]').forEach(t=>t.remove())})()</script>" % suffix
    return html.replace('<main id="app"></main>', '<main id="app"></main>' + templates + boot)
