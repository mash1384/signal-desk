"""Exercise the release-present branch absent from the public flash snapshot."""
import copy
import json
import pytest
from tests.check_site import validate
from tests.schema.test_review_contracts import RELEASE_PATH


@pytest.mark.parametrize('lang', ['ko', 'en'])
def test_release_chart_draws_and_reads_prices(session_page, site_server, lang):
    page, context, offline = session_page
    doc = json.loads(RELEASE_PATH.read_text())
    assert validate('flash', doc) == []
    doc = copy.deepcopy(doc)
    rel = doc['release']['items'][0]
    delta = offline.now - doc['at']
    doc['at'] += delta
    rel['ts'] += delta
    rel['updated'] += delta
    for market in rel['market'].values():
        for point in market['pts']:
            point[0] += delta
    context.route('https://signal-scheduler.mash1384.workers.dev/flash',
                  lambda route: route.fulfill(json=doc, headers={'access-control-allow-origin': '*'}))
    context.add_init_script("localStorage.setItem('df-lang', %s)" % json.dumps(lang))
    page.goto(site_server + 'calendar/', wait_until='networkidle')
    canvas = page.locator('#mxc')
    canvas.wait_for(state='visible')
    page.wait_for_function("document.querySelector('#mxc').height >= 230")
    assert canvas.evaluate('(c) => c.getContext("2d").getImageData(0,0,c.width,c.height).data.some((v,i) => i%4===3 && v>0)'), 'release chart is blank'
    canvas.focus()
    canvas.press('Home')
    first = page.locator('#mxr').inner_text()
    canvas.press('End')
    last = page.locator('#mxr').inner_text()
    assert first and last and first != last
    assert 'NaN' not in last and 'Infinity' not in last
    assert ('비트코인' if lang == 'ko' else 'Bitcoin') in last
    assert '+1.50%' in last, last
