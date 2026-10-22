"""The optional voice helper must preserve text and takes without requiring ML packages."""
from tests import _guard  # noqa: F401
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/arabic-narration/scripts/omnivoice_narrate.py'
spec = importlib.util.spec_from_file_location('omnivoice_narrate', SCRIPT)
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)


class TestOmniVoicePlugin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / 'script.json'
        self.texts = ['قَبْلَ أن تصبح بانيراي ساعةً فاخرة.', 'بدأت الحكاية في فلورنسا.']
        self.script.write_text(json.dumps({'lines': self.texts}, ensure_ascii=False))
        self.args = voice.parser().parse_args(['--script', str(self.script), '--output', str(self.root/'take.wav')])

    def test_plan_preserves_approved_text_and_natural_speed(self):
        self.args.plan = True
        plan = voice.generate(self.args)
        self.assertEqual(plan['text'], '\n'.join(self.texts))
        self.assertEqual(plan['speed'], 1.0)
        self.assertEqual(plan['language'], 'arb')
        self.assertEqual(plan['provider'], 'omnivoice')
        self.assertEqual(plan['status'], 'candidate')
        self.assertFalse(self.args.output.exists())

    def test_record_list_input(self):
        self.script.write_text(json.dumps([{'id': str(i), 'text': t} for i,t in enumerate(self.texts)]))
        self.assertEqual(voice.read_script(self.script), '\n'.join(self.texts))

    def test_rejects_invalid_input_before_loading_model(self):
        for value in ({}, {'lines': []}, {'lines': [None]}, {'lines': ['']}):
            with self.subTest(value=value):
                self.script.write_text(json.dumps(value))
                with self.assertRaises(ValueError): voice.generate(self.args)

    def test_never_overwrites_an_existing_take(self):
        self.args.output.write_bytes(b'approved recording')
        with self.assertRaises(FileExistsError): voice.generate(self.args)
        self.assertEqual(self.args.output.read_bytes(), b'approved recording')

    def test_existing_metadata_also_reserves_a_take(self):
        self.args.output.with_suffix('.json').write_text('{}')
        with self.assertRaises(FileExistsError): voice.generate(self.args)
        self.assertFalse(self.args.output.exists())

    def test_synthesis_passes_script_and_records_provenance(self):
        model = Mock(sampling_rate=24000)
        model.generate.return_value = [np.full(2400, 0.1)]
        factory = Mock(return_value=model)
        torch = SimpleNamespace(manual_seed=Mock(), float32='float32', float16='float16',
                                cuda=SimpleNamespace(is_available=lambda: False),
                                backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)))
        def write(path, audio, rate, subtype):
            Path(path).write_bytes(b'fake WAV from injected model')
        modules = {'torch': torch, 'soundfile': SimpleNamespace(write=write),
                   'omnivoice': SimpleNamespace(OmniVoice=SimpleNamespace(from_pretrained=factory))}
        with patch.dict('sys.modules', modules):
            result = voice.generate(self.args)
        factory.assert_called_once_with(voice.MODEL, device_map='mps', dtype='float16')
        self.assertEqual(model.generate.call_args.kwargs['text'], '\n'.join(self.texts))
        self.assertEqual(model.generate.call_args.kwargs['speed'], 1.0)
        self.assertEqual(model.generate.call_args.kwargs['language'], 'arb')
        self.assertEqual(result['seconds'], 0.1)
        self.assertEqual(json.loads(self.args.output.with_suffix('.json').read_text()), result)
        self.assertTrue(result['audio_sha256'])

    def test_skill_copies_match(self):
        for name in ['arabic-narration', 'video-director']:
            source = ROOT / 'skills' / name
            target = ROOT / '.claude/skills' / name
            for p in source.rglob('*'):
                if p.is_file() and '__pycache__' not in p.parts:
                    self.assertEqual(p.read_bytes(), (target / p.relative_to(source)).read_bytes(), str(p))
