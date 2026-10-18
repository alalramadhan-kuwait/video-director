"""Phase 1 safeguard tests: each injected error must be caught at the right level."""
from arabic_tts.diacritize import build_line

ORIG = 'الأطفال كانوا يتحسنون بحقنة صغيرة من الإنسولين.'
GOOD = 'الأَطْفَالُ كَانُوا يَتَحَسَّنُونَ بِحُقْنَةٍ صَغِيرَةٍ مِنَ الإِنْسُولِينِ.'

def kinds(r): return {(s, k) for s, k, _ in r['issues']}

def test_good_passes():
    r = build_line(ORIG, GOOD); assert r['status'] == 'PASS', r['issues']; assert r['tts'] == GOOD

def test_changed_word_fails():          # a medical term respelled (إنسولين → أنسولين)
    r = build_line(ORIG, GOOD.replace('الإِنْسُولِينِ', 'الأَنْسُولِينِ')); assert ('FAIL', 'skeleton') in kinds(r); assert r['tts'] == ORIG

def test_added_word_fails():
    r = build_line(ORIG, GOOD.replace('صَغِيرَةٍ', 'صَغِيرَةٍ جِدًّا')); assert r['status'] == 'FAIL'

def test_two_vowels_fails():
    r = build_line(ORIG, GOOD.replace('صَغِيرَةٍ', 'صَغِيَرَةٍ'.replace('يَ', 'يَِ'))); assert ('FAIL', 'malformed') in kinds(r)

def test_tanween_mid_word_fails():
    r = build_line(ORIG, GOOD.replace('صَغِيرَةٍ', 'صًغِيرَةٍ')); assert ('FAIL', 'malformed') in kinds(r)

def test_genitive_after_preposition_flagged():
    r = build_line(ORIG, GOOD.replace('مِنَ الإِنْسُولِينِ', 'مِنَ الإِنْسُولِينُ')); assert ('REVIEW', 'grammar') in kinds(r)

def test_attached_preposition_flagged():
    o = 'شرب كوبا بالماء.'; r = build_line(o, 'شَرِبَ كُوبًا بِالمَاءُ.'); assert ('REVIEW', 'grammar') in kinds(r)

def test_inna_accusative_flagged():
    o = 'إن العلاج طويل.'; r = build_line(o, 'إِنَّ العِلَاجُ طَوِيلٌ.'); assert ('REVIEW', 'grammar') in kinds(r)

def test_lam_jussive_flagged():
    o = 'لم يستجب جسمه.'; r = build_line(o, 'لَمْ يَسْتَجِيبُ جِسْمُهُ.'.replace('يَسْتَجِيبُ', 'يَسْتَجِبُ')); assert ('REVIEW', 'grammar') in kinds(r)

def test_missing_marks_flagged():
    r = build_line(ORIG, GOOD.replace('صَغِيرَةٍ', 'صغيرة')); assert ('REVIEW', 'coverage') in kinds(r)

def test_author_mark_kept_and_flagged():
    o = 'تسجيل طَرِيقَتَهُما'; r = build_line(o, 'تَسْجِيلَ طَرِيقَتِهِمَا')
    assert ('REVIEW', 'author') in kinds(r); assert 'طَرِيقَتَهُمَا' in r['tts'] or 'طَرِيقَتَهُما' in r['tts']

def test_author_conflict_proposal_policy():
    o = 'تسجيل طَرِيقَتَهُما'; r = build_line(o, 'تَسْجِيلَ طَرِيقَتِهِمَا', on_conflict='proposal'); assert 'طَرِيقَتِهِمَا' in r['tts']

def test_fathatan_on_alif_equivalent():
    o = 'كان مرضاً واحداً.'; r = build_line(o, 'كَانَ مَرَضًا وَاحِدًا.'); assert ('REVIEW', 'author') not in kinds(r), r['issues']

def test_catt_fallback_is_review():
    r = build_line(ORIG, None, catt=GOOD); assert r['status'] == 'REVIEW' and ('REVIEW', 'fallback') in kinds(r)

if __name__ == '__main__':
    import sys; fails = 0
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            try: f(); print('ok  ', n)
            except AssertionError as e: fails += 1; print('FAIL', n, e)
    sys.exit(1 if fails else 0)
