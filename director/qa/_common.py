"""Shared plumbing for the read-only QA adapters: hashing, the offline subprocess environment, copying inputs to a
scratch dir, and running a checker with a hard timeout. No checker logic lives here."""
from __future__ import annotations
import hashlib, os, shutil, signal, subprocess, time
from pathlib import Path

SCRATCH = Path(os.environ.get('VD_SCRATCH', '/tmp/claude-0/-home-user-timekeeper-online/d12c441f-3b9e-54a5-94c3-c8a78268d6ad/scratchpad'))
DEAD_PROXY = 'http://127.0.0.1:9'           # nothing listens on the discard port: every proxied request fails at once
SECRET_KEYS = ('ELEVENLABS_API_KEY', 'FAL_KEY')
LARGE_BYTES = 64 * 1024 * 1024               # files this big are symlinked into the copy instead of duplicated
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(root) -> dict:
    """relative path -> sha256 for every regular file under root (symlinks recorded by their target)."""
    root = Path(root)
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != '__pycache__')
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            rel = str(p.relative_to(root))
            out[rel] = ('link:' + os.readlink(p)) if p.is_symlink() else sha256_file(p)
    return out


def offline_env(extra: dict | None = None) -> dict:
    """The environment every checker runs in: no paid-API keys, every proxy pointed at a dead port (Chromium and npm
    honour these, so no page can fetch anything from the network), npm forced offline, debug switches off."""
    env = {k: v for k, v in os.environ.items()
           if k not in SECRET_KEYS and 'proxy' not in k.lower() and k not in ('PM_DEBUG', 'CHROME_PATH', 'PUPPETEER_PATH')}
    for k in ('http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'):
        env[k] = DEAD_PROXY
    env['no_proxy'] = env['NO_PROXY'] = ''
    env['npm_config_offline'] = 'true'
    env['npm_config_proxy'] = env['npm_config_https_proxy'] = DEAD_PROXY
    env.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/opt/pw-browsers')
    if extra:
        env.update(extra)
    return env


def _copy_or_link(src, dst, *, follow_symlinks=True):
    if os.path.getsize(src) >= LARGE_BYTES:
        os.symlink(os.path.abspath(src), dst)       # read-only use: the checkers never write to these
        return dst
    return shutil.copy2(src, dst)


def copy_tree(src, dst):
    """Copy a folder for a checker to run on. Big media files become symlinks to the originals (the checkers only
    read them); .git / node_modules are left out; dangling links are skipped."""
    shutil.copytree(src, dst, symlinks=False, ignore_dangling_symlinks=True,
                    ignore=lambda d, names: [n for n in names if n in SKIP_DIRS], copy_function=_copy_or_link)
    return Path(dst)


def run(cmd, *, env, cwd, timeout):
    """Run a checker; returns (exit_code or None on timeout, stdout, stderr, seconds). Kills the whole process group
    (node and its Chromium) on timeout."""
    t0 = time.monotonic()
    with subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True) as p:
        try:
            out, err = p.communicate(timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = p.communicate()
            code = None
    return code, out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace'), round(time.monotonic() - t0, 2)


def tmp_env(work) -> dict:
    """TMPDIR for the checker, inside its scratch dir so browser profiles go away with it -- but only when the path is
    short: Chromium puts its singleton socket there and fails to start when the socket path passes ~100 bytes."""
    t = Path(work) / 'tmp'
    if len(str(t)) > 60:
        return {}
    t.mkdir(exist_ok=True)
    return {'TMPDIR': str(t)}


def finding(code, severity, raw, *, scene=None, frm=None, to=None, detail='', **data):
    f = {'code': code, 'severity': severity, 'scene': scene, 'from': frm, 'to': to, 'detail': detail, 'raw': raw}
    if data:
        f['data'] = data
    return f
