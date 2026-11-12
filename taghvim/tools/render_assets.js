// Renders the widget artwork (occasion icons, prayer-time scenes, day backgrounds) to PNG files for the Android app.
// Usage (needs Node and Playwright): node taghvim/tools/render_assets.js
// Input: tools/icons.json (SVG shapes) and tools/themes.css (background gradients). Output: app/src/main/res/drawable-nodpi.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const out = path.join(root, 'app/src/main/res/drawable-nodpi');
fs.mkdirSync(out, { recursive: true });

const icons = JSON.parse(fs.readFileSync(path.join(__dirname, 'icons.json'), 'utf8'));
const themeCss = fs.readFileSync(path.join(__dirname, 'themes.css'), 'utf8');
const themes = [...themeCss.matchAll(/\.th-([a-z]+)\{/g)].map(m => m[1]);

const items = [];
for (const [k, body] of Object.entries(icons.motifs)) {
  items.push({ file: `ic_${k}.png`, size: 96, html: `<svg viewBox="0 0 24 24" width="96" height="96">${body}</svg>` });
}
for (const [k, body] of Object.entries(icons.prayer)) {
  items.push({ file: `pr_${k}.png`, size: 120, html: `<svg class="sq" viewBox="0 0 40 40" width="120" height="120">${body}</svg>` });
}
for (const t of themes) {
  items.push({ file: `bg_${t}.png`, size: 120, html: `<div class="sq th-${t}" style="width:120px;height:120px;background:var(--thbg)"></div>` });
}
const soft = { nat: 'rgba(91,192,235,.40)', rel: 'rgba(165,147,255,.45)', gre: 'rgba(111,208,138,.36)', today: '#ffffff' };
for (const [k, c] of Object.entries(soft)) {
  items.push({ file: k === 'today' ? 'bg_today.png' : `bg_soft_${k}.png`, size: 120, html: `<div class="sq" style="width:120px;height:120px;background:${c}"></div>` });
}

// the yellow frame of a tapped day (white here, tinted with the accent colour in the app)
items.push({ file: 'bg_select.png', size: 120, html: `<svg viewBox="0 0 120 120" width="120" height="120"><path d="M0,60 C0,12 12,0 60,0 C108,0 120,12 120,60 C120,108 108,120 60,120 C12,120 0,108 0,60Z" transform="translate(7 7) scale(0.883)" fill="none" stroke="#fff" stroke-width="10"/></svg>` });

const page = `<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;background:transparent}
.item{width:120px;height:120px;display:grid;place-items:center;position:absolute;left:0;top:0}
.sq{clip-path:url(#sq)}
${themeCss}
</style>
<svg width="0" height="0" style="position:absolute"><defs><clipPath id="sq" clipPathUnits="objectBoundingBox"><path d="M0,0.5 C0,0.1 0.1,0 0.5,0 C0.9,0 1,0.1 1,0.5 C1,0.9 0.9,1 0.5,1 C0.1,1 0,0.9 0,0.5 Z"/></clipPath></defs></svg>
<div id="stage"></div>`;

(async () => {
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 200, height: 200 } });
  await p.setContent(page);
  for (const it of items) {
    await p.evaluate(h => { document.getElementById('stage').innerHTML = '<div class="item" id="cur">' + h + '</div>'; }, it.html);
    const el = await p.$('#cur');
    await el.screenshot({ path: path.join(out, it.file), omitBackground: true });
  }
  await browser.close();
  console.log('rendered', items.length, 'images into', out);
})();
