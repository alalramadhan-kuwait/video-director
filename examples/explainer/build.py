"""Short explainer for the owner: what Video Director is, why the file, what it does, how the iPhone talks to it.
Free draft voice (Google TTS), paper-story engine, 1080x1920."""
import json, subprocess, sys
from pathlib import Path
VD = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VD))
from director.studio import art, engine

W = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1] in ("video", "stills") else Path(__file__).resolve().parent / "out")
W.mkdir(parents=True, exist_ok=True)
(W / 'voice').mkdir(exist_ok=True)
INK, PAPER = art.INK, art.PAPER
R = '#8E2B22'

def card(x, y, w, h, title, body='', at=0.3, dark=False, ts=40, bs=26, fr='slideR'):
    return {'type': 'card', 'x': x, 'y': y, 'w': w, 'h': h, 'tex': 'paper', 'title': title, 'titleSize': ts, 'body': body, 'bodySize': bs,
            'align': 'center', 'style': 'dark' if dark else 'plain', 'in': {'type': fr, 'at': at, 'from': 160}}

def text(t, y, size=60, at=0.0, color=INK, paper=False, x=360):
    e = {'type': 'text', 'text': t, 'font': 'title', 'size': size, 'color': color, 'x': x, 'y': y, 'w': 640, 'align': 'center', 'in': {'type': 'rise', 'at': at, 'dur': .45}}
    if paper: e['paper'] = PAPER
    return e

def arrow(x1, y1, x2, y2, at):
    return {'type': 'sketch', 'x': 360, 'y': 640, 'w': 720, 'h': 1280, 'pencil': False,
            'paths': [{'d': f'M{x1} {y1} L{x2} {y2}', 'at': at, 'dur': .5, 'stroke': INK, 'width': 5}]}

def cam(d): return {'zoom': [[0, 1.0], [d, 1.05, 'inOutCubic']], 'x': [[0, 360]], 'y': [[0, 640], [d, 650, 'inOutCubic']]}

S = [
 ('k1', 'tk-black', 'هذا مخرج الفيديو: تعطيه فكرة، ويطلّع لك فيديو قصيرًا جاهزًا.',
  [text('مخرج الفيديو', 540, 92, 0.1, PAPER), text('فكرة واحدة ← فيديو كامل', 700, 50, 0.9, PAPER)], None),
 ('k2', 'tk-bone', 'يبحث، ويكتب النص، ويسجّل الصوت، ويجيب صورًا حقيقية موثّقة، ويرسم المشاهد، ويجمع الفيلم.',
  [card(360, 400, 540, 84, 'بحث بمصادر', at=.2, ts=36), card(360, 500, 540, 84, 'نص', at=.8, ts=36), card(360, 600, 540, 84, 'صوت', at=1.4, ts=36),
   card(360, 700, 540, 84, 'صور حقيقية موثّقة', at=2.0, ts=36), card(360, 800, 540, 84, 'مشاهد', at=2.6, ts=36),
   card(360, 900, 540, 84, 'فيلم', at=3.2, dark=True, ts=36)], 'المساعد يشتغل'),
 ('k3', 'tk-bone', 'وأنت توافق على المحطات المهمة فقط. ولا شيء يمشي بدون موافقتك.',
  [text('أنت تقرر', 460, 84, 0.1), text('الفكرة · النص · الصوت · الأسلوب · الفيلم', 600, 36, 0.7),
   {'type': 'stamp', 'text': 'موافقة', 'x': 370, 'y': 790, 'size': 84, 'color': R, 'rot': -6, 'in': {'type': 'slam', 'at': 1.8}}], 'القرار لك'),
 ('k4', 'tk-bone', 'الملف هو التطبيق نفسه. يحتاج جهازًا يشغّله، لأن صنع الفيلم شغل ثقيل على الجوال.',
  [card(360, 470, 560, 170, 'الملف = التطبيق', at=.2, ts=52), text('يحتاج جهازًا يشغّله', 680, 52, 1.4),
   text('صنع الفيلم ثقيل على الجوال', 790, 36, 2.4)], 'ليش الملف؟'),
 ('k5', 'tk-bone', 'الماك يشغّله في البيت، والآيفون يفتحه من المتصفح على نفس الواي فاي، برمز دخول، مثل الريموت.',
  [card(360, 430, 400, 120, 'الآيفون', at=.2, ts=46), text('تشوف وتوافق', 530, 28, .6), arrow(360, 570, 360, 690, 1.4), text('واي فاي + رمز', 630, 28, 1.6, x=560),
   card(360, 760, 400, 120, 'الماك', at=2.0, dark=True, ts=46), text('يشغّل التطبيق', 860, 28, 2.4)], 'شلون يتواصل؟'),
 ('k6', 'tk-bone', 'والتطبيق يستعين بكلود للبحث والكتابة، ضمن ميزانية صغيرة تحددها أنت.',
  [card(360, 430, 400, 120, 'الماك', at=.2, dark=True, ts=46), text('التطبيق', 530, 28, .6), arrow(360, 570, 360, 690, 1.2), text('ميزانية تحددها أنت', 630, 28, 1.4, x=560),
   card(360, 760, 400, 120, 'Claude', at=1.8, ts=46), text('يبحث ويكتب', 860, 28, 2.2)], 'الذكاء'),
 ('k7', 'tk-bone', 'ولا يصرف شيئًا من نفسه، والتعليق المدفوع مقفل.',
  [text('لا صرف تلقائي', 470, 70, 0.1), text('التعليق المدفوع مقفل', 610, 40, 0.9),
   {'type': 'stamp', 'text': 'مقفل', 'x': 370, 'y': 790, 'size': 80, 'color': R, 'rot': -6, 'in': {'type': 'slam', 'at': 1.8}}], 'الأمان'),
 ('k8', 'tk-bone', 'نزّل الملف على الماك، شغّل الإعداد مرة واحدة، ثم افتح الرابط من الآيفون.',
  [card(360, 440, 580, 110, '١ · نزّل الملف على الماك', at=.2, ts=38), card(360, 590, 580, 110, '٢ · الإعداد مرة واحدة', at=1.5, ts=38),
   card(360, 740, 580, 110, '٣ · افتح الرابط من الآيفون', at=2.8, ts=38, dark=True)], 'الخطوات'),
 ('k9', 'tk-black', 'وإلى أن يصير عندك ماك: أرسل لي الفكرة هنا، وأنا أشغّله لك.',
  [text('ما عندك ماك؟', 500, 74, 0.1, PAPER), text('أرسل الفكرة هنا…', 650, 48, 1.0, PAPER), text('وأنا أشغّله لك', 750, 48, 1.8, PAPER)], None),
]

def say(i, line):
    mp3, wav = W / 'voice' / f'{i}.mp3', W / 'voice' / f'{i}.wav'
    if not wav.exists():
        from gtts import gTTS
        gTTS(line, lang='ar').save(str(mp3))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp3), '-af', 'atempo=1.22', '-ar', '44100', '-ac', '1', str(wav)], check=True)
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(wav)], capture_output=True, text=True).stdout)

scenes = []
for i, theme, line, els, banner in S:
    d = round(say(i, line) + 0.9, 2)
    scenes.append({'id': i, 'theme': theme, 'floor': False, 'elements': els, 'camera': cam(d), 'banner': banner, 'dur': d,
                   'transition': 'cut' if not scenes else 'paper', 'voice': f'voice/{i}.wav', 'voiceAt': 0.3, 'captions': line})
sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': scenes}
(W / 'explainer.json').write_text(json.dumps(sb, ensure_ascii=False, indent=1), encoding='utf-8')
print('seconds', round(sum(s['dur'] for s in scenes), 1))
if 'video' in sys.argv:
    engine.video(W / 'explainer.json', W / 'explainer.mp4', scale=1.5, workers=3, extra=('--crf', 24))
if 'stills' in sys.argv:
    print(engine.stills(sb, W, [round(sum(s['dur'] for s in scenes[:k]) + scenes[k]['dur'] * .8, 2) for k in range(len(scenes))], scale=0.5))
