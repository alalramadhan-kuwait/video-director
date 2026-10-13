"""Arabic text utilities shared by every phase: diacritic parsing, skeletons, tokens and affixes."""
import re

FATHA, DAMMA, KASRA, SUKUN, SHADDA = 'َ', 'ُ', 'ِ', 'ْ', 'ّ'
FATHATAN, DAMMATAN, KASRATAN, DAGGER = 'ً', 'ٌ', 'ٍ', 'ٰ'
VOWELS = {FATHA, DAMMA, KASRA}
TANWEEN = {FATHATAN, DAMMATAN, KASRATAN}
MARKS = VOWELS | TANWEEN | {SUKUN, SHADDA, DAGGER}
TATWEEL = 'ـ'
LETTERS = set('ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوىي')
SUN = set('تثدذرزسشصضطظلن')
ARABIC_WORD = re.compile(r'[ء-يً-ْٰـ]+')
DIAC_RE = re.compile('[ً-ْٰـ]')
# clitic pronouns that carry their own vowel after the case ending
PRONOUN_SUFFIXES = ('هما', 'هم', 'هن', 'ها', 'ه', 'كما', 'كم', 'كن', 'ك', 'نا', 'ي')


def strip(s):
    return DIAC_RE.sub('', s)


def is_arabic_word(tok):
    return bool(ARABIC_WORD.fullmatch(tok))


def tokens(text):
    """Split into Arabic words and everything else, keeping every character (join(tokens) == text)."""
    return re.findall(r'[ء-يً-ْٰـ]+|[^ء-يً-ْٰـ]+', text)


def letters(word):
    """[(letter, marks)] for one word; marks are canonical (sorted, fathatan moved off a trailing alif)."""
    out = []
    for ch in word:
        if ch == TATWEEL:
            continue
        if ch in MARKS:
            if out:
                out[-1][1] += ch
            continue
        out.append([ch, ''])
    # fathatan written on the alif after the letter (واحداً) is the same as on the letter (وَاحِدًا)
    for i in range(1, len(out)):
        if out[i][0] in 'اى' and FATHATAN in out[i][1]:
            out[i][1] = out[i][1].replace(FATHATAN, '')
            if FATHATAN not in out[i - 1][1]:
                out[i - 1][1] += FATHATAN
    return [(c, ''.join(sorted(m))) for c, m in out]


def rebuild(lets):
    return ''.join(c + m for c, m in lets)


def case_mark(word):
    """The mark on the case-bearing letter: last letter, skipping a clitic pronoun and a silent final alif."""
    lets = letters(word)
    base = strip(word)
    for suf in PRONOUN_SUFFIXES:
        if len(base) > len(suf) + 1 and base.endswith(suf):
            idx = len(base) - len(suf) - 1
            return lets[idx][1], 'before-pronoun'
    idx = len(lets) - 1
    if lets[idx][0] in 'ا' and idx > 0:
        idx -= 1
    return lets[idx][1], 'final'


def split_prefix(base):
    """Split a bare word into (proclitics, stem) for و ف ب ل ك + ال. Conservative: only splits when the
    remainder is at least 3 letters."""
    pre = ''
    rest = base
    if len(rest) > 3 and rest[0] in 'وف':
        pre, rest = pre + rest[0], rest[1:]
    if len(rest) > 3 and rest[0] in 'بلك' and (rest[1:3] == 'ال' or rest[0] == 'ب'):
        pre, rest = pre + rest[0], rest[1:]
    if rest.startswith('لل') and len(rest) > 4:
        pre, rest = pre + 'ل', 'ا' + rest[1:]   # لل = ل + ال with the alif dropped in writing
    if rest.startswith('ال') and len(rest) > 3:
        pre, rest = pre + 'ال', rest[2:]
    return pre, rest


def normalize_bare(s):
    s = strip(s)
    s = re.sub('[إأآا]', 'ا', s)
    return s.replace('ة', 'ه').replace('ى', 'ي')
