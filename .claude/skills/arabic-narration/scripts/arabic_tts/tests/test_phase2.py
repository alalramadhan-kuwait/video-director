"""Phase 2 lexicon tests."""
import tempfile, os
from arabic_tts.lexicon import Lexicon
from arabic_tts.diacritize import build_line
LX = Lexicon(os.path.join(os.path.dirname(__file__), '..', 'examples', 'diabetes-lexicon.yaml'))

def test_file_valid(): assert LX.errors == []

def test_bad_entry_detected():
    f = tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False, encoding='utf-8')
    f.write('entries:\n  - match: هرمون\n    stem: هُرْمُونَة\n'); f.close()
    assert Lexicon(f.name).errors

def test_medical_stem_applied():
    assert 'هُرْمُون' in LX.apply('أن الإنسولين هرمون مهم')[0]

def test_case_ending_kept_from_sentence():
    out = LX.apply('مِنَ الإِنْسُولِينِ')[0]; assert out.endswith('ينِ'), out
    out = LX.apply('الإِنْسُولِينُ هُرْمُونٌ')[0]; assert 'ينُ' in out and 'هُرْمُونٌ' in out, out

def test_pronoun_suffix_keeps_stem_and_case():
    out = LX.apply('ويبقى سُكَّرُهُمْ مرتفعا')[0]; assert 'سُكَّرُهُمْ' in out, out

def test_context_rule_plural_after_number():
    assert 'حُقَن' in LX.apply('ثلاث حقن في اليوم')[0]
    assert 'حَقْن' in LX.apply('عملية حقن الدواء')[0]

def test_sun_letter_gemination_kept():
    assert LX.apply('والسكري')[0] == 'والسُّكَّرِيّ'

def test_protected_mismatch_flagged_in_phase1():
    r = build_line('أن الإنسولين هرمون', 'أَنَّ الإِنْسُولِينَ هَرَمُونٌ', protected=LX.check_protected)
    assert any(k == 'protected' for _, k, _ in r['issues']), r['issues']

def test_protected_match_passes():
    r = build_line('أن الإنسولين هرمون', 'أَنَّ الإِنْسُولِينَ هُرْمُونٌ', protected=LX.check_protected)
    assert not any(k == 'protected' for _, k, _ in r['issues']), r['issues']

def test_spoken_abbreviation_whole_word_only():
    assert LX.spoken('الحمض DNA مهم')[0] == 'الحمض دِي إِنْ إِيه مهم'
    assert LX.spoken('DNAse')[0] == 'DNAse'

def test_risks_listed():
    assert LX.risks('من الإنسولين')[0]['term'] == 'إنسولين' and not LX.risks('من الماء')

def test_unknown_words_untouched():
    t = 'ذَهَبَ الطَّالِبُ إِلَى المَدْرَسَةِ.'; assert LX.apply(t)[0] == t

if __name__ == '__main__':
    import sys; fails = 0
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            try: f(); print('ok  ', n)
            except AssertionError as e: fails += 1; print('FAIL', n, e)
    sys.exit(1 if fails else 0)
