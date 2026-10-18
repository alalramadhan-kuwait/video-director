"""Phase 4 text preprocessing tests (the audio side of short lines is tested on the benchmark)."""
import os
from arabic_tts.preprocess import preprocess, year_genitive, is_short
from arabic_tts.lexicon import Lexicon
LX = Lexicon(os.path.join(os.path.dirname(__file__), '..', 'examples', 'diabetes-lexicon.yaml'))

def test_years_genitive():
    assert year_genitive(1936) == 'أَلْفٍ وَتِسْعِمِئَةٍ وَسِتَّةٍ وَثَلَاثِينَ'
    assert year_genitive(1977) == 'أَلْفٍ وَتِسْعِمِئَةٍ وَسَبْعَةٍ وَسَبْعِينَ'
    assert year_genitive(2001) == 'أَلْفَيْنِ وَوَاحِدٍ'
    assert year_genitive(1912) == 'أَلْفٍ وَتِسْعِمِئَةٍ وَاثْنَيْ عَشَرَ'

def test_year_after_diacritized_cue():
    r = preprocess('فِي عَامِ 1936 نُشِرَ البَحْثُ.'); assert '1936' not in r['tts'] and not r['flags']

def test_other_numbers_flagged_not_guessed():
    r = preprocess('تَنَاوَلَ 3 حُقَنٍ.'); assert '3' in r['tts'] and r['flags']

def test_abbreviation_spoken_caption_untouched():
    src = 'الحَمْضُ النَّوَوِيُّ DNA مُهِمٌّ.'
    r = preprocess(src, LX); assert 'دِي إِنْ إِيه' in r['tts'] and 'DNA' in src

def test_unknown_latin_flagged():
    r = preprocess('هذا XYZ مهم.', LX); assert any('Latin' in f for f in r['flags'])

def test_quotes_and_trailing_ellipsis():
    assert preprocess('«يَتْبَعُ…»')['tts'] == 'يَتْبَعُ.'

def test_inner_ellipsis_kept():
    t = 'كَيْفَ يَعْمَلُ… وَيَكَادُ يَفْشَلُ؟'; assert preprocess(t)['tts'] == t

def test_short_detection():
    assert is_short('يَتْبَعُ.') and not is_short('فَلَاحَظَ شَيْئًا غَرِيبًا.')

if __name__ == '__main__':
    import sys; fails = 0
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            try: f(); print('ok  ', n)
            except AssertionError as e: fails += 1; print('FAIL', n, e)
    sys.exit(1 if fails else 0)
