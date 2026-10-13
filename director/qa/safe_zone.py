"""Read-only adapter around video-ad-editor's safe-zone + hook checker: `node 08_safe_check.js <workdir> [--shot]`.

The checker writes `<workdir>/safe.jpg` with --shot, so it NEVER runs on the original: the workdir is copied to a
fresh scratch dir (big media symlinked, read-only use), an optional platform is merged into the COPY's safe.json, the
checker runs on the copy offline, and any safe.jpg is copied out to out_dir. Its Arabic report lines become findings.

    python -m director.qa.safe_zone WORKDIR [PLATFORM]
"""
from __future__ import annotations
import glob, json, os, re, shutil, sys, tempfile
from pathlib import Path

from ._common import copy_tree, finding, offline_env, run, sha256_file, tmp_env

TOOL = 'video-ad-editor 08_safe_check'
VAE = Path(os.environ.get('VD_VAE_ROOT', '/home/user/majedphotos/video-ad-editor/video-ad-editor'))
DEFAULT_TOOL = VAE / 'scripts/08_safe_check.js'
EXIT_OK, EXIT_FAIL = 0, 3

# ---- the checker's own sentences (08_safe_check.js) --------------------------------------------------------------
OK, BAD, WARN = '✅', '❌', '⚠️'
HOOK = re.compile(r'^(?P<mark>✅|❌) أول كابشن عند (?P<at>\d+(?:\.\d+)?) ثانية(?P<rest>.*)$')
HOOK_MAX = re.compile(r'لازم قبل (\d+(?:\.\d+)?)')
ZONE = re.compile(r'^(?P<mark>✅|❌|⚠️)\s*(?P<zone>.+?): (?P<pct>\d+(?:\.\d+)?)٪ من المساحة عند (?P<at>\d+(?:\.\d+)?)ث \(المسموح (?P<max>\d+(?:\.\d+)?)٪\)$')
SECTION = re.compile(r'^— المنطقة الآمنة · (?P<platform>\S+) \(عيّنة (?P<n>\d+) لقطة(?: · منها (?P<novid>\d+) بلا فيديو.*)?\) —$')
UNKNOWN_PLATFORM = re.compile(r'^⚠️ منصة مو معروفة «(?P<p>.*)»')
SHOT = re.compile(r'^🖼\s+(?P<path>.+?safe\.jpg) \(540 عرض\) — اللقطة عند (?P<at>\d+(?:\.\d+)?)ث')
KNOWN = {  # fixed lines that carry no data beyond their presence
    '— الهوك —': 'hook_section',
    'ℹ️  ما فيه compose.html — فحص البكسل للمحرّك الخفيف بس.': 'no_compose',
    'ℹ️  ما فيه فشل — ما طلّعت safe.jpg': 'shot_skipped',
    '❌ لا تسلّم قبل الإصلاح: ارفع العنصر فوق الحزام أو صغّره.': 'verdict_fail',
    '✅ كل شي داخل المنطقة الآمنة.': 'verdict_pass',
}
REMOTION_HINT = re.compile(r'^\s+بريموشن: ')
OFFLINE_RES = re.compile(r'net::ERR_(PROXY_CONNECTION_FAILED|INTERNET_DISCONNECTED|NAME_NOT_RESOLVED|TUNNEL_CONNECTION_FAILED)')


def _chrome() -> str | None:
    if os.environ.get('CHROME_PATH') and os.path.isfile(os.environ['CHROME_PATH']):
        return os.environ['CHROME_PATH']
    base = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '/opt/pw-browsers')
    for p in sorted(glob.glob(os.path.join(base, 'chromium-*/chrome-linux*/chrome')), reverse=True):
        if os.access(p, os.X_OK):
            return p
    return None


def parse(stdout: str, stderr: str, unmap=lambda s: s):
    findings, summary = [], {'zones': []}
    for line in stdout.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        if s in KNOWN:
            k = KNOWN[s]
            if k.startswith('verdict_'):
                summary['verdict'] = k[8:]
            elif k == 'no_compose':
                summary['pixel_check'] = False
                findings.append(finding('NO_PIXEL_CHECK', 'info', line,
                                        detail='no compose.html in the workdir: only the hook was checked, not the safe zones'))
            elif k == 'shot_skipped':
                summary['shot'] = 'skipped (nothing failed)'
            continue
        if REMOTION_HINT.match(s):
            continue
        m = HOOK.match(s)
        if m:
            at = float(m.group('at'))
            mx = HOOK_MAX.search(m.group('rest'))
            summary['hook'] = {'first_caption_s': at, 'ok': m.group('mark') == OK, 'max_s': float(mx.group(1)) if mx else None}
            if m.group('mark') == BAD:
                findings.append(finding('HOOK_LATE', 'major', line, frm=at, to=at,
                                        detail=f'first caption at {at:.2f}s' + (f', must be before {mx.group(1)}s' if mx else ''),
                                        first_caption_s=at, max_s=float(mx.group(1)) if mx else None))
            continue
        m = UNKNOWN_PLATFORM.match(s)
        if m:
            findings.append(finding('UNKNOWN_PLATFORM', 'major', line, detail=f'unknown platform «{m.group("p")}»: checked with the reels zones'))
            continue
        m = SECTION.match(s)
        if m:
            summary.update(pixel_check=True, platform=m.group('platform'), samples=int(m.group('n')),
                           no_video_samples=int(m.group('novid') or 0))
            continue
        m = ZONE.match(s)
        if m:
            pct, at, mx = float(m.group('pct')), float(m.group('at')), float(m.group('max'))
            mark = m.group('mark')
            z = {'zone': m.group('zone'), 'ink_pct': pct, 'at_s': at, 'allowed_pct': mx,
                 'status': {OK: 'ok', BAD: 'hard_fail', WARN: 'soft_warn'}[mark]}
            summary['zones'].append(z)
            if mark != OK:
                code, sev = ('ZONE_HARD', 'critical') if mark == BAD else ('ZONE_SOFT', 'minor')
                findings.append(finding(code, sev, line, frm=at, to=at,
                                        detail=f'{m.group("zone")}: {pct}% ink at {at:.2f}s (allowed {mx}%)',
                                        zone=m.group('zone'), ink_pct=pct, allowed_pct=mx))
            continue
        m = SHOT.match(s)
        if m:
            summary['shot'] = {'printed_path': unmap(m.group('path')), 'at_s': float(m.group('at'))}
            continue
        findings.append(finding('UNPARSED', 'info', line, detail='stdout line the adapter does not recognise'))
    for line in stderr.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        if s.startswith('[compose] ') and OFFLINE_RES.search(s):
            findings.append(finding('OFFLINE_RESOURCE', 'info', line,
                                    detail='a web resource (usually a Google font) was blocked by the offline sandbox; text was measured with the fallback font'))
        elif s.startswith('[compose] '):
            findings.append(finding('COMPOSE_ERROR', 'major', line, detail=unmap(s[10:])))
        else:
            findings.append(finding('UNPARSED', 'info', line, detail='stderr line the adapter does not recognise', stream='stderr'))
    return findings, summary


def _consistency(findings, summary, code):
    out = []
    blocking = [f for f in findings if f['code'] in ('HOOK_LATE', 'ZONE_HARD')]
    if code == EXIT_FAIL and not blocking:
        out.append(finding('PARSE_MISMATCH', 'major', '', detail='exit 3 but no failing hook or hard zone was parsed'))
    if code == EXIT_OK and blocking:
        out.append(finding('PARSE_MISMATCH', 'major', '', detail='exit 0 but a failing hook or hard zone was parsed'))
    if code == EXIT_OK and 'hook' not in summary:
        out.append(finding('PARSE_MISMATCH', 'major', '', detail='exit 0 but the hook line was not seen'))
    return out


def check(workdir, platform=None, shot=True, out_dir=None, timeout=600, *, tool_path=None, tmp_root=None) -> dict:
    tool = Path(tool_path or DEFAULT_TOOL).resolve()
    wd = Path(workdir).resolve()
    res = {'tool': TOOL, 'tool_path': str(tool), 'tool_sha256': sha256_file(tool) if tool.is_file() else None,
           'input': str(wd), 'platform_requested': platform, 'exit_code': None, 'passed': False, 'findings': [],
           'summary': {}, 'safe_jpg': None, 'raw_stdout': '', 'raw_stderr': '', 'ran_on_copy': True,
           'network_blocked': True, 'seconds': None}

    def fail(msg):
        res['findings'].append(finding('TOOL_ERROR', 'critical', '', detail=msg))
        return _save(res, out_dir)
    if not tool.is_file():
        return fail(f'checker not found: {tool}')
    if not wd.is_dir():
        return fail(f'workdir not found: {wd}')
    for need in ('sfx.json', 'caps.json'):
        if not (wd / need).is_file():
            return fail(f'workdir has no {need} (the checker reads it first)')
    chrome = _chrome()
    if not chrome:
        return fail('no Chromium found (set CHROME_PATH or PLAYWRIGHT_BROWSERS_PATH)')
    had_safe_jpg = (wd / 'safe.jpg').exists()
    out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix='qa-safe-out-'))
    out.mkdir(parents=True, exist_ok=True)
    if tmp_root:
        Path(tmp_root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qa-safe-', dir=tmp_root) as td:
        work = Path(td)
        try:
            copy = copy_tree(wd, work / wd.name)
        except OSError as e:
            return fail(f'could not copy the workdir: {e}')
        if (copy / 'safe.jpg').exists() or (copy / 'safe.jpg').is_symlink():
            (copy / 'safe.jpg').unlink()                      # so a safe.jpg after the run is this run's
        if platform:
            sj = copy / 'safe.json'
            try:
                cfg = json.loads(sj.read_text(encoding='utf-8')) if sj.is_file() else {}
            except ValueError as e:
                return fail(f'safe.json in the workdir is not valid JSON, cannot add the platform: {e}')
            if not isinstance(cfg, dict):
                return fail('safe.json in the workdir is not a JSON object, cannot add the platform')
            if sj.is_symlink():
                sj.unlink()
            cfg['platform'] = platform
            sj.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding='utf-8')
        env = offline_env({'CHROME_PATH': chrome, **tmp_env(work)})
        cmd = ['node', tool, copy] + (['--shot'] if shot else [])
        code, so, se, secs = run(cmd, env=env, cwd=work, timeout=timeout)
        unmap = lambda s: s.replace(str(copy), str(out) if 'safe.jpg' in s else str(wd))
        if (copy / 'safe.jpg').is_file():
            shutil.copy2(copy / 'safe.jpg', out / 'safe.jpg')
            res['safe_jpg'] = str(out / 'safe.jpg')
    res.update(exit_code=code, raw_stdout=so, raw_stderr=se, seconds=secs)
    findings, summary = parse(so, se, unmap)
    if code is None:
        findings.append(finding('TOOL_ERROR', 'critical', '', detail=f'checker timed out after {timeout}s'))
    elif code not in (EXIT_OK, EXIT_FAIL):
        last = next((l for l in reversed(se.splitlines()) if l.strip() and not l.startswith('    at ')), '')
        findings.append(finding('TOOL_ERROR', 'critical', '', detail=f'checker exited with {code}: {unmap(last)[:300]}'))
    findings += _consistency(findings, summary, code)
    if not had_safe_jpg and (wd / 'safe.jpg').exists():
        findings.append(finding('ORIGINAL_TOUCHED', 'critical', '', detail='a safe.jpg appeared in the ORIGINAL workdir'))
    res['findings'], res['summary'] = findings, summary
    res['passed'] = code == EXIT_OK and not any(f['code'] in ('TOOL_ERROR', 'PARSE_MISMATCH', 'ORIGINAL_TOUCHED') for f in findings)
    return _save(res, out)


def _save(res, out_dir):
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / 'safe_zone_check.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    return res


if __name__ == '__main__':
    r = check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps({k: v for k, v in r.items() if k not in ('raw_stdout', 'raw_stderr')}, ensure_ascii=False, indent=1))
    sys.exit(0 if r['passed'] else 1)
