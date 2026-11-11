"""A take through the ElevenLabs connector (the owner, 10 Nov 2026: «yes», to this route, after «the connector of 11
labs will work in this chat»): record_flow.py --prepare runs the whole gate and writes what the voice must get, with
no call; --import takes the connector's audio back only through a passed gate on the same script."""
from tests import _guard  # noqa: F401
import json
import math
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from tools import record_flow

WORDS = ['ساعة', 'بدون', 'بطارية', 'تمشي', 'طول', 'اليوم', 'فيها', 'دقات']
CLEAN = [{'n': 1, 'text': 'ساعة بدون بطارية'}, {'n': 2, 'text': 'تمشي طول اليوم'}]


def script(d: Path, lines, kw_ok=WORDS) -> Path:
    (d / 's.json').write_text(json.dumps({'lines': lines, 'kw_ok': kw_ok, 'rules_ok': []}, ensure_ascii=False), encoding='utf-8')
    return d / 's.json'


class Prepare(unittest.TestCase):
    def prepare(self, lines, *extra):
        d = Path(tempfile.mkdtemp())
        s = script(d, lines)
        with mock.patch.object(record_flow, 'speak', side_effect=RuntimeError('PAID')) as sp:
            rc = record_flow.main([str(s), '--voice', 'x', '--model', 'eleven_v3', '--prepare', str(d / 'p'), *extra])
        return d, rc, sp.called

    def test_prepare_writes_the_take_and_pays_nothing(self):
        d, rc, paid = self.prepare(CLEAN)
        self.assertEqual(rc, 0); self.assertFalse(paid)
        take = json.loads((d / 'p' / 'take.json').read_text(encoding='utf-8'))
        gate = json.loads((d / 'p' / 'gate.json').read_text(encoding='utf-8'))
        self.assertEqual(take, {'text': 'ساعة بدون بطارية. تمشي طول اليوم.', 'voice_id': 'x', 'model_id': 'eleven_v3'})
        self.assertTrue(gate['passed']); self.assertEqual(gate['route'], 'connector')
        self.assertEqual(gate['script_hash'], record_flow.script_hash(record_flow.load(str(d / 's.json'))[0]))
        for k in ('settings', 'voice_id', 'model_id', 'prepared_at'): self.assertIn(k, gate)

    def test_prepare_refuses_when_the_voice_gate_fails(self):
        d, rc, paid = self.prepare([{'n': 1, 'text': 'ساعة بدون بطارية', 'say': 'ساعة فيها 8 دقات'}])
        self.assertEqual(rc, 5); self.assertFalse(paid)
        self.assertFalse((d / 'p' / 'take.json').exists()); self.assertFalse((d / 'p' / 'gate.json').exists())

    def test_prepare_keeps_the_override_rule(self):
        d, rc, paid = self.prepare(CLEAN, '--rules-ok')
        self.assertEqual(rc, 6); self.assertFalse(paid); self.assertFalse((d / 'p').exists())


class Import(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.s = script(self.d, CLEAN)
        self.audio = self.d / 'take.mp3'; self.audio.write_bytes(b'not really audio')

    def imp(self):
        with mock.patch.object(record_flow, 'speak', side_effect=RuntimeError('PAID')) as sp, \
             mock.patch.object(record_flow, 'transcribe', return_value=None):
            rc = record_flow.main([str(self.s), str(self.d / 'v'), '--import', str(self.audio), '--from', str(self.d / 'p')])
        self.assertFalse(sp.called)
        return rc

    def test_import_refuses_without_a_gate(self):
        self.assertEqual(self.imp(), 7); self.assertFalse((self.d / 'v').exists())

    def test_import_refuses_a_changed_script(self):
        self.assertEqual(record_flow.main([str(self.s), '--voice', 'x', '--prepare', str(self.d / 'p')]), 0)
        script(self.d, [{'n': 1, 'text': 'ساعة بدون بطارية'}, {'n': 2, 'text': 'تمشي بدون بطارية'}])
        self.assertEqual(self.imp(), 7); self.assertFalse((self.d / 'v').exists())

    def test_import_refuses_a_failed_gate(self):
        self.assertEqual(record_flow.main([str(self.s), '--voice', 'x', '--prepare', str(self.d / 'p')]), 0)
        g = self.d / 'p' / 'gate.json'
        g.write_text(json.dumps({**json.loads(g.read_text(encoding='utf-8')), 'passed': False}), encoding='utf-8')
        self.assertEqual(self.imp(), 7)

    def test_import_refuses_audio_that_reads_another_text(self):
        record_flow.main([str(self.s), '--voice', 'x', '--prepare', str(self.d / 'p')])
        with mock.patch.object(record_flow, 'pcm', return_value=b'\0\0' * 24000), \
             mock.patch.object(record_flow, 'transcribe', return_value=[{'word': 'مرحبا', 'start': 0, 'end': .5},
                                                                         {'word': 'كيفكم', 'start': .5, 'end': 1}]):
            rc = record_flow.main([str(self.s), str(self.d / 'v'), '--import', str(self.audio), '--from', str(self.d / 'p')])
        self.assertEqual(rc, 8); self.assertFalse((self.d / 'v').exists())

    def test_whisper_words_place_the_cut(self):
        text, spans = record_flow.paragraph(['ساعة بدون بطارية', 'تمشي طول اليوم'])
        words = [{'word': w, 'start': i * .5, 'end': i * .5 + .4} for i, w in enumerate(['ساعه', 'بدون', 'بطاريه'])] + \
                [{'word': w, 'start': 2 + i * .5, 'end': 2.4 + i * .5} for i, w in enumerate(['تمشي', 'طول', 'اليوم'])]
        self.assertEqual(record_flow.cuts_by_words(text, spans, words, 3.5), [(0.0, 1.7), (1.7, 3.5)])

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg')
    def test_import_cuts_at_the_silence_without_whisper(self):
        record_flow.main([str(self.s), '--voice', 'x', '--prepare', str(self.d / 'p')])
        self.audio = self.d / 'take.wav'
        tone = lambda sec: b''.join(struct.pack('<h', int(8000 * math.sin(2 * math.pi * 220 * i / 24000))) for i in range(int(sec * 24000)))
        with wave.open(str(self.audio), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
            w.writeframes(tone(1.0) + b'\0\0' * 12000 + tone(1.0))
        self.assertEqual(self.imp(), 0)
        l1 = json.loads((self.d / 'v' / 'l1.json').read_text(encoding='utf-8'))
        self.assertEqual(l1['via'], 'connector'); self.assertEqual(l1['cut_by'], 'silences')
        self.assertAlmostEqual(l1['to'], 1.25, delta=.05)
        gate = json.loads((self.d / 'v' / 'gate.json').read_text(encoding='utf-8'))
        self.assertTrue(gate['passed']); self.assertEqual(gate['imported'], 'take.wav')
        self.assertTrue((self.d / 'v' / 'l2.wav').exists()); self.assertTrue((self.d / 'v' / 'raw' / 'whole.wav').exists())


if __name__ == '__main__':
    unittest.main()
