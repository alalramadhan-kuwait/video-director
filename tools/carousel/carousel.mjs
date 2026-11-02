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
const OV_W = asset('White_temp.png'), OV_B = asset('Black_temp.png'), BAHIJ = asset('Bahij-Helvetica-Neue-Bold.ttf');
const font = BAHIJ ? `@font-face{font-family:TK;src:url('${BAHIJ}')}` :
  `@font-face{font-family:TK;src:url('file://${HERE}/fonts/tajawal-arabic-800-normal.woff2');font-weight:800}@font-face{font-family:TK;src:url('file://${HERE}/fonts/tajawal-arabic-500-normal.woff2');font-weight:500}`;
// Text sizes in px on the 1080×1350 slide. The owner: «the size of the text, it is small… increase it about 10%»
// (was title 74, body 40, reader's question 58, name 28, number 30, cover line 78). Keep studio-page's KIT.SIZE the same.
const SIZE = { title: 81, body: 44, ask: 64, name: 31, num: 33, cover: 86 };
const PAPER = spec.paper || '#f3ead6', INK = spec.ink || '#1c1510', ACCENT = spec.accent || '#a3172e';
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
.num{font-size:${SIZE.num}px;font-weight:800;color:${ACCENT};letter-spacing:.05em;margin-bottom:18px;direction:ltr;text-align:right}
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
const h=t.offsetHeight;if(L==='topImage'){const top=Math.min(850,${BOTTOM}-h);t.style.top=top+'px';f.style.height=Math.max(0,top-${GAP}-parseFloat(f.style.top))+'px'}
if(L==='bottomImage'){const y=t.offsetTop+h+${GAP},end=f.dataset.end*1;f.style.top=y+'px';f.style.bottom='auto';f.style.height=Math.max(0,end-y)+'px'}})</script>`;
const order = ['topImage', 'rightBleed', 'bottomImage', 'leftBleed', 'bigCorner'];
function bright(img) { try { return parseFloat(execFileSync('python3', ['-c', "import sys;from PIL import Image;im=Image.open(sys.argv[1]).convert('L').resize((64,64));print(sum(im.getpixel((x,y)) for x in range(8,56) for y in range(4,12))/384)", img]).toString()); } catch { return 0; } }
function coverHtml(c) {
  const dark = c.palette ? c.palette === 'light' : bright(A(c.image).slice(7)) > 150;
  const box = c.box === 'dark' ? ['#111111', '#FFFFFF'] : ['#FFFFFF', '#111111'];
  return `<html><head><style>${css}</style></head><body><img class="photo" src="${A(c.image)}">${overlay(dark)}
  <div id="hw">${[c.top, c.bottom].filter(Boolean).map(s => `<div class="hb" style="background:${box[0]};color:${box[1]}">${s}</div>`).join('')}</div>
  <script>for(const b of document.querySelectorAll('.hb')){let f=${SIZE.cover};b.style.fontSize=f+'px';while(b.scrollWidth>940&&f>32){f-=2;b.style.fontSize=f+'px'}}</script></body></html>`;
}
function slideHtml(s, i, n) {
  const name = s.layout || order[i % order.length], L = LAYOUTS[name];
  const fig = (s.watch && WHOLE[name]) || L.fig, end = s.watch ? 1300 : 1410;   // where a bottom picture ends: inside the slide, or bled off it
  return `<html><head><style>${css}</style></head><body>${s.image ? `<img class="fig" data-end="${end}" style="${fig}" src="${A(s.image)}">` : ''}
  <div class="txt" data-layout="${name}" style="${L.txt}"><div class="num">${String(i + 1).padStart(2, '0')} / ${String(n).padStart(2, '0')}</div><div class="rule"></div>
  <div class="ttl">${s.title}</div>${s.name ? `<div class="nm">${s.name}</div>` : ''}<div class="bd">${s.body}</div>${s.ask ? `<div class="ask">${s.ask}</div>` : ''}</div>${overlay(true)}${fitScript}</body></html>`;
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
