"""Read-only adapter around paper-story's own layout checker: `node render.mjs <storyboard.json> --check`.

The storyboard's folder is copied to a scratch dir first (relative asset paths that climb out of the folder are copied
into the same relative place, big media is symlinked), the checker runs on the copy offline, and its stdout lines
become findings. Nothing is decided here: every finding is a line the checker printed.

    python -m director.qa.paper_story STORYBOARD.json
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

from ._common import SCRATCH, copy_tree, finding, offline_env, run, sha256_file, tmp_env

TOOL = 'paper-story --check'
DEFAULT_TOOL = Path(os.environ.get('VD_PAPER_STORY_RENDER',
                                   SCRATCH / 'audit/claude_success-story-video/.claude/skills/paper-story/scripts/render.mjs'))
SEVERITY = {'FACE_COVERED': 'major', 'UNDER_BANNER': 'major', 'CUT_BY_FRAME': 'major', 'OVERLAP': 'major',
            'ON_CAPTIONS': 'major', 'SOFT_IMAGE': 'minor', 'PLACEHOLDER': 'minor', 'TOOL_WARNING': 'minor',
            'PAGE_ERROR': 'major', 'PARSE_MISMATCH': 'major', 'TOOL_ERROR': 'critical', 'UNPARSED': 'info'}
BLOCKING = ('FACE_COVERED', 'UNDER_BANNER', 'CUT_BY_FRAME', 'OVERLAP', 'ON_CAPTIONS')

# ---- the checker's own sentences (render.mjs, `if (opt.check)` block) -------------------------------------------
SCENE_LINE = re.compile(r'^scene (\d+)\s+(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)s\s+(.*)$')
BODIES = [  # order matters: the face sentence also contains " covers "
    ('UNDER_BANNER', re.compile(r'^(?P<subject>.+) is (?P<pct>\d+)% under the banner$')),
    ('FACE_COVERED', re.compile(r'^(?P<subject>.+) covers (?P<pct>\d+)% of the head of (?P<person>.+)$')),
    ('CUT_BY_FRAME', re.compile(r'^(?P<subject>.+) is (?P<pct>\d+)% outside the frame$')),
    ('ON_CAPTIONS', re.compile(r'^(?P<subject>.+) sits on the captions \((?P<pct>\d+)% of a word\)$')),
    ('OVERLAP', re.compile(r'^(?P<subject>.+ covers (?:the label of )?.+) \((?P<pct>\d+)%\)$')),
]
SOFT_LINE = re.compile(r'^note: scene (\d+)\s+(?P<subject>.+) is shown at (?P<pct>\d+)% of its file \((?P<file>\d+)px wide\): it will look soft$')
SUMMARY = [
    ('clashes', re.compile(r'^(\d+) clash\(es\)$'), 'no face covered, nothing under the banner'),
    ('cut', re.compile(r'^(\d+) cut by the frame$'), 'nothing cut by the frame'),
    ('overlap_or_captions', re.compile(r'^(\d+) overlap\(s\) or picture\(s\) on the captions$'),
     'no print over another, nothing on the captions'),
]
ERR_LINES = [
    ('TOOL_ERROR', re.compile(r'^render: (?P<msg>.*)$')),
    ('PLACEHOLDER', re.compile(r'^placeholders still showing \((?P<n>\d+)\): (?P<msg>.*)$')),
    ('TOOL_WARNING', re.compile(r'^warning: (?P<msg>.*)$')),
    ('PAGE_ERROR', re.compile(r'^page (?:error|console): (?P<msg>.*)$')),
]

_npm_root = None


def _playwright_roots(tool: Path) -> list[str]:
    """Folders that already hold playwright-core (read-only use). render.mjs would otherwise `npm install` it."""
    global _npm_root
    if _npm_root is None:
        try:
            _npm_root = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True, timeout=30,
                                       env=offline_env()).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            _npm_root = ''
    cands = [str(tool.parent), *[p for p in os.environ.get('NODE_PATH', '').split(os.pathsep) if p],
             str(Path.home() / '.cache/paper-story')]
    if _npm_root:
        cands += [_npm_root, os.path.join(_npm_root, 'playwright')]
    return [c for c in cands if os.path.isfile(os.path.join(c, 'node_modules/playwright-core/package.json'))
            or os.path.isfile(os.path.join(c, 'playwright-core/package.json'))]


def _local_refs(sb) -> list[str]:
    """Relative file paths the storyboard names (the keys render.mjs resolves against the storyboard folder)."""
    refs = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in ('src', 'avatar', 'voice', 'file') and isinstance(v, str):
                    refs.append(v)
                elif k == 'parts' and isinstance(v, dict):
                    refs.extend(x for x in v.values() if isinstance(x, str))
                else:
                    walk(v)
    walk(sb)
    au = sb.get('audio') or {}
    refs += [au[k] for k in ('voice', 'voiceover', 'music') if isinstance(au.get(k), str)]
    return [r for r in refs if not re.match(r'^(https?:|data:|file:)', r) and not os.path.isabs(r)]


def _mirror(storyboard: Path, work: Path):
    """Copy the storyboard folder into work/mirror, keeping every relative path the storyboard uses valid.
    Returns (copied storyboard path, mirror root, original root, parsed storyboard)."""
    sb_dir = storyboard.parent
    sb = json.loads(storyboard.read_text(encoding='utf-8'))
    targets = [os.path.normpath(os.path.join(sb_dir, r)) for r in _local_refs(sb)]
    outside = sorted({t for t in targets if os.path.exists(t) and os.path.commonpath([t, str(sb_dir)]) != str(sb_dir)})
    root = Path(os.path.commonpath([str(sb_dir), *outside])) if outside else sb_dir
    mroot = work / 'mirror'
    msb_dir = mroot / sb_dir.relative_to(root)
    msb_dir.parent.mkdir(parents=True, exist_ok=True)
    copy_tree(sb_dir, msb_dir)
    for t in outside:
        dst = mroot / Path(t).relative_to(root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            continue
        if os.path.isdir(t):
            copy_tree(t, dst)
        else:
            shutil.copy2(t, dst)
    return msb_dir / storyboard.name, mroot, root, sb


def _unmap(s: str, mroot: Path, root: Path) -> str:
    return s.replace(mroot.as_uri(), root.as_uri()).replace(str(mroot), str(root))


def parse(stdout: str, stderr: str, scenes=None, unmap=lambda s: s):
    """Turn the checker's printed lines into (findings, summary). Every non-empty line ends up somewhere."""
    findings, summary = [], {}
    sid = lambda n: (scenes[n - 1].get('id') if scenes and 0 < n <= len(scenes) and isinstance(scenes[n - 1], dict) else None)
    for line in stdout.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        m = SCENE_LINE.match(s)
        if m:
            n, body = int(m.group(1)), m.group(4)
            for code, rx in BODIES:
                b = rx.match(body)
                if b:
                    d = {k: unmap(v) for k, v in b.groupdict().items() if v is not None}
                    d['pct'] = int(d['pct'])
                    findings.append(finding(code, SEVERITY[code], line, scene=n, frm=float(m.group(2)), to=float(m.group(3)),
                                            detail=unmap(body), scene_id=sid(n), **d))
                    break
            else:
                findings.append(finding('UNPARSED', 'info', line, scene=n, detail='scene line in an unknown form'))
            continue
        m = SOFT_LINE.match(s)
        if m:
            n = int(m.group(1))
            findings.append(finding('SOFT_IMAGE', 'minor', line, scene=n, detail=unmap(s.split('  ', 1)[-1]), scene_id=sid(n),
                                    subject=unmap(m.group('subject')), pct=int(m.group('pct')), file_px=int(m.group('file'))))
            continue
        for key, rx, zero in SUMMARY:
            m = rx.match(s)
            if m or s == zero:
                summary[key] = int(m.group(1)) if m else 0
                break
        else:
            findings.append(finding('UNPARSED', 'info', line, detail='stdout line the adapter does not recognise'))
    for line in stderr.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        for code, rx in ERR_LINES:
            m = rx.match(s)
            if m:
                findings.append(finding(code, SEVERITY[code], line, detail=unmap(m.group('msg'))))
                break
        else:
            findings.append(finding('UNPARSED', 'info', line, detail='stderr line the adapter does not recognise', stream='stderr'))
    return findings, summary


def _consistency(findings, summary, code):
    """The checker prints its own totals; if our parse disagrees, the output format has changed under us."""
    n = lambda *cs: sum(1 for f in findings if f['code'] in cs)
    out = []
    expect = {'clashes': n('FACE_COVERED', 'UNDER_BANNER'), 'cut': n('CUT_BY_FRAME'), 'overlap_or_captions': n('OVERLAP', 'ON_CAPTIONS')}
    for k, v in expect.items():
        if k in summary and summary[k] != v:
            out.append(finding('PARSE_MISMATCH', 'major', '', detail=f'checker says {k}={summary[k]}, adapter parsed {v}'))
    if code == 0 and len(summary) < 3:
        out.append(finding('PARSE_MISMATCH', 'major', '', detail='exit 0 but the three summary lines were not all seen'))
    if code == 1 and not any(f['code'] in BLOCKING + ('TOOL_ERROR',) for f in findings):
        out.append(finding('PARSE_MISMATCH', 'major', '', detail='exit 1 but no blocking finding was parsed'))
    return out


def check(storyboard_path, out_dir=None, timeout=600, *, tool_path=None, tmp_root=None) -> dict:
    tool = Path(tool_path or DEFAULT_TOOL).resolve()
    storyboard = Path(storyboard_path).resolve()
    res = {'tool': TOOL, 'tool_path': str(tool), 'tool_sha256': sha256_file(tool) if tool.is_file() else None,
           'input': str(storyboard), 'exit_code': None, 'passed': False, 'findings': [], 'summary': {},
           'raw_stdout': '', 'raw_stderr': '', 'ran_on_copy': True, 'network_blocked': True, 'seconds': None}

    def fail(msg):
        res['findings'].append(finding('TOOL_ERROR', 'critical', '', detail=msg))
        return _save(res, out_dir)
    if not tool.is_file():
        return fail(f'checker not found: {tool}')
    if not storyboard.is_file():
        return fail(f'storyboard not found: {storyboard}')
    if not shutil.which('node'):
        return fail('node is not on PATH')
    roots = _playwright_roots(tool)
    if not roots:
        return fail('playwright-core is not installed anywhere render.mjs looks; refusing to let it npm-install one')
    if tmp_root:
        Path(tmp_root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qa-paper-', dir=tmp_root) as td:
        work = Path(td)
        try:
            copy_sb, mroot, root, sb = _mirror(storyboard, work)
        except (OSError, ValueError) as e:
            return fail(f'could not copy the storyboard folder: {e}')
        env = offline_env({'NODE_PATH': os.pathsep.join(roots), **tmp_env(work)})
        code, out, err, secs = run(['node', tool, copy_sb, '--check'], env=env, cwd=work, timeout=timeout)
        unmap = lambda s: _unmap(s, mroot, root)
    res.update(exit_code=code, raw_stdout=out, raw_stderr=err, seconds=secs)
    findings, summary = parse(out, err, sb.get('scenes') if isinstance(sb, dict) else None, unmap)
    if code is None:
        findings.append(finding('TOOL_ERROR', 'critical', '', detail=f'checker timed out after {timeout}s'))
    elif code not in (0, 1):
        findings.append(finding('TOOL_ERROR', 'critical', '', detail=f'checker exited with {code}'))
    findings += _consistency(findings, summary, code)
    res['findings'], res['summary'] = findings, summary
    res['passed'] = code == 0 and not any(f['code'] in ('TOOL_ERROR', 'PARSE_MISMATCH') for f in findings)
    return _save(res, out_dir)


def _save(res, out_dir):
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / 'paper_story_check.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    return res


if __name__ == '__main__':
    r = check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps({k: v for k, v in r.items() if k not in ('raw_stdout', 'raw_stderr')}, ensure_ascii=False, indent=1))
    sys.exit(0 if r['passed'] else 1)
