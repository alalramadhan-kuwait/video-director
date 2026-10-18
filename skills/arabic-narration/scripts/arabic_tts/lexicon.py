"""Phase 2: configurable pronunciation lexicon (see lexicon.yaml for the format).

  python -m arabic_tts.lexicon apply LEXICON.yaml IN.json OUT.json [--text-key tts]   # writes the lexicon-adjusted text
  python -m arabic_tts.lexicon check LEXICON.yaml                                    # validates the file itself
"""
import re, sys, json, argparse
import yaml
from .arabic import (letters, rebuild, strip, tokens, is_arabic_word, split_prefix, normalize_bare,
                     PRONOUN_SUFFIXES, SHADDA, SUKUN, VOWELS, TANWEEN, SUN)

NUMBER_WORDS = {'ثلاث', 'ثلاثة', 'أربع', 'أربعة', 'خمس', 'خمسة', 'ست', 'ستة', 'سبع', 'سبعة', 'ثماني', 'ثمانية', 'تسع', 'تسعة',
                'عشر', 'عشرة', 'اثنتين', 'اثنتان', 'اثنين', 'اثنان'}


class Lexicon:
    def __init__(self, path):
        data = yaml.safe_load(open(path, encoding='utf-8'))
        self.entries = data['entries']
        self.by_bare = {}
        self.latin = []
        for e in self.entries:
            if re.search('[A-Za-z]', e['match']):
                self.latin.append(e)
            else:
                self.by_bare.setdefault(normalize_bare(e['match']), e)
        self.errors = self.validate()

    # ---- file validation -------------------------------------------------------------------------------------
    def validate(self):
        errs = []
        for e in self.entries:
            if 'stem' in e and strip(e['stem']) != e['match']:
                errs.append(f"{e['match']}: stem letters «{strip(e['stem'])}» differ from match")
            for c in e.get('contexts', []):
                if 'stem' in c and strip(c['stem']) != e['match']:
                    errs.append(f"{e['match']}: context stem «{c['stem']}» has different letters")
            if 'stem' not in e and 'spoken' not in e:
                errs.append(f"{e['match']}: needs stem or spoken")
        return errs

    # ---- matching ----------------------------------------------------------------------------------------------
    def lookup(self, word):
        """(entry, stem_start, stem_end) in letter indices of `word`, or None. Tries every split into proclitics
        (up to و/ف + ب/ل/ك + ال, or لل) + stem + clitic pronoun, and keeps the longest stem found in the lexicon."""
        b = strip(word)
        best = None
        sufs = [''] + [s for s in PRONOUN_SUFFIXES if b.endswith(s)]
        for suf in sufs:
            body = b[:len(b) - len(suf)] if suf else b
            for p in range(0, 5):
                stem = body[p:]
                if len(stem) < 3:
                    break
                pre = body[:p]
                if pre and not re.fullmatch('[وف]?[بلك]?(ال|ل)?', pre):
                    continue
                e = self.by_bare.get(normalize_bare(stem))
                if e and 'stem' in e and (best is None or len(stem) > best[2] - best[1]):
                    best = (e, p, p + len(stem))
        return best

    def rule(self, e, prev_b, next_b):
        for c in e.get('contexts', []):
            ok = True
            if 'prev' in c:
                ok &= prev_b is not None and normalize_bare(split_prefix(prev_b)[1]) in {normalize_bare(x) for x in c['prev']}
            if 'next' in c:
                ok &= next_b is not None and normalize_bare(split_prefix(next_b)[1]) in {normalize_bare(x) for x in c['next']}
            if c.get('prev_number'):
                ok &= prev_b is not None and (prev_b in NUMBER_WORDS or prev_b.isdigit())
            if ok:
                return c
        return None

    def apply_word(self, word, prev_b=None, next_b=None):
        m = self.lookup(word)
        if not m:
            return word, None
        e, s, t = m
        r = self.rule(e, prev_b, next_b)
        stem = (r or {}).get('stem', e['stem'])
        lw, ls = letters(word), letters(stem)
        new = list(lw)
        if e.get('plain'):
            # the engine reads this word better without diacritics: strip the stem's marks, keep the proclitics'
            for j in range(s, t):
                new[j] = (new[j][0], '')
            out = rebuild(new)
            return out, dict(term=e['match'], kind=e.get('kind'), rule=bool(r), before=word, after=out)
        for i, (c, mk) in enumerate(ls):
            j = s + i
            if j >= len(new):
                break
            last = (i == len(ls) - 1)
            if last and e.get('ending') != 'fixed':
                # keep the sentence's case vowel on the final letter; keep the lexicon's shadda/sukun-free stem marks
                sent = new[j][1]
                case = ''.join(x for x in sent if x in VOWELS | TANWEEN)
                base = mk.replace(SUKUN, '')
                base = ''.join(x for x in base if x not in VOWELS | TANWEEN) if case else base
                new[j] = (new[j][0], ''.join(sorted(base + case)))
            else:
                new[j] = (new[j][0], mk)
        # sun letter right after the article is geminated (السُّكَّرِيّ): keep that shadda
        if s >= 2 and strip(word)[s - 2:s] in ('ال', 'لل') and new[s][0] in SUN and SHADDA not in new[s][1]:
            new[s] = (new[s][0], ''.join(sorted(new[s][1] + SHADDA)))
        out = rebuild(new)
        return out, dict(term=e['match'], kind=e.get('kind'), rule=bool(r), before=word, after=out)

    def apply(self, text):
        toks = tokens(text)
        words = [i for i, t in enumerate(toks) if is_arabic_word(t)]
        changes = []
        for n, i in enumerate(words):
            prev_b = strip(toks[words[n - 1]]) if n else None
            next_b = strip(toks[words[n + 1]]) if n + 1 < len(words) else None
            new, ch = self.apply_word(toks[i], prev_b, next_b)
            if ch and new != toks[i]:
                changes.append(ch)
            toks[i] = new
        return ''.join(toks), changes

    def check_protected(self, words):
        """Phase 1 hook: protected terms diacritized differently from the lexicon (ignoring the case ending)."""
        out = []
        for n, w in enumerate(words):
            m = self.lookup(w)
            if not m or not m[0].get('protect'):
                continue
            e, s, t = m
            want, _ = self.apply_word(w, strip(words[n - 1]) if n else None, strip(words[n + 1]) if n + 1 < len(words) else None)
            if want != w:
                out.append(f'«{w}» should be «{want}» (lexicon: {e["match"]})')
        return out

    def risks(self, text):
        """avoid-patterns for terms present in `text` (used by Phase 3)."""
        out = []
        b = strip(text)
        for e in self.entries:
            if 'avoid' in e and normalize_bare(e['match']) in normalize_bare(b):
                out.append(dict(term=e['match'], **e['avoid']))
        return out

    def spoken(self, text):
        """Phase 4 hook: replace Latin terms/abbreviations with their spoken forms. Returns (text, changes)."""
        changes = []
        for e in sorted(self.latin, key=lambda e: -len(e['match'])):
            pat = re.compile(r'(?<![A-Za-z0-9])' + re.escape(e['match']) + r'(?![A-Za-z0-9])', re.I)
            if pat.search(text) and 'spoken' in e:
                text = pat.sub(e['spoken'], text)
                changes.append(dict(term=e['match'], spoken=e['spoken']))
        return text, changes


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd'); ap.add_argument('lexicon'); ap.add_argument('inp', nargs='?'); ap.add_argument('out', nargs='?')
    ap.add_argument('--text-key', default='tts')
    a = ap.parse_args(argv)
    lx = Lexicon(a.lexicon)
    if lx.errors:
        print('LEXICON ERRORS:', *lx.errors, sep='\n  ')
    if a.cmd == 'check':
        print(len(lx.entries), 'entries;', 'OK' if not lx.errors else f'{len(lx.errors)} errors')
        return
    items = json.load(open(a.inp))
    for it in items:
        new, ch = lx.apply(it[a.text_key])
        it['lexicon_changes'] = ch
        it[a.text_key] = new
        for c in ch:
            print(it['id'], c['term'], c['before'], '→', c['after'], '(context rule)' if c['rule'] else '')
    json.dump(items, open(a.out, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
