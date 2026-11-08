// The TK carousel renderer (the owner's tk-topic-carousel kit, carousel.mjs): a spec.json -> 1080x1350 PNG slides.
//   node tools/carousel/carousel.mjs spec.json out      -> prints FILE: lines (01_cover.png, 02_slide.png …)
// The TK overlay (Black_temp.png, White_temp.png) and the optional Bahij font live in brand/carousel/ (kept out of git;
// TK_CAROUSEL_ASSETS points elsewhere). Without them the overlay is drawn as a plain TIME KEEPER band.
import fs from 'fs'; import path from 'path'; import { createRequire } from 'module';
const require = createRequire(import.meta.url); const { chromium } = require('playwright'); const { execFileSync } = require('child_process');
const [specPath, outDir = 'out'] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8')); const base = path.dirname(path.resolve(specPath));
const HERE = path.dirname(new URL(import.meta.url).pathname);
const A = p => p ? 'file://' + (path.isAbsolute(p) ? p : path.join(base, p)) : '';
const ASSETS = process.env.TK_CAROUSEL_ASSETS || path.join(HERE, '..', '..', 'brand', 'carousel');   // the TK overlay PNGs (not in git)
const asset = f => { const p = path.join(ASSETS, f); return fs.existsSync(p) ? 'file://' + p : null; };
const OV_W = asset('White_temp.png'), OV_B = asset('Black_temp.png'), BAHIJ = asset('Bahij-Helvetica-Neue-Bold.ttf'), BAHIJ_R = asset('Bahij-Helvetica-Neue-Roman.ttf');
const font = BAHIJ ? `@font-face{font-family:TK;src:url('${BAHIJ}');font-weight:800}@font-face{font-family:TK;src:url('${BAHIJ_R || BAHIJ}');font-weight:500}` :
  `@font-face{font-family:TK;src:url('file://${HERE}/fonts/tajawal-arabic-800-normal.woff2');font-weight:800}@font-face{font-family:TK;src:url('file://${HERE}/fonts/tajawal-arabic-500-normal.woff2');font-weight:500}`;
// Text sizes in px on the 1080×1350 slide. The owner: «the size of the text, it is small… increase it about 10%»
// (was title 74, body 40, reader's question 58, name 28, number 30, cover line 78). Keep studio-page's KIT.SIZE the same.
// Time Keeper's own green, the secondary colour of its posts (the owner, 8 Nov 2026: «use the same green as the secondary
// color»): key words, the reader's question, the cover's «اسحب للمزيد».
const TK_GREEN = '#2C6048';
const SIZE = { title: 81, body: 44, ask: 64, name: 31, num: 33, cover: 86 };
const PAPER = spec.paper || '#f3ead6', INK = spec.ink || '#1c1510', ACCENT = spec.accent || TK_GREEN;
const overlay = (dark) => { const f = dark ? OV_B : OV_W; if (f) return `<img class="ov" src="${f}">`;
  const c = dark ? '#111' : '#fff'; return `<div class="ph" style="color:${c}"><div class="ph-top">TIME KEEPER</div><div class="ph-bot">@timekeeperkw</div></div>`; };
const css = `${font}*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1350px;overflow:hidden}
body{font-family:TK,sans-serif;direction:rtl;background:${PAPER};color:${INK};position:relative}
.ov{position:absolute;left:0;top:-25px;width:1080px;height:1350px;object-fit:fill;z-index:2}
.ph{position:absolute;inset:0;z-index:2;direction:ltr;font-family:Georgia,serif;letter-spacing:.3em;text-align:center}
.ph-top{position:absolute;top:70px;left:70px;font-size:30px;font-weight:700}.ph-bot{position:absolute;top:76px;right:70px;font-size:22px;letter-spacing:.12em}   /* like the real overlay: logo top-left, handle top-right */
.photo{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1}
#hw{position:absolute;right:52px;left:52px;bottom:196px;z-index:3}
.hb{display:block;width:fit-content;margin-left:auto;padding:5px 22px 6px;margin-bottom:7px;max-width:940px;line-height:1.02;white-space:nowrap;font-weight:800}
.fig{position:absolute;z-index:1}
.txt{position:absolute;z-index:3;text-align:right}
.num{display:block;width:fit-content;margin:0 0 24px auto;padding:4px 16px 6px;background:#111111;color:#FFFFFF;font-size:${SIZE.num}px;font-weight:800;letter-spacing:.05em;direction:ltr}
.head{position:absolute;top:200px;left:40px;right:40px;display:flex;align-items:center;justify-content:space-between;z-index:3}
.head .ht{font-size:40px;font-weight:800;color:${INK}}.head .num{margin:0}
.cards{position:absolute;top:276px;left:40px;right:40px;bottom:46px;display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:1fr;gap:22px;z-index:3}
.card{border:3px solid ${ACCENT};border-radius:30px;padding:18px 14px 16px;display:flex;flex-direction:column;align-items:center;text-align:center;min-height:0}
.card .ct{font-size:30px;font-weight:800;color:${ACCENT};line-height:1.15;min-height:70px;display:flex;align-items:center}
.card .ci{flex:1;min-height:0;width:100%;object-fit:contain;margin:8px 0}
.card .cb,.hero .cb{font-size:24px;font-weight:800;direction:ltr;letter-spacing:.04em}
.card .cm,.hero .cm{font-size:21px;font-weight:500;direction:ltr;line-height:1.25}
.card .cr,.hero .cr{font-size:19px;font-weight:500;color:${ACCENT};direction:ltr;margin-top:8px;letter-spacing:.06em;font-family:Menlo,monospace}
.hero{position:absolute;top:276px;left:40px;right:40px;bottom:46px;border:3px solid ${ACCENT};border-radius:34px;z-index:3}
.hero .hi{position:absolute;top:40px;left:60px;right:60px;bottom:270px;width:calc(100% - 120px);height:calc(100% - 310px);object-fit:contain}
.hero .hc{position:absolute;right:40px;bottom:40px;text-align:right}.hero .ht2{font-size:46px;font-weight:800;margin-bottom:6px}
.hero .cb{font-size:30px}.hero .cm{font-size:28px}
.seal{position:absolute;width:230px;height:230px;border-radius:50%;background:${ACCENT};color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;box-shadow:0 0 0 8px #fff,0 0 0 11px ${ACCENT};z-index:4;font-weight:800;line-height:1.15}
.seal b{font-size:40px}.seal i{font-style:normal;font-size:24px;font-weight:500;margin-top:6px}
.pc{position:absolute;top:276px;left:40px;right:40px;bottom:46px;z-index:3}
.pc .pi{position:absolute;top:0;left:40px;right:40px;width:calc(100% - 80px);height:600px;object-fit:contain}
.pc .pt{position:absolute;top:628px;right:24px;left:24px;text-align:right;border-top:4px solid ${ACCENT};padding-top:22px}
.pc .pk{font-size:36px;font-weight:800;color:${ACCENT};margin-bottom:10px}
.pc .cb{font-size:40px;font-weight:800;direction:ltr;letter-spacing:.04em}.pc .cm{font-size:31px;font-weight:500;direction:ltr;line-height:1.3}
.pc .cr{font-size:24px;font-weight:500;color:${ACCENT};direction:ltr;margin-top:6px;letter-spacing:.06em;font-family:Menlo,monospace}
.pc .pp{font-size:88px;font-weight:800;line-height:1.1;margin-top:20px}.pc .po{font-size:29px;font-weight:500;opacity:.75}
.end{position:absolute;inset:0;background:${TK_GREEN};color:#fff;z-index:1;display:flex;flex-direction:column;justify-content:center;padding:0 90px;text-align:right}
.end .et{font-size:${SIZE.title + 9}px;font-weight:800;line-height:1.15;margin-bottom:30px}.end .eb{font-size:${SIZE.body}px;font-weight:500;line-height:1.55}
.end .eh{margin-top:44px;font-size:40px;font-weight:800;direction:ltr;text-align:right;letter-spacing:.04em}
.ch{position:absolute;top:252px;left:36px;right:36px;bottom:40px;z-index:3}
.ch .ct{font-size:52px;font-weight:800;line-height:1.15}.ch .cs{font-size:28px;font-weight:500;opacity:.7;margin:6px 0 14px}
.ch .rows{display:flex;flex-direction:column}
.ch .r{display:grid;grid-template-columns:300px 50px 1fr;align-items:center;column-gap:12px;border-top:1px solid #e3e3e3}
.ch .rl{text-align:right;direction:ltr;line-height:1.05;overflow:hidden;white-space:nowrap}.ch .rl b{display:block;font-size:20px;font-weight:800;letter-spacing:.02em}.ch .rl i{font-style:normal;font-size:16px;opacity:.7}
.ch .ri{width:50px;height:46px;object-fit:contain}
.ch .rb{display:flex;align-items:center;gap:10px;direction:rtl}.ch .bar{height:24px;background:${ACCENT};border-radius:4px 0 0 4px;flex:none}
.ch .rv{font-size:24px;font-weight:800;white-space:nowrap}
.sw{margin-top:14px;font-size:40px;font-weight:800;color:${TK_GREEN};text-align:right}.sw .ar{letter-spacing:-.18em;margin-left:16px}
.ttl{font-size:${SIZE.title}px;font-weight:800;line-height:1.12;margin-bottom:26px}
.nm{font-size:${SIZE.name}px;font-weight:500;opacity:.75;direction:ltr;text-align:right;margin:-14px 0 22px}
.bd{font-size:${SIZE.body}px;font-weight:500;line-height:1.55}
.bd b{color:${ACCENT};font-weight:800}
.ask{font-size:${SIZE.ask}px;font-weight:800;line-height:1.3;color:${ACCENT};margin-top:26px}
.rule{width:120px;height:6px;background:${ACCENT};margin:0 0 26px auto}`;
const LAYOUTS = {
  topImage: { fig: 'left:-40px;top:130px;width:1160px;height:700px;object-fit:contain', txt: 'right:80px;left:80px;top:850px' },
  rightBleed: { fig: 'right:-300px;top:200px;width:900px;height:950px;object-fit:contain', txt: 'right:620px;left:60px;top:300px' },
  leftBleed: { fig: 'left:-300px;top:200px;width:900px;height:950px;object-fit:contain', txt: 'right:70px;left:620px;top:300px' },
  bottomImage: { fig: 'left:-20px;bottom:-60px;width:1120px;height:760px;object-fit:contain', txt: 'right:80px;left:80px;top:270px' },
  bigCorner: { fig: 'left:-200px;bottom:-300px;width:880px;height:850px;object-fit:contain', txt: 'right:80px;left:300px;top:270px' },
  // the photo is the slide (tools/carousel/full_photo.py made it 1080×1350, faded into its paper); the text sits on the paper
  full: { fig: 'left:0;top:0;width:1080px;height:1350px', txt: 'right:80px;left:80px;bottom:64px' },
};
// A watch or a movement is shown whole (references/carousel.md): its picture stays inside the slide, never bled off it.
const WHOLE = {
  topImage: 'left:60px;top:150px;width:960px;height:680px;object-fit:contain',
  bottomImage: 'left:60px;bottom:50px;width:960px;height:620px;object-fit:contain',
};
// With the bigger text the fixed boxes no longer fit, so on topImage and bottomImage the picture takes the room the text
// leaves: the text is measured first, then the picture fills the rest (never under PIC_MIN tall; a shorter one is a WARN).
const BOTTOM = 1290, GAP = 24, PIC_MIN = 420;
const fitScript = `<script>document.fonts.ready.then(()=>{const t=document.querySelector('.txt'),f=document.querySelector('.fig'),L=t.dataset.layout;if(!f)return;
const h=t.offsetHeight;if(L==='topImage'){if(document.body.dataset.big)f.style.top='210px';const top=Math.min(document.body.dataset.big?${BOTTOM}:850,${BOTTOM}-h);t.style.top=top+'px';f.style.height=Math.max(0,top-${GAP}-parseFloat(f.style.top))+'px'}
if(L==='bottomImage'){const y=t.offsetTop+h+${GAP},end=f.dataset.end*1;f.style.top=y+'px';f.style.bottom='auto';f.style.height=Math.max(0,end-y)+'px'}})</script>`;
const order = ['topImage', 'rightBleed', 'bottomImage', 'leftBleed', 'bigCorner'];
const lum = (hex) => { const m = String(hex).match(/^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i); return m ? 0.299 * parseInt(m[1], 16) + 0.587 * parseInt(m[2], 16) + 0.114 * parseInt(m[3], 16) : 255; };
function bright(img) { try { return parseFloat(execFileSync('python3', ['-c', "import sys;from PIL import Image;im=Image.open(sys.argv[1]).convert('L').resize((64,64));print(sum(im.getpixel((x,y)) for x in range(8,56) for y in range(4,12))/384)", img]).toString()); } catch { return 0; } }
// A ranking chart (the owner, 8 Nov 2026: «نخليها غراف بالترتيب من اغلى الى الاقل»): one bar a piece, longest first,
// growing right to left from the names, in TK green, the value at each bar's end. Linear, so the gap shows; a bar is
// never under 4px, so the smallest still shows. As the cover: `"cover": {"type": "chart", ...}`.
function chartHtml(c) {
  const rows = c.rows || [], max = Math.max(...rows.map(r => +r.value || 0)), W = c.bar_width || 500;
  return `<html><head><style>${css}</style></head><body><div class="ch"><div class="ct">${c.title || ''}</div>${c.sub ? `<div class="cs">${c.sub}</div>` : ''}<div class="rows">${rows.map(r => `<div class="r" style="height:${c.row || 47}px"><div class="rl"><b>${r.label || ''}</b><i>${r.model || ''}</i></div>${r.image ? `<img class="ri" src="${A(r.image)}">` : '<span></span>'}<div class="rb"><span class="bar" style="width:${Math.max(4, Math.round(W * (+r.value || 0) / max))}px"></span><span class="rv">${r.text || ''}</span></div></div>`).join('')}</div>${c.swipe === false ? '' : '<div class="sw" style="margin-top:8px;font-size:30px"><span class="ar">▶▶</span>اسحب للمزيد</div>'}</div>${overlay(true)}</body></html>`;
}
function coverHtml(c) {
  if (c.type === 'chart') return chartHtml(c);
  const dark = c.palette ? c.palette === 'light' : bright(A(c.image).slice(7)) > 150;
  const box = c.box === 'dark' ? ['#111111', '#FFFFFF'] : ['#FFFFFF', '#111111'];
  return `<html><head><style>${css}</style></head><body><img class="photo" src="${A(c.image)}">${overlay(dark)}
  ${c.badge ? `<div class="seal" style="top:${c.badge.top ?? 215}px;right:${c.badge.right ?? 30}px;width:${c.badge.size ?? 190}px;height:${c.badge.size ?? 190}px"><b style="font-size:${Math.round((c.badge.size ?? 190) / 6)}px">${c.badge.text}</b>${c.badge.sub ? `<i style="font-size:${Math.round((c.badge.size ?? 190) / 10)}px">${c.badge.sub}</i>` : ''}</div>` : ''}
  <div id="hw"${c.gap != null ? ` style="bottom:${+c.gap}px"` : ''}>${[c.top, c.bottom].filter(Boolean).map(s => `<div class="hb" style="background:${box[0]};color:${box[1]}">${s}</div>`).join('')}${c.swipe === false ? '' : (() => { const lt = c.swipe === 'light' || !dark; return `<div class="sw"${lt ? ' style="color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.6)"' : ''}><span class="ar"${lt ? ` style="color:${TK_GREEN};text-shadow:0 0 2px #fff"` : ''}>▶▶</span>اسحب للمزيد</div>`; })()}</div>
  <script>const fit=()=>{for(const b of document.querySelectorAll('.hb')){let f=${SIZE.cover};b.style.fontSize=f+'px';while(b.scrollWidth>940&&f>32){f-=2;b.style.fontSize=f+'px'}}};fit();document.fonts.ready.then(fit)</script></body></html>`;
}
// The awards style (learnt from a list carousel the owner liked, 8 Nov 2026): one header line on every slide, the top
// winner alone in a frame with a seal, then six outlined cards a slide: category, the watch, brand, model, reference.
function headHtml(s, i, n) { return `<div class="head"><div class="ht">${s.head || spec.head || ''}</div><div class="num">${String(i + 1).padStart(2, '0')} / ${String(n).padStart(2, '0')}</div></div>`; }
function cardsHtml(s, i, n) {
  return `<html><head><style>${css}</style></head><body>${headHtml(s, i, n)}<div class="cards">${(s.cards || []).map(c => `<div class="card"><div class="ct">${c.title}</div><img class="ci" src="${A(c.image)}"><div class="cb">${c.brand || ''}</div><div class="cm">${c.model || ''}</div>${c.ref ? `<div class="cr">REF. ${c.ref}</div>` : ''}</div>`).join('')}</div>${overlay(true)}</body></html>`;
}
function heroHtml(s, i, n) {
  return `<html><head><style>${css}</style></head><body>${headHtml(s, i, n)}<div class="hero"><img class="hi" src="${A(s.image)}"><div class="hc"><div class="ht2">${s.title}</div><div class="cb">${s.brand || ''}</div><div class="cm">${s.model || ''}</div>${s.ref ? `<div class="cr">REF. ${s.ref}</div>` : ''}</div>${s.badge ? `<div class="seal" style="left:44px;bottom:44px"><b>${s.badge.text}</b>${s.badge.sub ? `<i>${s.badge.sub}</i>` : ''}</div>` : ''}</div>${overlay(true)}</body></html>`;
}
// The price-list style (learnt 8 Nov 2026 from a menu-like carousel the owner liked, in TK's identity): the header line,
// one watch a slide on its own white ground, then the category, BRAND, model, REF. and the price in dinars, large, with
// the official price it comes from in a small line. The last slide can be the TK green card (`"type": "end"`).
function priceHtml(s, i, n) {
  return `<html><head><style>${css}</style></head><body>${headHtml(s, i, n)}<div class="pc"><img class="pi" src="${A(s.image)}"><div class="pt">${s.title ? `<div class="pk">${s.title}</div>` : ''}<div class="cb">${s.brand || ''}</div><div class="cm">${s.model || ''}</div>${s.ref ? `<div class="cr">REF. ${s.ref}</div>` : ''}<div class="pp">${s.price || ''}</div>${s.price_note ? `<div class="po">${s.price_note}</div>` : ''}</div></div>${overlay(true)}</body></html>`;
}
function endHtml(s, i, n) {
  return `<html><head><style>${css}</style></head><body><div class="end"><div class="et">${s.title || ''}</div>${s.body ? `<div class="eb">${s.body}</div>` : ''}<div class="eh">${s.handle || '@timekeeperkw'}</div></div>${overlay(false)}</body></html>`;
}
function slideHtml(s, i, n) {
  if (s.type === 'price') return priceHtml(s, i, n);
  if (s.type === 'end') return endHtml(s, i, n);
  if (s.type === 'cards') return cardsHtml(s, i, n);
  if (s.type === 'hero') return heroHtml(s, i, n);
  const name = s.layout || order[i % order.length], L = LAYOUTS[name];
  const fig = (s.watch && WHOLE[name]) || L.fig, end = s.watch ? 1300 : 1410;   // where a bottom picture ends: inside the slide, or bled off it
  // A photo on its own ground (a steel table, a portrait's grey) takes that ground as the slide's paper (`"paper"` on the
  // slide); a dark one turns the text and the logo white. The watch is never cut out of it.
  const sp = s.paper ? `background:${s.paper};color:${s.ink || (lum(s.paper) < 140 ? '#FFFFFF' : INK)}` : '', dk = s.paper && lum(s.paper) < 140;
  return `<html><head><style>${css}${dk ? '.bd b,.ask{color:#9ED8B9}' : ''}</style></head><body${spec.big ? ' data-big="1"' : ''}${sp ? ` style="${sp}"` : ''}>${s.image ? `<img class="fig" data-end="${end}" style="${fig}" src="${A(s.image)}">` : ''}
  <div class="txt" data-layout="${name}" style="${L.txt}"><div class="num">${String(i + 1).padStart(2, '0')} / ${String(n).padStart(2, '0')}</div>
  <div class="ttl">${s.title}</div>${s.name ? `<div class="nm">${s.name}</div>` : ''}<div class="bd">${s.body}</div>${s.ask ? `<div class="ask">${s.ask}</div>` : ''}</div>${overlay(!dk)}${fitScript}</body></html>`;
}
const browser = await chromium.launch(); const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } });
fs.mkdirSync(outDir, { recursive: true }); const files = [];
const shoot = async (html, name) => { const f = path.join(outDir, name); fs.writeFileSync(f + '.html', html); await page.goto('file://' + path.resolve(f + '.html')); await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(150); await page.screenshot({ path: f + '.png' }); fs.unlinkSync(f + '.html'); files.push(f + '.png'); };
// What the bigger text can break: it runs off the slide, or (picture below the text) into the picture. Printed as WARN: lines.
const fits = () => page.evaluate((PIC_MIN) => {
  const t = document.querySelector('.txt'); if (!t) { const f = parseFloat(document.querySelector('.hb')?.style.fontSize || 99); return f < 60 ? 'the cover line is long: its type shrank to ' + f + 'px' : ''; }
  const bottom = t.getBoundingClientRect().bottom, im = document.querySelector('.fig');
  if (im && ['topImage', 'bottomImage'].includes(t.dataset.layout) && im.getBoundingClientRect().height < PIC_MIN) return `the picture is squeezed to ${Math.round(im.getBoundingClientRect().height)}px by the text: shorten it`;
  if (im && t.dataset.layout === 'bigCorner' && im.naturalWidth) {
    const r = im.getBoundingClientRect(), k = Math.min(r.width / im.naturalWidth, r.height / im.naturalHeight);
    const top = r.top + (r.height - im.naturalHeight * k) / 2;
    if (bottom > top - 8) return `the text runs into the picture (${Math.round(bottom)} > ${Math.round(top)}): shorten it`;
  }
  return bottom > 1350 ? `the text runs off the slide (${Math.round(bottom)} > 1350): shorten it` : '';
}, PIC_MIN);
const warn = async (what) => { const w = await fits(); if (w) console.log(`WARN:${what}: ${w}`); };
await shoot(coverHtml(spec.cover), '01_cover'); await warn('cover');
for (let i = 0; i < spec.slides.length; i++) { await shoot(slideHtml(spec.slides[i], i, spec.slides.length), String(i + 2).padStart(2, '0') + '_slide'); await warn(`slide ${i + 1}`); }
await browser.close(); for (const f of files) console.log('FILE:' + f);
