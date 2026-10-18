"""Prove approved audio and production files are never touched by development work.

  python -m arabic_tts.hashguard snapshot LIST.txt PATH [PATH ...]   # record sha256 of every file under the paths
  python -m arabic_tts.hashguard verify LIST.txt                     # exit 1 if anything changed or vanished
"""
import hashlib, os, sys


def files(paths):
    for p in paths:
        if os.path.isdir(p):
            for d, _, fs in os.walk(p):
                for f in sorted(fs):
                    yield os.path.abspath(os.path.join(d, f))
        else:
            yield os.path.abspath(p)


def sha(fn):
    return hashlib.sha256(open(fn, 'rb').read()).hexdigest()


if __name__ == '__main__':
    cmd, lst = sys.argv[1], sys.argv[2]
    if cmd == 'snapshot':
        with open(lst, 'w') as out:
            for fn in sorted(set(files(sys.argv[3:]))):
                out.write(f'{sha(fn)}  {fn}\n')
        print(sum(1 for _ in open(lst)), 'files recorded in', lst)
    else:
        bad = ok = 0
        for line in open(lst):
            h, fn = line.split(None, 1); fn = fn.strip()
            if not os.path.exists(fn):
                print('MISSING', fn); bad += 1
            elif sha(fn) != h:
                print('CHANGED', fn); bad += 1
            else:
                ok += 1
        print(f'{ok} unchanged, {bad} changed or missing')
        sys.exit(1 if bad else 0)
