"""Phase 1: full contextual diacritization with safeguards.

The original script is never edited. For each line this builds a fully diacritized TTS text from a reviewed
proposal (written with the whole sentence in view) or, when there is none, from CATT as an unreviewed fallback,
then checks it:

  FAIL (line is blocked from TTS)
    skeleton   the letters differ from the original: a word, letter or hamza was changed, added or dropped
    malformed  impossible mark combinations (two vowels, shadda+sukun, tanween mid-word, shadda on a first letter)
  REVIEW (needs a human decision before recording)
    author     the proposal contradicts a mark the script author wrote
    protected  a protected term (lexicon) is diacritized differently from its approved form
    grammar    a likely case-ending error (preposition, inna-sisters, lam/lan before a verb)
    coverage   letters left without a mark
    fallback   no reviewed proposal; text comes from CATT
  INFO
    catt       CATT reads a word differently (second opinion only; CATT was wrong on 17% of audit words)

usage: python -m arabic_tts.diacritize SCRIPT.json PROPOSALS.json OUT.json [--on-conflict author|proposal] [--lexicon lexicon.yaml]
"""
import json, sys, argparse, os
from .arabic import (letters, rebuild, strip, tokens, is_arabic_word, case_mark, split_prefix,
                     VOWELS, TANWEEN, SUKUN, SHADDA, FATHA, KASRA, DAMMA, FATHATAN, KASRATAN, DAMMATAN, SUN)

PREPOSITIONS = {'في', 'من', 'إلى', 'على', 'عن', 'مع', 'عند', 'بعد', 'قبل', 'بين', 'فوق', 'تحت', 'خلال', 'دون', 'حول', 'نحو', 'لدى'}
INNA = {'إن', 'أن', 'لكن', 'كأن', 'ليت', 'لعل'}
# words that never take a visible case ending or are not nouns after a preposition
NO_CASE = {'هذا', 'هذه', 'ذلك', 'تلك', 'هؤلاء', 'أولئك', 'الذي', 'التي', 'الذين', 'اللذان', 'اللتان', 'ما', 'من', 'هو', 'هي',
           'هم', 'هما', 'أن', 'لا', 'كل', 'نفسه'}


def well_formed(word):
    issues = []
    lets = letters(word)
    for i, (c, m) in enumerate(lets):
        v = [x for x in m if x in VOWELS | TANWEEN]
        if len(v) > 1:
            issues.append(f'{word}: two vowels on «{c}»')
        if SHADDA in m and SUKUN in m:
            issues.append(f'{word}: shadda with sukun on «{c}»')
        if SUKUN in m and v:
            issues.append(f'{word}: sukun with a vowel on «{c}»')
        if any(x in TANWEEN for x in m) and i < len(lets) - 1 and not (i == len(lets) - 2 and lets[-1][0] in 'اى'):
            issues.append(f'{word}: tanween in the middle of the word on «{c}»')
        if SHADDA in m and i == 0:
            issues.append(f'{word}: shadda on the first letter')
        if c == 'ا' and i > 0 and v and not (KASRA in m and i == 1):
            issues.append(f'{word}: vowel on a long alif')
    return issues


def unmarked(word):
    """Letters that should carry a mark in full diacritization but do not."""
    lets = letters(word)
    miss = []
    base = strip(word)
    for i, (c, m) in enumerate(lets):
        if m:
            continue
        prev = lets[i - 1] if i else ('', '')
        nxt = lets[i + 1] if i + 1 < len(lets) else ('', '')
        if c in 'اىآ':
            continue
        if c == 'ة' and i == len(lets) - 1:
            continue                                     # pause form allowed at the end
        if c == 'و' and (DAMMA in prev[1] or (i == len(lets) - 2 and nxt[0] == 'ا')):
            continue                                     # long u, or waw of the plural before silent alif
        if c == 'ي' and KASRA in prev[1]:
            continue                                     # long i
        if c == 'و' and base.startswith('أولئك') and i == 1:
            continue
        if c == 'ل' and prev[0] == 'ا' and (i == 1 or (i == 2 and lets[0][0] in 'وفبكل')):
            continue                                     # lam of the article: assimilated, or moon-letter sukun (optional)
        if c == 'ل' and i >= 1 and lets[i - 1][0] == 'ل' and i <= 2:
            continue                                     # للـ
        miss.append(f'{c}@{i + 1}')
    return miss


def grammar(words):
    """Heuristic case-ending checks over a list of diacritized Arabic words. Warnings only."""
    out = []
    bare = [strip(w) for w in words]
    for i in range(len(words) - 1):
        b, nxt, nb = bare[i], words[i + 1], bare[i + 1]
        if nb in NO_CASE or len(nb) < 3:
            continue
        mark, where = case_mark(nxt)
        if not mark:
            continue
        if b in PREPOSITIONS:
            if DAMMA in mark or DAMMATAN in mark or FATHATAN in mark:
                out.append(f'after «{b}» expected genitive (kasra) on «{nxt}»')
            elif FATHA in mark and nb[-1] in 'ةء' :
                out.append(f'after «{b}» expected genitive (kasra) on «{nxt}»')
            # plain fatha elsewhere is allowed: sound plural/dual -ِينَ -َيْنِ, or a diptote (ممنوع من الصرف)
        if b in INNA and (DAMMA in mark or DAMMATAN in mark) and where == 'final' and not nb.endswith(('ون', 'ان')):
            out.append(f'after «{b}» expected accusative (fatha) on «{nxt}»')
        if b == 'لم' and (DAMMA in mark) and where == 'final':
            out.append(f'after «لم» expected jussive (sukun / dropped ending) on «{nxt}»')
        if b == 'لن' and (DAMMA in mark) and where == 'final':
            out.append(f'after «لن» expected subjunctive (fatha) on «{nxt}»')
    # attached prepositions on definite nouns: بال للـ كال
    for w, b in zip(words, bare):
        pre, stem = split_prefix(b)
        if pre and pre[-2:] == 'ال' and pre[:-2] and pre[:-2][-1] in 'بلك' and len(stem) >= 3:
            mark, where = case_mark(w)
            if where == 'final' and (DAMMA in mark or (FATHA in mark and not b.endswith(('ين', 'ات')))):
                out.append(f'«{w}» has an attached preposition but no genitive ending')
    return out


def compare_author(orig_word, prop_word):
    """Marks the author wrote that the proposal changes (adding marks is fine, changing them is not)."""
    lo, lp = letters(orig_word), letters(prop_word)
    out = []
    for (c, mo), (_, mp) in zip(lo, lp):
        for x in mo:
            if x == SUKUN and not mp:
                continue
            if x not in mp:
                out.append(f'«{orig_word}» → «{prop_word}»: author wrote {name(x)} on «{c}»')
                break
    return out


def name(x):
    return {FATHA: 'fatha', DAMMA: 'damma', KASRA: 'kasra', SUKUN: 'sukun', SHADDA: 'shadda', FATHATAN: 'fathatan',
            KASRATAN: 'kasratan', DAMMATAN: 'dammatan'}.get(x, repr(x))


def catt_diff(prop_word, catt_word):
    lp, lc = letters(prop_word), letters(catt_word)
    if len(lp) != len(lc):
        return True
    for (c, a), (_, b) in zip(lp, lc):
        a2, b2 = a.replace(SUKUN, ''), b.replace(SUKUN, '')
        if a2 and b2 and a2 != b2:
            return True
    return False


def build_line(original, proposal, catt=None, protected=None, on_conflict='author'):
    """Return dict(tts, status, issues[]) for one line."""
    issues = []
    src = proposal if proposal is not None else catt
    if src is None:
        return dict(tts=original, status='FAIL', issues=[('FAIL', 'nothing', 'no proposal and no CATT output')])
    if proposal is None:
        issues.append(('REVIEW', 'fallback', 'no reviewed proposal; using CATT output'))
    if strip(src).replace('ـ', '') != strip(original).replace('ـ', ''):
        a, b = strip(original), strip(src)
        k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
        issues.append(('FAIL', 'skeleton', f'letters differ from the original near «{a[max(0, k - 8):k + 8]}» vs «{b[max(0, k - 8):k + 8]}»'))
        return dict(tts=original, status='FAIL', issues=issues)
    ot, pt = tokens(original), tokens(src)
    words_o = [t for t in ot if is_arabic_word(t)]
    words_p = [t for t in pt if is_arabic_word(t)]
    out_tokens = list(pt)
    if len(words_o) != len(words_p):
        issues.append(('FAIL', 'skeleton', 'word boundaries differ from the original'))
        return dict(tts=original, status='FAIL', issues=issues)
    # author marks win unless told otherwise
    wi = 0
    for ti, t in enumerate(pt):
        if not is_arabic_word(t):
            continue
        conf = compare_author(words_o[wi], t)
        if conf:
            issues += [('REVIEW', 'author', c) for c in conf]
            if on_conflict == 'author':
                out_tokens[ti] = merge_author(words_o[wi], t)
        wi += 1
    tts = ''.join(out_tokens)
    words_t = [t for t in tokens(tts) if is_arabic_word(t)]
    for w in words_t:
        issues += [('FAIL', 'malformed', x) for x in well_formed(w)]
        miss = unmarked(w)
        if miss:
            issues.append(('REVIEW', 'coverage', f'«{w}» unmarked letters: {", ".join(miss)}'))
    issues += [('REVIEW', 'grammar', g) for g in grammar(words_t)]
    if protected:
        issues += [('REVIEW', 'protected', p) for p in protected(words_t)]
    if catt is not None and proposal is not None:
        cw = [t for t in tokens(catt) if is_arabic_word(t)]
        if len(cw) == len(words_t):
            d = [f'«{a}» / CATT «{b}»' for a, b in zip(words_t, cw) if catt_diff(a, b)]
            if d:
                issues.append(('INFO', 'catt', '; '.join(d)))
    status = 'FAIL' if any(s == 'FAIL' for s, _, _ in issues) else ('REVIEW' if any(s == 'REVIEW' for s, _, _ in issues) else 'PASS')
    return dict(tts=tts, status=status, issues=issues)


def merge_author(orig_word, prop_word):
    """Proposal marks, except on letters where the author wrote marks: there the author's marks are kept."""
    lo, lp = letters(orig_word), letters(prop_word)
    return rebuild([(c, mo if mo.replace(SUKUN, '') else mp) for (c, mo), (_, mp) in zip(lo, lp)])


def catt_batch(texts):
    """CATT run in an isolated interpreter path (audit tooling); returns None if unavailable."""
    try:
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        r = subprocess.run([sys.executable, os.path.join(here, 'catt_worker.py')], input=json.dumps(texts, ensure_ascii=False),
                           capture_output=True, text=True, timeout=600)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        print('CATT unavailable:', e, file=sys.stderr)
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('script'); ap.add_argument('proposals'); ap.add_argument('out')
    ap.add_argument('--text-key', default='d', help='field holding the script text the author wrote (keeps the author marks)')
    ap.add_argument('--on-conflict', default='author', choices=['author', 'proposal'])
    ap.add_argument('--lexicon', default=None)
    ap.add_argument('--no-catt', action='store_true')
    a = ap.parse_args(argv)
    lines = json.load(open(a.script))
    props = json.load(open(a.proposals))
    protected = None
    if a.lexicon:
        from .lexicon import Lexicon
        protected = Lexicon(a.lexicon).check_protected
    catt = None if a.no_catt else catt_batch([strip(l.get(a.text_key) or l['text']) for l in lines])
    out = []
    for i, l in enumerate(lines):
        orig = l.get(a.text_key) or l['text']
        r = build_line(orig, props.get(l['id']), catt[i] if catt else None, protected, a.on_conflict)
        out.append(dict(id=l['id'], original=orig, caption=l.get('text', orig), tts=r['tts'], status=r['status'],
                        issues=[dict(level=s, kind=k, msg=m) for s, k, m in r['issues']]))
    json.dump(out, open(a.out, 'w'), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(x['status'] for x in out))
    for x in out:
        for i in x['issues']:
            if i['level'] != 'INFO':
                print(x['id'], i['level'], i['kind'], i['msg'])


if __name__ == '__main__':
    main()
