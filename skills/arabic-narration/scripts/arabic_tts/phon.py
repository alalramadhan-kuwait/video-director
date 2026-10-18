# Coarse phoneme utilities: expected sequence from fully-diacritized Arabic, and normalization of recognizer IPA
import re
F, K, D, SUK, SH = 'َ', 'ِ', 'ُ', 'ْ', 'ّ'
TAN = {'ً': 'an', 'ٍ': 'in', 'ٌ': 'un'}
V = {F: 'a', K: 'i', D: 'u'}
C = dict(zip('بتثجحخدذرزسشصضطظعغفقكلمنهوي', 'b t θ ʒ ħ x d ð r z s ʃ s d t ð ʕ ɣ f q k l m n h w j'.split()))
for h in 'أإؤئء': C[h] = 'ʔ'
SUN = set('تثدذرزسشصضطظلن')
AR = re.compile(r'[ء-يً-ْٰ]+')
def word_ph(w, initial, final):
    out = []; i = 0; n = len(w)
    def nxt_diac(j):
        d = ''; j += 1
        while j < n and w[j] in 'ًٌٍَُِّْٰ': d += w[j]; j += 1
        return d, j
    while i < n:
        ch = w[i]; d, j = nxt_diac(i)
        if ch == 'ا':
            if i == 0:                                   # hamzat wasl
                if initial:
                    out += ['ʔ', 'a' if (n > 1 and w[1] == 'ل') else ('u' if D in w[2:5] and w.find(D) < 5 else 'i')]
            elif i == 1 and w[0] in 'وفبل' and n > 2:    # prefix + wasl (وَاسْتَخْدَمَ)
                pass
            elif d and K in d: out.append('i')            # الِاخْتِبَار: kasra on wasl alif
            i = j; continue
        if ch in 'ىٰ' or ch == 'ٰ': i = j; continue
        if ch == 'آ': out += ['ʔ', 'a']; i = j; continue
        if ch == 'ة':
            if d and not final: out.append('t')
            v = [V[c] for c in d if c in V] + [TAN[c] for c in d if c in TAN]
            if v and not final: out += list(v[0])
            i = j; continue
        if ch == 'ل' and i >= 1 and w[i-1] == 'ا' and (i == 1 or (i == 2 and w[0] in 'وفبلك')) and j < n and w[j] in SUN and not d:
            i = j; continue                              # sun-letter assimilation
        if ch in ('و', 'ي') and not d and out and out[-1] in ('u', 'i', 'a'):
            i = j; continue                              # long vowel letter
        if ch not in C: i = j; continue
        c = C[ch]; out.append(c)
        if SH in d: out.append(c)
        last = (j >= n) or all(x in 'اى' for x in w[j:])
        for x in d:
            if x in V:
                if not (final and last): out.append(V[x])
            elif x in TAN:
                if final and last: (out.append('a') if x == 'ً' else None)
                else: out += list(TAN[x])
        if ch == 'ا': pass
        i = j
    return out
def expected(text):
    """text -> list of (word, phonemes) for Arabic words; pause (waqf) at punctuation/end"""
    toks = re.findall(r'[ء-يً-ْٰ]+|[^\sء-ْٰ]+', text)
    res = []; first = True
    for k, t in enumerate(toks):
        if not AR.fullmatch(t): first = first or bool(re.search(r'[.,،؟?!…:;«»]', t)); continue
        nxt = toks[k+1] if k + 1 < len(toks) else '.'
        final = not AR.fullmatch(nxt) and bool(re.search(r'[.,،؟?!…:;»]', nxt)) or k + 1 == len(toks)
        res.append((t, word_ph(t, first, final))); first = False
    return res
RMAP = [('dʒ','ʒ'),('tʃ','ʃ'),('ɡ','ʒ'),('dˤ','d'),('ɾ','r'),('ɹ','r'),('ʁ','ɣ'),('χ','x'),('ɫ','l'),('ç','x'),('ɦ','h'),('c','k'),('ɟ','ʒ')]
VA = set('a ɑ æ ɐ ä ʌ ɒ'.split()); VI = set('i ɪ e ɛ ᵻ ɨ'.split()); VU = set('u ʊ o ɔ ɵ ɯ ʉ'.split())
def norm_rec(ph):
    out = []
    for p in ph.split():
        p = re.sub(r'[0-9ˤʲ\[\]\.]', '', p).replace('ː', '').replace('̃', '').replace('̞', '')
        for a, b in RMAP: p = p.replace(a, b)
        for c in (p if len(p) > 0 else ''):
            if c in VA: out.append('a')
            elif c in VI: out.append('i')
            elif c in VU: out.append('u')
            elif c == 'ə': out.append('ə')
            elif c in 'bθʒħxdðrzsʃtʕɣfqklmnhwjʔpvy': out.append({'p':'b','v':'f','y':'i'}.get(c, c))
    # merge doubled vowels (length)
    m = []
    for c in out:
        if m and c == m[-1] and c in 'aiuə': continue
        m.append(c)
    return m
def cost(a, b):
    if a == b: return 0
    if 'ə' in (a, b) and (a in 'aiuə' and b in 'aiuə'): return 0.5
    if {a, b} <= {'k', 'q'} or {a, b} <= {'h', 'ħ'} or {a, b} <= {'ʔ', 'ʕ'} or {a, b} <= {'s', 'z'} or {a, b} <= {'ð', 'z', 'd'}: return 0.5
    return 1
def local(E, R):
    """semi-global alignment: best window of R matching E. returns (dist, window, ops)"""
    n, m = len(E), len(R)
    INF = 1e9; Dm = [[0.0] * (m + 1)] + [[0.0] * (m + 1) for _ in range(n)]
    for i in range(1, n + 1): Dm[i][0] = i
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            Dm[i][j] = min(Dm[i-1][j-1] + cost(E[i-1], R[j-1]), Dm[i-1][j] + 1, Dm[i][j-1] + 1)
    j = min(range(m + 1), key=lambda j: Dm[n][j]); best = Dm[n][j]
    i, jj = n, j; ops = []
    while i > 0:
        if jj > 0 and Dm[i][jj] == Dm[i-1][jj-1] + cost(E[i-1], R[jj-1]): ops.append((E[i-1], R[jj-1])); i -= 1; jj -= 1
        elif Dm[i][jj] == Dm[i-1][jj] + 1: ops.append((E[i-1], None)); i -= 1
        else: ops.append((None, R[jj-1])); jj -= 1
    return best, R[jj:j], ops[::-1]
def vowel_errs(ops):
    tot = sum(1 for e, r in ops if e in ('a', 'i', 'u')); bad = sum(1 for e, r in ops if e in ('a', 'i', 'u') and r != e and r != 'ə')
    return tot, bad
