"""국면 지도 축 이름과 오른쪽 위 칸 이름의 실제 글자 윤곽은 겹치지 않는다."""
import pytest


@pytest.mark.parametrize("width", [320, 390])
def test_regime_axis_labels_do_not_overlap(width, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','en')")
    page.add_init_script("""(() => {
      window.__regimeLabels={};
      const fill=CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText=function(text,x,y,...rest){
        if(this.canvas.id==='rgc'){
          const m=this.measureText(text);
          __regimeLabels[text]={left:x-m.actualBoundingBoxLeft,right:x+m.actualBoundingBoxRight,
            top:y-m.actualBoundingBoxAscent,bottom:y+m.actualBoundingBoxDescent};
        }
        return fill.call(this,text,x,y,...rest);
      };
    })();""")
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(site_server + 'calendar/', wait_until='networkidle')
    page.evaluate('document.fonts.ready')
    for size in (width, 768, 1440):
        page.set_viewport_size({"width": size, "height": 1000})
        page.wait_for_timeout(200)
        labels = page.evaluate('window.__regimeLabels')
        axis, corner = labels['↑ prices hotter'], labels['Overheating']
        overlap = (axis['left'] < corner['right'] and axis['right'] > corner['left']
                   and axis['top'] < corner['bottom'] and axis['bottom'] > corner['top'])
        assert not overlap, (size, axis, corner)
        canvas_width = page.locator('#rgc').evaluate('e=>e.clientWidth')
        assert axis['left'] >= 0 and axis['right'] <= canvas_width
        assert axis['top'] >= 0
