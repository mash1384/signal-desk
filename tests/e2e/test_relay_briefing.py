"""분야 판독의 경계 입력과 근거 버튼을 실제 브라우저에서 확인한다(외부 요청은 Offline)."""
import json
from unittest import mock

import pytest
from pipeline import build
from tests.unit.test_briefing_page import doc as fixture_doc


@pytest.mark.parametrize("mode", ["escape", "missing-english", "malformed-parts", "stale", "source"])
def test_desk_contract(mode, session_page, site_server):
    page, _, _ = session_page
    page.goto(site_server + 'themes/crypto/', wait_until='networkidle')
    result = page.evaluate("""async (mode) => {
      const version=new URL(document.querySelector('link[rel="modulepreload"][href*="/t2.js"]').href).search;
      const K=await import('../../assets/df/tk.js'+version), LK=await import('../../assets/df/lk.js'+version);
      const id='r\" autofocus onfocus=\"window.__relayXss=1', text='<img src=x onerror=alert(1)>';
      LK.store.byId.set(id,{id,ko:'근거 소식',en:'Source story',t:Date.now()/1000,v:'중립',s:1,n:1});
      const x={state:text,refs:[id],drivers:[{s:text,refs:[id]}]}, d={made:Date.now()/1000,desks:{crypto:{ko:x,en:x}}};
      if(mode==='missing-english') d.desks.crypto={};
      if(mode==='malformed-parts') { x.drivers={}; x.refs={}; }
      if(mode==='stale') d.made-=49*3600;
      const html=K.deskHTML(d,'crypto'), template=document.createElement('template'); template.innerHTML=html;
      const b=template.content.querySelector('[data-id]');
      if(mode==='source') {
        document.querySelector('.tsum').innerHTML=html;
        document.querySelector('.tsum [data-id]').click();
        return {open:document.querySelector('#sheet').classList.contains('on'), text:document.querySelector('#det').textContent};
      }
      return {html,id:b?.dataset.id,unsafe:!!template.content.querySelector('img,[onfocus],[autofocus]'),expected:id};
    }""", mode)
    if mode in ('missing-english', 'stale'):
        assert result['html'] == ''
    elif mode == 'malformed-parts':
        assert result['html'] and not result['unsafe']
    elif mode == 'source':
        assert result['open'] and any(t in result['text'] for t in ('근거 소식', 'Source story'))
    else:
        assert not result['unsafe'], result
        assert result['id'] == result['expected']
        assert '&lt;img' in result['html']


@pytest.mark.parametrize('payload', [None, {'stories': {'x': None}}])
def test_null_briefing_does_not_break_theme(payload, session_page, site_server):
    page, context, _ = session_page
    context.route('**/daily/briefing.json*', lambda route: route.fulfill(body=json.dumps(payload), content_type='application/json'))
    page.goto(site_server + 'themes/crypto/', wait_until='networkidle')
    page.wait_for_function("document.querySelector('#stories .srow') && document.querySelector('.tsum li')")


@pytest.mark.parametrize('kind', ['fresh', 'missing', 'stub', 'stale'])
def test_briefing_languages_and_source(kind, session_page, site_server, tmp_path):
    page, context, offline = session_page
    data = fixture_doc(made=offline.now - (49 * 3600 if kind == 'stale' else 3600), next=offline.now + 3600)
    (tmp_path / 'daily').mkdir()
    if kind != 'missing':
        (tmp_path / 'daily/briefing.json').write_text(json.dumps({'v': 0} if kind == 'stub' else data))
    # 실제 렌더러를 합성 자료로 실행한다. 운영 파일의 유무나 현재 시각이 검사 결과를 바꾸지 않는다.
    with mock.patch.object(build.config, 'FLASH_DIR', str(tmp_path)):
        html = build.page_brief_df(offline.now)
    context.route(site_server + 'brief/', lambda route: route.fulfill(body=html, content_type='text/html'))
    page.goto(site_server + 'brief/', wait_until='networkidle')
    for lang in ('ko', 'en'):
        page.locator('[data-lang="%s"]' % lang).click()
        assert page.locator('.lanes .lane[data-pick]').count() > 0
        if kind != 'fresh':
            assert page.locator('#bf, #bf-stories').count() == 0
            continue
        assert page.locator('#bf .bf-c').count() == 3
        assert page.locator('#bf h1').inner_text() == data[lang]['headline']
        page.locator('#bf [data-bf]').first.click()
        assert page.locator('#sheet').get_attribute('aria-hidden') == 'false'
        assert page.locator('#det').inner_text().strip()
        page.keyboard.press('Escape')
        assert page.locator('#sheet').get_attribute('aria-hidden') == 'true'
