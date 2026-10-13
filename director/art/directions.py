"""Creative directions: a comparison page per project, built from profiles/directions.yaml.

Guarantees checked here (and in tests):
  * every colour and font a direction names appears in the source file it cites; a value with no source is refused,
    so the page can only show unassigned (null) or sourced values;
  * engine support, cost and accuracy per technique come from art/techniques.yaml (one place of truth);
  * techniques outside the project's profile are flagged, not hidden;
  * nothing here writes to a profile: the owner's reactions are stored by the page, and locking a profile stays a
    separate, explicit approval.
"""
from __future__ import annotations
import json, re, shutil, subprocess, tempfile
from pathlib import Path
import yaml

from .. import profiles
from .selector import load_registry

ROOT = Path(__file__).resolve().parents[2]
HEX = re.compile(r'#[0-9A-Fa-f]{6}\b')


def source_paths(scratch: Path) -> dict:
    synced = sorted(Path('/root/.claude/skills/synced').glob('*/timekeeper-post/SKILL.md'))
    return {'tk_template': synced[0] if synced else None,
            'tk_style': scratch / 'audit/claude_success-story-video/video/success-story/tk-style.json',
            'ro_style': scratch / 'audit/claude_success-story-video/video/royal-oak/ro-style.json',
            'dh_ep7': ROOT / 'profiles/diabetes-history-sci.yaml',
            'ro_usage': scratch / 'audit/claude_success-story-video/video/royal-oak/voice-abdullah/clips.json'}


def check_sources(doc: dict, paths: dict) -> list[str]:
    """Problems found; empty means every named colour/font is backed by its cited source."""
    errs = []
    for pk, proj in doc['projects'].items():
        for d in proj['directions']:
            for kind in ('palette', 'fonts'):
                block = d.get(kind) or {}
                vals, src = block.get('values'), block.get('source')
                if not vals:
                    if not block.get('missing'):
                        errs.append(f"{d['id']}/{kind}: unassigned without saying so ('missing')")
                    continue
                if not src:
                    errs.append(f"{d['id']}/{kind}: values without a source"); continue
                p = paths.get(src)
                if p is None or not Path(p).exists():
                    errs.append(f"{d['id']}/{kind}: source {src} not found"); continue
                text = Path(p).read_text(encoding='utf-8')
                for k, v in vals.items():
                    if v and str(v).lower() not in text.lower():
                        errs.append(f"{d['id']}/{kind}.{k}: {v} does not appear in {src}")
            if (d.get('palette') or {}).get('accent'):
                errs.append(f"{d['id']}: accent set but no source names an accent")
    return errs


def build_data(doc: dict, registry: dict) -> dict:
    out = {'sources': doc['sources'], 'projects': {}}
    for pk, proj in doc['projects'].items():
        prof = profiles.load(ROOT / f"profiles/{proj['profile']}.yaml")
        allowed = set((prof.get('art') or {}).get('allowed', []))
        dirs = []
        for d in proj['directions']:
            techs = []
            for t in d['techniques']:
                r = registry[t]
                techs.append({'id': t, 'name': r['name'], 'status': r['status'], 'support': r.get('support'),
                              'cost': r['cost'], 'accuracy': r['accuracy'], 'in_profile': t in allowed})
            paid = [t['id'] for t in techs if t['cost'] == 'paid']
            dirs.append({**{k: d[k] for k in ('id', 'name', 'visual_style', 'suitable_scenes', 'engine', 'required_assets',
                                               'limitations', 'accuracy_risks', 'palette', 'fonts', 'preview')},
                         'techniques': techs,
                         'cost': {'render': 'free (local)' if not paid else f"paid techniques: {', '.join(paid)}",
                                  'images': 'no paid image or video generation' if not paid else 'needs a paid plan',
                                  'narration': proj['narration_cost']},
                         'support_summary': 'all techniques available today' if all(t['status'] == 'available' for t in techs)
                                            else 'some techniques need work: ' + ', '.join(t['id'] for t in techs if t['status'] != 'available'),
                         'outside_profile': [t['id'] for t in techs if not t['in_profile']]})
        out['projects'][pk] = {'profile': proj['profile'], 'profile_status': prof.get('status'),
                               'profile_version': prof.get('version'), 'directions': dirs}
    return out


# ------------------------------------------------------------------------------------------------ previews
BOARD = """<!doctype html><meta charset=utf-8><style>
@font-face{{font-family:Cairo;src:url('file://{font}')}}
html,body{{margin:0;width:540px;height:960px;overflow:hidden;background:{bg};font-family:Cairo}}
.grid{{position:absolute;inset:0;background-image:linear-gradient({line} 1px,transparent 1px),linear-gradient(90deg,{line} 1px,transparent 1px);background-size:36px 36px;opacity:{grid}}}
.banner{{position:absolute;top:120px;left:50%;transform:translateX(-50%) rotate(-1.2deg);background:{paper};color:{ink};font-weight:800;font-size:30px;padding:6px 26px;white-space:nowrap}}
.photo{{position:absolute;top:250px;left:50%;transform:translateX(-50%) rotate(1.5deg);width:300px;height:340px;background:{frame};padding:14px 14px 52px;box-shadow:0 8px 24px rgba(0,0,0,.35)}}
.photo div{{width:100%;height:100%;background:repeating-linear-gradient(45deg,{ph1} 0 10px,{ph2} 10px 20px);display:flex;align-items:center;justify-content:center;text-align:center;color:{phink};font-size:21px;font-weight:700;line-height:1.5}}
.tape{{position:absolute;top:-14px;left:50%;width:110px;height:30px;transform:translateX(-50%) rotate(-3deg);background:rgba(200,192,170,.8)}}
.cap{{position:absolute;top:700px;left:40px;right:40px;background:{capbg};color:{capink};font-size:30px;font-weight:700;padding:14px 22px;direction:rtl}}
.foot{{position:absolute;bottom:22px;left:0;right:0;text-align:center;color:{foot};font-size:15px;direction:rtl}}
</style><div class=grid></div><div class=banner>{banner}</div>
<div class=photo><span class=tape></span><div>صورة حقيقية مطلوبة<br>لا صور مولّدة</div></div>
<div class=cap>{caption}</div><div class=foot>لوحة أسلوب، ليست لقطة من فيلم · الخط: Cairo بديل مؤقت</div>"""


def board_tokens(theme: str, paths: dict) -> dict:
    if theme == 'editorial':                            # brand template only: black, white, nothing else
        return dict(bg='#111111', paper='#FFFFFF', ink='#111111', frame='#FFFFFF', ph1='#2a2a2a', ph2='#202020',
                    phink='#FFFFFF', capbg='#FFFFFF', capink='#111111', foot='#FFFFFF', line='#FFFFFF', grid=0)
    src = paths['tk_style'] if theme.startswith('tk-') else paths['ro_style']
    st = json.loads(Path(src).read_text(encoding='utf-8'))
    th, ban = st['themes'][theme], st['style']['banner']
    return dict(bg=th['bg'], paper=ban['paper'], ink=ban['ink'], frame=ban['paper'], ph1=th['blot'][0], ph2=th['blot'][1],
                phink=ban['ink'], capbg=th['capBg'], capink=th['capInk'], foot=th['capBg'], line=th['floorTop'],
                grid=.35 if theme.startswith('ro-') else 0)


def render_previews(data: dict, out_dir: Path, paths: dict, pack_dir: Path, font: Path) -> dict:
    (out_dir / 'img').mkdir(parents=True, exist_ok=True)
    files = {}
    for pk, proj in data['projects'].items():
        for d in proj['directions']:
            pv, imgs = d['preview'], []
            if pv['kind'] == 'style_board':
                tok = board_tokens(pv['theme'], paths)
                html = BOARD.format(font=font, banner='عنوان المشهد', caption='نص الكابشن يظهر هنا', **tok)
                with tempfile.TemporaryDirectory() as td:
                    h = Path(td) / 'b.html'; h.write_text(html, encoding='utf-8')
                    dst = out_dir / 'img' / f"{d['id']}.jpg"
                    subprocess.run(['node', str(ROOT / 'tools/html_shot.mjs'), str(h), str(dst), '540', '960'], check=True)
                imgs.append(f"img/{d['id']}.jpg")
            elif pv['kind'] == 'real_frames':
                for s in pv['scenes']:
                    dst = out_dir / 'img' / f"{d['id']}-{s}.jpg"
                    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(pack_dir / 'stills' / f'{s}_mid.jpg'),
                                    '-vf', 'scale=360:-2', '-q:v', '4', str(dst)], check=True)
                    imgs.append(f"img/{d['id']}-{s}.jpg")
            d['preview']['images'] = imgs
            for i in imgs:
                files[i] = out_dir / i
    return files


def build(out_dir, scratch: Path, pack_dir: Path, font: Path):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    doc = yaml.safe_load((ROOT / 'profiles/directions.yaml').read_text(encoding='utf-8'))
    paths = source_paths(scratch)
    errs = check_sources(doc, paths)
    if errs:
        raise ValueError('directions use values their sources do not contain:\n  ' + '\n  '.join(errs))
    data = build_data(doc, load_registry(ROOT / 'art/techniques.yaml'))
    files = render_previews(data, out_dir, paths, pack_dir, font)
    html = (Path(__file__).parent / 'directions_template.html').read_text(encoding='utf-8')
    (out_dir / 'index.html').write_text(html.replace('__DATA__', json.dumps(data, ensure_ascii=False)), encoding='utf-8')
    (out_dir / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    return data, sorted(files)


if __name__ == '__main__':
    import sys
    from tests.fixtures import S
    d, f = build(sys.argv[1], S, ROOT / 'var/review/ep7-final',
                 Path('/home/user/majedphotos/video-ad-editor/video-ad-editor/motion/fonts/Cairo-VF.ttf'))
    print({k: [x['id'] for x in v['directions']] for k, v in d['projects'].items()}, len(f), 'images')
