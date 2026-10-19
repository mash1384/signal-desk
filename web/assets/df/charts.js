// One pinned library download, only when a chart enters the viewport.
let pending;
function library() {
  if (window.LightweightCharts) return Promise.resolve();
  if (!pending) pending = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js';
    script.onload = () => window.LightweightCharts ? resolve() : reject(new Error('chart library missing'));
    script.onerror = reject;
    document.head.appendChild(script);
  }).catch(error => { pending = null; throw error; });
  return pending;
}
const waiting = new Map(), current = new WeakMap();
let observer;
export function whenVisible(el, draw, failed = () => {}) {
  // Rerenders may detach pending charts without explicitly destroying them.
  for (const [box, cancel] of waiting) if (!box.isConnected) cancel();
  current.get(el)?.();
  let active = true;
  const cancel = () => { active = false; observer?.unobserve(el); waiting.delete(el); };
  current.set(el, cancel);
  const run = () => {
    observer?.unobserve(el); waiting.delete(el);
    library().then(() => { if (active && el.isConnected) draw(); }, () => { if (active && el.isConnected) failed(); });
  };
  if (!('IntersectionObserver' in window)) run();
  else {
    observer ||= new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) entry.target.__drawVisible?.();
    });
    el.__drawVisible = run;
    waiting.set(el, cancel); observer.observe(el);
  }
  return cancel;
}
