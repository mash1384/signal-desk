import { every } from './lk.js?v=e2db2637';
import { calendarLayout } from './cv.js?v=e2db2637';
import * as E from './ek.js?v=e2db2637';
import { mount } from './cc.js?v=e2db2637';
let rel = null;
try { rel = JSON.parse(document.getElementById('prerender-release')?.textContent || 'null'); } catch (e) {}
mount((doc,S) => calendarLayout(doc,S,rel), {
  after: (root, doc) => { E.drawRelease(root, rel); E.drawRegime(root, doc); E.drawPaths(root, doc); E.drawTimeline(root, doc); E.drawFomc(root, doc); },
  resize: (root, doc) => { E.drawRelease(root, rel); E.drawRegime(root, doc); E.drawPaths(root, doc); E.drawTimeline(root, doc); E.drawFomc(root, doc); },
  live: (doc, rerender) => {
    const pull = () => E.loadRelease().then((items) => { const r = E.recent(items)[0] || null; if ((r && r.updated) !== (rel && rel.updated) || (r && r.id) !== (rel && rel.id)) { rel = r; rerender(); } });
    pull();
    every(() => { const now = Date.now() / 1000; if ((doc.upcoming || []).some((u) => u.ts - now < 2 * 3600 && now - u.ts < 3 * 3600)) pull(); }, 20000);
  },
});
